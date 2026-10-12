"""Data-quality checks for routine facility reports.

Each check returns a DataFrame of flags with columns
``facility_id, period, check, detail`` so results can be stacked and scored.
The dimensions follow the WHO Data Quality Review framework:
completeness, timeliness, internal consistency and outliers.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .synthetic import INDICATORS, expected_grid

FLAG_COLS = ["district", "facility_id", "period", "check", "detail"]


def _flags(df: pd.DataFrame, check: str, detail) -> pd.DataFrame:
    out = df[["district", "facility_id", "period"]].copy()
    out["check"] = check
    out["detail"] = detail if isinstance(detail, str) else list(detail)
    return out[FLAG_COLS]


def completeness(df: pd.DataFrame) -> pd.DataFrame:
    """Flag facility-months with no report submitted."""
    grid = expected_grid(df)
    got = df[["facility_id", "period"]].assign(_has=1)
    m = grid.merge(got, on=["facility_id", "period"], how="left")
    missing = m[m["_has"].isna()]
    return _flags(missing, "completeness", "report missing")


def timeliness(df: pd.DataFrame) -> pd.DataFrame:
    """Flag reports submitted after the deadline."""
    late = df[df["submitted_at"] > df["deadline"]]
    days = (late["submitted_at"] - late["deadline"]).dt.days
    return _flags(late, "timeliness", (f"{d} days late" for d in days))


def consistency(df: pd.DataFrame) -> pd.DataFrame:
    """Flag logically impossible combinations between related indicators."""
    rules = {
        "malaria_positive > malaria_tested": df["malaria_positive"] > df["malaria_tested"],
        "deliveries > 3 x anc1_visits": df["deliveries"] > 3 * df["anc1_visits"].clip(lower=1),
    }
    parts = [_flags(df[mask], "consistency", rule) for rule, mask in rules.items() if mask.any()]
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=FLAG_COLS)


def outliers_mad(df: pd.DataFrame, threshold: float = 3.5, indicators=INDICATORS) -> pd.DataFrame:
    """Flag values far from the facility's own median, using the modified z-score.

    Modified z = 0.6745 * (x - median) / MAD (Iglewicz & Hoaglin). It is robust
    because the median and MAD are not pulled by the outliers themselves.
    """
    parts = []
    for ind in indicators:
        g = df.groupby("facility_id")[ind]
        med = g.transform("median")
        mad = g.transform(lambda s: np.median(np.abs(s - s.median())))
        z = 0.6745 * (df[ind] - med) / mad.replace(0, np.nan)
        hit = df[z.abs() > threshold]
        if len(hit):
            zz = z[z.abs() > threshold]
            parts.append(_flags(hit, "outlier", (f"{ind}: value {v}, modified z={s:.1f}" for v, s in zip(hit[ind], zz))))
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=FLAG_COLS)


def zero_reporting(df: pd.DataFrame, indicators=INDICATORS) -> pd.DataFrame:
    """Flag reports where every indicator is zero (often a placeholder submission)."""
    allzero = (df[list(indicators)] == 0).all(axis=1)
    return _flags(df[allzero], "zero_report", "all indicators reported as 0")


def run_all(df: pd.DataFrame) -> pd.DataFrame:
    """Run every check and return one stacked flag table."""
    return pd.concat(
        [completeness(df), timeliness(df), consistency(df), outliers_mad(df), zero_reporting(df)],
        ignore_index=True,
    )
