# Architecture (mirrors the Notion blueprint)

Source of truth: Notion page "Veritas AI — Project Blueprint (Report
Source)", Section 4. Keep this file in sync with that page — it should be a
short pointer, not a fork.

## Layers

1. Deterministic micro-batching — enforced in n8n Code nodes, never prompts.
2. Closed-set structured outputs — JSON-Schema Structured Output Parser +
   Code-node re-validation.
3. Ground-truth citation validation — `.bib` parsed in code; Auditor
   sidecar regex-verifies every citeP against the database.
4. Multi-model consensus — two models vote on classification; disagreement
   routes to a human review tray.
5. Total audit trail — n8n execution history stores every raw prompt/
   response per batch; reproducibility hash per project.
6. Retrieval grounding (Qdrant + NVIDIA NIM) — embeddings ground the
   Synthesizer's claims and catch near-duplicate documents at ingestion.
   Retrieval aid only; cluster assignment always flows through the
   closed-set classifier in Layer 2, never vector proximity.

## Stage -> component mapping

| Stage | n8n workflow | Heavy logic |
| --- | --- | --- |
| Ingest | `01-ingest.json` | Code node: CSV parse + dedup |
| Citation keys | `02-citep.json` | Code node: `.bib` parse; LLM lookup |
| Embed + index | `03-embed-index.json` | NIM embeddings -> Qdrant upsert |
| Taxonomy | `04-taxonomy.json` | 2x LLM brainstorm + human lock (Wait node) |
| Classification | `05-classify.json` | 2x LLM consensus + closed-set validation |
| Screening | `06-screen.json` | LLM + Code node flag/reason |
| Synthesis | `07-synthesize.json` | Qdrant retrieval (RAG) + LLM + citeP check |
| Audit | `08-audit.json` | Python sidecar: `auditor.py` |
| Report | `09-report.json` | Python sidecar: `report_export.py` |

Evaluation (Cohen's kappa vs manual SLR, reproducibility reruns) runs
outside n8n entirely, in `python/evaluation/`.
