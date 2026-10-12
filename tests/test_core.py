"""Tests on the fictional fixture corpus. Every expected value is worked
out by hand in the comments, not copied from a previous run."""

import math
from pathlib import Path

import pytest

from regcite.answer import answer
from regcite.bm25 import BM25Index
from regcite.corpus import Section, parse_xml, passages
from regcite.text import normalize_for_quote, tokenize
from regcite.verify import check_answer, check_citation

FIXTURE = Path(__file__).parent / "fixtures" / "sample_ecfr.xml"


@pytest.fixture(scope="module")
def sections():
    return parse_xml(FIXTURE.read_bytes(), title=99)


@pytest.fixture(scope="module")
def by_id(sections):
    return {s.section: s for s in sections}


@pytest.fixture(scope="module")
def index(sections):
    return BM25Index(passages(sections))


# --- text --------------------------------------------------------------------

def test_tokenize_keeps_decimals_and_negation():
    assert tokenize("Cb above 0.68 must not") == ["cb", "above", "0.68", "must", "not"]


def test_tokenize_strips_plurals_consistently():
    assert tokenize("air pipes")[1] == tokenize("air pipe")[1] == "pipe"
    assert tokenize("bodies") == ["body"]
    assert tokenize("class") == ["class"]          # "ss" ending kept


def test_normalize_evens_quotes_but_keeps_numbers():
    assert normalize_for_quote("“not  less” – 1.25") == '"not less" - 1.25'


# --- parsing -----------------------------------------------------------------

def test_parse_finds_sections_and_skips_reserved(sections):
    assert [s.section for s in sections] == ["9.10-5", "9.10-10", "9.10-15", "9.20-1"]


def test_parse_strips_section_number_from_heading(sections):
    assert sections[0].heading == "Minimum bow height."


def test_parse_keeps_inline_markup_text_and_drops_citations(sections):
    text = sections[0].text
    assert "weathertight forecastle" in text           # <I> content kept
    assert "FR 1234" not in text                        # <CITA> dropped


def test_parse_flattens_tables(sections):
    paras = sections[2].paragraphs
    assert "Bulwark length (m) | Freeing port area (m2)" in paras
    assert "10 | 0.70" in paras


def test_parse_refuses_unknown_structure():
    with pytest.raises(ValueError, match="No sections found"):
        parse_xml(b"<ROOT><P>text</P></ROOT>", title=1)


def test_cite_and_url(sections):
    assert sections[0].cite == "99 CFR 9.10-5"
    assert sections[0].url == "https://www.ecfr.gov/current/title-99/section-9.10-5"


def test_passages_never_span_sections_and_split_long_ones():
    long = Section(1, "1.1", "Long", [("word " * 100).strip()] * 3)
    short = Section(1, "1.2", "Short", ["tiny paragraph"])
    ps = passages([long, short], min_words=40, max_words=180)
    assert [p.section.section for p in ps] == ["1.1", "1.1", "1.1", "1.2"]


def test_passage_label_uses_paragraph_letter(sections):
    p = passages(sections)[0]
    assert p.label == "99 CFR 9.10-5(a)"


# --- BM25, against a hand calculation ----------------------------------------

def test_bm25_score_matches_hand_calculation():
    a = Section(1, "1.1", "", ["air pipe air"])
    b = Section(1, "1.2", "", ["freeing port"])
    idx = BM25Index(passages([a, b]))
    # N = 2, avg_len = (3 + 2) / 2 = 2.5. "air": n = 1, tf = 2 in doc a (len 3)
    idf = math.log((2 - 1 + 0.5) / (1 + 0.5) + 1)            # = ln 2
    norm = 1 - 0.75 + 0.75 * 3 / 2.5                           # = 1.15
    expected = idf * 2 * (1.5 + 1) / (2 + 1.5 * norm)          # = ln2 * 5 / 3.725
    assert idx.score(["air"], 0) == pytest.approx(expected, rel=1e-12)
    assert idx.score(["air"], 1) == 0.0


def test_coverage_penalises_terms_absent_from_corpus():
    a = Section(1, "1.1", "", ["air pipe air"])
    b = Section(1, "1.2", "", ["freeing port"])
    idx = BM25Index(passages([a, b]))
    ln2, ln6 = math.log(2), math.log((2 + 0.5) / 0.5 + 1)     # "banana" never appears: n = 0
    assert idx.coverage(["air", "banana"], 0) == pytest.approx(ln2 / (ln2 + ln6))


@pytest.mark.parametrize("question, expected", [
    ("How high must air pipes extend above the deck?", "9.10-10"),
    ("What is the minimum bow height?", "9.10-5"),
    ("How much oil may be in discharged water?", "9.20-1"),
    ("What freeing port area is needed for a 20 m bulwark?", "9.10-15"),
])
def test_search_ranks_right_section_first(index, question, expected):
    assert index.search_sections(question)[0].passage.section.section == expected


def test_refuses_question_outside_corpus(index):
    a = answer(index, "How fast must a lifeboat davit lower the boat?", threshold=0.5)
    assert a.refused


def test_answers_question_inside_corpus(index):
    a = answer(index, "minimum bow height harbour craft", threshold=0.5)
    assert not a.refused and a.hits[0].passage.section.section == "9.10-5"


# --- the quote check ---------------------------------------------------------

GENUINE = "The bow height of a harbour craft must be not less than 1.25 metres"


def test_genuine_quote_passes(by_id):
    assert check_citation("9.10-5", GENUINE, by_id).ok


def test_curly_quotes_and_extra_spaces_still_pass(by_id):
    assert check_citation("9.10-5", "The bow height of a harbour  craft must be not less than 1.25 metres", by_id).ok


@pytest.mark.parametrize("tampered, why", [
    (GENUINE.replace("1.25", "1.20"), "number changed"),
    (GENUINE.replace("not less", "less"), "negation dropped"),
    (GENUINE.replace("harbour craft", "harbour vessel"), "one word changed"),
])
def test_tampered_quote_fails(by_id, tampered, why):
    assert not check_citation("9.10-5", tampered, by_id).ok, why


def test_right_quote_wrong_section_fails(by_id):
    assert not check_citation("9.10-10", GENUINE, by_id).ok


def test_unknown_section_and_short_quote_fail(by_id):
    assert "does not exist" in check_citation("9.99-9", GENUINE, by_id).reason
    assert "shorter" in check_citation("9.10-5", "bow height", by_id).reason


def test_answer_without_citations_fails(by_id):
    checks = check_answer([], by_id)
    assert len(checks) == 1 and not checks[0].ok
