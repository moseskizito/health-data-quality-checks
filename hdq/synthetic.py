"""Synthetic monthly facility reports with known, injected data-quality problems.

The data imitate the shape of routine HMIS/DHIS2-style aggregate reports
(one row per facility per month). They contain NO real data. Every injected
problem is recorded in the ``_injected`` column so checks can be validated.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

INDICATORS = ["anc1_visits", "deliveries", "malaria_tested", "malaria_positive"]


def make_facility_reports(
    n_districts: int = 4,
    facilities_per_district: int = 15,
    months: int = 24,
    start: str = "2024-01",
    missing_rate: float = 0.06,
    late_rate: float = 0.10,
    seed: int = 42,
) -> pd.DataFrame:
    """Return a long-format DataFrame of synthetic monthly facility reports."""
    rng = np.random.default_rng(seed)
    periods = pd.period_range(start, periods=months, freq="M")
    rows = []
    for d in range(1, n_districts + 1):
        for f in range(1, facilities_per_district + 1):
            fid = f"D{d:02d}F{f:03d}"
            size = rng.lognormal(mean=3.5, sigma=0.6)  # facility catchment scale
            for i, p in enumerate(periods):
                season = 1 + 0.35 * np.sin(2 * np.pi * (p.month - 3) / 12)  # malaria seasonality
                anc1 = rng.poisson(size)
                deliveries = rng.binomial(anc1, 0.55) if anc1 else 0
                tested = rng.poisson(size * 3 * season)
                positive = rng.binomial(tested, 0.35 * season / 1.35) if tested else 0
                deadline = (p + 1).to_timestamp() + pd.Timedelta(days=14)
                submitted = deadline - pd.Timedelta(days=int(rng.integers(1, 12)))
                rows.append(
                    dict(
                        district=f"District {d}",
                        facility_id=fid,
                        period=str(p),
                        anc1_visits=anc1,
                        deliveries=deliveries,
                        malaria_tested=tested,
                        malaria_positive=positive,
                        submitted_at=submitted,
                        deadline=deadline,
                        _injected="",
                    )
                )
    df = pd.DataFrame(rows)
    n = len(df)

    def pick(k):
        return rng.choice(n, size=k, replace=False)

    # 1. Missing reports (row removed later, so mark first)
    miss = pick(int(n * missing_rate))
    df.loc[miss, "_injected"] = "missing"
    # 2. Late submissions
    pool = df.index[df["_injected"] == ""].to_numpy()
    late = rng.choice(pool, size=int(n * late_rate), replace=False)
    df.loc[late, "submitted_at"] = df.loc[late, "deadline"] + pd.to_timedelta(
        rng.integers(1, 40, size=len(late)), unit="D"
    )
    df.loc[late, "_injected"] = "late"
    # 3. Inconsistency: positives > tested
    pool = df.index[df["_injected"] == ""].to_numpy()
    inc = rng.choice(pool, size=max(1, n // 100), replace=False)
    df.loc[inc, "malaria_positive"] = df.loc[inc, "malaria_tested"] + rng.integers(5, 50, size=len(inc))
    df.loc[inc, "_injected"] = "inconsistent"
    # 4. Outliers: typing error (extra digit)
    pool = df.index[df["_injected"] == ""].to_numpy()
    out = rng.choice(pool, size=max(1, n // 80), replace=False)
    df.loc[out, "anc1_visits"] = df.loc[out, "anc1_visits"] * 10 + rng.integers(0, 9, size=len(out))
    df.loc[out, "_injected"] = "outlier"
    # 5. Zero reporting: whole report filled with zeros
    pool = df.index[df["_injected"] == ""].to_numpy()
    zer = rng.choice(pool, size=max(1, n // 120), replace=False)
    df.loc[zer, INDICATORS] = 0
    df.loc[zer, "_injected"] = "zero_report"

    df = df[df["_injected"] != "missing"].reset_index(drop=True)
    return df


def expected_grid(df: pd.DataFrame) -> pd.DataFrame:
    """All facility x period combinations that *should* have a report."""
    fac = df[["district", "facility_id"]].drop_duplicates()
    per = pd.DataFrame({"period": sorted(df["period"].unique())})
    return fac.merge(per, how="cross")
