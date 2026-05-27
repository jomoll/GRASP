# Backend presets

Each `<name>.yaml` here is a complete agent block (`module` + `parameters`) for
one model backend. A run selects one with, in order of precedence:

```
--agent <name>      # CLI flag on the cycle script
GRASP_BACKEND=<name>  # environment variable
agent_preset: <name>  # default in the task config
```

Presets contain **no secrets**. Endpoints, keys, projects, and model handles are
read from environment variables at run time via `${VAR}` / `${VAR:-default}`
placeholders, expanded by `src/agent_preset.py`.

| Preset | Model (paper) | Provider | Required env |
|---|---|---|---|
| `gptoss` | gpt-oss-120b | self-hosted, OpenAI-compatible | `OSS_API_BASE` (opt: `OSS_API_KEY`, `OSS_MODEL`) |
| `deepseek` | DeepSeek V4 Flash | self-hosted, OpenAI-compatible | `DEEPSEEK_API_BASE` (opt: `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL`) |
| `gemini` | Gemini 3.1 Flash Lite | Google Vertex AI | `GOOGLE_CLOUD_PROJECT` + ADC (opt: `GOOGLE_CLOUD_LOCATION`, `GEMINI_MODEL`) |
| `gpt5` | GPT-5.4 (low) | Azure OpenAI Responses API | `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_BASE_URL` |
| `gpt4` | GPT-4.1 | Azure OpenAI (via LiteLLM) | `AZURE_API_KEY`, `AZURE_API_BASE`, `AZURE_API_VERSION` |
| `local` | any | generic OpenAI-compatible endpoint | `LOCAL_API_BASE`, `LOCAL_MODEL` (opt: `LOCAL_API_KEY`) |

The four AgentBench environments are reported in the paper on `gptoss` only;
the other presets are provided so the same configs can be run with any backend.

## Examples

```bash
# self-hosted gpt-oss-120b (paper setting)
export OSS_API_BASE="http://localhost:8000/v1"
python -m src.grasp --config configs/grasp_os.yaml --run-name run_001 --agent gptoss

# Gemini via Vertex
export GOOGLE_CLOUD_PROJECT="my-project"
gcloud auth application-default login
GRASP_BACKEND=gemini python -m src.grasp --config configs/grasp_os.yaml --run-name run_001

# any other OpenAI-compatible server
export LOCAL_API_BASE="http://localhost:4000/v1" LOCAL_MODEL="my-model"
python -m src.grasp --config configs/grasp_dbbench.yaml --run-name run_001 --agent local
```
