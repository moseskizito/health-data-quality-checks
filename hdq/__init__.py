"""hdq: data-quality checks for routine (aggregate) health facility reports."""
from .synthetic import make_facility_reports
from .checks import (
    completeness,
    timeliness,
    consistency,
    outliers_mad,
    zero_reporting,
    run_all,
)
from .score import facility_scores, district_summary

__all__ = [
    "make_facility_reports",
    "completeness",
    "timeliness",
    "consistency",
    "outliers_mad",
    "zero_reporting",
    "run_all",
    "facility_scores",
    "district_summary",
]
__version__ = "0.1.0"
