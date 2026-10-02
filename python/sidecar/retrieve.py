"""PSJ AI batch-restricted semantic retrieval."""

from __future__ import annotations

import argparse
import os

import psycopg2
from dotenv import load_dotenv

from python.sidecar.qdrant_client import get_client, retrieve_context

load_dotenv()


def get_db():
    host = os.getenv("POSTGRES_HOST", "localhost")
    if host == "postgres":
        host = "localhost"

    return psycopg2.connect(
        host=host,
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "veritas"),
        user=os.getenv("POSTGRES_USER", "veritas"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--project-id", type=int, required=True)
    parser.add_argument("--top-k", type=int, default=5)

    args = parser.parse_args()

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id
                FROM documents
                WHERE project_id = %s
                  AND qdrant_point_id IS NOT NULL
                ORDER BY id
                """,
                (args.project_id,),
            )
            allowed_ids = [row[0] for row in cur.fetchall()]

            cur.execute(
                """
                SELECT id, title, doi
                FROM documents
                WHERE project_id = %s
                """,
                (args.project_id,),
            )
            metadata = {
                row[0]: {
                    "title": row[1],
                    "doi": row[2],
                }
                for row in cur.fetchall()
            }

    client = get_client()

    results = retrieve_context(
        client,
        args.query,
        allowed_ids,
        top_k=args.top_k,
    )

    print("=== PSJ AI Semantic Retrieval ===")
    print(f"Project: {args.project_id}")
    print(f"Query: {args.query}")
    print(f"Allowed documents: {len(allowed_ids)}")
    print()

    for rank, document_id in enumerate(results, 1):
        info = metadata.get(document_id, {})
        print(f"{rank}. Document ID: {document_id}")
        print(f"   Title: {info.get('title')}")
        print(f"   DOI: {info.get('doi')}")
        print()


if __name__ == "__main__":
    main()
