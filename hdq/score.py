"""Turn flags into facility and district data-quality scores."""
from __future__ import annotations

import pandas as pd

from .synthetic import expected_grid

CHECKS = ["completeness", "timeliness", "consistency", "outlier", "zero_report"]


def facility_scores(df: pd.DataFrame, flags: pd.DataFrame) -> pd.DataFrame:
    """Percentage of expected facility-months passing each check, plus an overall score."""
    grid = expected_grid(df)
    expected = grid.groupby(["district", "facility_id"]).size().rename("expected_reports")
    flagged = (
        flags.drop_duplicates(["facility_id", "period", "check"])
        .groupby(["district", "facility_id", "check"]).size()
        .unstack("check", fill_value=0)
        .reindex(columns=CHECKS, fill_value=0)
    )
    out = expected.to_frame().join(flagged, how="left").fillna(0)
    for c in CHECKS:
        out[f"{c}_pct"] = 100 * (1 - out[c] / out["expected_reports"])
    any_flag = flags.drop_duplicates(["facility_id", "period"]).groupby("facility_id").size()
    out["clean_reports_pct"] = 100 * (
        1 - out.index.get_level_values("facility_id").map(any_flag).fillna(0).to_numpy() / out["expected_reports"]
    )
    return out.reset_index().sort_values("clean_reports_pct")


def district_summary(scores: pd.DataFrame) -> pd.DataFrame:
    cols = [f"{c}_pct" for c in CHECKS] + ["clean_reports_pct"]
    return scores.groupby("district")[cols].mean().round(1)
