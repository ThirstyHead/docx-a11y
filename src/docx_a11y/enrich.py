"""Report enrichment with official WCAG criterion text.

Delegates core enrichment and MCP fetching to engine_a11y.enrich.
"""
from pathlib import Path
from engine_a11y.enrich import (
    BUNDLED_CACHE,
    PROTOCOL_VERSION,
    SERVER_PATH_ENV,
    SERVER_TOOL,
    Cache,
    build_enrichment,
    fetch_via_server,
    find_server,
    get_criterion_text,
    load_cache_json,
    parse_criterion,
)

# Keep local BUNDLED_CACHE reference if local file exists, otherwise engine cache
LOCAL_CACHE = Path(__file__).resolve().parent / "sc_cache.json"
if LOCAL_CACHE.exists():
    BUNDLED_CACHE = LOCAL_CACHE

__all__ = [
    "BUNDLED_CACHE",
    "SERVER_PATH_ENV",
    "SERVER_TOOL",
    "PROTOCOL_VERSION",
    "find_server",
    "parse_criterion",
    "fetch_via_server",
    "Cache",
    "get_criterion_text",
    "build_enrichment",
    "load_cache_json",
]
