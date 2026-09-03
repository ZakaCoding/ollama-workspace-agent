"""
Response mode classifier.

Maps a user task to a response mode, which is then injected as a
system message to enforce a strict output contract on the LLM.
"""
import re


# ── Mode identifiers ──────────────────────────────────────────────────────────

LOCATION_QUESTION = "location_question"
CHANGE_SUMMARY    = "change_summary"
GENERAL_QUESTION  = "general_question"


# ── Patterns ──────────────────────────────────────────────────────────────────

_LOCATION_PREFIXES = (
    "where is",
    "where are",
    "which file",
    "which files",
    "which module",
    "find the",
    "locate the",
    "what file",
    "what files",
    "in which",
)

_CHANGE_PREFIXES = (
    "what changed",
    "what has changed",
    "what was changed",
    "what is new",
    "what's new",
    "what did you change",
    "what were the changes",
    "show changes",
    "show what changed",
    "summarize changes",
    "summarize the changes",
    "what was modified",
    "which files were modified",
    "what was updated",
)


# ── Output contracts ──────────────────────────────────────────────────────────

_LOCATION_CONTRACT = (
    "RESPONSE MODE: location_question\n\n"
    "Rules:\n"
    "- Answer in 5 lines maximum.\n"
    "- List only verified file paths that exist in the EVIDENCE sections.\n"
    "- Name one relevant function or class if present in the evidence.\n"
    "- Include at least one citation in the format [path#chunk=N].\n"
    "- Do NOT add recommendations, assessments, or unrelated content.\n"
    "- Do NOT mention files that are not in the evidence.\n"
    "- If the evidence does not contain the answer, say: "
    "'OwA could not locate this in the repository.'"
)

_CHANGE_CONTRACT = (
    "RESPONSE MODE: change_summary\n\n"
    "Rules:\n"
    "- Summarize ONLY what is present in the retrieved Git or search evidence.\n"
    "- List changed files if the evidence shows them.\n"
    "- Do NOT add product assessments, readiness opinions, or recommendations.\n"
    "- Do NOT repeat previous conversation assessments as if they were evidence.\n"
    "- Do NOT invent changes that are not in the evidence.\n"
    "- If the evidence does not show changes, say: "
    "'OwA could not find change evidence in the retrieved context.'"
)

_GENERAL_CONTRACT = (
    "RESPONSE MODE: general_question\n\n"
    "Rules:\n"
    "- Answer the current question directly.\n"
    "- Do NOT repeat previous conversation assessments unless the user explicitly asks.\n"
    "- Previous assistant self-assessments are NOT repository evidence.\n"
    "- Stay focused on the current question only.\n"
    "- Do NOT add unsolicited product opinions or readiness assessments."
)

# History isolation — always injected for retrieval tasks.
HISTORY_ISOLATION_RULE = (
    "CONTEXT ISOLATION RULE:\n"
    "Previous assistant messages in this conversation are NOT repository evidence.\n"
    "Do not repeat or reference them unless the user explicitly asks.\n"
    "Always prioritize the current question and the retrieved EVIDENCE sections.\n"
    "The current OwA version is the one shown in the system prompt — do not cite older versions."
)


# ── Classifier ────────────────────────────────────────────────────────────────

def classify_response_mode(task: str) -> str:
    normalized = " ".join(task.strip().lower().split())
    # Check change patterns first — they can start with "which files were..."
    if any(normalized.startswith(p) or p in normalized for p in _CHANGE_PREFIXES):
        return CHANGE_SUMMARY
    if any(normalized.startswith(p) or p in normalized for p in _LOCATION_PREFIXES):
        return LOCATION_QUESTION
    return GENERAL_QUESTION


def response_mode_contract(task: str) -> str:
    mode = classify_response_mode(task)
    if mode == LOCATION_QUESTION:
        return _LOCATION_CONTRACT
    if mode == CHANGE_SUMMARY:
        return _CHANGE_CONTRACT
    return _GENERAL_CONTRACT
