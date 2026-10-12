

from __future__ import annotations

import json
import os

import urllib.request
from dataclasses import dataclass, field
from typing import Callable, Protocol

from .bm25 import BM25Index
from .corpus import Section
from .verify import check_answer

MAX_STEPS = 6
MAX_RETRIES_AFTER_FAILED_CHECK = 1

SYSTEM_PROMPT = """You answer questions about two US regulations only:
46 CFR Part 42 (load lines) and 33 CFR Part 157 (oil tank vessels).

Reply with exactly one JSON object per turn and nothing else. Actions:
{"action": "search", "query": "<words to search for>"}
{"action": "read", "section": "<section number, e.g. 42.20-70>"}
{"action": "answer", "answer": "<short answer>", "citations": [{"section": "<number>", "quote": "<exact words copied from that section>"}]}
{"action": "refuse", "reason": "<why the regulations do not answer this>"}

Rules:
- Search before answering. Read a section before quoting it.
- Every answer needs at least one citation. Each quote must be copied
  word for word from the section you cite, at least 25 characters long.
  It will be checked mechanically; paraphrases fail.
- If the two regulations do not answer the question, refuse.
"""


class ChatModel(Protocol):
    def __call__(self, messages: list[dict]) -> str: ...


@dataclass
class Result:
    status: str                      # "answered" | "refused"
    answer: str = ""
    citations: list[dict] = field(default_factory=list)
    reason: str = ""
    steps: list[dict] = field(default_factory=list)


def extract_json(text: str) -> dict | None:
    start = text.find("{")
    while start != -1:
        depth, in_str, esc = 0, False, False
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
            elif ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(text[start:i + 1])
                        return obj if isinstance(obj, dict) else None
                    except json.JSONDecodeError:
                        break
        start = text.find("{", start + 1)
    return None


def run(question: str, model: ChatModel, index: BM25Index,
        sections: dict[str, Section]) -> Result:
    messages = [{"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question}]
    result = Result(status="refused")
    retries_left = MAX_RETRIES_AFTER_FAILED_CHECK

    for _ in range(MAX_STEPS):
        reply = model(messages)
        messages.append({"role": "assistant", "content": reply})
        action = extract_json(reply)
        step = {"model": reply, "action": action}
        result.steps.append(step)

        if action is None:
            feedback = "Your reply was not a JSON object. Reply with one JSON action."
        elif action.get("action") == "search":
            hits = index.search(str(action.get("query", "")), k=5)
            feedback = json.dumps([{"section": h.passage.section.section,
                                    "heading": h.passage.section.heading,
                                    "text": h.passage.text[:600]} for h in hits])
        elif action.get("action") == "read":
            sec = sections.get(str(action.get("section", "")))
            feedback = (json.dumps({"section": sec.section, "heading": sec.heading,
                                    "text": sec.text[:6000]})
                        if sec else f"No section {action.get('section')!r}. Search first.")
        elif action.get("action") == "answer":
            cits = action.get("citations") or []
            checks = check_answer(cits if isinstance(cits, list) else [], sections)
            step["checks"] = [c.__dict__ for c in checks]
            if all(c.ok for c in checks):
                result.status, result.answer, result.citations = "answered", str(action.get("answer", "")), cits
                return result
            if retries_left == 0:
                result.reason = "answer failed the quote check twice: " + \
                    "; ".join(c.reason for c in checks if not c.ok)
                return result
            retries_left -= 1
            feedback = ("Quote check FAILED: " + "; ".join(c.reason for c in checks if not c.ok)
                        + ". Read the section again and copy the words exactly, or refuse.")
        elif action.get("action") == "refuse":
            result.reason = str(action.get("reason", ""))
            return result
        else:
            feedback = f"Unknown action {action.get('action')!r}."

        step["feedback"] = feedback
        messages.append({"role": "user", "content": feedback})

    result.reason = f"no verified answer within {MAX_STEPS} steps"
    return result



PROVIDERS = {
    "openai": "https://api.openai.com/v1",
    "groq": "https://api.groq.com/openai/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
}


def openai_compatible(base_url: str, model: str, api_key: str) -> Callable[[list[dict]], str]:
    def call(messages: list[dict]) -> str:
        body = json.dumps({"model": model, "messages": messages, "temperature": 0}).encode()
        req = urllib.request.Request(
            base_url.rstrip("/") + "/chat/completions", data=body,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"})
        import time
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    return json.loads(resp.read())["choices"][0]["message"]["content"]
            except urllib.error.HTTPError as e:
                if e.code in (500, 502, 503, 504, 429) and attempt < 3:
                    time.sleep(3 * (attempt + 1))
                    continue
                raise
    return call


def model_from_env() -> Callable[[list[dict]], str]:
    provider = os.environ.get("REGCITE_PROVIDER", "")
    if provider not in PROVIDERS:
        raise SystemExit("Set REGCITE_PROVIDER to one of: " + ", ".join(PROVIDERS))
    model = os.environ.get("REGCITE_MODEL") or ""
    key = os.environ.get("REGCITE_API_KEY") or ""
    if not model or not key:
        raise SystemExit("Set REGCITE_MODEL and REGCITE_API_KEY.")
    return openai_compatible(PROVIDERS[provider], model, key)
