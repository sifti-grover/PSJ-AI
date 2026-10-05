"""Insert normalized PSJ AI documents into PostgreSQL."""

from __future__ import annotations

import os
import sys
from typing import Any

import psycopg2
from dotenv import load_dotenv
load_dotenv()


def get_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost").replace("postgres", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "veritas"),
        user=os.getenv("POSTGRES_USER", "veritas"),
        password=os.getenv("POSTGRES_PASSWORD"),
    )


def insert_documents(
    project_id: int,
    records: list[dict[str, Any]],
) -> list[int]:
    conn = get_connection()
    inserted_ids = []

    try:
        with conn:
            with conn.cursor() as cur:
                for record in records:
                    cur.execute(
                        """
                        INSERT INTO documents
                            (project_id, doi, title, authors, year, abstract)
                        VALUES
                            (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (project_id, doi)
                        DO UPDATE SET
                            title = EXCLUDED.title,
                            authors = EXCLUDED.authors,
                            year = EXCLUDED.year,
                            abstract = EXCLUDED.abstract
                        RETURNING id
                        """,
                        (
                            project_id,
                            record.get("doi"),
                            record.get("title"),
                            record.get("authors"),
                            record.get("year"),
                            record.get("abstract"),
                        ),
                    )

                    row = cur.fetchone()
                    if row:
                        inserted_ids.append(row[0])

    finally:
        conn.close()

    return inserted_ids


if __name__ == "__main__":
    print("Database ingestion helper loaded successfully.")
