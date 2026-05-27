---
description: Ensures the target object is cleaned before it is placed in the requested
  receptacle.
name: apply_clean_before_placement
provenance:
  action: ADD
  epoch: 3
  fixes: 3
  probe_score: 3
  regressions: 0
  triggering_sample_ids:
  - 9
  - 15
  - 27
  - 23
  - 16
  - 31
  - 43
  - 4
  - 8
  - 20
  update_cycle: 0
tags:
- clean
- wash
- pick_clean_then_place
- cleaning
version: 1
---

# Apply Cleaning Before Placement

## Pattern Description
When a task explicitly asks for a *clean* object (e.g., `pick_clean_then_place`), the agent must perform a cleaning action on the picked item before any placement action. This pattern avoids leaving dirty objects in appliances or on countertops, which the evaluator treats as an incomplete or incorrect solution. The cleaning step typically involves using a sink basin (or other appropriate cleaning station) with actions such as `wash <obj> with sinkbasin` or `clean <obj> with sinkbasin`.

## When to Use This Skill
- The instruction contains the word **clean** (e.g., `pick_clean_then_place`, `pick_clean_then_place_in_recep`).
- The target object is a food‑related item or utensil that can be washed (mug, knife, spatula, etc.).
- No explicit cleaning step appears in the agent’s current plan.

## Example Application
**Task**: `pick_clean_then_place_in_recep-Mug-None-CoffeeMachine-10`

**Wrong trajectory (fails)**
- *Think*: I need to pick the mug and put it in the coffee machine.
- *Act*: `take mug 1 from cabinet 2`
- *Obs*: I am now carrying mug 1.
- *Think*: I can place it directly.
- *Act*: `put mug 1 in/on coffee machine 1`
- *Obs*: The mug is placed but still dirty → task considered incorrect.

**Correct trajectory (skill applied)**
- *Think*: The task requires a clean mug before placement.
- *Act*: `take mug 1 from cabinet 2`
- *Obs*: I am now carrying mug 1.
- *Think*: I must clean it first. The sink basin is the cleaning station.
- *Act*: `go to sinkbasin 1`
- *Obs*: I am at sinkbasin 1.
- *Think*: Clean the mug.
- *Act*: `wash mug 1 with sinkbasin 1`
- *Obs*: Mug 1 is now clean.
- *Think*: Place the clean mug.
- *Act*: `go to coffeemachine 1`
- *Obs*: I am at the coffee machine.
- *Think*: Place the cleaned mug.
- *Act*: `put mug 1 in/on coffeemachine 1`
- *Obs*: Clean mug is correctly placed → task succeeds.

## Pitfalls to Avoid
- **Skipping the cleaning step** because the object is already in inventory; always verify the task wording first.
- **Cleaning after placement** – the cleaning action must precede any `put` or `place` command.
- **Using the wrong cleaning station** – only use actions like `wash/clean … with sinkbasin` (or `wash … with dishwasher` if available). Attempting to `clean` with a non‑cleaning appliance (e.g., microwave) will be rejected.
- **Repeated cleaning** – one clean action is sufficient; avoid multiple `wash` calls on the same object as it wastes steps.

---
