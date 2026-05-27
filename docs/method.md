# GRASP, the method

GRASP turns an agent's **own failure traces** into a small library of reusable
**skills** — short Markdown documents injected into the agent's context — and
keeps a skill only when it **demonstrably improves performance on a held-out
probe set**. That acceptance test (the *regression gate*) is what keeps the
library small and monotonically useful instead of accumulating plausible-sounding
but unhelpful advice.

This document describes the algorithm as implemented in
[`grasp/cycle.py`](../grasp/cycle.py) (`SkillCycleRunner`, exposed as
`SkillLearningMethod`).

## The loop

```
for each epoch:
  shuffle dev split (seeded)
  for each batch of dev samples:
    1. ROLLOUT   run the skill-aware agent on every sample (in parallel)
    2. SCORE     task.evaluate(sample, rollout) -> correct / incorrect
    3. PROPOSE   from the failing traces, sample K candidate skill edits
    4. GATE      for each candidate: fork the library, apply it, and re-run a
                 balanced probe set; keep the best candidate **only if** it nets
                 more fixes than regressions vs. the current library
    5. APPLY     write the winning edit (ADD / MODIFY / REMOVE), or nothing
  evaluate silently on the val split (no skill updates from val)
  snapshot the library if val improved (best checkpoint)
restore the best-val checkpoint as the final library
```

### 1–2. Rollout and scoring

Each dev sample is run through `task.rollout(sample, agent)`, where `agent` is
the base backend wrapped in a `SkillAwareAgent` that injects the current skill
library into the prompt (see *Skill injection* below). `task.evaluate` returns a
boolean. Optional `task.failure_tags(sample, rollout)` attaches short mechanism
tags to failures, which sharpen the proposal step.

### 3. Proposal (best-of-K, grouped by failure mode)

Failing traces are first **classified** into mechanism labels and **diagnosed**
against the current library (what skill should have fired but didn't). Failures
are grouped by label so each proposal call sees a homogeneous set, and `K`
candidate edits are sampled at a higher *proposal temperature* for diversity.
Each candidate is one of:

- **ADD** a new skill (blocked when the library is at `max_learned_skills`,
  unless paired with a REMOVE),
- **MODIFY** an existing skill (fix a specific gap), or
- **REMOVE** a redundant or harmful skill.

### 4. The regression gate

This is the core idea. For each candidate the loop:

1. **forks** the skill library (a temp copy),
2. **applies** the candidate to the fork,
3. **re-runs** a balanced **probe set** — up to `grpo_eval_n/2` previously
   *failing* and `grpo_eval_n/2` previously *passing* samples, drawn
   *out-of-sample* from earlier batches (or the previous epoch), and
4. compares against a **baseline probe** run with the *current* library, so the
   score is causal rather than absolute.

The candidate's score is

```
adjusted = (fixes - baseline_fixes)
         - (regressions - baseline_regressions)
         - penalty * invalid_action_regressions
```

A candidate is eligible to win only if `adjusted > 0` **and** it introduces no
new regressions beyond baseline. If no candidate clears the bar, **nothing is
applied** — the library never changes on faith. The passing/failing balance
means a skill cannot win just by helping failures while silently breaking
samples that already worked.

### 5. Refinements

- **Contrastive revision** — if the winner still causes a few regressions, the
  updater is asked to narrow it, and the revision must beat the original on the
  same probe set to be kept.
- **Dev-collapse recovery** — if an epoch's dev accuracy collapses with skills
  present, the most recently added skill is probed for removal.
- **Best checkpoint** — the library is snapshotted whenever val improves, and
  the best-val snapshot is restored at the end, so a late bad epoch can't
  degrade the final library.

## Skill injection

`SkillAwareAgent` ranks the library against the current context (tags, names,
descriptions, the "When to Use" section) and injects up to 3 skills per turn:
**prepended** before the task on the first decision (so behavioural rules are
read before acting), **appended** on continuation turns (recency, close to
generation). A task may also supply a `protocol_hook` to inject an
environment-specific tool reminder.

## Skill file format

Skills are Markdown with YAML frontmatter, managed by
[`SkillRepository`](../grasp/skills/repository.py); learned skills carry
provenance (which epoch/probe score produced them) and a version history.

```markdown
---
name: observation_value_extraction
description: Extract the numeric lab value, not the formatted string
tags: [observation, magnesium, glucose]
version: 2
---

## When to Use This Skill
When a task asks for a lab value from a FHIR Observation ...

## Recommended Patterns
CORRECT: valueQuantity.value extracted as a number -> FINISH([3.5])
WRONG:   FINISH(["3.5 mmol/L"])  # units in the value
...
```

The read-only `skeleton` skill in each `skills/base/` directory is the template
and quality bar shown to the skill writer; it is never injected or edited.

## Key hyperparameters (`cycle:` in the config)

| Key | Meaning |
|---|---|
| `epochs` | passes over the dev split |
| `update_every` | dev samples per batch (a skill update happens per batch) |
| `grpo_k` | candidate proposals sampled per update |
| `grpo_eval_n` | probe set size (half failing, half passing) |
| `max_learned_skills` | library capacity |
| `proposal_temperature` | decoding temperature for proposal diversity |
| `run_baseline` | run a no-skills val eval before epoch 0 |
| `seed` | RNG seed for shuffling and probe sampling |
