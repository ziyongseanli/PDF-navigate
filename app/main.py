from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from core.config import PDF_DIR
from core.db import Document, Page, QueryHistory, SessionLocal, init_db
from core.embeddings import EmbeddingService
from core.search import (
    chunk_text,
    cosine_similarity,
    extract_pages,
    normalize_scores,
    page_scores_from_chunk_scores,
    smooth_scores,
    top_passages_for_page,
)

app = FastAPI(title="PDF Navigator")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

init_db()
embeddings = EmbeddingService.build_default()

frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/assets", StaticFiles(directory=frontend_dir), name="assets")


class QueryRequest(BaseModel):
    document_id: int
    query: str
    smoothing: float = 2.0
    threshold: float = 0.0
    top_k: int = 10


@app.get("/")
def root() -> FileResponse:
    return FileResponse(frontend_dir / "index.html")


@app.post("/api/upload")
def upload_pdf(file: UploadFile = File(...)) -> dict:
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    target = PDF_DIR / file.filename
    with target.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    pages = extract_pages(str(target))

    with SessionLocal() as db:
        doc = Document(filename=file.filename, filepath=str(target), page_count=len(pages))
        db.add(doc)
        db.flush()

        for i, text in enumerate(pages, start=1):
            chunks = chunk_text(text)
            vectors = embeddings.encode(chunks).tolist()
            db.add(
                Page(
                    document_id=doc.id,
                    page_number=i,
                    text=text,
                    chunks=chunks,
                    vectors=vectors,
                )
            )
        db.commit()
        return {"document_id": doc.id, "filename": doc.filename, "page_count": doc.page_count}


@app.get("/api/documents")
def list_documents() -> list[dict]:
    with SessionLocal() as db:
        docs = db.query(Document).all()
        return [{"id": d.id, "filename": d.filename, "page_count": d.page_count} for d in docs]


@app.get("/api/document/{document_id}/file")
def get_pdf(document_id: int) -> FileResponse:
    with SessionLocal() as db:
        doc = db.get(Document, document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        return FileResponse(doc.filepath, media_type="application/pdf")


@app.get("/api/document/{document_id}/history")
def get_history(document_id: int) -> list[dict]:
    with SessionLocal() as db:
        rows = (
            db.query(QueryHistory)
            .filter(QueryHistory.document_id == document_id)
            .order_by(QueryHistory.id.desc())
            .limit(15)
            .all()
        )
    return [
        {
            "query": r.query,
            "smoothing": r.smoothing,
            "threshold": r.threshold,
            "top_k": r.top_k,
        }
        for r in rows
    ]


@app.post("/api/search")
def search(req: QueryRequest) -> dict:
    with SessionLocal() as db:
        pages = db.query(Page).filter(Page.document_id == req.document_id).order_by(Page.page_number).all()
        if not pages:
            raise HTTPException(status_code=404, detail="Document not found")

        qv = embeddings.encode([req.query])[0]
        chunk_scores_per_page: list[np.ndarray] = []
        passages: list[dict] = []

        for p in pages:
            matrix = np.array(p.vectors, dtype=np.float32)
            scores = cosine_similarity(qv, matrix)
            chunk_scores_per_page.append(scores)
            passages.extend(top_passages_for_page(p.chunks, scores, p.page_number, top_n=2))

        raw = page_scores_from_chunk_scores(chunk_scores_per_page)
        norm = normalize_scores(raw)
        smooth = normalize_scores(smooth_scores(norm, req.smoothing))

        ranked = [
            {"page": i + 1, "score": float(s)}
            for i, s in enumerate(smooth)
            if float(s) >= req.threshold
        ]
        ranked.sort(key=lambda x: x["score"], reverse=True)
        ranked = ranked[: req.top_k]

        top_pages = {item["page"] for item in ranked}
        filtered_passages = [
            p for p in sorted(passages, key=lambda x: x["score"], reverse=True) if p["page"] in top_pages
        ][: req.top_k * 2]

        db.add(
            QueryHistory(
                document_id=req.document_id,
                query=req.query,
                smoothing=req.smoothing,
                threshold=req.threshold,
                top_k=req.top_k,
            )
        )
        db.commit()

    return {
        "raw_scores": [float(x) for x in norm],
        "smoothed_scores": [float(x) for x in smooth],
        "top_pages": ranked,
        "passages": filtered_passages,
        "backend": embeddings.backend.name,
    }


@app.post("/api/export/{document_id}")
def export_results(document_id: int, payload: dict) -> dict:
    out_dir = Path("data") / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)

    base = out_dir / f"doc_{document_id}_results"
    json_path = base.with_suffix(".json")
    csv_path = base.with_suffix(".csv")

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    with csv_path.open("w", encoding="utf-8") as f:
        f.write("page,score\n")
        for row in payload.get("top_pages", []):
            f.write(f"{row['page']},{row['score']:.6f}\n")

    return {"json": str(json_path), "csv": str(csv_path)}
