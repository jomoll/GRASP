"""
Quickstart entry point.

    python -m examples.quickstart.run --agent local

Runs GRASP on a self-contained slice of MedAgentBench's read-only FHIR lookup
tasks, served by an in-process mock — no Docker, no live FHIR server. Point the
``local`` backend at any OpenAI-compatible endpoint via environment variables
(see configs/agents/local.yaml), then watch GRASP learn skills that lift val
accuracy. Run from the repository root.
"""

import argparse
from pathlib import Path

from grasp import run_grasp

from .task import FHIRQuickstartTask

_CONFIG = Path(__file__).resolve().parent / "configs" / "grasp.yaml"


def main() -> None:
    parser = argparse.ArgumentParser(description="GRASP FHIR quickstart")
    parser.add_argument("--agent", "-a", default="local",
                        help="Backend preset in configs/agents/ (default: local)")
    parser.add_argument("--run-name", "-n", default=None)
    parser.add_argument("--force", "-f", action="store_true")
    parser.add_argument("--resume", "-r", action="store_true")
    parser.add_argument("--set", metavar="KEY=VALUE", nargs="*", default=[],
                        help="Override config values, e.g. cycle.epochs=2")
    args = parser.parse_args()

    run_dir = run_grasp(
        FHIRQuickstartTask(),
        _CONFIG,
        agent=args.agent,
        overrides=args.set,
        run_name=args.run_name,
        force=args.force,
        resume=args.resume,
    )
    print(f"\nDone. Run artifacts in: {run_dir}")
    print(f"Learned skills:        {run_dir / 'skills' / 'best'}")
    print(f"Learning curve:        {run_dir / 'val_scores.json'}")


if __name__ == "__main__":
    main()
