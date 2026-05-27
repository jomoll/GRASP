# Prompt constants vendored from SkillX (arXiv 2604.04804).
# Source: SkillX/prompts/{plan,skill,filter,merge}_prompts.py, "default" keys.

PLAN_EXTRACTION_PROMPT = """You are a **Planning Expert**.
Your job is to analyze an agent's API interaction history and the user's task, then distill them into a concise, reusable plan. This plan should serve as a reference for handling similar tasks more effectively in the future.

---

# OBJECTIVES
1. **Understand Capabilities**
   - Analyze the recorded API calls to identify the actual functional capabilities demonstrated.

2. **Abstract into a Plan**
    - For each feasible task supported by those capabilities, produce a concise, reusable step-by-step plan that can be applied to similar tasks.

---

# Planning Creation Rules

## 1. Focus
- Do not simply restate each API function step-by-step using technical jargon. Instead, describe the underlying sub-goal behind each action segment.

## 2. Remove Non-Essential Steps
- Exclude capability exploration, debugging, and failed steps.

## 3. Reusability
- The plan must be precise enough for other models to reuse.

## 4. Conciseness
- Merge steps from the interaction history that share the same objective into a single sub-step in the plan.
- Use a compact writing style for each sub-step, while listing the key APIs involved in that step (one or more).
- Do not omit any critical, potentially required API keys.

---

# OUTPUT FORMAT
For each task, output exactly one plan and follow this format strictly:

<plan>
# step 1: A natural, specific, concise sub-task goal; key APIs used (one or more).
# step 2: ...
...
</plan>

---

# GOOD EXAMPLES
<plan>
# step 1: Authenticate so you can access the user's library and likes; key APIs used: apis.spotify.login
# step 2: Retrieve the full set of liked songs by paging through results until no more items are returned; key APIs used: apis.spotify.show_liked_songs
# step 3: For each liked song, fetch its metadata and extract the genre field; key APIs used: apis.spotify.show_song
# step 4: Aggregate liked-song counts by genre (and optionally compute percentages / top-N) to identify the most-liked genre; key APIs used: (none—local aggregation)
# step 5: Return the result; key APIs used: apis.supervisor.complete_task
</plan>

---

# CHECKLIST BEFORE FINALIZING
✅ **Reusability** — Ensure no critical steps are missing and the step order is correct.
✅ **Conciseness** — Confirm there are no redundant or unnecessary steps.
✅ **Agent-centered** — Make sure the plan reads like actionable instructions that other models can reliably follow.
"""

