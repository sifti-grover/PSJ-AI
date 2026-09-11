"""Parse a .bib file into a ground-truth citation-key set.

Used by the Citation stage (Layer 3: ground-truth citation validation).
The Citation Agent performs *lookup*, never generation: it must return a key
that exists in the set produced here.
"""
from __future__ import annotations

import re
from pathlib import Path

# Matches the citation key immediately after any BibTeX entry type, e.g.
# @article{smith2024iot,  ->  "smith2024iot"
_ENTRY_KEY_RE = re.compile(r"@\w+\{\s*([^,\s]+)\s*,", re.MULTILINE)


def parse_bib_keys(bib_path: str | Path) -> set[str]:
    """Return the set of all citation keys declared in a .bib file."""
    text = Path(bib_path).read_text(encoding="utf-8", errors="replace")
    return set(_ENTRY_KEY_RE.findall(text))


def resolve_doi_to_key(doi: str, bib_text: str, keys: set[str]) -> str | None:
    """Best-effort lookup of the citation key for a given DOI within the
    raw .bib text. Returns None if no entry references the DOI — callers
    must treat that as PENDING/FAILED, never guess a key.
    """
    for key in keys:
        # Find this entry's block and check whether it references the DOI.
        pattern = re.compile(
            rf"@\w+\{{\s*{re.escape(key)}\s*,.*?\n\}}", re.DOTALL
        )
        match = pattern.search(bib_text)
        if match and doi.lower() in match.group(0).lower():
            return key
    return None


if __name__ == "__main__":
    import sys

    keys = parse_bib_keys(sys.argv[1])
    print(f"Found {len(keys)} citation keys")
