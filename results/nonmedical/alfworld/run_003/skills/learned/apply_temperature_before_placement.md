---
description: Heat or cool the target object before placing it, as required by the
  task instruction.
name: apply_temperature_before_placement
provenance:
  action: ADD
  epoch: 2
  fixes: 3
  probe_score: 3
  regressions: 3
  triggering_sample_ids:
  - 23
  - 8
  - 19
  - 4
  - 27
  - 25
  - 3
  - 40
  - 16
  - 43
  update_cycle: 0
tags:
- heat
- cool
- temperature
version: 1
---

# apply_temperature_before_placement

## Pattern Description
You must ensure that any object the instruction asks to be **heated** or **cooled** is processed with the appropriate temperature appliance before it is placed in its final receptacle. Heating devices (microwave, stoveburner) and cooling devices (fridge) are present in virtually every ALFWorld layout, so the pattern works across rooms. The skill inserts a mandatory temperature step after picking up the object and before the first `put`/`place` action.

## When to Use This Skill
- When the task instruction contains the word **heat** (e.g., `pick_heat_then_place…`) **or** **cool** (e.g., `pick_cool_then_place…`).
- When the target object is temperature‑sensitive (tomato, apple, mug, egg, potato, lettuce, etc.) and is currently in your inventory.
- When no heating/cooling action has yet been issued for that object.

## Example Application
### Wrong trajectory (failure)
```
Think: I need to pick the tomato and then put it in the GarbageCan.
Act:  take_action({"action": "take tomato 1 from fridge 1"})
Obs:  You pick up the tomato 1.
Think: I will now place it.
Act:  take_action({"action": "put tomato 1 in/on garbagecan 1"})
Obs:  ... task limit reached, tomato never heated.
```
The agent never performed a heating step, so the task fails.

### Correct trajectory with the skill
```
Think: The instruction contains "heat" → trigger apply_temperature_before_placement.
Act:  take_action({"action": "take tomato 1 from fridge 1"})
Obs:  You pick up the tomato 1.
Think: Find a heating device; microwave is available.
Act:  take_action({"action": "heat tomato 1 with microwave 1"})
Obs:  You heat the tomato 1 using the microwave 1.
Think: Now place the heated tomato.
Act:  take_action({"action": "put tomato 1 in/on garbagecan 1"})
Obs:  ... task completed.
```
The extra heating action satisfies the temperature requirement and the task succeeds.

## Pitfalls to Avoid
- Do not issue a heating/cooling action **after** the object has already been placed; the temperature step must precede the first `put`.
- Choose the correct appliance: use `microwave` or `stoveburner` for heating, `fridge` for cooling. Trying to `heat` with a fridge or `cool` with a microwave wastes a step and may be rejected.
- If the object is already in the required temperature state (e.g., a cold drink taken from the fridge), you may skip the step, but the skill should first verify the object's current temperature if such observation is available.
