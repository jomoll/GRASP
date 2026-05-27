---
description: Require a cooling step before putting an item into its final receptacle
  for pick_cool_then_place tasks.
name: enforce_cooling_before_placement
provenance:
  action: ADD
  epoch: 2
  fixes: 4
  probe_score: 3
  regressions: 2
  triggering_sample_ids:
  - 27
  - 43
  - 31
  - 32
  - 20
  - 38
  - 23
  - 19
  - 11
  - 15
  update_cycle: 0
tags:
- cool
- pick_cool_then_place
- cooling
version: 1
---

# Enforce Cooling Before Placement

## Pattern Description
When a task explicitly asks to *pick, cool, then place* an object, the agent must insert a cooling action (e.g., `cool <object> with <fridge>` or `cool <object> with <freezer>`) **before** any `put … in/on …` action. This prevents the agent from shortcutting the cooling step and satisfying the placement goal with a warm object. The pattern is reusable for any object that can be cooled and any receptacle that expects a cooled item (microwave, countertop, cabinet, etc.).

## When to Use This Skill
- The instruction contains the phrase **"pick_cool_then_place"** or mentions the word **"cool"** together with a placement target (e.g., "put a cool tomato in the microwave").
- The object to be placed is a food item that can be cooled (tomato, lettuce, potato, etc.).
- The environment offers a cooling appliance (fridge, freezer, cooler) that can perform a `cool` action on the object.

## Example Application
**Task:** `pick_cool_then_place_in_recep-Tomato-None-Microwave-10`

**Wrong trajectory (failure):**
1. *Think:* I have the tomato, I need to put it in the microwave.
   *Act:* `take tomato 1 from countertop 2`
   *Obs:* Tomato is in inventory.
2. *Think:* The goal is achieved by placing it.
   *Act:* `put tomato 1 in/on microwave 1`
   *Obs:* Tomato is inside the microwave (warm) → task fails because cooling was omitted.

**Correct trajectory (skill applied):**
1. *Think:* The task requires a cool tomato. I must cool it first.
   *Act:* `go to fridge 1`
   *Obs:* Fridge is closed.
2. *Think:* Cool the tomato using the fridge.
   *Act:* `cool tomato 1 with fridge 1`
   *Obs:* Tomato is now cool.
3. *Think:* Now place the cooled tomato.
   *Act:* `go to microwave 1`
   *Obs:* Microwave is closed.
4. *Think:* Put the cooled tomato inside.
   *Act:* `open microwave 1`
   *Obs:* Microwave is open.
5. *Think:* Final placement.
   *Act:* `put tomato 1 in/on microwave 1`
   *Obs:* Cool tomato is inside the microwave – task succeeds.

## Pitfalls to Avoid
- **Skipping the cooling action** because the object is already in inventory; always check the task wording for "cool" before placement.
- **Cooling after placement** (e.g., placing first then cooling) – the cooling must occur while the object is still in the agent's possession.
- **Using an inappropriate appliance**; only use actions like `cool … with fridge` or `cool … with freezer`. Attempting to `heat` or `clean` instead will not satisfy the cooling requirement.
- **Repeating the cooling step** after the object has already been cooled; once cooled, proceed directly to placement.
