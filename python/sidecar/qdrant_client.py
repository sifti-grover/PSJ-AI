"""Layer 6 helper: NVIDIA NIM embeddings + Qdrant upsert/query.

Called from the `03-embed-index.json` (index) and `07-synthesize.json`
(retrieve) n8n workflows via HTTP Request / Execute Command nodes.
Strictly a retrieval aid: results returned here are context for the
Synthesizer Agent, never a cluster/label decision.
"""
from __future__ import annotations

import os
from typing import Any

import requests
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

NIM_BASE_URL = os.environ.get("NVIDIA_NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
NIM_API_KEY = os.environ.get("NVIDIA_NIM_API_KEY", "")
NIM_EMBED_MODEL = os.environ.get("NVIDIA_NIM_EMBED_MODEL", "nvidia/nv-embedqa-e5-v5")
COLLECTION = os.environ.get("QDRANT_COLLECTION", "veritas_documents")
EMBED_DIM = 1024  # adjust to match the chosen NIM embedding model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Call the NVIDIA NIM (OpenAI-compatible) embeddings endpoint."""
    resp = requests.post(
        f"{NIM_BASE_URL}/embeddings",
        headers={"Authorization": f"Bearer {NIM_API_KEY}"},
        json={"model": NIM_EMBED_MODEL, "input": texts, "input_type": "passage"},
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()["data"]
    return [row["embedding"] for row in data]


def get_client() -> QdrantClient:
    return QdrantClient(
        url=os.environ.get("QDRANT_URL", "http://localhost:6333"),
        api_key=os.environ.get("QDRANT_API_KEY") or None,
    )


def ensure_collection(client: QdrantClient) -> None:
    if not client.collection_exists(COLLECTION):
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
        )


def index_documents(client: QdrantClient, documents: list[dict[str, Any]]) -> None:
    """documents: [{id, project_id, doi, text}, ...]. Embeds and upserts."""
    ensure_collection(client)
    vectors = embed_texts([d["text"] for d in documents])
    points = [
        PointStruct(
            id=d["id"],
            vector=vec,
            payload={"project_id": d["project_id"], "doi": d.get("doi")},
        )
        for d, vec in zip(documents, vectors)
    ]
    client.upsert(collection_name=COLLECTION, points=points)


def find_near_duplicates(client: QdrantClient, doc_id: int, threshold: float = 0.95) -> list[int]:
    """Semantic dedup check (Layer 6). Returns ids of near-duplicate docs."""
    hit = client.retrieve(collection_name=COLLECTION, ids=[doc_id], with_vectors=True)
    if not hit:
        return []
    results = client.search(
        collection_name=COLLECTION,
        query_vector=hit[0].vector,
        limit=5,
        score_threshold=threshold,
    )
    return [r.id for r in results if r.id != doc_id]


def retrieve_context(client: QdrantClient, query_text: str, batch_doc_ids: list[int], top_k: int = 5) -> list[int]:
    """Retrieve the most relevant document ids *within the current locked
    batch only* — grounding must stay scoped to what the Synthesizer is
    already allowed to see (never expands the batch-of-10 boundary).
    """
    vector = embed_texts([query_text])[0]
    results = client.search(
        collection_name=COLLECTION,
        query_vector=vector,
        query_filter={"must": [{"key": "id", "match": {"any": batch_doc_ids}}]},
        limit=top_k,
    )
    return [r.id for r in results]
