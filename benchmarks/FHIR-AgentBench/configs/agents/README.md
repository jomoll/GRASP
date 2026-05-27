# Backend presets (FHIR-AgentBench)

Select a model backend with `--agent <name>`, `GRASP_BACKEND=<name>`, or
`agent_preset: <name>` in a config (precedence in that order). Each `<name>.yaml`
sets the LiteLLM `model` (and `base_url` / `project_id` / `location`) for the
executing agent, the skill-writer (`updater`), and the grader (`eval`); all
other tuning keys in the config are preserved.

Presets contain no secrets — endpoints/projects come from environment variables.

| Preset | Model (paper) | Required env |
|---|---|---|
| `gptoss` | gpt-oss-120b | `OSS_API_BASE` |
| `deepseek` | DeepSeek V4 Flash | `DEEPSEEK_API_BASE` |
| `gemini` | Gemini 3.1 Flash Lite | `GOOGLE_CLOUD_PROJECT` + ADC |
| `gpt5` | GPT-5.4 (low) | `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_BASE_URL` |
| `gpt4` | GPT-4.1 | `AZURE_API_KEY`, `AZURE_API_BASE`, `AZURE_API_VERSION` |
| `local` | any | `LOCAL_API_BASE`, `LOCAL_MODEL` |

Without a selection, the config's inline `agent` block is used unchanged.
