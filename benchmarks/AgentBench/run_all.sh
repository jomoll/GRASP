#!/usr/bin/env bash
# Run GRASP on all four AgentBench environments with one backend.
#
# Usage: ./run_all.sh <backend> [run_name]
#   backend:  gptoss | deepseek | gemini | gpt4 | gpt5 | local
#   run_name: defaults to run_001; the trailing integer is used as the seed
#             (run_001 -> seed 1, run_002 -> seed 2, ...), so multi-seed runs
#             are ./run_all.sh gptoss run_001, run_002, run_003.
#
# Task workers must already be running (see README.md "Starting task workers").
# Each config points at its worker's controller port; override per task below
# if you started workers on different ports.
set -euo pipefail

BACKEND="${1:-}"
RUN_NAME="${2:-run_001}"
if [[ -z "$BACKEND" ]]; then
    echo "Usage: $0 <backend> [run_name]" >&2
    echo "  backend: gptoss | deepseek | gemini | gpt4 | gpt5 | local" >&2
    exit 1
fi
SEED=$((10#${RUN_NAME##*_}))

cd "$(dirname "$0")"

for task in os dbbench webshop alfworld; do
    config="configs/grasp_${task}.yaml"
    out="outputs/grasp_${task}/${RUN_NAME}"
    if [[ -f "${out}/test_scores.json" ]]; then
        echo "--- ${config} (${RUN_NAME}): already complete, skipping ---"
        continue
    fi
    echo ""
    echo "=== GRASP ${task} | backend=${BACKEND} | ${RUN_NAME} (seed ${SEED}) ==="
    python -m src.grasp --config "$config" --run-name "$RUN_NAME" \
        --agent "$BACKEND" --resume --set "cycle.seed=${SEED}"
done
