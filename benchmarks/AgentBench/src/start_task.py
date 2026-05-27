import argparse
import datetime
import os
import signal
import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

from src.configs import ConfigLoader

_procs = []  # all subprocesses started by this script
_log_files = []  # open log file handles, closed on shutdown

_LOG_DIR = Path(__file__).parent.parent.parent / "logs"  # skill-agent-dev/logs/


def _open_log(name: str, port: int):
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = _LOG_DIR / f"task_worker_{name}_{port}_{ts}.log"
    f = open(path, "w", buffering=1, encoding="utf-8")
    print(f"[start_task] worker log: {path}")
    _log_files.append(f)
    return f


def _start_worker(name, port, controller, definition):
    conf = definition[name]
    if "docker" in conf and "image" in conf["docker"]:
        docker = conf["docker"]
        project_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
        # Mount host gcloud credentials so Docker-based task workers can call Vertex AI
        gcloud_dir = os.path.expanduser("~/.config/gcloud")
        gcloud_args = []
        if os.path.exists(gcloud_dir):
            gcloud_args = [
                "-v", f"{gcloud_dir}:/root/.config/gcloud:ro",
                "-e", "GOOGLE_APPLICATION_CREDENTIALS=/root/.config/gcloud/application_default_credentials.json",
            ]
        proxy_args = []
        for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
                    "http_proxy", "https_proxy", "all_proxy", "no_proxy"):
            if os.environ.get(key):
                proxy_args.extend(["-e", key])
        # If data/ or outputs/ are symlinks, mounting only project_root leaves
        # them dangling inside the container, so bind-mount each symlink's real
        # target at its identical path.
        symlink_args = []
        for link in ("data", "outputs"):
            link_path = os.path.join(project_root, link)
            if os.path.islink(link_path):
                target = os.path.realpath(link_path)
                symlink_args.extend(["-v", f"{target}:{target}"])
        # Optionally mount a local models directory into the worker (only needed
        # when self-hosting model weights inside the container). Set via env var.
        models_args = []
        models_dir = os.environ.get("AGENTBENCH_MODELS_DIR")
        if models_dir:
            models_args.extend(["-v", f"{models_dir}:/root/models:ro"])
        log_f = _open_log(name, port)
        proc = subprocess.Popen(
            [
                "docker",
                "run",
                "--rm",
                "-p",
                f"{port}:{port}",
                "--add-host",
                "host.docker.internal:host-gateway",
                "-v",
                f"{project_root}:/root/workspace",
                "-w",
                "/root/workspace",
            ] + models_args + symlink_args + gcloud_args + proxy_args + [
                docker["image"],
                "bash",
                "-c",
                docker.get("command", "") + f" python -m src.server.task_worker {name}"
                                            f" --self http://localhost:{port}/api"
                                            f" --port {port}"
                                            f" --controller {controller.replace('localhost', 'host.docker.internal')}",
            ],
            stdout=log_f, stderr=log_f,
        )
    else:
        log_f = _open_log(name, port)
        proc = subprocess.Popen(
            [
                "python",
                "-m",
                "src.server.task_worker",
                name,
                "--self",
                f"http://localhost:{port}/api",
                "--port",
                str(port),
                "--controller",
                controller,
            ],
            stdout=log_f, stderr=log_f,
        )
    _procs.append(proc)


def _shutdown(signum=None, frame=None):
    for proc in _procs:
        try:
            proc.terminate()
        except Exception:
            pass
    for f in _log_files:
        try:
            f.close()
        except Exception:
            pass
    raise SystemExit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=str,
        help="Config file to load",
        default="configs/start_task.yaml",
    )
    parser.add_argument(
        "--start",
        "-s",
        dest="start",
        type=str,
        nargs="*",
        help="name num_worker name num_worker ...",
    )
    parser.add_argument("--controller", "-l", dest="controller_addr", default="")
    parser.add_argument(
        "--auto-controller", "-a", dest="controller", action="store_true"
    )
    parser.add_argument("--base-port", "-p", dest="port", type=int, default=5002)
    parser.add_argument("--controller-port", dest="controller_port", type=int, default=5001)

    args = parser.parse_args()

    config = ConfigLoader().load_from(args.config)

    if args.controller_port == 5001 and "controller_port" in config:
        args.controller_port = int(config["controller_port"])
    if args.port == 5002 and "base_port" in config:
        args.port = int(config["base_port"])

    root = os.path.dirname(os.path.abspath(__file__))

    # Resolve the controller URL (and its port) from, in priority order:
    #   -l/--controller  >  config["controller"]  >  --controller-port
    # so multiple runs can each use their own controller, e.g.
    #   -a -l http://localhost:5200/api --base-port 5201
    # (matching the MedAgentBench workflow), while the existing
    #   -a --controller-port 5080 --base-port 5081
    # invocation keeps working.
    if args.controller_addr:
        controller_addr = args.controller_addr
    elif "controller" in config:
        controller_addr = config["controller"]
    else:
        controller_addr = f"http://localhost:{args.controller_port}/api"
    controller_port = urlparse(controller_addr).port or args.controller_port

    if args.controller:
        # Reuse a controller already listening at this address; otherwise start one.
        try:
            requests.get(controller_addr + "/list_workers")
            print(f"Reusing controller at {controller_addr}")
        except Exception:
            print(f"Starting controller on port {controller_port}")
            proc = subprocess.Popen(
                ["python", "-m", "src.server.task_controller", "--port", str(controller_port)]
            )
            _procs.append(proc)
            for i in range(10):
                try:
                    requests.get(f"http://localhost:{controller_port}/api/list_workers")
                    break
                except Exception:
                    print("Waiting for controller to start...")
                    time.sleep(0.5)
            else:
                raise Exception("Controller failed to start")

    base_port = args.port

    if "start" in config.keys() and not args.start:
        for key, val in config.get("start", {}).items():
            for _ in range(val):
                _start_worker(key, base_port, controller_addr, config["definition"])
                base_port += 1

    n = len(args.start) if args.start else 0
    if n % 2 != 0:
        raise ValueError(
            "--start argument should strictly follow the format: name1 num1 name2 num2 ..."
        )
    for i in range(0, n, 2):
        for _ in range(int(args.start[i + 1])):
            _start_worker(args.start[i], base_port, controller_addr, config["definition"])
            base_port += 1

    while True:
        input()

# try: python start_task.py ../configs/server/test.yaml -a
