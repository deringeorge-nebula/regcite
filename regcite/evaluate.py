

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .answer import SETTINGS_FILE, best_coverage
from .bm25 import BM25Index
from .corpus import Section, load_sections, passages
from .verify import check_citation

ROOT = Path(__file__).resolve().parent.parent
QUESTIONS_FILE = ROOT / "eval" / "questions.jsonl"
REPORT_FILE = ROOT / "results" / "eval_report.md"


@dataclass
class Q:
    id: str
    question: str
    gold: list[str]
    split: str


def load_questions(path: Path = QUESTIONS_FILE) -> list[Q]:
    with path.open(encoding="utf-8") as f:
        return [Q(**json.loads(line)) for line in f if line.strip()]



def first_gold_rank(ranked: list[str], gold: list[str]) -> int | None:
    for i, s in enumerate(ranked, 1):
        if s in gold:
            return i
    return None


def recall_at(ranks: list[int | None], k: int) -> float:
    return sum(1 for r in ranks if r is not None and r <= k) / len(ranks) if ranks else 0.0


def mrr(ranks: list[int | None]) -> float:
    return sum(1 / r for r in ranks if r is not None) / len(ranks) if ranks else 0.0



def balanced_accuracy(cov_answerable: list[float], cov_unanswerable: list[float], t: float) -> float:
    kept = sum(c >= t for c in cov_answerable) / len(cov_answerable)
    refused = sum(c < t for c in cov_unanswerable) / len(cov_unanswerable)
    return (kept + refused) / 2


def choose_threshold(cov_answerable: list[float], cov_unanswerable: list[float]) -> float:
    values = sorted(set(cov_answerable) | set(cov_unanswerable))
    candidates = [values[0] - 1e-9] + [(a + b) / 2 for a, b in zip(values, values[1:])] + [values[-1] + 1e-9]
    best_t, best_s = candidates[0], -1.0
    for t in candidates:
        s = balanced_accuracy(cov_answerable, cov_unanswerable, t)
        if s > best_s + 1e-12:
            best_t, best_s = t, s
    return best_t



_NUMBER = re.compile(r"\d+(?:\.\d+)?")


def tamper_number(sentence: str) -> str | None:
    m = _NUMBER.search(sentence)
    if not m:
        return None
    s = m.group(0)
    if "." in s:
        whole, frac = s.split(".")
        new = f"{whole}.{(int(frac) + 1) % (10 ** len(frac)):0{len(frac)}d}"
    else:
        new = str(int(s) + 1)
    return sentence[:m.start()] + new + sentence[m.end():]


def tamper_negation(sentence: str) -> str | None:
    return sentence.replace(" not ", " ", 1) if " not " in sentence else None


def quote_candidates(sec: Section, limit: int = 3) -> list[str]:
    out = []
    for para in sec.paragraphs:
        for sent in re.split(r"(?<=[.;:])\s+", para):
            if 25 <= len(sent) <= 220:
                out.append(sent)
    return out[:limit * 4]


def tamper_test(sections: list[Section]) -> dict:
    by_id = {s.section: s for s in sections}
    genuine_ok = genuine_total = 0
    caught = {"number": [0, 0], "negation": [0, 0]}
    for sec in sections:
        for sent in quote_candidates(sec):
            genuine_total += 1
            genuine_ok += check_citation(sec.section, sent, by_id).ok
            for kind, fn in (("number", tamper_number), ("negation", tamper_negation)):
                t = fn(sent)
                if t and t != sent:
                    caught[kind][1] += 1
                    caught[kind][0] += not check_citation(sec.section, t, by_id).ok
    return {"genuine_accepted": genuine_ok, "genuine_total": genuine_total,
            "number_caught": caught["number"][0], "number_total": caught["number"][1],
            "negation_caught": caught["negation"][0], "negation_total": caught["negation"][1]}



