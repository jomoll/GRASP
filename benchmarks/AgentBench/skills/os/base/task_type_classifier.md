---
name: task_type_classifier
description: Classify a task as execute-and-report vs write-a-command before taking the first action
tags: [os, classification, task_type]
---

# Task Type Classifier

OS Interaction tasks fall into two fundamentally different types that share similar surface
language. Confusing them is one of the most common failure modes: the agent either executes
commands and returns a number when it should output a script, or writes a script when it should
run commands and return the result.

**Before your first OS tool call, classify the task type.** This takes one internal
reasoning step and costs nothing, but prevents a category of failures that cannot be recovered
from once the wrong path is taken.

## When to Use This Skill

Apply at the very start of every OS Interaction task, before issuing any action.

## Task Types

### Type A — Execute and Report

The task asks you to interact with the live environment, run commands, and return the
observed value (a number, string, file path, etc.) as the final answer.

**Signals (any one is sufficient):**
- "how many files / directories / lines / processes"
- "what is the current value of"
- "find and count", "list all", "check the state of"
- "output the result of running"
- Refers to files or state that plausibly exist on the live system

**Action:** Execute commands with `bash_action`, observe real output, submit the
value with `answer_action`.

### Type B — Write a Command or Script

The task asks you to produce a command, one-liner, or script **as the answer itself**.
You are not expected to run it to get a result; the command text is the deliverable.

**Signals (any one is sufficient):**
- "write a command that would ...", "write a bash script to ..."
- "what command would output / count / list ..."
- "design a prompt", "create a tool that", "write a one-liner"
- Refers to a **hypothetical** or **abstract** resource: "a given directory",
  "a specific file", "a directory named X" where X is clearly a placeholder,
  "N files", "some log file"
- The object of the task does not plausibly exist on the live system

**Action:** Write the command or script directly and submit it with
`answer_action`.
**Do NOT execute it to obtain a numeric result** — the command text is the answer.

## Common Failure Patterns

- **Type B mistaken for Type A:** Task says "write a command to count lines in a given
  directory." Agent runs `wc -l` on a real directory and returns a number. The correct
  answer is the command string, e.g. `find /given_dir -type f | xargs wc -l | tail -1`.

- **Type A mistaken for Type B:** Task says "how many hidden files are in the home
  directory?" Agent outputs a `find` command instead of executing it and returning the count.

- **Placeholder not recognized:** Task says "a target_directory" or "the given log file."
  Agent searches for a literal path named `target_directory` and fails. These are
  placeholders — the task is Type B; the description is the specification for the command
  to write.

## Example Applications

**Task:** "Write a Linux command that counts the number of lines in all `.py` files
under a given directory."

Classification: **Type B** — "a given directory" is a placeholder; task asks for a command.

CORRECT: call `answer_action` with `{"answer": "find /given_dir -name '*.py' | xargs wc -l | tail -1"}`
WRONG:   Execute `wc -l` on a real directory and return an integer.

---

**Task:** "How many subdirectories are in `/home/ubuntu`?"

Classification: **Type A** — refers to a live path, asks for an observed count.

CORRECT: call `bash_action` with `{"script": "find /home/ubuntu -mindepth 1 -maxdepth 1 -type d | wc -l"}`
         then call `answer_action` with the observed result
WRONG:   Output a `find` command string as the answer.

## Success Indicators

- Agent classifies the task type in its first reasoning step.
- Type A tasks end with a numeric or string value obtained from real command output.
- Type B tasks end with a command or script string, not a computed result.

## Failure Indicators

- Agent returns an integer for a Type B task.
- Agent outputs a command string for a Type A task.
- Agent searches for a literal placeholder path (e.g. `find / -name target_directory`).
