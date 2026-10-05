"""Robust BibTeX citation-key parser for PSJ AI."""

from __future__ import annotations

import re
from pathlib import Path


ENTRY_RE = re.compile(
    r"@\s*[A-Za-z]+\s*\{\s*([^,\s]+)\s*,",
    re.MULTILINE,
)


def parse_bib_keys(bib_path: str | Path) -> set[str]:
    """Return all citation keys declared in a BibTeX file."""
    text = Path(bib_path).read_text(
        encoding="utf-8",
        errors="replace",
    )

    return {
        key.strip()
        for key in ENTRY_RE.findall(text)
        if key.strip()
    }


def resolve_doi_to_key(
    doi: str,
    bib_text: str,
    keys: set[str],
) -> str | None:
    """Resolve a DOI to its BibTeX citation key."""
    if not doi:
        return None

    doi_normalized = doi.strip().lower()

    matches = list(ENTRY_RE.finditer(bib_text))

    for i, match in enumerate(matches):
        key = match.group(1).strip()

        if key not in keys:
            continue

        start = match.start()
        end = (
            matches[i + 1].start()
            if i + 1 < len(matches)
            else len(bib_text)
        )

        entry = bib_text[start:end].lower()

        if doi_normalized in entry:
            return key

    return None


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print(
            "Usage: python -m "
            "python.sidecar.bib_parser <bib_file>"
        )
        raise SystemExit(1)

    keys = parse_bib_keys(sys.argv[1])
    print(f"Found {len(keys)} citation keys")
