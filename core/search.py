from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from pypdf import PdfReader


def chunk_text(text: str, chunk_size: int = 420, overlap: int = 60) -> list[str]:
    if not text.strip():
        return [""]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


def extract_pages(pdf_path: str) -> list[str]:
    reader = PdfReader(pdf_path)
    pages: list[str] = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return pages


def cosine_similarity(query_vec: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    return np.dot(matrix, query_vec)


def page_scores_from_chunk_scores(page_chunk_scores: list[np.ndarray], agg: str = "max") -> np.ndarray:
    scores = []
    for arr in page_chunk_scores:
        if arr.size == 0:
            scores.append(0.0)
            continue
        if agg == "mean":
            scores.append(float(np.mean(arr)))
        else:
            scores.append(float(np.max(arr)))
    return np.array(scores, dtype=np.float32)


def normalize_scores(scores: np.ndarray) -> np.ndarray:
    if scores.size == 0:
        return scores
    min_v = float(np.min(scores))
    max_v = float(np.max(scores))
    if max_v - min_v < 1e-8:
        return np.zeros_like(scores)
    return (scores - min_v) / (max_v - min_v)


def gaussian_kernel(radius: int, sigma: float) -> np.ndarray:
    x = np.arange(-radius, radius + 1)
    kernel = np.exp(-0.5 * (x / max(sigma, 1e-6)) ** 2)
    return kernel / kernel.sum()


def smooth_scores(scores: np.ndarray, sigma: float) -> np.ndarray:
    if sigma <= 0:
        return scores
    radius = int(max(1, sigma * 2))
    kernel = gaussian_kernel(radius, sigma)
    padded = np.pad(scores, (radius, radius), mode="edge")
    smooth = np.convolve(padded, kernel, mode="same")
    return smooth[radius:-radius]


@dataclass
class SearchResult:
    page_scores: list[float]
    smoothed_scores: list[float]
    passages: list[dict]


def top_passages_for_page(chunks: list[str], chunk_scores: np.ndarray, page_number: int, top_n: int = 2) -> list[dict]:
    order = np.argsort(chunk_scores)[::-1][:top_n]
    results = []
    for idx in order:
        snippet = chunks[int(idx)].replace("\n", " ")[:220]
        results.append(
            {
                "page": page_number,
                "chunk_index": int(idx),
                "score": float(chunk_scores[int(idx)]),
                "snippet": snippet,
            }
        )
    return results
