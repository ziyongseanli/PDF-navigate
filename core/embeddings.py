from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.preprocessing import normalize


class EmbeddingBackend:
    name = "base"

    def encode(self, texts: list[str]) -> np.ndarray:
        raise NotImplementedError


class SklearnHashingBackend(EmbeddingBackend):
    name = "sklearn-hashing"

    def __init__(self) -> None:
        self.vectorizer = HashingVectorizer(n_features=384, alternate_sign=False, norm=None)

    def encode(self, texts: list[str]) -> np.ndarray:
        matrix = self.vectorizer.transform(texts).toarray().astype(np.float32)
        return normalize(matrix)


class SentenceTransformerBackend(EmbeddingBackend):
    name = "sentence-transformers"

    def __init__(self) -> None:
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer("all-MiniLM-L6-v2")

    def encode(self, texts: list[str]) -> np.ndarray:
        vectors = self.model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        return vectors.astype(np.float32)


@dataclass
class EmbeddingService:
    backend: EmbeddingBackend

    @classmethod
    def build_default(cls) -> "EmbeddingService":
        try:
            backend: EmbeddingBackend = SentenceTransformerBackend()
        except Exception:
            backend = SklearnHashingBackend()
        return cls(backend=backend)

    def encode(self, texts: list[str]) -> np.ndarray:
        return self.backend.encode(texts)