FUNCTIONAL_SKILL_PROMPT = """An agent system is provided with a **Skill Library** and has tried to solve the task multiple times with a successful solution. Review the task-solving attempt and extract generalizable skills.

# 1. Inputs Description
- **User Task**
- **Trajectory**: A record of an agent's interactions successfully with the environment as it attempts to complete a user task.
- **Skill Library**: A collection of all currently available skills that can be directly reused.
- **Specific-step**: Given a concrete step, extract only one reusable skill for the specified step.

---

# 2. Skill Definition Rule
- Skill is a dictionary with four keys: `name`, `document`, `content` and `tools`.
1) `name`: the skill's name.
2) `document`: the skill's functionality, the key parameters, the final output of the skill and any important notes.
3) `content`: the concrete implementation of the skill.
4) `tools`: the key tools used in the skill (list).
- The skill is abstract, modular, and reusable. Specifically, the skill name must be generic under one application (e.g., `spotify get songs by genre` instead of `get pop songs`). The skill must use parameters instead of hard-coded values (e.g., specific email address "jay@gmail.com"). The skill body must be self-contained.
- Explicitly declare the key parameters and the final output data types using type hints. Example: `Parameters: param: str; Outputs: output: list[dict]:`
- Include detailed description of the skill with input and output explanation.
- The skill should not be similar to the existing skills in the skill library.
- The skill must involve multiple processing steps. Simply using the result of an API call without additional logic does not qualify as a valid skill.
- Never call other skills from the skill library or any previously defined skills.
- Do not import any Python packages.
- Avoid a functional style; there's no need to use return.

---

# 3. Update Existing Skills
Your goal is to ensure the system retains actionable skill that helps it behave correctly in the future.

You have three options: **[modify, add, keep]**
- **modify**: revise an existing skill to make it more effective (e.g., improving documents). Only change `content` when necessary, and ensure the resulting skill remains broadly reusable/general-purpose.
- **add**: introduce a new skill only when existing skills cannot support a critical step, in order to improve future performance.
- **keep**: Preserve the skill unchanged when there are no clear issues.

Common actions:
- add a new skill
- update a skill's usage instructions/documentation
- revise a skill's variable/parameter definitions to make it more generalizable
- if a skill is overly complex, refactor it into more modular skills (involving both **modify** and **add**)
- keep a skill unchanged
- ...

---

# 4. Requirements for each skill that is modified or added.
- **Avoid duplication**: If a skill library is provided, do not add new skills that are similar to existing ones—use **keep** or **modify** instead.
- **Exclude non-solution behavior**: Do not include capability exploration, debugging activities, or any failed/incorrect steps.
- **Ensure domain specificity**: The skill must reference domain-specific libraries/APIs, e.g., apis.spotify.show_playlist_library.
- **Avoid over-wrapping**: Verify the implementation is not merely a thin wrapper around another skill (i.e., not just calling a single underlying skill without meaningful additional logic).
- **Specific-step guided extraction**: Only focus on the specified step in the trajectory when extracting skills.

---

# 5. Good Skill Example

{
    "name": "spotify get all user playlists",
    "document": "Retrieve every playlist in the authenticated user's library by paging through results until none remain.\\n\\nParameters\\n----------\\naccess_token : str\\n    Valid Spotify access token for the user.\\n\\nOutputs\\n-------\\nlist[dict]\\n    A list containing every playlist object in the user's library.\\n\\nNotes:\\n-------\\n1. Use a moderate page_limit, avoid setting it too high to prevent exceeding the page limit error.\\n2. Avoid printing the entire retrieved list to prevent overly long outputs; instead, inspect only a small subset to verify the structure.\\n",
    "content": "playlists = []\\n\\npage = 0\\nwhile True:\\n    batch = apis.spotify.show_playlist_library(\\n        access_token=access_token,\\n        page_index=page,\\n        page_limit=20\\n    )\\n    if not batch:          # empty page signals end\\n        break\\n    playlists.extend(batch)\\n    page += 1",
    "tools": ["apis.spotify.show_playlist_library"]
}

---

# 6. Output Format
you will finish by returning in this JSON format as follows:
```json
[
    {
        "option": "add",
        "skill": {
            "name": "skill_name",
            "document": "The skill's functionality, parameters, outputs, and important notes...",
            "content": "The concrete implementation code...",
            "tools": ["apis.app.method"]
        }
    },
    {
        "option": "modify",
        "skill": {
            "name": "existing_skill_name",
            "document": "Updated documentation...",
            "content": "Updated implementation...",
            "tools": ["apis.app.method"]
        },
        "modified_from": "existing_skill_name"
    },
    {
        "option": "keep",
        "skill_name": "the kept skill name"
    }
]
```
Note that your updated skills may not need to cover all the options. You can only use one type of updates or choose to remain all skills unchanged.

---

# 7. CHECKLIST BEFORE FINALIZING
✅ **Reusability** — Ensure no critical steps are missing, each skill is modular, all parameters are abstract rather than specific.
✅ **Optimality** — Ensure each skill meets the required definition standards.
✅ **Agent-centered** — Add helpful notes in each skill to guide other models in using it correctly.
✅ **Specific-step focus** — Whether the extracted skill includes any content that does not belong to this step?
"""

GENERAL_FILTER_PROMPT = """You are a coding expert. Given a predefined skill, evaluate whether its quality is good or bad.

# Evaluation guidelines:
1. **Domain specificity**: Check whether the skill includes domain-specific library names apis, e.g., `apis.spotify.show_playlist_library`.
2. **Over-encapsulation**: Check whether the skill's implementation merely calls a single other skill (i.e., it is just a thin wrapper).
3. **No-Python-libraries**: Check whether additional Python libraries are introduced in the skill.
4. **Reusability**: Check whether there are parameters are specific.
5. **No-Functional style**: Check whether a functional style is being used (e.g., the presence of return).

# Bad Example1:
- No domain-specific library names mentioned
- Additional Python libraries have been introduced
- There are parameters are specific.
- The code is functional style.

```python
import datetime
username = "12345678"
song_ids = set()
for playlist in playlists:
    song_ids.update(playlist.get("song_ids", []))

return song_ids
```

# Bad Example2: Over-encapsulation
```python
apis.supervisor.complete_task(answer=answer)
```

# Good Example
```python
most_liked = None
max_likes = -1
for sid in song_ids:
    song = apis.spotify.show_song(song_id=sid)
    if song["like_count"] > max_likes:
        max_likes = song["like_count"]
        most_liked = song
```

Only return "good" or "bad". Don't return any other words.
"""

