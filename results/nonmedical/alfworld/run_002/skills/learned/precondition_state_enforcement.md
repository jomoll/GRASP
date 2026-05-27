---
description: Enforce clean/heat/cool preconditions before placing an object when the
  instruction specifies such a precondition.
name: precondition_state_enforcement
provenance:
  action: ADD
  epoch: 1
  fixes: 6
  probe_score: 5
  regressions: 0
  triggering_sample_ids:
  - 43
  - 9
  - 34
  - 16
  - 25
  - 15
  - 27
  - 20
  - 49
  - 11
  update_cycle: 0
tags: []
version: 1
---

# Precondition State Enforcement (Clean/Heat/Cool)

## Pattern Description
When a task instruction explicitly requires a state change—cleaning, heating, or cooling—*before* the object is placed, the agent must insert the appropriate state‑changing action prior to any `put` command. This pattern captures a reusable rule across many query types (e.g., `pick_clean_then_place`, `pick_heat_then_place`, `pick_cool_then_place`). By detecting the precondition keyword in the instruction, the agent avoids the common failure of skipping the required transformation and ending the episode with the object in the wrong state.

## When to Use This Skill
- The instruction contains the word **clean**, **heat**, or **cool** followed by “then place” (e.g., `pick_clean_then_place‑Mug‑None‑CounterTop`).
- The task type is `pick_clean_then_place`, `pick_heat_then_place`, or `pick_cool_then_place`.
- The agent has not yet performed the corresponding state‑changing action on the held object.

## Example Application
**Wrong trajectory (missing precondition)**
```
Think: I need to put the mug on the countertop.
Act:  take_action({"action": "take mug 1 from countertop 1"})
Obs:  You pick up the mug 1 from the countertop 1.
Think: I will put it directly.
Act:  take_action({"action": "put mug 1 in/on countertop 1"})
Obs:  The mug is now on the countertop.
```
The task required *clean* then place, but the cleaning step was omitted, causing failure.

**Correct trajectory (skill applied)**
```
Think: The instruction says "pick_clean_then_place" – I must clean the mug before placing it.
Act:  take_action({"action": "take mug 1 from countertop 1"})
Obs:  You pick up the mug 1 from the countertop 1.
Think: I need a sinkbasin to clean the mug.
Act:  take_action({"action": "go to sinkbasin 1"})
Obs:  You are at sinkbasin 1.
Think: Clean the mug now.
Act:  take_action({"action": "clean mug 1 with sinkbasin 1"})
Obs:  The mug 1 is now clean.
Think: Place the clean mug on the target.
Act:  take_action({"action": "put mug 1 in/on countertop 1"})
Obs:  The clean mug 1 is now on the countertop.
```
The same pattern works for `heat` (use `heat <obj> with <appliance>`) and `cool` (use `cool <obj> with fridge`).

## Pitfalls to Avoid
- **Redundant actions**: Do not clean an object that is already clean; check the observation after a `clean` action to confirm the state.
- **Wrong appliance**: Use the appropriate appliance (`sinkbasin` for cleaning, `microwave`/`stoveburner` for heating, `fridge` for cooling). Selecting the wrong one will waste steps and may produce an error.
- **Missing target**: Ensure you have moved to the location of the required appliance before issuing the state‑changing command.
- **Premature placement**: Never issue a `put` command until the state‑change observation confirms success.

---
Tags: ["clean", "heat", "cool", "precondition", "state_change"]
