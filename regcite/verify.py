

from __future__ import annotations

from dataclasses import dataclass

from .corpus import Section
from .text import normalize_for_quote

MIN_QUOTE_CHARS = 25


@dataclass
class Check:
    ok: bool
    reason: str


def check_citation(section_id: str, quote: str, sections: dict[str, Section]) -> Check:
    sec = sections.get(section_id)
    if sec is None:
        return Check(False, f"section {section_id!r} does not exist in the corpus")
    q = normalize_for_quote(quote)
    if len(q) < MIN_QUOTE_CHARS:
        return Check(False, f"quote is shorter than {MIN_QUOTE_CHARS} characters")
    if q not in normalize_for_quote(sec.text):
        return Check(False, f"quote does not appear word for word in {sec.cite}")
    return Check(True, "ok")


def check_answer(citations: list[dict], sections: dict[str, Section]) -> list[Check]:
    if not citations:
        return [Check(False, "answer has no citations")]
    return [check_citation(str(c.get("section", "")), str(c.get("quote", "")), sections)
            for c in citations]
