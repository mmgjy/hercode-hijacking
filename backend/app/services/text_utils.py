"""Deterministic, dependency-light text utilities.

We implement TF-IDF vectors, cosine similarity, agglomerative clustering and a
fuzzy ratio in pure Python (stdlib ``difflib`` for fuzziness). This keeps the
whole pipeline deterministic and installable without native ML wheels. The
interfaces mirror what you'd get from scikit-learn / RapidFuzz so they can be
swapped in for scale later without touching callers.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from difflib import SequenceMatcher

_TOKEN_RE = re.compile(r"[a-z0-9]+")
# Lightweight stopword list — enough to stop generic words dominating vectors.
STOPWORDS = {
    "the", "a", "an", "and", "or", "for", "with", "of", "to", "in", "on",
    "new", "product", "products", "outdoor", "men", "women", "mens", "womens",
}


def tokenize(text: str | None) -> list[str]:
    if not text:
        return []
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in STOPWORDS]


def token_set(text: str | None) -> set[str]:
    return set(tokenize(text))


def fuzzy_ratio(a: str | None, b: str | None) -> float:
    """Return a similarity ratio in [0, 1] (0 if either side empty)."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


class TfidfVectorizer:
    """Minimal deterministic TF-IDF vectorizer."""

    def __init__(self) -> None:
        self.vocab: dict[str, int] = {}
        self.idf: dict[str, float] = {}

    def fit(self, documents: list[str]) -> "TfidfVectorizer":
        df: Counter[str] = Counter()
        n = len(documents)
        token_lists = [tokenize(d) for d in documents]
        for tokens in token_lists:
            for tok in set(tokens):
                df[tok] += 1
        self.vocab = {tok: i for i, tok in enumerate(sorted(df))}
        # Smoothed idf so terms in every doc still carry a little weight.
        self.idf = {tok: math.log((1 + n) / (1 + c)) + 1.0 for tok, c in df.items()}
        return self

    def transform_one(self, document: str) -> dict[int, float]:
        tokens = tokenize(document)
        if not tokens:
            return {}
        tf = Counter(tokens)
        length = len(tokens)
        vec: dict[int, float] = {}
        for tok, count in tf.items():
            if tok not in self.vocab:
                continue
            vec[self.vocab[tok]] = (count / length) * self.idf.get(tok, 0.0)
        # L2 normalize
        norm = math.sqrt(sum(v * v for v in vec.values()))
        if norm > 0:
            vec = {k: v / norm for k, v in vec.items()}
        return vec

    def fit_transform(self, documents: list[str]) -> list[dict[int, float]]:
        self.fit(documents)
        return [self.transform_one(d) for d in documents]


def cosine_sparse(a: dict[int, float], b: dict[int, float]) -> float:
    if not a or not b:
        return 0.0
    if len(a) > len(b):
        a, b = b, a
    return sum(val * b.get(idx, 0.0) for idx, val in a.items())


def agglomerative_cluster(
    vectors: list[dict[int, float]], threshold: float
) -> list[int]:
    """Single-linkage agglomerative clustering on cosine similarity.

    Two items are linked when their cosine similarity >= ``threshold``. Returns a
    cluster label per input index. Deterministic: depends only on the inputs.
    """
    n = len(vectors)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[max(rx, ry)] = min(rx, ry)

    for i in range(n):
        for j in range(i + 1, n):
            if cosine_sparse(vectors[i], vectors[j]) >= threshold:
                union(i, j)

    roots = {}
    labels = []
    for i in range(n):
        r = find(i)
        if r not in roots:
            roots[r] = len(roots)
        labels.append(roots[r])
    return labels


def shared_terms(
    vec_a: dict[int, float], vec_b: dict[int, float], vocab: dict[str, int], top: int = 8
) -> list[str]:
    """Return the terms that contribute most to the similarity of two vectors."""
    inv = {idx: tok for tok, idx in vocab.items()}
    contrib = {
        inv[idx]: val * vec_b.get(idx, 0.0)
        for idx, val in vec_a.items()
        if idx in vec_b and idx in inv
    }
    return [t for t, _ in sorted(contrib.items(), key=lambda kv: -kv[1])[:top]]
