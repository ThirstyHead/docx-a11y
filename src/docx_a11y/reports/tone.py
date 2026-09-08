"""Social model tone phrasing, who-benefits mappings, and language guards."""

# Approved "Who Benefits" statements grounded in the Social Model of Disability
WHO_MAP = {
    "1.1.1": (
        "People who are blind, have low vision, or process information through audio now receive the complete "
        "message through spoken screen reader narration or braille displays."
    ),
    "1.3.1": (
        "People navigating by screen reader, or individuals who benefit from clean, predictable structure, "
        "can follow headings, table headers, and document outlines without disorientation."
    ),
    "1.3.2": (
        "People who use screen readers or keyboard-only navigation experience content in the logical order "
        "intended by the author, rather than by accidental visual layering or floating shapes."
    ),
    "1.4.3": (
        "People with low vision, color vision differences, or anyone reading under bright ambient light "
        "can comfortably distinguish text from its background."
    ),
    "2.4.2": (
        "People who navigate documents using title landmarks—such as screen reader users and audiences "
        "scanning lists or window titles—can immediately identify and differentiate documents."
    ),
    "2.4.4": (
        "People listening to links in a list or scanning quickly can instantly understand where each destination "
        "leads without needing to decipher ambiguous phrases."
    ),
    "3.1.1": (
        "People relying on text-to-speech tools or automated translation software will hear the document read "
        "with accurate phonetics, accentuation, and grammatical inflection."
    ),
    "4.1.2": (
        "People using third-party assistive tools receive consistent, reliable names, roles, and values for every "
        "structural and interactive element in the document."
    ),
}

# Approved barrier descriptions emphasizing document deficiencies
RULE_BARRIER_EXPLANATIONS = {
    "title-missing": (
        "The document lacks an embedded title in its metadata properties, meaning file managers and screen "
        "readers identify it only by its raw filename."
    ),
    "language-missing": (
        "Text runs do not declare an explicit language tag, risking incorrect pronunciation by speech tools."
    ),
    "heading-level-skipped": (
        "The heading hierarchy skips one or more levels (such as H1 directly to H3), creating gaps in navigation outlines."
    ),
    "headings-none": (
        "The document contains no semantic heading styles, preventing assistive technology users from skimming by section."
    ),
    "multiple-h1": (
        "The document contains multiple Heading 1 styles, obscuring the primary document title."
    ),
    "image-alt-missing": (
        "This visual asset has neither alternative text nor a decorative marker, leaving screen reader users "
        "unaware of its presence or purpose."
    ),
    "table-header-missing": (
        "The table does not mark its top row as a header row, so screen readers cannot announce column headers as "
        "users move between data cells."
    ),
    "merged-cell": (
        "The table contains merged or split cells, disrupting the two-dimensional grid and causing screen "
        "readers to lose track of column and row relationships."
    ),
    "color-contrast": (
        "The text contrast ratio is below the required 4.5:1 threshold, creating a visual barrier under typical "
        "reading conditions."
    ),
    "link-text-vague": (
        "The hyperlink uses generic anchor text (such as 'click here') rather than describing the destination."
    ),
    "document-restricted-access": (
        "The document has password encryption or Information Rights Management (IRM) enabled, blocking "
        "assistive technologies from accessing its structure."
    ),
}

# Prohibited medical-model and condescending phrases
BANNED_PHRASES = [
    "suffer from",
    "suffers from",
    "handicapped",
    "normal users",
    "regular users",
    "afflicted with",
    "victim of",
    "confined to",
    "inaccessible to disabled",
    "broken document",
    "stupid mistake",
]


def assert_social_model_language(text: str) -> None:
    """Validate that text does not contain prohibited medical model or condescending terminology."""
    lower_text = text.lower()
    for phrase in BANNED_PHRASES:
        if phrase in lower_text:
            raise ValueError(f"Prohibited language detected: '{phrase}'. Adhere strictly to the Social Model.")
