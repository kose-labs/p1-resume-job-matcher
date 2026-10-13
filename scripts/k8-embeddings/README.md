# K8: embedding model comparison

Experiment behind [ADR-0004](../../docs/adr/0004-embedding-model.md). Scores all 900 corpus pairs
with three small embedding models, each chunked (the backend's `EmbeddingMatcher`) and whole-document,
and measures speed and peak memory. Results: [`docs/experiments/k8-embeddings.md`](../../docs/experiments/k8-embeddings.md).

## Run it

```bash
uv sync
uv run python compare.py
```

Needs the corpus (`scripts/k5-corpus`). The first run downloads about 210 MB of model weights into
`models/` and the Hugging Face cache (git-ignored). It prints a Markdown table and writes
`data/scores/<model>-<mode>.csv` for the evaluation script:

```bash
cd ../j2-pairs && uv run python evaluate.py score ../../data/scores/minilm-l6-chunked.csv
```

The script imports the matcher from `backend/app/ml/embeddings.py` directly, so the experiment and
the API use the same code.
