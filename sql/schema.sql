-- Veritas AI application schema.
-- Run against the `veritas` Postgres database (separate from n8n's own
-- internal database, which n8n manages itself).

CREATE TABLE IF NOT EXISTS projects (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  source_query TEXT,
  status TEXT NOT NULL,               -- INGESTED | CITED | TAXONOMY_LOCKED |
                                      -- CLASSIFYING | SCREENED | SYNTHESIZED | DONE
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS documents (
  id SERIAL PRIMARY KEY,
  project_id INTEGER REFERENCES projects(id),
  doi TEXT,
  title TEXT,
  authors TEXT,
  year INTEGER,
  abstract TEXT,
  citep TEXT,                         -- resolved citation key
  citep_status TEXT,                  -- RESOLVED | PENDING | FAILED
  cluster_id INTEGER,
  cluster_confidence REAL,
  is_primary_research BOOLEAN,        -- false = survey/review
  screening_reason TEXT,
  qdrant_point_id TEXT,               -- link to the embedded vector (Layer 6)
  UNIQUE(project_id, doi)
);

CREATE TABLE IF NOT EXISTS clusters (
  id SERIAL PRIMARY KEY,
  project_id INTEGER REFERENCES projects(id),
  title TEXT,
  description TEXT,
  locked BOOLEAN DEFAULT false         -- frozen after human gate
);

ALTER TABLE documents
  ADD CONSTRAINT fk_documents_cluster
  FOREIGN KEY (cluster_id) REFERENCES clusters(id)
  DEFERRABLE INITIALLY DEFERRED;

CREATE TABLE IF NOT EXISTS batches (                -- backbone of the audit trail
  id SERIAL PRIMARY KEY,
  project_id INTEGER REFERENCES projects(id),
  type TEXT,                          -- CITEP | CLASSIFY | SYNTHESIZE
  seq INTEGER,
  doc_ids JSONB,                      -- array, length <= 10, sliced in code
  model TEXT,
  temperature REAL DEFAULT 0,
  raw_prompt TEXT,
  raw_response TEXT,
  status TEXT,                        -- VALIDATED | RETRY | FAILED | HUMAN_REVIEW
  validation_errors TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS consensus_votes (        -- multi-model agreement record
  id SERIAL PRIMARY KEY,
  doc_id INTEGER REFERENCES documents(id),
  model TEXT,
  cluster_id INTEGER REFERENCES clusters(id),
  batch_id INTEGER REFERENCES batches(id)
);

CREATE TABLE IF NOT EXISTS insights (
  id SERIAL PRIMARY KEY,
  project_id INTEGER REFERENCES projects(id),
  cluster_id INTEGER REFERENCES clusters(id),
  batch_id INTEGER REFERENCES batches(id),
  differences TEXT,
  similarities TEXT,
  paragraph TEXT
);

CREATE INDEX IF NOT EXISTS idx_documents_project ON documents(project_id);
CREATE INDEX IF NOT EXISTS idx_documents_cluster ON documents(cluster_id);
CREATE INDEX IF NOT EXISTS idx_batches_project ON batches(project_id);
CREATE INDEX IF NOT EXISTS idx_insights_cluster ON insights(cluster_id);
