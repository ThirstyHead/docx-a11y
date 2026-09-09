"""Source document immutability and provenance tracking.

Delegates core verification to engine_a11y.immutability.
"""
from engine_a11y.immutability import (
    assert_not_same_path,
    assert_source_unchanged,
    get_remediated_path,
    sha256_file,
    verify_immutability,
)

__all__ = [
    "sha256_file",
    "assert_source_unchanged",
    "assert_not_same_path",
    "get_remediated_path",
    "verify_immutability",
]
