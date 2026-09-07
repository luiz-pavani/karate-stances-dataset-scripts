"""Batch driver: walk the dataset root, process every trial, emit summary
tables.

Usage (from the repository root):
    python -m kds.batch \\
        --data-root "/path/to/Kinematic Data" \\
        --output-dir "./output"

Outputs (in --output-dir):
    summary_all_trials.csv  : 180 rows, one per gyaku-tsuki trial
    summary_static.csv      : 9 rows, one per STATIC reference (ID006–ID014)
    subject_means.csv       : 12 rows, per-subject means by stance
    qc_report.csv           : per-trial QC flags
    pipeline_metadata.json  : pipeline version + run parameters
"""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
import numpy as np
import pandas as pd

from . import __version__
from .loader import read_c3d_trial, discover_trials, discover_pos_txt, read_pos_com_txt
from .descriptors import trial_descriptors
from .strike_detection import detect_strike
from .demographics import SUBJECTS


def run_pipeline(data_root: str | Path, output_dir: str | Path,
                 prefer_filtered: bool = True) -> dict:
    data_root = Path(data_root)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    trials = discover_trials(data_root, prefer_filtered=prefer_filtered)
    pos_map = discover_pos_txt(data_root)

    rows_dynamic: list[dict] = []
    rows_static: list[dict] = []
    rows_qc: list[dict] = []

    n_total = len(trials)
    print(f"[kds.batch] Processing {n_total} trials "
          f"(filtered={prefer_filtered})  out -> {output_dir}", flush=True)

    for i, path in enumerate(trials, 1):
        rec = read_c3d_trial(path)
        subj = SUBJECTS.get(rec.subject)
        if subj is None:
            print(f"  ! Skipping unknown subject {rec.subject}", file=sys.stderr)
            continue
        qc = {"subject": rec.subject, "base": rec.base, "trial": rec.trial,
              "filtered": rec.filtered, "n_frames": rec.n_frames,
              "rate_hz": rec.rate_hz, "duration_s": float(rec.time[-1])}

        try:
            if rec.base == "STATIC":
                # STATIC: use single window covering full trial; no strike
                from .descriptors import _window_slice, _com_descriptors
                from .kinematics_linear import whole_body_com
                com = whole_body_com(rec, sex=subj.sex)
                full = slice(0, rec.n_frames)
                row = {
                    "subject": rec.subject, "base": rec.base, "trial": rec.trial,
                    "filtered": rec.filtered, "rate_hz": rec.rate_hz,
                    "n_frames": rec.n_frames, "duration_s": float(rec.time[-1]),
                    "sex": subj.sex,
                }
                row.update(_com_descriptors(com, full, "static", rec.base))
                rows_static.append(row)
                qc["status"] = "ok"
            else:
                # Dynamic trial: full descriptor panel
                pos_df = None
                key = (rec.subject, rec.base, rec.trial)
                if key in pos_map:
                    try:
                        pos_df = read_pos_com_txt(pos_map[key])
                    except Exception as e:
                        qc["pos_txt_error"] = str(e)[:120]
                strike = detect_strike(rec)
                row = trial_descriptors(rec, sex=subj.sex,
                                        pos_df=pos_df, strike_event=strike)
                rows_dynamic.append(row)
                qc["status"] = "ok"
                qc["strike_peak_time_s"] = strike.peak_time_s
                qc["strike_peak_speed_mps"] = strike.peak_speed_mps
                qc["v3d_com_offset_mm"] = row.get("v3d_com_offset_norm_mm")
        except Exception as e:
            qc["status"] = "error"
            qc["error"] = repr(e)[:200]
            print(f"  ! ERROR {rec.subject} {rec.base} T{rec.trial}: {e}",
                  file=sys.stderr)
        rows_qc.append(qc)
        if i % 20 == 0 or i == n_total:
            print(f"  [{i}/{n_total}] {rec.subject} {rec.base} T{rec.trial} "
                  f"({qc['status']})", flush=True)

    # Emit CSVs
    df_dyn = pd.DataFrame(rows_dynamic)
    df_sta = pd.DataFrame(rows_static)
    df_qc = pd.DataFrame(rows_qc)
    df_dyn.to_csv(output_dir / "summary_all_trials.csv", index=False)
    df_sta.to_csv(output_dir / "summary_static.csv", index=False)
    df_qc.to_csv(output_dir / "qc_report.csv", index=False)

    # Subject means by base (numeric columns only, excluding identifying ints)
    if not df_dyn.empty:
        drop_cols = {"trial", "filtered", "rate_hz", "n_frames",
                     "strike_hand", "sex"}
        means = df_dyn.drop(columns=[c for c in drop_cols if c in df_dyn.columns])\
                      .groupby(["subject", "base"], as_index=False)\
                      .mean(numeric_only=True)
        means.to_csv(output_dir / "subject_means.csv", index=False)

    meta = {
        "pipeline_version": __version__,
        "run_timestamp": datetime.utcnow().isoformat() + "Z",
        "data_root": str(data_root),
        "prefer_filtered": prefer_filtered,
        "n_trials_processed": int(len(df_dyn)),
        "n_static_processed": int(len(df_sta)),
        "n_errors": int((df_qc["status"] == "error").sum()) if not df_qc.empty else 0,
    }
    (output_dir / "pipeline_metadata.json").write_text(json.dumps(meta, indent=2))
    print(f"[kds.batch] Done. "
          f"Dynamic={len(df_dyn)}, Static={len(df_sta)}, Errors={meta['n_errors']}")
    return meta


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="kds.batch")
    ap.add_argument("--data-root", required=True,
                    help="Path to the Kinematic Data root (with ID003.. subdirs).")
    ap.add_argument("--output-dir", default="./output",
                    help="Directory to write the summary CSVs and QC report.")
    ap.add_argument("--raw", action="store_true",
                    help="Use raw _pose_0.c3d instead of the filtered variant.")
    args = ap.parse_args(argv)
    run_pipeline(args.data_root, args.output_dir,
                 prefer_filtered=not args.raw)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
