# regcite

A question-answering agent for maritime regulations that must quote its source word for word, or refuse.

> Ask: *"How high must air pipes be above the deck?"*
> Get: the answer, the section number, and the exact sentence from the regulation, checked mechanically against the official text. If the quote is not in the cited section word for word, the answer is rejected.

In regulations, a paraphrase that changes one number or drops one "not" is a wrong answer that looks right. Language models produce exactly that kind of error. This project is about catching it, and about measuring how well the system finds the right rule and refuses questions it cannot answer.

**Corpus:** two US federal regulations, which are public domain:
- **46 CFR Part 42**: load lines (the US implementation of the International Convention on Load Lines)
- **33 CFR Part 157**: tank vessels carrying oil in bulk (double hulls, segregated ballast, oil discharge limits, crude oil washing)

Downloaded from the official eCFR API, with a SHA-256 checksum recorded for each file.

---

## How it works

```
question
   │
   ▼
 search (BM25)  ──►  read section  ──►  answer + citations
                                             │
                                             ▼
                              quote check: is every quote word for word
                              in the section it cites?
                                  │                    │
                                 yes                   no ──► told exactly what failed,
                                  │                          one retry, then refuse
                                  ▼
                               answer
```

Two ways to use it:

| Mode | Needs | What it does |
| --- | --- | --- |
| `ask` | nothing | Returns the best-matching sections with the exact passage text and citations, or **refuses** when the question's key terms are not in the regulations. No language model, no cost. |
| `agent` | an API key for any OpenAI-compatible model (OpenAI, Groq, Google Gemini) | A tool-using agent searches, reads sections and writes an answer. Every citation must pass the quote check. |

**Retrieval** is BM25, written out in about 80 lines rather than taken from a library, and checked against a hand calculation in the tests.

**Refusal** uses *term coverage*: the share of the question's information (idf weight) found in the best passage. A question about lifejackets uses words that hardly appear in load line rules, so its coverage is low and it is refused. The threshold is chosen on the development half of the questions and reported on the test half only.

**The quote check** evens out whitespace, curly quotes and dashes, and nothing else. A changed number, a dropped "not", or a real quote attached to the wrong section all fail.

The agent loop is plain Python on purpose, so every step is visible. The same four steps would be four nodes in LangGraph.

## Results

*To be filled from `results/eval_report.md` after running on the official text.*

## Tests

45 tests run on a small fictional regulation in the same XML layout as eCFR, so they need no download:

- **BM25** against a hand-worked score; **coverage** against a hand-worked value.
- **Parsing:** sections found, reserved sections skipped, tables flattened, citations dropped, and a loud failure on unknown XML instead of a silent empty corpus.
- **Quote check:** genuine quotes pass; a changed number, a dropped "not", one changed word, the wrong section, an unknown section, a too-short quote and an answer with no citation all fail.
- **Agent loop, with scripted models** that are honest, fabricate quotes, correct themselves after feedback, cite the wrong section, refuse, or reply with nonsense. Each must end in the right state.

I also broke the code on purpose to check the tests notice:

| Deliberate break | Tests failing |
| --- | --- |
| Quote check compares only the first 20 characters | 6 |
| Agent allowed unlimited retries after a failed check | 1 |
| BM25 idf formula loses its "+ 1" | 2 |

## Run it

Python 3.10 or newer. No packages are needed except `pytest` for the tests.

```bash
pip install pytest
python -m pytest                       # 45 tests, under a second
python -m regcite.corpus fetch         # download the two regulations from eCFR
python -m regcite.corpus build         # parse them into data/sections.jsonl
python -m regcite.evaluate             # retrieval, refusal and tamper results
python -m regcite ask "What is the minimum bow height?"
```

Agent mode with a free-tier model (example: Google Gemini):

```bash
# Windows PowerShell: use  $env:REGCITE_PROVIDER="gemini"  etc.
export REGCITE_PROVIDER=gemini
export REGCITE_MODEL=<model name from Google AI Studio>
export REGCITE_API_KEY=<your key>
python -m regcite agent "What is the minimum bow height?"
```

## Limits

- Two regulations only. It does not know SOLAS, MARPOL as written by IMO, class rules or anything else, and it says so.
- BM25 matches words, not meaning. A question phrased with different words from the regulation can miss. Embedding search is the obvious next step; it is not here yet.
- The evaluation questions were written by me from the section list, so the gold labels reflect my reading. Misses are listed in the report so each one can be checked.
- Answers are not legal or compliance advice. The point is that every answer points to the exact text a person should read.

## Files

| Path | What it is |
| --- | --- |
| `regcite/corpus.py` | Download from eCFR, checksum, parse XML into sections and passages |
| `regcite/text.py` | Tokenising (lossy, for search) and quote normalising (not lossy) |
| `regcite/bm25.py` | BM25 search and term coverage |
| `regcite/verify.py` | The quote check |
| `regcite/answer.py` | Extractive answers and refusal |
| `regcite/agent.py` | The tool-using agent loop and an OpenAI-compatible client |
| `regcite/evaluate.py` | Retrieval, refusal and tamper evaluation |
| `eval/questions.jsonl` | 45 questions with known answer sections, 16 the regulations do not cover |
| `tests/` | 45 tests and the fictional fixture regulation |

## About

Built by **Derin George M A**, final-year Naval Architecture & Ship Building, Indian Maritime University, with an AI coding assistant (Claude). I set the goal and the standard (every claim checked against the source text), ran every step, checked every result, and can explain every line.

Contact: derin@thalwag.com · Preprint: [doi.org/10.31223/X59B8P](https://doi.org/10.31223/X59B8P)
