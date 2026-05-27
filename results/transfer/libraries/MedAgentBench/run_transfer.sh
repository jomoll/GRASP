#!/usr/bin/env bash
# Evaluate all transferred skill packs (gemini-001..003, oss-001..003) on both
# splits (in-distribution `id_test` and out-of-distribution `test`).
#
# Usage:
#   bash transfer_skills/run_transfer.sh           # from MedAgentBench/
#   bash run_transfer.sh                            # from MedAgentBench/transfer_skills/
#
# Before running:
#   1. Point the `agent` block of configs/skill_cycle.yaml at your model
#      (e.g. gpt-5.4).
#   2. Make sure the task controller is listening at $CONTROLLER_ADDRESS.
#
# Overridable env vars:
#   MODEL_TAG           short tag baked into run names      (default: gpt54)
#   CONTROLLER_ADDRESS  task controller URL                 (default: http://localhost:5900/api)
#   CONFIG              path to the skill_cycle config      (default: configs/skill_cycle.yaml)
#   EXTRA_ARGS          extra flags forwarded to run_eval   (e.g. --resume)
#
# Results land in transfer_skills/eval/<pack>-to-<MODEL_TAG>-{id,ood}/.

set -euo pipefail

# Run from the MedAgentBench repo root regardless of invocation directory.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

MODEL_TAG="${MODEL_TAG:-gpt54}"
CONTROLLER_ADDRESS="${CONTROLLER_ADDRESS:-http://localhost:5900/api}"
CONFIG="${CONFIG:-configs/skill_cycle.yaml}"
EXTRA_ARGS="${EXTRA_ARGS:-}"

PACKS=(gemini-001 gemini-002 gemini-003 oss-001 oss-002 oss-003)

for pack in "${PACKS[@]}"; do
    skills_dir="transfer_skills/${pack}"
    if [[ ! -d "$skills_dir" ]]; then
        echo "!! Skipping ${pack}: ${skills_dir} not found" >&2
        continue
    fi

    echo "=== ${pack} -> ${MODEL_TAG} ==="

    python -m src.run_eval --config "$CONFIG" --split id_test \
        --controller-address "$CONTROLLER_ADDRESS" \
        --skills-dir "$skills_dir" \
        --run-name "${pack}-to-${MODEL_TAG}-id" \
        ${EXTRA_ARGS}

    python -m src.run_eval --config "$CONFIG" --split test \
        --controller-address "$CONTROLLER_ADDRESS" \
        --skills-dir "$skills_dir" \
        --run-name "${pack}-to-${MODEL_TAG}-ood" \
        ${EXTRA_ARGS}
done
