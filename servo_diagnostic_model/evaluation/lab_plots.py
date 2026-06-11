"""Command-line entry point for laboratory diagnostic plots."""

from __future__ import annotations

import argparse

from servo_diagnostic_model.evaluation.plots import build_all_lab_plots


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--results", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--session", nargs="+", default=["E2", "LOAD", "MED", "R02"])
    parser.add_argument("--format", default="png", choices=["png"])
    args = parser.parse_args()
    generated = build_all_lab_plots(
        args.summary,
        args.results,
        args.output_dir,
        session_filter=" ".join(args.session),
    )
    for name, path in generated.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