def evaluate(sections: list[Section], questions: list[Q], k_search: int = 10) -> dict:
    index = BM25Index(passages(sections))
    known = {s.section for s in sections}
    rows = []
    for q in questions:
        hits = index.search_sections(q.question, k=k_search)
        ranked = [h.passage.section.section for h in hits]
        rows.append({
            "q": q, "ranked": ranked,
            "headings": [h.passage.section.heading for h in hits[:3]],
            "rank": first_gold_rank(ranked, q.gold) if q.gold else None,
            "coverage": best_coverage(hits[:5]),
            "gold_missing_from_corpus": [g for g in q.gold if g not in known],
        })

    def part(split: str, answerable: bool):
        return [r for r in rows if r["q"].split == split and bool(r["q"].gold) == answerable]

    dev_a, dev_u, test_a, test_u = part("dev", True), part("dev", False), part("test", True), part("test", False)
    t = choose_threshold([r["coverage"] for r in dev_a], [r["coverage"] for r in dev_u])

    all_a = dev_a + test_a
    out = {
        "threshold": t,
        "retrieval": {name: {"n": len(rs),
                             "recall@1": recall_at([r["rank"] for r in rs], 1),
                             "recall@3": recall_at([r["rank"] for r in rs], 3),
                             "recall@5": recall_at([r["rank"] for r in rs], 5),
                             "mrr": mrr([r["rank"] for r in rs])}
                      for name, rs in (("dev", dev_a), ("test", test_a), ("all", all_a))},
        "refusal_test": {
            "answerable_kept": sum(r["coverage"] >= t for r in test_a), "answerable_n": len(test_a),
            "unanswerable_refused": sum(r["coverage"] < t for r in test_u), "unanswerable_n": len(test_u),
        },
        "tamper": tamper_test(sections),
        "misses": [r for r in all_a if r["rank"] is None or r["rank"] > 5],
        "bad_gold": [r for r in rows if r["gold_missing_from_corpus"]],
        "rows": rows,
    }
    return out


def report(res: dict, n_sections: int) -> str:
    L = ["# Evaluation report", "", f"Corpus: {n_sections} sections. "
         f"Refusal threshold chosen on dev questions: coverage < {res['threshold']:.3f}.", ""]
    L += ["## Finding the right section (answerable questions)", "",
          "| Split | Questions | Recall@1 | Recall@3 | Recall@5 | MRR |", "|---|---:|---:|---:|---:|---:|"]
    for name, m in res["retrieval"].items():
        L.append(f"| {name} | {m['n']} | {m['recall@1']:.0%} | {m['recall@3']:.0%} | "
                 f"{m['recall@5']:.0%} | {m['mrr']:.3f} |")
    r = res["refusal_test"]
    L += ["", "## Refusing what the regulations do not answer (test split only)", "",
          f"- Answerable questions answered: {r['answerable_kept']} of {r['answerable_n']}",
          f"- Unanswerable questions refused: {r['unanswerable_refused']} of {r['unanswerable_n']}"]
    tm = res["tamper"]
    L += ["", "## Quote check against tampered quotes", "",
          f"- Genuine quotes accepted: {tm['genuine_accepted']} of {tm['genuine_total']}",
          f"- Quotes with one number changed, rejected: {tm['number_caught']} of {tm['number_total']}",
          f"- Quotes with 'not' removed, rejected: {tm['negation_caught']} of {tm['negation_total']}"]
    if res["bad_gold"]:
        L += ["", "## Gold labels that name sections not in the corpus (fix these first)", ""]
        for row in res["bad_gold"]:
            L.append(f"- {row['q'].id}: {row['gold_missing_from_corpus']}")
    L += ["", "## Misses: gold section not in the top 5", ""]
    if not res["misses"]:
        L.append("None.")
    for row in res["misses"]:
        q = row["q"]
        top = "; ".join(f"{s} ({h})" for s, h in zip(row["ranked"][:3], row["headings"]))
        L.append(f"- **{q.id}** ({q.split}) \"{q.question}\" gold {q.gold}, rank {row['rank']}. Top 3: {top}")
    L += ["", "## Every question", "", "| id | split | gold | rank | coverage | top result |",
          "|---|---|---|---:|---:|---|"]
    for row in res["rows"]:
        q = row["q"]
        L.append(f"| {q.id} | {q.split} | {', '.join(q.gold) or '(none)'} | "
                 f"{row['rank'] if row['rank'] else '-'} | {row['coverage']:.2f} | "
                 f"{row['ranked'][0] if row['ranked'] else '-'} |")
    return "\n".join(L) + "\n"


def main() -> None:
    sections = load_sections()
    questions = load_questions()
    res = evaluate(sections, questions)
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps({"coverage_threshold": res["threshold"]}, indent=2))
    text = report(res, len(sections))
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(text, encoding="utf-8")
    print(text.split("## Every question")[0])
    print(f"Full report: {REPORT_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
