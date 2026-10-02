"""NVIDIA NIM embeddings + Qdrant indexing and retrieval."""

from __future__ import annotations

import os
from typing import Any

import requests
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

load_dotenv()

NIM_BASE_URL = os.environ.get(
    "NVIDIA_NIM_BASE_URL",
    "https://integrate.api.nvidia.com/v1",
)
NIM_API_KEY = os.environ.get("NVIDIA_NIM_API_KEY", "")
NIM_EMBED_MODEL = os.environ.get(
    "NVIDIA_NIM_EMBED_MODEL",
    "nvidia/nemotron-3-embed-1b",
)
COLLECTION = os.environ.get("QDRANT_COLLECTION", "veritas_documents")
EMBED_DIM = 2048


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate embeddings using NVIDIA NIM."""
    response = requests.post(
        f"{NIM_BASE_URL}/embeddings",
        headers={
            "Authorization": f"Bearer {NIM_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": NIM_EMBED_MODEL,
            "input": texts,
            "input_type": "passage",
        },
        timeout=60,
    )
    response.raise_for_status()

    data = response.json()["data"]
    return [row["embedding"] for row in data]


def get_client() -> QdrantClient:
    """Create a Qdrant client usable from WSL or Docker."""
    url = os.environ.get(
        "QDRANT_URL",
        "http://localhost:6333",
    ).replace(
        "http://qdrant:6333",
        "http://localhost:6333",
    )

    return QdrantClient(
        url=url,
        api_key=os.environ.get("QDRANT_API_KEY") or None,
    )


def ensure_collection(client: QdrantClient) -> None:
    """Create the collection if it does not already exist."""
    if not client.collection_exists(COLLECTION):
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(
                size=EMBED_DIM,
                distance=Distance.COSINE,
            ),
        )


def index_documents(
    client: QdrantClient,
    documents: list[dict[str, Any]],
) -> None:
    """Embed and upsert documents into Qdrant."""
    ensure_collection(client)

    vectors = embed_texts(
        [d["text"] for d in documents]
    )

    points = [
        PointStruct(
            id=d["id"],
            vector=vector,
            payload={
                "project_id": d["project_id"],
                "doi": d.get("doi"),
            },
        )
        for d, vector in zip(documents, vectors)
    ]

    client.upsert(
        collection_name=COLLECTION,
        points=points,
    )


def find_near_duplicates(
    client: QdrantClient,
    doc_id: int,
    threshold: float = 0.95,
) -> list[int]:
    """Return semantic near-duplicate document IDs."""
    hit = client.retrieve(
        collection_name=COLLECTION,
        ids=[doc_id],
        with_vectors=True,
    )

    if not hit:
        return []

    results = client.query_points(
        collection_name=COLLECTION,
        query=hit[0].vector,
        limit=5,
        score_threshold=threshold,
    ).points

    return [
        r.id
        for r in results
        if r.id != doc_id
    ]


def retrieve_context(
    client: QdrantClient,
    query_text: str,
    batch_doc_ids: list[int],
    top_k: int = 5,
) -> list[int]:
    """Retrieve documents only from the supplied batch."""
    vector = embed_texts([query_text])[0]

    results = client.query_points(
        collection_name=COLLECTION,
        query=vector,
        query_filter={
            "must": [
                {
                    "has_id": batch_doc_ids,
                }
            ]
        },
        limit=top_k,
    ).points

    return [r.id for r in results]
def retrieve_context_with_payload(
    client,
    query: str,
    batch_doc_ids: list[int],
    top_k: int = 5,
) -> list[dict]:
    """Retrieve batch-restricted documents with metadata and context."""
    vector = embed_texts([query])[0]

    result = client.query_points(
        collection_name=COLLECTION,
        query=vector,
        limit=top_k,
        with_payload=True,
        query_filter={
            "must": [
                {
                    "has_id": batch_doc_ids
                }
            ]
        },
    )

    output = []

    for point in result.points:
        payload = point.payload or {}

        output.append(
            {
                "document_id": int(point.id),
                "score": float(point.score),
                "doi": payload.get("doi"),
                "title": payload.get("title"),
                "authors": payload.get("authors"),
                "text": payload.get("text"),
            }
        )

    return output
