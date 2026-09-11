# Veritas AI

A hallucination-constrained multi-agent system for citation-verified insight
extraction from document collections. Validated on a Systematic Literature
Review (SLR) use case against a manually completed, expert-verified ground
truth.

Full design rationale, objectives, evaluation plan, and report-chapter
mapping live in the Notion blueprint page: **"Veritas AI — Project Blueprint
(Report Source)"**. This repo is the implementation companion to that page.

## Architecture (confirmed)

- **Orchestration:** n8n (self-hosted, queue mode) — a deterministic DAG.
  The LLM never controls flow; n8n does.
- **Agents:** n8n LLM nodes (OpenAI / Anthropic, optionally NVIDIA NIM),
  temperature 0, JSON-Schema structured outputs.
- **Validation:** n8n Code nodes (fast checks) + Python sidecar (heavy
  checks: citation audit, evaluation).
- **Retrieval grounding (Layer 6):** Qdrant vector store, embeddings via
  NVIDIA NIM NeMo Retriever models. Retrieval aid only — never a decision
  maker; cluster assignment always goes through the closed-set classifier.
- **Database:** PostgreSQL (also backs n8n queue mode).
- **Interface:** n8n Chat Trigger (ChatGPT-style) or CLI via n8n REST API.
  No custom frontend.
- **Evaluation harness:** pure Python (pandas / scikit-learn) — Cohen's
  kappa vs the manual-SLR ground truth, reproducibility reruns.

## Repo layout

```
veritas-ai/
├── docker-compose.yml       # n8n + postgres + redis + qdrant
├── .env.example             # copy to .env and fill in API keys
├── docs/
│   └── architecture.md      # short pointer + diagram (mirrors Notion)
├── sql/
│   └── schema.sql           # projects/documents/clusters/batches/insights
├── n8n/
│   └── workflows/           # one importable workflow skeleton per stage
│       ├── 01-ingest.json
│       ├── 02-citep.json
│       ├── 03-embed-index.json
│       ├── 04-taxonomy.json
│       ├── 05-classify.json
│       ├── 06-screen.json
│       ├── 07-synthesize.json
│       ├── 08-audit.json
│       └── 09-report.json
├── python/
│   ├── requirements.txt
│   ├── sidecar/              # heavy validation + export, called from n8n
│   │   ├── bib_parser.py     # .bib -> ground-truth citation key set
│   │   ├── auditor.py        # regex-verify citeP usage vs DB (Layer 3)
│   │   ├── qdrant_client.py  # NIM embeddings + Qdrant upsert/query (Layer 6)
│   │   └── report_export.py # merge insights -> DOCX/LaTeX/PDF + PRISMA
│   └── evaluation/           # kept outside n8n for rigor and testability
│       ├── agreement.py      # Cohen's kappa vs manual SLR ground truth
│       └── run_eval.py       # CLI entrypoint for the results chapter
└── data/
    ├── uploads/               # incoming CSV / .bib files
    └── exports/               # generated reports, images
```

## Quick start

1. `cp .env.example .env` and fill in `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`,
   `NVIDIA_NIM_API_KEY`, and Postgres/Qdrant credentials.
2. `docker compose up -d` — brings up n8n (queue mode), Postgres, Redis,
   and Qdrant.
3. Run `sql/schema.sql` against the `veritas` Postgres database to create
   the application tables (separate from n8n's own internal database).
4. Open the n8n editor (default `http://localhost:5678`) and import the
   workflow skeletons from `n8n/workflows/` in numeric order; wire each
   stage's Code/LLM nodes per the sticky-note instructions inside it.
5. Install Python dependencies: `pip install -r python/requirements.txt`.
6. Trigger a run via the n8n Chat Trigger URL, or the CLI
   (`python/evaluation/run_eval.py --help` once a project has run).

## Status

This is a scaffold: folder structure, schema, Docker config, and one
importable sticky-note skeleton per pipeline stage. Node-by-node workflow
logic, agent prompts, and JSON-Schema output parsers are implemented next.
