"""Find near-duplicate Qdrant documents and store human-review records."""

from __future__ import annotations

import sys

import psycopg2
from dotenv import load_dotenv

from python.sidecar.qdrant_client import get_client

load_dotenv()

COLLECTION = "veritas_documents"
THRESHOLD = 0.95


def get_db():
    import os

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


def review_project(project_id: int) -> int:
    client = get_client()

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
                (project_id,),
            )
            document_ids = [row[0] for row in cur.fetchall()]

            inserted = 0

            for document_id in document_ids:
                points = client.retrieve(
                    collection_name=COLLECTION,
                    ids=[document_id],
                    with_vectors=True,
                )

                if not points or points[0].vector is None:
                    continue

                vector = points[0].vector

                result = client.query_points(
                    collection_name=COLLECTION,
                    query=vector,
                    limit=10,
                    score_threshold=THRESHOLD,
                    with_payload=True,
                )

                for match in result.points:
                    duplicate_id = int(match.id)

                    if duplicate_id == document_id or document_id > duplicate_id:
                         continue

                    payload = match.payload or {}

                    if payload.get("project_id") != project_id:
                        continue

                    cur.execute(
                        """
                        INSERT INTO near_duplicate_reviews
                            (project_id, document_id, duplicate_document_id,
                             similarity, threshold)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (document_id, duplicate_document_id)
                        DO UPDATE SET
                            similarity = EXCLUDED.similarity,
                            threshold = EXCLUDED.threshold
                        """,
                        (
                            project_id,
                            document_id,
                            duplicate_id,
                            float(match.score),
                            THRESHOLD,
                        ),
                    )

                    inserted += 1

            conn.commit()

    return inserted


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m python.sidecar.duplicate_review <project_id>")
        raise SystemExit(1)

    project_id = int(sys.argv[1])
    count = review_project(project_id)

    print(f"Near-duplicate review records created/updated: {count}")
    print(f"Cosine threshold: {THRESHOLD}")
