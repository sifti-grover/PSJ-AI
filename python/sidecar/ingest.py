"""Deterministic CSV ingestion helper for PSJ AI."""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Any


COLUMN_ALIASES = {
    "doi": ["doi", "DOI"],
    "title": ["title", "Title"],
    "authors": ["authors", "author", "Authors", "Author"],
    "year": ["year", "Year", "publication year", "Publication Year"],
    "abstract": ["abstract", "Abstract"],
}


def find_column(row: dict[str, Any], names: list[str]) -> str | None:
    for name in names:
        if name in row:
            return row[name]
    return None


def normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    doi = find_column(row, COLUMN_ALIASES["doi"])
    title = find_column(row, COLUMN_ALIASES["title"])
    authors = find_column(row, COLUMN_ALIASES["authors"])
    year = find_column(row, COLUMN_ALIASES["year"])
    abstract = find_column(row, COLUMN_ALIASES["abstract"])

    year_value = None
    if year:
        try:
            year_value = int(str(year).strip())
        except ValueError:
            year_value = None

    return {
        "doi": str(doi or "").strip().lower() or None,
        "title": str(title or "").strip() or None,
        "authors": str(authors or "").strip() or None,
        "year": year_value,
        "abstract": str(abstract or "").strip() or None,
    }


def load_csv(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = [normalize_row(row) for row in reader]

    # Remove duplicate DOIs within this batch.
    seen_dois: set[str] = set()
    result = []

    for row in rows:
        doi = row["doi"]

        if doi:
            if doi in seen_dois:
                continue
            seen_dois.add(doi)

        result.append(row)

    return result


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m python.sidecar.ingest <csv_file>")
        sys.exit(1)

    records = load_csv(sys.argv[1])

    print(f"Loaded {len(records)} unique records")

    for i, record in enumerate(records[:3], start=1):
        print(f"{i}: {record}")
