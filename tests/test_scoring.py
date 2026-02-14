import numpy as np

from core.search import normalize_scores, page_scores_from_chunk_scores, smooth_scores


def test_page_aggregation_max():
    arr = [np.array([0.1, 0.8]), np.array([0.2, 0.3])]
    out = page_scores_from_chunk_scores(arr, agg="max")
    assert np.allclose(out, np.array([0.8, 0.3]))


def test_normalize_scores():
    scores = np.array([2.0, 4.0, 6.0])
    norm = normalize_scores(scores)
    assert np.allclose(norm, np.array([0.0, 0.5, 1.0]))


def test_smooth_scores_keeps_shape():
    scores = np.array([0.0, 1.0, 0.0])
    smoothed = smooth_scores(scores, sigma=1.0)
    assert smoothed.shape == scores.shape
    assert smoothed[1] > smoothed[0]
