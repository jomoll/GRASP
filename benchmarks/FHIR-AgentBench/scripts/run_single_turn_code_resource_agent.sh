model="${LLM_MODEL:-openai/gpt-oss-120b}"
base_url="${LLM_BASE_URL:-http://localhost:4000}"
agent_strategy="single_turn_code_resource"
python run_agent.py \
  --agent_strategy $agent_strategy \
  --model $model \
  --base_url $base_url \
  --input final_dataset/questions_answers_sql_fhir.csv \
  --output output/${agent_strategy}_${model}_results.json \
  --num_processes 1