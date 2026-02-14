# PDF Navigator (Local-First)

PDF Navigator is an offline-first app for exploring **semantic relevance across PDF pages** as a smooth timeline wave + heatmap.

## Architecture & Stack (with reasoning)

- **Backend**: FastAPI + SQLite + SQLAlchemy
  - Fast local API, easy async-friendly expansion, and robust local persistence.
- **PDF ingestion**: `pypdf`
  - Simple local text extraction per page.
- **Embeddings abstraction**:
  - Default: `sentence-transformers` if available.
  - Fallback (fully offline, no model download): sklearn `HashingVectorizer` embeddings.
  - This keeps MVP reliable and runnable without paid APIs.
- **Frontend**: vanilla HTML/CSS/JS
  - Lightweight, no build step required, easy local deployment.
- **Desktop option**: `pywebview`
  - Wraps local web app in a native desktop window.

## Features

- Import PDF locally.
- Typed semantic query.
- Optional voice dictation via browser SpeechRecognition API.
- Relevance wave timeline across full page range.
- Heatmap intensity behind wave.
- Click timeline to jump PDF page.
- Right panel with top snippets + page + confidence.
- Controls for smoothing, threshold, top-K.
- Search history per PDF.
- Export result payload to JSON and top-page scores to CSV.

## Project structure

```
app/
  main.py            # FastAPI routes
  desktop.py         # Desktop launcher (pywebview)
core/
  config.py          # Paths
  db.py              # SQLite models
  embeddings.py      # Embedding backend abstraction
  search.py          # Chunking, scoring, smoothing logic
frontend/
  index.html
  styles.css
  app.js
scripts/
  ingest_sample.py   # ingest helper script
tests/
  test_scoring.py
  test_integration.py
```

## How search scoring works

1. Extract text per page.
2. Chunk each page into overlapping text windows.
3. Embed chunks (local backend).
4. Embed query and compute cosine similarity vs each chunk.
5. Aggregate chunk similarities to page scores (max by default).
6. Normalize page scores to [0,1].
7. Apply Gaussian smoothing (sigma from UI slider).
8. Re-normalize and filter by threshold/top-K.

## Controls behavior

- **Smoothing**: larger value = broader, smoother relevance wave.
- **Threshold**: hide low-score pages.
- **Top K**: cap number of high-priority pages/snippets.

## Install

### macOS / Linux

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[test]
# Optional richer local semantic embeddings
pip install -e .[local-embeddings]
```

### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[test]
# Optional
pip install -e .[local-embeddings]
```

## Run (web mode)

```bash
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000

## Run (desktop mode)

```bash
python -m app.desktop
```

## Ingest PDFs

- Use file picker in UI, or:

```bash
python scripts/ingest_sample.py /path/to/your.pdf
```

## Export

Use **Export JSON/CSV** button after a search. Files are saved to `data/exports/`.

## Voice dictation

- Click microphone button.
- Uses browser Web Speech API when available.
- If unavailable, typed input remains fully supported.

## Tests

```bash
pytest -q
```

## Troubleshooting

- **Some pages empty**: scanned/image PDFs need OCR (future enhancement).
- **Low semantic quality**: install `sentence-transformers` optional dependency.
- **Slow on huge PDFs**: use higher threshold/lower top-K and ingest once (cached vectors).
- **No mic support**: browser may not expose SpeechRecognition; typed mode still works.
- **`pip install -e .[test]` fails with `Multiple top-level packages discovered`**: use the latest repo version that explicitly sets setuptools packages in `pyproject.toml` (no auto-discovery), then rerun install.
- **Still seeing the same error after pulling?** You may be in the wrong nested folder from a ZIP extract (e.g. `.../PDF-navigate-main/PDF-navigate-main`). Run commands in the folder that directly contains `pyproject.toml`, `app/`, and `core/`.

## Security / privacy

- Local-first by default.
- No PDF upload to external services.
- Optional cloud embeddings can be added later behind explicit env configuration.

## Future enhancements

- OCR pipeline (Tesseract/PaddleOCR) for scanned PDFs.
- True PDF text-region highlighting using pdf.js text layer coordinates.
- Background job queue + progress bars per page.
- FAISS/HNSW index for very large corpora.
- Multi-document library search.
