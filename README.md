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

Official text downloaded on 13 Oct 2026 (eCFR, as of 8 Oct 2026): **248 sections**, 123 in 46 CFR Part 42 and 125 in 33 CFR Part 157. Full report: [`results/eval_report.md`](results/eval_report.md).

**Finding the right section** (45 questions with a known answer section):

| Split | Questions | Recall@1 | Recall@3 | Recall@5 | MRR |
| --- | ---: | ---: | ---: | ---: | ---: |
| dev | 23 | 70% | 96% | 96% | 0.818 |
| test | 22 | 82% | 100% | 100% | 0.909 |
| all | 45 | 76% | 98% | 98% | 0.862 |

**Refusing what the regulations do not cover.** The threshold (term coverage < 0.418) was chosen on the dev questions only. On the held-out test questions:
- answerable questions answered: **22 of 22**
- out-of-scope questions refused: **8 of 8** (lifejackets, ballast water standards, fire pumps and similar)

**The quote check against tampered quotes.** Every sentence of 25–220 characters in the corpus was quoted as-is, then with one number changed and with "not" removed:
- genuine quotes accepted: **1,410 of 1,410**
- one number changed, rejected: **829 of 830**
- "not" removed, rejected: **139 of 139**

The one changed-number quote that passed is being traced. The likely cause is that the altered sentence also exists word for word elsewhere in the same section, in which case accepting it is correct.

**One retrieval miss in the top 5.** *"Is it allowed to load a ship so that its load line marks are submerged?"* found the right section (42.07-10) only at rank 7. BM25 ranked 42.07-5 (*Marks placed on vessel*) first, because the question shares more words with it. This is the word-matching limit described below.

**Live model, two questions only** (Google Gemini, free tier). This is a check that the loop works with a real model, not an evaluation:
- *"What is the minimum bow height?"* answered in 3 steps; the quote from 46 CFR 42.20-70 passed the check.
- *"How many lifejackets must a cargo ship carry?"* refused in 3 steps: neither regulation covers it.

## What went wrong

- **The download failed with HTTP 406.** The eCFR API requires compressed responses. Fixed by sending `Accept-Encoding: gzip` and decompressing.
- **The first model names failed.** `gemini-1.5-flash` returned 404, and `gemini-2.5-flash` is no longer offered to new users. I listed the available models through the API and used `gemini-flash-latest`.
- **The model service returned 503 (overloaded).** Added retries with back-off for 429 and 5xx responses.
- **Not yet done:** running all 61 evaluation questions through the live agent. Today the agent has been checked by the 45 tests (scripted models) and two live questions.

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
export REGCITE_MODEL=gemini-flash-latest   # names change; list them via the API if this fails
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
