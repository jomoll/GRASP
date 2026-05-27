#!/usr/bin/env bash
# Run all six learning methods on FHIR-AgentBench with one model backend.
#
# Usage: ./run_all.sh <backend> [run_name]
#   backend:  gptoss | deepseek | gemini | gpt4 | gpt5 | local
#   run_name: defaults to run_001; trailing integer is the seed (run_00N -> seed N)
#
# --agent selects the model (overriding each config's default). Results are
# separated per backend under outputs/<method>_<backend>/.
set -euo pipefail

BACKEND="${1:-}"
RUN_NAME="${2:-run_001}"
if [[ -z "$BACKEND" ]]; then
    echo "Usage: $0 <backend> [run_name]   (gptoss|deepseek|gemini|gpt4|gpt5|local)" >&2
    exit 1
fi
SEED=$((10#${RUN_NAME##*_}))

cd "$(dirname "$0")"

for method in grasp memory_cycle batch_memory_cycle evo_memory_cycle expel_cycle skillx_cycle; do
    base="configs/${method}.yaml"   # structural base; --agent selects the model
    [[ -e "$base" ]] || { echo "Missing base config: $base" >&2; exit 1; }
    out="outputs/${method}_${BACKEND}"
    if [[ -f "${out}/${RUN_NAME}/id_test_eval_best/test_score.json" ]]; then
        echo "--- ${method} (${BACKEND}, ${RUN_NAME}): already complete, skipping ---"
        continue
    fi
    echo ""
    echo "=== ${method} | backend=${BACKEND} | ${RUN_NAME} (seed ${SEED}) ==="
    python "${method}.py" --config "$base" --run-name "$RUN_NAME" \
        --agent "$BACKEND" --resume --set "output_dir=${out}" "cycle.seed=${SEED}"
done
