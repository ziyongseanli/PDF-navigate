from pathlib import Path

from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas

from app.main import app


def make_pdf(path: Path) -> None:
    c = canvas.Canvas(str(path))
    c.drawString(100, 750, "This page discusses machine learning for medical diagnosis.")
    c.showPage()
    c.drawString(100, 750, "This section explains cooking recipes and ingredients.")
    c.showPage()
    c.save()


def test_ingest_and_search(tmp_path):
    client = TestClient(app)
    pdf = tmp_path / "sample.pdf"
    make_pdf(pdf)

    with pdf.open("rb") as f:
        up = client.post("/api/upload", files={"file": ("sample.pdf", f, "application/pdf")})
    assert up.status_code == 200
    doc_id = up.json()["document_id"]

    resp = client.post(
        "/api/search",
        json={"document_id": doc_id, "query": "medical model", "smoothing": 1.0, "threshold": 0.0, "top_k": 2},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["smoothed_scores"]) == 2
