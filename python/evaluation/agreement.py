"""Objective 2: agreement between pipeline output and the manually
completed, expert-verified SLR (ground truth).
"""
from __future__ import annotations

import pandas as pd
from sklearn.metrics import cohen_kappa_score


def cluster_agreement(pipeline_df: pd.DataFrame, manual_df: pd.DataFrame, key: str = "doi") -> dict:
    """pipeline_df / manual_df: columns [key, cluster_label].
    Returns raw agreement rate and Cohen's kappa on the shared document set.
    """
    merged = pipeline_df.merge(manual_df, on=key, suffixes=("_pipeline", "_manual"))
    if merged.empty:
        raise ValueError("No overlapping documents between pipeline and manual SLR sets")

    raw_agreement = (merged["cluster_label_pipeline"] == merged["cluster_label_manual"]).mean()
    kappa = cohen_kappa_score(merged["cluster_label_manual"], merged["cluster_label_pipeline"])

    return {
        "n_compared": len(merged),
        "raw_agreement": raw_agreement,
        "cohens_kappa": kappa,
        "meets_target": raw_agreement >= 0.90,
    }


def citation_validity_rate(total_checked: int, unmatched: int) -> float:
    if total_checked == 0:
        return 1.0
    return 1 - (unmatched / total_checked)
