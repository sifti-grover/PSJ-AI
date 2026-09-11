"""CLI entrypoint for the results chapter: compares one pipeline run against
the manual-SLR ground truth CSV and prints the metrics table used in
Section 9 of the blueprint (Evaluation Plan).

Usage:
    python run_eval.py --pipeline pipeline_output.csv --manual manual_slr.csv
"""
from __future__ import annotations

import argparse

import pandas as pd

from agreement import cluster_agreement


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pipeline", required=True, help="CSV: doi,cluster_label")
    parser.add_argument("--manual", required=True, help="CSV: doi,cluster_label (ground truth)")
    args = parser.parse_args()

    pipeline_df = pd.read_csv(args.pipeline)
    manual_df = pd.read_csv(args.manual)

    result = cluster_agreement(pipeline_df, manual_df)
    print("=== Cluster-assignment agreement vs manual SLR ===")
    for k, v in result.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
