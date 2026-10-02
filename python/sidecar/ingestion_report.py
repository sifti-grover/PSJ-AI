"""Generate an ingestion summary for a CSV batch and optional project."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from python.sidecar.ingest import load_csv


def build_report(csv_path: str | Path) -> dict[str, Any]:
    """Return deterministic ingestion statistics for a CSV file."""
    import csv

    path = Path(csv_path)

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        raw_rows = list(csv.DictReader(f))

    normalized = load_csv(path)

    missing_doi = sum(1 for row in normalized if not row.get("doi"))
    rows_in = len(raw_rows)
    unique_rows = len(normalized)
    duplicates_dropped = rows_in - unique_rows

    return {
        "file": str(path),
        "rows_in": rows_in,
        "unique_rows": unique_rows,
        "duplicates_dropped": duplicates_dropped,
        "missing_doi": missing_doi,
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(
            "Usage: python -m python.sidecar.ingestion_report <csv_file>"
        )
        raise SystemExit(1)

    report = build_report(sys.argv[1])

    print("=== PSJ AI Ingestion Report ===")
    print(f"File:               {report['file']}")
    print(f"Rows in:            {report['rows_in']}")
    print(f"Unique rows:        {report['unique_rows']}")
    print(f"Duplicates dropped: {report['duplicates_dropped']}")
    print(f"Missing DOI:        {report['missing_doi']}")
