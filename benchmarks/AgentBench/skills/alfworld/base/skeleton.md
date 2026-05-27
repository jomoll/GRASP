---
name: skeleton
description: Template and quality standard for learned skills — read-only
tags: []
---

# Skill Title

Use a title that names a reusable navigation, manipulation, or reasoning strategy
for household tasks.
Prefer titles like `Systematic Container Search` or
`Multi-Object Pickup Sequencing` over titles that reference only one
specific game instance.

## Pattern Description

Write 1–3 paragraphs. State the central reusable lesson. Describe when this
action or reasoning pattern improves task completion.

- Keep the opening general and reusable across different room layouts.
- Focus on a stable strategy, not one isolated game outcome.

## When to Use This Skill

Bullet list of trigger conditions where this skill applies.

- Example: "When the target object is not visible in the starting room,
  systematically open containers (drawers, cabinets, fridge) before
  moving to adjacent rooms"
- Example: "When a pick_two_obj task requires two identical objects,
  locate both before picking up the first to avoid backtracking"

## Example Application

Describe a concrete scenario and how the skill changes agent behavior.
Keep this grounded in ALFWorld action types (go to, open, pick up, put,
clean, heat, cool, examine).

## Pitfalls to Avoid

- Example: "Do not examine an object after already having picked it up —
  this wastes a step and confuses the action parser"
- Example: "Avoid issuing 'go to X' when already standing at X —
  check the observation for your current location first"
