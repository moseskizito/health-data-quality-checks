"""End-to-end demo: generate synthetic reports, run checks, score, and plot.

Usage:  python examples/run_demo.py
Writes outputs to examples/output/.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from hdq import make_facility_reports, run_all, facility_scores, district_summary
from hdq.score import CHECKS

out = Path(__file__).parent / "output"
out.mkdir(exist_ok=True)

df = make_facility_reports()
flags = run_all(df)
scores = facility_scores(df, flags)
summary = district_summary(scores)

flags.to_csv(out / "flags.csv", index=False)
scores.round(1).to_csv(out / "facility_scores.csv", index=False)
summary.to_csv(out / "district_summary.csv")

# Detection check against the injected ground truth
truth = df[df["_injected"].isin(["late", "inconsistent", "outlier", "zero_report"])]
check_for = {"late": "timeliness", "inconsistent": "consistency", "outlier": "outlier", "zero_report": "zero_report"}
recall = {}
for kind, check in check_for.items():
    t = truth[truth["_injected"] == kind][["facility_id", "period"]]
    f = flags[flags["check"] == check][["facility_id", "period"]].drop_duplicates()
    recall[kind] = len(t.merge(f)) / max(len(t), 1)

print(f"Reports: {len(df)} | flags: {len(flags)}")
print("\nFlags by check:\n", flags["check"].value_counts().to_string())
print("\nDistrict summary (% of expected reports passing):\n", summary.to_string())
print("\nRecall of injected problems:", {k: round(v, 2) for k, v in recall.items()})

# Chart: district x check heatmap
cols = [f"{c}_pct" for c in CHECKS]
fig, ax = plt.subplots(figsize=(8, 3.2))
im = ax.imshow(summary[cols].to_numpy(), cmap="RdYlGn", vmin=80, vmax=100, aspect="auto")
ax.set_xticks(range(len(cols)), [c.replace("_pct", "").replace("_", " ") for c in cols])
ax.set_yticks(range(len(summary)), summary.index)
for i in range(len(summary)):
    for j, c in enumerate(cols):
        ax.text(j, i, f"{summary.iloc[i][c]:.1f}", ha="center", va="center", fontsize=9)
ax.set_title("Share of expected facility reports passing each check (%) — synthetic data")
fig.colorbar(im, ax=ax, shrink=0.8)
fig.tight_layout()
fig.savefig(out / "district_heatmap.png", dpi=150)
print(f"\nSaved outputs to {out}")
