---
description: Require a cleaning step before putting an object into its final receptacle
  for pick_clean_then_place tasks.
name: enforce_clean_before_placement
provenance:
  action: ADD
  epoch: 3
  fixes: 6
  probe_score: 4
  regressions: 1
  triggering_sample_ids:
  - 43
  - 16
  - 9
  - 19
  - 20
  - 4
  - 15
  - 3
  - 49
  - 27
  update_cycle: 0
tags:
- clean
- pick_clean_then_place
- cleaning
version: 1
---

# Enforce Cleaning Before Placement

## Pattern Description
You must never place a target object into its final receptacle until it has been cleaned. This constraint applies to any task whose instruction explicitly mentions *clean* (e.g., "pick_clean_then_place", "clean the X before placing") or whose query type is `pick_clean_then_place`. By enforcing a cleaning action **immediately after** the object is picked up and **before** any placement, you guarantee that the environment’s state satisfies the task’s cleanliness requirement, avoiding silent failures where the agent thinks the task is complete but the object remains dirty.

## When to Use This Skill
- When the instruction contains the word **clean** (case‑insensitive) or the phrase *"clean the <object>"*.
- When the query type is `pick_clean_then_place`.
- When you have just executed a `take <obj> from <location>` action and the object is not yet known to be clean (no prior `clean <obj> with <device>` observation).

## Example Application
**Wrong trajectory (fails due to missing cleaning step)**
```
Think: The task is "pick_clean_then_place‑Spatula‑None‑Drawer‑10". I will pick the spatula.
Act: take spatula 1 from drawer 2
Obs: You are now carrying spatula 1.
Think: I have the spatula, I will place it in the drawer.
Act: put spatula 1 in/on drawer 1
Obs: Spatula 1 is now in drawer 1.
```
The task ends without a cleaning action, so the environment reports the goal as incomplete.

**Correct trajectory (skill forces cleaning before placement)**
```
Think: The instruction mentions "clean", so enforce cleaning before placement.
Act: take spatula 1 from drawer 2
Obs: You are now carrying spatula 1.
Think: Before placing, I must clean the spatula.
Act: clean spatula 1 with sinkbasin 1
Obs: Spatula 1 is now clean.
Think: Now I can place the clean spatula.
Act: put spatula 1 in/on drawer 1
Obs: Spatula 1 is now in drawer 1.
```
The additional `clean` action satisfies the task’s requirement and the episode completes successfully.

## Pitfalls to Avoid
- **Do not clean after placement** – the skill forces cleaning *before* any `put` action for the target object.
- **Do not clean an object that is already clean** – if the observation after a `clean` action says the object was already clean, you may skip the redundant step.
- **Select the appropriate cleaning device** – only use devices capable of cleaning (e.g., `sinkbasin`, `dishwasher`). Attempting to clean with a non‑cleaning object will generate an invalid‑action error.
- **Do not apply this skill to tasks that do not mention cleaning** – the trigger is the presence of the word "clean" in the instruction; applying it elsewhere can waste steps.
