"""
Split OS Interaction data into dev / val / test sets for the skill cycle.

Data split:
  dev  (skill learning) — 60% of worlds 1-5, 7, stratified per world  (~81 samples)
  val  (monitoring)     — 40% of worlds 1-5, 7, stratified per world  (~54 samples)
  test (held-out)       — world 6 (9 samples) + dev.json (26 samples)  (35 samples)

dev.json is the original benchmark held-out set — kept as test.
World 6 is held out because its tasks (web scraping / HTTP) are structurally
different from the other worlds.

Dev and val are drawn from the same world distribution, making val a reliable
proxy for skill generalisation during the cycle.

Usage:
    python data/os_interaction/split_dataset.py

Outputs:
    data/os_interaction/split_dev.json
    data/os_interaction/split_val.json
    data/os_interaction/split_test.json
"""

import glob
import json
import os
import random
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
DATA_ROOT = REPO_ROOT / "data" / "os_interaction" / "data"
OUT_DIR = REPO_ROOT / "data" / "os_interaction"

SEED = 42
DEV_RATIO = 0.6


def _load_problems(problem_file: str, index_prefix: str):
    if problem_file.endswith(".json"):
        with open(problem_file, encoding="utf-8") as f:
            raw = json.load(f)
        items = raw if isinstance(raw, list) else [raw]
    elif problem_file.endswith(".jsonl"):
        with open(problem_file, encoding="utf-8") as f:
            items = [json.loads(line) for line in f if line.strip()]
    else:
        raise ValueError(f"Unsupported file format: {problem_file}")

    basename = os.path.basename(problem_file)
    basename = basename.removesuffix(".json").removesuffix(".jsonl")
    full_prefix = index_prefix + basename + "-"

    return [
        {"id": full_prefix + "%05d" % idx, "description": item.get("description", "")}
        for idx, item in enumerate(items)
    ]


def _collect_world(world_num: int) -> list:
    pattern = str(DATA_ROOT / str(world_num) / "*.json")
    files = sorted(glob.glob(pattern))
    prefix = f"std-{world_num:03d}-"
    samples = []
    for f in files:
        samples.extend(_load_problems(f, prefix))
    return samples


def main():
    rng = random.Random(SEED)

    dev_samples = []
    val_samples = []

    # 60/40 stratified split within each world
    for world in [1, 2, 3, 4, 5, 7]:
        world_samples = _collect_world(world)
        shuffled = world_samples[:]
        rng.shuffle(shuffled)
        n_dev = max(1, int(len(shuffled) * DEV_RATIO))
        dev_samples.extend(shuffled[:n_dev])
        val_samples.extend(shuffled[n_dev:])
        print(f"  World {world}: {len(shuffled)} → {n_dev} dev + {len(shuffled) - n_dev} val")

    # Test: world 6 + dev.json
    test_samples = _collect_world(6)
    dev_json_samples = _load_problems(str(DATA_ROOT / "dev.json"), "dev-001-")
    test_samples.extend(dev_json_samples)
    print(f"  World 6 (test): {len(_collect_world(6))} samples")
    print(f"  dev.json (test): {len(dev_json_samples)} samples")

    print(f"\nDev:  {len(dev_samples)} samples")
    print(f"Val:  {len(val_samples)} samples")
    print(f"Test: {len(test_samples)} samples")

    with open(OUT_DIR / "split_dev.json", "w", encoding="utf-8") as f:
        json.dump(dev_samples, f, indent=2, ensure_ascii=False)
    print(f"\nWrote {OUT_DIR / 'split_dev.json'}")

    with open(OUT_DIR / "split_val.json", "w", encoding="utf-8") as f:
        json.dump(val_samples, f, indent=2, ensure_ascii=False)
    print(f"Wrote {OUT_DIR / 'split_val.json'}")

    with open(OUT_DIR / "split_test.json", "w", encoding="utf-8") as f:
        json.dump(test_samples, f, indent=2, ensure_ascii=False)
    print(f"Wrote {OUT_DIR / 'split_test.json'}")


if __name__ == "__main__":
    main()
