

from __future__ import annotations

import json
import sys

from . import agent
from .answer import answer, format_answer
from .bm25 import BM25Index
from .corpus import load_sections, passages


def main() -> None:
    if len(sys.argv) < 3 or sys.argv[1] not in {"ask", "agent"}:
        print(__doc__)
        return
    cmd, question = sys.argv[1], " ".join(sys.argv[2:])
    secs = load_sections()
    index = BM25Index(passages(secs))
    if cmd == "ask":
        print(format_answer(answer(index, question)))
    else:
        res = agent.run(question, agent.model_from_env(), index, {s.section: s for s in secs})
        print(json.dumps({"status": res.status, "answer": res.answer,
                          "citations": res.citations, "reason": res.reason,
                          "steps": len(res.steps)}, indent=2))


if __name__ == "__main__":
    main()
