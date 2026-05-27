# Contributing

Thanks for your interest in GRASP. This repository has two parts, and
contributions are welcome to both:

- **`grasp/`** — the reusable core (the method + the `Task` / `Method`
  interfaces). Changes here should keep the public API stable and stay
  benchmark-agnostic: anything environment-specific belongs behind a `Task` hook
  (`failure_tags`, `protocol_hook`, `updater_*`), not hardcoded in the core.
- **`benchmarks/`** — the paper artifact, vendored to reproduce the published
  results. Please keep these faithful to the paper; substantive method changes
  belong in `grasp/`, not here.

## Good first contributions

- A new `Task` for another environment (see [`docs/add_a_task.md`](docs/add_a_task.md)) —
  wiring one of the unwired AgentBench families is especially welcome.
- A new `Method` baseline (see [`docs/add_a_method.md`](docs/add_a_method.md)).
- Additional reference agents under `grasp/agents/`.
- Docs and quickstart improvements.

## Development

```bash
pip install -e ".[dev]"
```

The core depends only on PyYAML; the reference agent uses the standard library.
Please keep new core dependencies minimal and optional where possible. Run the
quickstart end to end before opening a PR that touches the loop:

```bash
python -m examples.quickstart.run --agent local --set cycle.epochs=1
```

## Conventions

- Match the surrounding style; keep the core readable — it doubles as the
  reference description of the method.
- Don't commit run artifacts, secrets, or large data. Backends read endpoints
  and keys from environment variables via the `configs/agents/` presets; never
  hardcode them.

By contributing you agree that your contributions are licensed under the
repository's [MIT license](LICENSE).
