---
name: skeleton
description: Template and quality standard for learned skills — read-only
tags: []
---

# Skill Title

Use a title that names one reusable web-shopping strategy expressed through the
two available tools (`search_action` with `keywords`, `click_action` with a
`value` taken from the listed available actions).
Prefer titles like `Search With Salient Attributes First` or
`Select Required Options Before Buy Now` over titles tied to one specific
product or instruction.

## Pattern Description

Write 1–3 paragraphs. State the central reusable lesson for earning full reward
(1.0), which requires buying a product that matches the instruction's type,
every requested attribute/option, AND the price ceiling.

- Keep the opening general and reusable across instructions and product types.
- Focus on a stable navigation strategy, not one isolated purchase.

## When to Use This Skill

Bullet list of observable trigger conditions.

- Good: "When the instruction lists specific options (size, color, count),
  click each matching option button on the item page before clicking `Buy Now`"
- Good: "When the first search returns no relevant items, re-`search_action`
  with fewer / more salient keywords instead of clicking an irrelevant result"
- Bad: "When shopping is hard"

## Failure Pattern

Bullet list of exact mistakes this skill prevents. Reference the real action
values (`search[...]`, `click[Buy Now]`, `click[< Prev]`, option buttons) and
the available-actions list.

- Good: "Clicking `Buy Now` before selecting the requested color/size options,
  scoring partial reward instead of 1.0"
- Good: "Passing a `click_action` value that is not in the listed available
  actions, so the action is ignored and a round is wasted"
- Bad: "Buying the wrong thing"

## Action Rule

Step-by-step operational guidance that changes the next tool call.

**Rule 1: primary behavior**
State the keyword/click sequence: search → open candidate → set options → buy.

**Rule 2: fallback**
State what to do when results are poor or an option is missing
(re-search with different keywords, or `click[< Prev]` / `click[Back to Search]`).

## Verification Rule

State how to confirm before clicking `Buy Now`.

- Does the open item match the requested type and all attributes?
- Have all instruction options been clicked (they appear selected/echoed)?
- Is the price within the stated ceiling?

## Do Not

2–5 specific behaviors to avoid.

- Good: "Do not click a value that is absent from the available-actions list"
- Good: "Do not click `Buy Now` while any requested option is still unselected"
- Bad: "Do not make mistakes"

## Example Trajectory

Provide one wrong and one correct trajectory of 2–3 turns each, using the real
`search_action` / `click_action` tools and values from available actions.

**WRONG trajectory:**
Instruction: "[buy a <type>, <color>, under $X]"
Turn 1: search_action(keywords="<type>")  → results listed
Turn 2: click_action(value="<item id>")   → item page with color options
Turn 3: click_action(value="Buy Now")     → bought without selecting <color>
→ FAIL (partial reward)

**CORRECT trajectory:**
Instruction: "[same]"
Turn 1: search_action(keywords="<type> <color>")  → results listed
Turn 2: click_action(value="<item id>")           → item page
Turn 3: click_action(value="<color>")             → option selected
Turn 4: click_action(value="Buy Now")             → bought matching item
→ PASS (reward 1.0)

## Notes

Optional short bullets only if they improve generalization.

---

Quality bar:

- One skill = one failure mechanism.
- The skill must be specific enough to predict a different next tool call.
- Do not encode answers to specific instructions or hard-code product ids.
- Prefer 25–50 lines of dense operational guidance over generic prose.
