from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
from hdq import make_facility_reports, completeness, timeliness, consistency, outliers_mad, zero_reporting, run_all, facility_scores


def _pairs(frame):
    return set(map(tuple, frame[["facility_id", "period"]].drop_duplicates().to_numpy()))


df = make_facility_reports(seed=1)


def test_completeness_counts_removed_rows():
    expected = df["facility_id"].nunique() * df["period"].nunique()
    assert len(completeness(df)) == expected - len(df)


def test_timeliness_finds_every_late_report():
    late = df[df["_injected"] == "late"]
    assert _pairs(late) <= _pairs(timeliness(df))


def test_consistency_finds_injected_rows():
    bad = df[df["_injected"] == "inconsistent"]
    assert _pairs(bad) <= _pairs(consistency(df))


def test_outliers_catch_most_digit_errors():
    bad = _pairs(df[df["_injected"] == "outlier"])
    found = _pairs(outliers_mad(df))
    assert len(bad & found) / len(bad) >= 0.8


def test_zero_reports():
    bad = df[df["_injected"] == "zero_report"]
    assert _pairs(bad) == _pairs(zero_reporting(df))


def test_scores_bounded():
    s = facility_scores(df, run_all(df))
    pct = s.filter(like="_pct")
    assert ((pct >= 0) & (pct <= 100)).all().all()
