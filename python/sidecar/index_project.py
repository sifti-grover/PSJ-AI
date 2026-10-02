"""Index a PostgreSQL project into NVIDIA NIM + Qdrant."""

from __future__ import annotations

import os

import psycopg2
from dotenv import load_dotenv
from qdrant_client.models import PointStruct

from python.sidecar.qdrant_client import (
    COLLECTION,
    embed_texts,
    get_client,
)

load_dotenv()

BATCH_SIZE = 25


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


def index_project(project_id: int):
    client = get_client()

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, project_id, doi, title, authors, abstract
                FROM documents
                WHERE project_id = %s
                  AND qdrant_point_id IS NULL
                ORDER BY id
                """,
                (project_id,),
            )

            documents = cur.fetchall()

            print(f"Documents to index: {len(documents)}")

            for start in range(0, len(documents), BATCH_SIZE):
                batch = documents[start:start + BATCH_SIZE]

                texts = [
                    "\n".join(
                        str(value)
                        for value in (title, authors, abstract)
                        if value
                    )
                    for _, _, _, title, authors, abstract in batch
                ]

                print(
                    f"Embedding documents "
                    f"{start + 1}-{start + len(batch)}..."
                )

                vectors = embed_texts(texts)

                points = []

                for row, text, vector in zip(batch, texts, vectors):
                    doc_id, proj_id, doi, title, authors, abstract = row

                    points.append(
                        PointStruct(
                            id=doc_id,
                            vector=vector,
                            payload={
                                "project_id": proj_id,
                                "doi": doi,
                                "title": title,
                                "authors": authors,
                                "text": text,
                            },
                        )
                    )

                client.upsert(
                    collection_name=COLLECTION,
                    points=points,
                    wait=True,
                )

                for row in batch:
                    doc_id = row[0]

                    cur.execute(
                        """
                        UPDATE documents
                        SET qdrant_point_id = %s
                        WHERE id = %s
                        """,
                        (str(doc_id), doc_id),
                    )

                conn.commit()

                print(
                    f"Indexed {start + len(batch)}/{len(documents)}"
                )

    print("Indexing complete.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python -m python.sidecar.index_project <project_id>")
        raise SystemExit(1)

    index_project(int(sys.argv[1]))
