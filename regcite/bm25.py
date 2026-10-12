

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass

from .corpus import Passage
from .text import tokenize


@dataclass
class Hit:
    passage: Passage
    score: float
    coverage: float


class BM25Index:
    def __init__(self, passages: list[Passage], k1: float = 1.5, b: float = 0.75):
        self.passages = passages
        self.k1, self.b = k1, b
        self.docs = [tokenize(p.section.heading + " " + p.text) for p in passages]
        self.tf = [Counter(d) for d in self.docs]
        self.lengths = [len(d) for d in self.docs]
        self.n = len(passages)
        self.avg_len = sum(self.lengths) / self.n if self.n else 0.0
        df = Counter()
        for d in self.tf:
            df.update(d.keys())
        self.df = df

    def idf(self, term: str) -> float:
        n_t = self.df.get(term, 0)
        return math.log((self.n - n_t + 0.5) / (n_t + 0.5) + 1)

    def score(self, query_terms: list[str], i: int) -> float:
        tf, length = self.tf[i], self.lengths[i]
        s = 0.0
        for t in query_terms:
            f = tf.get(t, 0)
            if f:
                norm = 1 - self.b + self.b * length / self.avg_len
                s += self.idf(t) * f * (self.k1 + 1) / (f + self.k1 * norm)
        return s

    def coverage(self, query_terms: list[str], i: int) -> float:
        terms = set(query_terms)
        total = sum(self.idf(t) for t in terms)
        if total == 0:
            return 0.0
        found = sum(self.idf(t) for t in terms if t in self.tf[i])
        return found / total

    def search(self, query: str, k: int = 5) -> list[Hit]:
        q = tokenize(query)
        scored = [(self.score(q, i), i) for i in range(self.n)]
        scored.sort(key=lambda x: (-x[0], x[1]))
        return [Hit(self.passages[i], s, self.coverage(q, i)) for s, i in scored[:k] if s > 0]

    def search_sections(self, query: str, k: int = 5) -> list[Hit]:
        best: dict[str, Hit] = {}
        for h in self.search(query, k=max(50, k * 10)):
            key = h.passage.section.cite
            if key not in best:
                best[key] = h
        return list(best.values())[:k]