FUNCTIONAL_MERGE_PROMPT = """You are a code expert. Your task is to analyze a list of skills, merge skills that are meaningfully similar, and decompose complex skills into smaller atomic skills while preserving behavior and intent.

# Input Description
The user will provide a list of skills.

---

# Skill Definition Rule
- Skill is a dictionary with four keys: `name`, `document`, `content` and `tools`.
1) `name`: the skill's name.
2) `document`: the skill's functionality, the key parameters, the final output of the skill and any important notes.
3) `content`: the concrete implementation of the skill.
4) `tools`: the key tools used in the skill (list).
- The skill is abstract, modular, and reusable. Specifically, the skill name must be generic under one application (e.g., `spotify get songs by genre` instead of `get pop songs`). The skill must use parameters instead of hard-coded values (e.g., specific email address "jay@gmail.com"). The skill body must be self-contained.
- Explicitly declare the key parameters and the final output data types using type hints. Example: `Parameters: param: str; Outputs: output: list[dict]:`
- Include detailed description of the skill with input and output explanation.
- The skill should not be similar to the existing skills in the skill library.
- The skill must involve multiple processing steps. Simply using the result of an API call without additional logic does not qualify as a valid skill.
- Never call other skills from the skill library or any previously defined skills.
- Do not import any Python packages.
- Avoid a functional style; there's no need to use return.

# Good skill:

{
    "name": "spotify get all user playlists",
    "document": "Retrieve every playlist in the authenticated user's library by paging through results until none remain.\\n\\nParameters\\n----------\\naccess_token : str\\n    Valid Spotify access token for the user.\\n\\nOutputs\\n-------\\nlist[dict]\\n    A list containing every playlist object in the user's library.\\n\\nNotes:\\n-------\\n1. Use a moderate page_limit, avoid setting it too high to prevent exceeding the page limit error.\\n2. Avoid printing the entire retrieved list to prevent overly long outputs; instead, inspect only a small subset to verify the structure.\\n",
    "content": "playlists = []\\n\\npage = 0\\nwhile True:\\n    batch = apis.spotify.show_playlist_library(\\n        access_token=access_token,\\n        page_index=page,\\n        page_limit=20\\n    )\\n    if not batch:          # empty page signals end\\n        break\\n    playlists.extend(batch)\\n    page += 1",
    "tools": ["apis.spotify.show_playlist_library"]
}

---

# Focus
1. Focus on skills with similar names and similar skillality.
2. Carefully analyze the concrete implementation differences between similar skills.

# Merge Guidelines
1. **Generality**: Merge skills that have similar names and similar skillality. The merged skill should use a generic name, and its **Notes** and implementation should cover all plausible variants and edge cases.
2. **Atomicity**: If skills have a containment relationship (one skill's skillality subsumes or builds on another), follow the skill definitions to preserve atomicity and avoid merging.
3. **Merge Constraints**: Any merged skill must comply with the skill definition rules, especially atomicity and reusability-and should avoid being tied to a specific task or scenario.

# Decompose Guidelines
1. **Atomicity**: Only decompose skills whose skillality are overly complex (e.g., they include skillality already covered by other provided skills) into smaller sub-skills.
2. **Generality**: The decomposed skills must follow the skill-definition rules and remain reusable—avoid coupling them to any specific task or scenario.

# Output Format
Output a list containing the skills (with one or multiple skills) from merging and/or decomposing the skills in the input skill list as follows:
<skill>
[
    "skill 1",
    ...
]
</skill>

Note: You don't necessarily need to both merge and decompose. You may choose to only merge them into a single skill.
"""
