"""
Phase 8, Feature 2: User Context Engine — Persona-Aware Prompt Injection

Shared module that builds dynamic prompt modifiers based on the user's
skill level, preferred language, and goal. Used by both the chatbot
(Architect Agent) and the Explain endpoint.
"""

from pydantic import BaseModel


class UserProfile(BaseModel):
    level: str = "junior"       # "student" | "junior" | "senior"
    language: str = "English"   # "English" | "Hindi" | "Tamil" | "Hinglish" | ...
    goal: str = "contributing"  # "learning" | "contributing"


# ── Level modifiers ──────────────────────────────────────────────────────

_LEVEL_MODIFIERS: dict[str, str] = {
    "student": (
        "The user is a FIRST-YEAR STUDENT. "
        "Explain using simple real-world analogies (cooking, traffic, school). "
        "Avoid jargon — if you must use a technical term, immediately define it. "
        "Be warm, encouraging, and patient. Use emojis sparingly to keep it friendly."
    ),
    "junior": (
        "The user is a JUNIOR DEVELOPER with some coding experience. "
        "Use clear, practical explanations. Define technical terms briefly on first use. "
        "Include code snippets where helpful."
    ),
    "senior": (
        "The user is a SENIOR ENGINEER. "
        "Be concise and technical. Skip basic explanations. "
        "Focus on edge cases, architectural tradeoffs, and performance implications. "
        "No hand-holding."
    ),
}

# ── Goal modifiers ───────────────────────────────────────────────────────

_GOAL_MODIFIERS: dict[str, str] = {
    "learning": (
        "The user's goal is LEARNING. Include 'why' explanations, "
        "useful mental models, and suggest further reading or related concepts."
    ),
    "contributing": (
        "The user's goal is CONTRIBUTING code. Focus on actionable steps, "
        "exact file locations, and specific code changes to make."
    ),
}

# ── Language modifier ────────────────────────────────────────────────────

def _language_modifier(language: str) -> str:
    """Build a linguistic instruction for the given language."""
    if language.lower() == "english":
        return ""
    if language.lower() == "hinglish":
        return (
            "LINGUISTIC INSTRUCTION: Output in Hinglish — use Roman script "
            "with common English technical terms (e.g., 'Function call kar raha hai'). "
            "Keep code blocks and technical identifiers in English."
        )
    return (
        f"LINGUISTIC INSTRUCTION: Output all explanations in {language}. "
        "Keep code blocks, variable names, and technical identifiers in English."
    )


def build_persona_modifier(profile: UserProfile | None) -> str:
    """
    Build a prompt suffix string from a UserProfile.
    Returns empty string if profile is None.
    """
    if profile is None:
        return ""

    parts: list[str] = []

    # Level
    level_mod = _LEVEL_MODIFIERS.get(profile.level.lower(), _LEVEL_MODIFIERS["junior"])
    parts.append(level_mod)

    # Goal
    goal_mod = _GOAL_MODIFIERS.get(profile.goal.lower(), _GOAL_MODIFIERS["contributing"])
    parts.append(goal_mod)

    # Language
    lang_mod = _language_modifier(profile.language)
    if lang_mod:
        parts.append(lang_mod)

    return "\n\n".join(parts)
