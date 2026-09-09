"""Social model tone phrasing, who-benefits mappings, and language guards.

Delegates to engine_a11y.reports.tone.
"""
from engine_a11y.reports.tone import (
    BANNED_PHRASES,
    RULE_BARRIER_EXPLANATIONS,
    WHO_MAP,
    WORD_ASSISTANT_NOTES,
    assert_social_model_language,
)

__all__ = [
    "WHO_MAP",
    "RULE_BARRIER_EXPLANATIONS",
    "WORD_ASSISTANT_NOTES",
    "BANNED_PHRASES",
    "assert_social_model_language",
]
