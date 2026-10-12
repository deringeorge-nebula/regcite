"""The evaluation's own arithmetic, checked on cases small enough to do by hand."""

from pathlib import Path

import pytest

from regcite.corpus import parse_xml
from regcite.evaluate import (Q, balanced_accuracy, choose_threshold, evaluate,
                              first_gold_rank, mrr, recall_at, tamper_negation,
                              tamper_number)

FIXTURE = Path(__file__).parent / "fixtures" / "sample_ecfr.xml"


def test_first_gold_rank():
    assert first_gold_rank(["a", "b", "c"], ["c", "x"]) == 3
    assert first_gold_rank(["a", "b"], ["z"]) is None


def test_recall_and_mrr():
    ranks = [1, 3, None, 2]
    assert recall_at(ranks, 1) == 0.25
    assert recall_at(ranks, 3) == 0.75
    assert mrr(ranks) == pytest.approx((1 + 1 / 3 + 0 + 1 / 2) / 4)


def test_threshold_separates_clean_case():
    # answerable all >= 0.6, unanswerable all <= 0.3: any t in (0.3, 0.6] is perfect
    t = choose_threshold([0.6, 0.8, 0.9], [0.1, 0.3])
    assert 0.3 < t <= 0.6
    assert balanced_accuracy([0.6, 0.8, 0.9], [0.1, 0.3], t) == 1.0


def test_tamper_number():
    assert tamper_number("not less than 1.25 metres") == "not less than 1.26 metres"
    assert tamper_number("at least 760 mm") == "at least 761 mm"
    assert tamper_number("0.99 here") == "0.00 here"
    assert tamper_number("no digits") is None


def test_tamper_negation():
    assert tamper_negation("must not discharge") == "must discharge"
    assert tamper_negation("must discharge") is None


def test_evaluate_end_to_end_on_fixture():
    secs = parse_xml(FIXTURE.read_bytes(), title=99)
    qs = [Q("a1", "How high above the deck must air pipes extend?", ["9.10-10"], "dev"),
          Q("a2", "What is the minimum bow height for harbour craft?", ["9.10-5"], "test"),
          Q("u1", "How often must lifeboats be lowered into the water?", [], "dev"),
          Q("u2", "What is the sulphur limit for fuel in emission control areas?", [], "test")]
    res = evaluate(secs, qs)
    assert res["retrieval"]["all"]["recall@1"] == 1.0
    assert res["refusal_test"] == {"answerable_kept": 1, "answerable_n": 1,
                                   "unanswerable_refused": 1, "unanswerable_n": 1}
    tm = res["tamper"]
    assert tm["genuine_accepted"] == tm["genuine_total"] > 0
    assert tm["number_caught"] == tm["number_total"] > 0
    assert tm["negation_caught"] == tm["negation_total"] > 0
    assert not res["bad_gold"]
