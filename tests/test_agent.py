"""The agent loop, driven by scripted models instead of a real one.

Each scripted model plays a behaviour a real model can show: honest,
fabricating, self-correcting, refusing, or replying with nonsense. The
loop must end in the right state every time. No API key needed."""

import json
from pathlib import Path

import pytest

from regcite import agent
from regcite.bm25 import BM25Index
from regcite.corpus import parse_xml, passages

FIXTURE = Path(__file__).parent / "fixtures" / "sample_ecfr.xml"
REAL_QUOTE = "Air pipes on the weather deck must extend at least 760 millimetres above the deck"
FAKE_QUOTE = "Air pipes on the weather deck must extend at least 600 millimetres above the deck"


@pytest.fixture(scope="module")
def world():
    secs = parse_xml(FIXTURE.read_bytes(), title=99)
    return BM25Index(passages(secs)), {s.section: s for s in secs}


def scripted(*replies):
    """A model that returns the given replies in order and records what it saw."""
    seen = []

    def model(messages):
        seen.append(messages[-1]["content"])
        return replies[min(len(seen) - 1, len(replies) - 1)]
    model.seen = seen
    return model


def act(**kw):
    return json.dumps(kw)


def answer(quote, section="9.10-10"):
    return act(action="answer", answer="At least 760 mm.",
               citations=[{"section": section, "quote": quote}])


def test_honest_model_is_answered(world):
    m = scripted(act(action="search", query="air pipe height"),
                 act(action="read", section="9.10-10"),
                 answer(REAL_QUOTE))
    r = agent.run("How high must air pipes be?", m, *world)
    assert r.status == "answered" and len(r.steps) == 3
    assert "9.10-10" in m.seen[1]              # search results reached the model
    assert "760 millimetres" in m.seen[2]      # the section text reached the model


def test_fabricating_model_is_refused(world):
    m = scripted(answer(FAKE_QUOTE), answer(FAKE_QUOTE))
    r = agent.run("How high must air pipes be?", m, *world)
    assert r.status == "refused"
    assert "quote check twice" in r.reason


def test_model_that_corrects_itself_is_answered(world):
    m = scripted(answer(FAKE_QUOTE), answer(REAL_QUOTE))
    r = agent.run("How high must air pipes be?", m, *world)
    assert r.status == "answered"
    assert "Quote check FAILED" in m.seen[1]    # it was told exactly what failed


def test_real_quote_cited_to_wrong_section_is_refused(world):
    m = scripted(answer(REAL_QUOTE, section="9.10-5"), answer(REAL_QUOTE, section="9.10-5"))
    assert agent.run("q", m, *world).status == "refused"


def test_answer_without_citation_is_refused(world):
    no_cite = act(action="answer", answer="760 mm", citations=[])
    assert agent.run("q", scripted(no_cite, no_cite), *world).status == "refused"


def test_model_may_refuse(world):
    r = agent.run("q", scripted(act(action="refuse", reason="not covered")), *world)
    assert r.status == "refused" and r.reason == "not covered"


def test_nonsense_replies_end_after_max_steps(world):
    r = agent.run("q", scripted("I think the answer is 760 mm."), *world)
    assert r.status == "refused" and len(r.steps) == agent.MAX_STEPS


def test_unknown_section_read_gets_helpful_feedback(world):
    m = scripted(act(action="read", section="1.1-1"), act(action="refuse", reason="x"))
    agent.run("q", m, *world)
    assert "No section" in m.seen[1]


@pytest.mark.parametrize("text, expected", [
    ('Sure! {"action": "search", "query": "bow"} hope that helps', {"action": "search", "query": "bow"}),
    ('{"action": "answer", "answer": "use {braces}", "citations": []}',
     {"action": "answer", "answer": "use {braces}", "citations": []}),
    ("no json here", None),
    ('{broken json} then {"action": "refuse"}', {"action": "refuse"}),
])
def test_extract_json(text, expected):
    assert agent.extract_json(text) == expected
