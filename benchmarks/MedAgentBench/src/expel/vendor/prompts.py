# Prompt constants vendored/adapted from ExpeL (arXiv 2308.10144).
# Sources: ExpeL/prompts/templates/human.py and benchmark-specific prompt files.
# System prompts are adapted for FHIR/medical agent context.

SYSTEM_CRITIQUE_COMPARE_PROMPT = (
    "You will be given two previous task trials in which an agent used FHIR APIs "
    "to complete a clinical data retrieval task: one successful and one unsuccessful trial. "
    "You failed the trial either because the answer was incorrect or the agent produced an error."
)

SYSTEM_CRITIQUE_SUCCESS_PROMPT = (
    "You will be given successful task trials in which an agent used FHIR APIs "
    "to complete clinical data retrieval tasks."
)

# Verbatim from ExpeL/prompts/templates/human.py
FORMAT_RULES_OPERATION_TEMPLATE = """\
<OPERATION> <RULE NUMBER>: <RULE>

The available operations are: AGREE (if the existing rule is strongly relevant for the task), REMOVE (if one existing rule is contradictory or similar/duplicated to other existing rules), EDIT (if any existing rule is not general enough or can be enhanced, rewrite and improve it), ADD (add new rules that are very different from existing rules and relevant for other tasks). Each needs to CLOSELY follow their corresponding formatting below (any existing rule not edited, not agreed, nor removed is considered copied):

AGREE <EXISTING RULE NUMBER>: <EXISTING RULE>
REMOVE <EXISTING RULE NUMBER>: <EXISTING RULE>
EDIT <EXISTING RULE NUMBER>: <NEW MODIFIED RULE>
ADD <NEW RULE NUMBER>: <NEW RULE>

Do not mention the trials in the rules because all the rules should be GENERALLY APPLICABLE. Each rule should be concise and easy to follow. Any operation can be used MULTIPLE times. Do at most 4 operations and each existing rule can only get a maximum of 1 operation.\
"""

# Verbatim from ExpeL/prompts/templates/human.py — human_critique_existing_rules_template
HUMAN_CRITIQUE_COMPARE_TEMPLATE = """\
{instruction}
Here are the two previous trials to compare and critique:
TRIAL TASK:
{task}

SUCCESSFUL TRIAL:
{success_history}

FAILED TRIAL:
{fail_history}

Here are the EXISTING RULES:
{existing_rules}

By examining and contrasting to the successful trial, and the list of existing rules, you can perform the following operations: add, edit, remove, or agree so that the new list of rules is GENERAL and HIGH LEVEL critiques of the failed trial or proposed way of Thought so they can be used to avoid similar failures when encountered with different questions in the future. Have an emphasis on critiquing how to perform better Thought and Action. Follow the below format:

{format_ops}
{critique_suffix}\
"""

# Verbatim from ExpeL/prompts/templates/human.py — human_critique_existing_rules_all_success_template
HUMAN_CRITIQUE_SUCCESS_TEMPLATE = """\
{instruction}
Here are the trials:
{success_history}

Here are the EXISTING RULES:
{existing_rules}

By examining the successful trials, and the list of existing rules, you can perform the following operations: add, edit, remove, or agree so that the new list of rules are general and high level insights of the successful trials or proposed way of Thought so they can be used as helpful tips to different tasks in the future. Have an emphasis on tips that help the agent perform better Thought and Action. Follow the below format:

{format_ops}
{critique_suffix}\
"""

# Verbatim from ExpeL/prompts/templates/human.py — CRITIQUE_SUMMARY_SUFFIX
CRITIQUE_SUFFIX = {
    "full": (
        "Focus on REMOVE rules first, and stop ADD rule unless the new rule is VERY insightful "
        "and different from EXISTING RULES. Below are the operations you do to the above list of EXISTING RULES:"
    ),
    "not_full": "Below are the operations you do to the above list of EXISTING RULES:",
}

# FHIR/medical framing replacing ExpeL's benchmark-specific RULE_TEMPLATE
RULE_INJECTION_TEMPLATE = (
    "The following are insights (in decreasing order of importance) extracted from past "
    "FHIR API agent tasks. Use these as references to help you perform better:\n{rules}"
)
