"""Auditor sidecar (Stage 7a / Layer 3 + Layer 5).

Called from the n8n `08-audit.json` workflow via an Execute Command node.
Regex-extracts every citeP referenced in generated insight text and verifies
it exists in the database's resolved citation keys. Any unmatched key is a
hard failure — it must never reach the final report.

Usage:
    python auditor.py --project-id 1 --dsn postgresql://...
"""
from __future__ import annotations

import argparse
import re
import sys

import psycopg2

# citeP references appear in synthesized text as e.g. [smith2024iot] or
# \cite{smith2024iot}; adjust to match the Synthesizer Agent's exact format.
_CITEP_REF_RE = re.compile(r"\[([a-zA-Z0-9_\-]+)\]|\\cite\{([a-zA-Z0-9_\-]+)\}")


def extract_citeps(text: str) -> set[str]:
    found = set()
    for m in _CITEP_REF_RE.finditer(text or ""):
        found.add(m.group(1) or m.group(2))
    return found


def audit_project(dsn: str, project_id: int) -> dict:
    conn = psycopg2.connect(dsn)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT citep FROM documents WHERE project_id = %s AND citep IS NOT NULL",
                (project_id,),
            )
            valid_keys = {row[0] for row in cur.fetchall()}

            cur.execute(
                "SELECT id, paragraph, differences, similarities FROM insights WHERE project_id = %s",
                (project_id,),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    unmatched: dict[int, list[str]] = {}
    total_refs = 0
    for insight_id, paragraph, differences, similarities in rows:
        refs = set()
        for field in (paragraph, differences, similarities):
            refs |= extract_citeps(field)
        total_refs += len(refs)
        bad = sorted(refs - valid_keys)
        if bad:
            unmatched[insight_id] = bad

    return {
        "project_id": project_id,
        "valid_key_count": len(valid_keys),
        "total_citations_checked": total_refs,
        "unmatched_by_insight": unmatched,
        "citation_validity_rate": (
            1.0 if total_refs == 0 else 1 - sum(len(v) for v in unmatched.values()) / total_refs
        ),
        "passed": len(unmatched) == 0,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-id", type=int, required=True)
    parser.add_argument("--dsn", required=True, help="Postgres connection string")
    args = parser.parse_args()

    report = audit_project(args.dsn, args.project_id)
    print(report)
    sys.exit(0 if report["passed"] else 1)
