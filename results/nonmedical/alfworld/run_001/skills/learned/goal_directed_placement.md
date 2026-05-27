---
description: Enforce immediate placement of the target object after it is picked up
name: goal_directed_placement
provenance:
  action: ADD
  epoch: 0
  fixes: 4
  probe_score: 5
  regressions: 1
  triggering_sample_ids:
  - 31
  - 3
  - 43
  - 11
  - 16
  - 14
  - 23
  - 45
  - 40
  - 4
  update_cycle: 0
tags:
- place
- put
- insert
- placement
version: 1
---

# Goal-Directed Placement

## Pattern Description
You must treat any task that explicitly asks to *put* or *place* a specific object into a receptacle as a two‑step workflow: **pick the correct target object, then immediately place it in/on the indicated receptacle**.  The agent should not wander to unrelated containers or perform extraneous actions between the `take` and the `put`.  This pattern prevents loops where the agent keeps searching for other objects, which is the dominant cause of task‑limit failures in pick‑and‑place, pick‑cool‑then‑place, pick‑heat‑then‑place and pick‑clean‑then‑place instructions.

## When to Use This Skill
- When the instruction contains a phrase like "put *OBJECT* in/on *RECEPTACLE*", "place *OBJECT* on *RECEPTACLE*", or "store *OBJECT* in *RECEPTACLE*".
- When the goal description names a single target object (e.g., *SaltShaker*, *Mug*, *SoapBar*) and a destination container (e.g., *drawer 1*, *cabinet 2*, *microwave*).
- When the agent’s inventory shows the target object has just been taken.

## Example Application
**Wrong trajectory (fails to apply the skill)**
```
Think: I need to put the saltshaker in drawer 1.
Act: take_action({"action": "go to cabinet 3"})
Obs: You are in cabinet 3. Nothing relevant here.
Think: Maybe the saltshaker is elsewhere, keep looking.
Act: take_action({"action": "go to cabinet 5"})
Obs: ...
```
*The agent continues roaming and never issues a `put` action, eventually hitting the step limit.*

**Correct trajectory (skill applied)**
```
Think: I need to put the saltshaker in drawer 1.
Act: take_action({"action": "go to shelf 2"})
Obs: On the shelf 2, you see a saltshaker 1.
Think: I have found the target object.
Act: take_action({"action": "take saltshaker 1 from shelf 2"})
Obs: You pick up the saltshaker 1.
Think: The task now requires placing it in drawer 1.
Act: take_action({"action": "go to drawer 1"})
Obs: You are at drawer 1. It is closed.
Act: take_action({"action": "open drawer 1"})
Obs: The drawer 1 is open.
Act: take_action({"action": "put saltshaker 1 in/on drawer 1"})
Obs: You put the saltshaker 1 in/on drawer 1. Task completed.
```
*The agent follows the pick‑then‑place sequence without unrelated navigation, reaching the goal within the step budget.*

## Pitfalls to Avoid
- Do not issue any `go to` or `open` actions after the target object is in inventory **unless** they are required to reach the specified receptacle.
- Do not pick up a different object of the same class; verify the object’s name matches the one mentioned in the instruction before picking.
- If the receptacle is already open, skip the `open` action.
- Ensure the `put` action uses the exact object and receptacle identifiers from the observation (e.g., `put saltshaker 1 in/on drawer 1`).
