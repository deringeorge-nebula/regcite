

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .bm25 import BM25Index, Hit

SETTINGS_FILE = Path(__file__).resolve().parent.parent / "data" / "settings.json"
DEFAULT_THRESHOLD = 0.5


def load_threshold() -> float:
    if SETTINGS_FILE.exists():
        return json.loads(SETTINGS_FILE.read_text()).get("coverage_threshold", DEFAULT_THRESHOLD)
    return DEFAULT_THRESHOLD


@dataclass
class Answer:
    refused: bool
    hits: list[Hit]
    coverage: float


def best_coverage(hits: list[Hit]) -> float:
    return max((h.coverage for h in hits), default=0.0)


def answer(index: BM25Index, question: str, threshold: float | None = None, k: int = 3) -> Answer:
    threshold = load_threshold() if threshold is None else threshold
    hits = index.search_sections(question, k=5)
    cov = best_coverage(hits)
    return Answer(refused=cov < threshold, hits=hits[:k], coverage=cov)


def format_answer(a: Answer) -> str:
    lines = []
    if a.refused:
        lines.append(f"NOT FOUND in 46 CFR Part 42 or 33 CFR Part 157 "
                     f"(term coverage {a.coverage:.2f}). Nearest sections, for reference only:")
    for h in a.hits:
        s = h.passage.section
        lines.append(f"\n[{h.passage.label}] {s.heading}  (score {h.score:.2f}, coverage {h.coverage:.2f})")
        lines.append(f"  \"{h.passage.text}\"")
        lines.append(f"  {s.url}")
    return "\n".join(lines)
