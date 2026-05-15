"""Export per-trial raw kinematic time-series CSVs.

For each trial in the dataset, write one CSV containing the pure
time-series signals computed by the kinematic pipeline:

  - frame index and time (s)
  - linear position of each of the 19 segment origins (m)
  - linear position of the whole-body centre of mass (m, sex-specific)
  - Cardan/Euler joint angles of the 12 ISB joints (deg)

The output carries no aggregated descriptors and no demographic columns;
the sex required for the sex-specific COM inertia is looked up internally
from the demographic table and is not written into the CSV.

Output layout:
    <output_dir>/
    ├── <ID>_<BASE>_T<N>_kinematics.csv         dynamic trials (180 files)
    └── static/<ID>_STATIC_T1_kinematics.csv    STATIC references (9 files)

CLI:
    python -m kds.export_timeseries \\
        --data-root "/path/to/Kinematic Data" \\
        --output-dir ./data/timeseries_raw
"""

from __future__ import annotations
import argparse
import sys
from pathlib import Path
import numpy as np
import pandas as pd

from .loader import (
    read_c3d_trial, discover_trials, SEGMENT_LABELS_EXPECTED, TrialRecord,
)
from .kinematics_linear import segment_origins, whole_body_com
from .kinematics_angular import joint_angles, JOINT_DEFINITIONS
from .demographics import SUBJECTS


AXES_LIN = ("x", "y", "z")
AXES_ANG = ("flx", "abd", "rot")


def build_trial_df(record: TrialRecord) -> pd.DataFrame:
    """Build a (n_frames, ~98) DataFrame of pure kinematic time-series."""
    n = record.n_frames
    cols: dict[str, np.ndarray] = {
        "frame": np.arange(n, dtype=np.int32),
        "time_s": record.time,
    }
    # 19 segments × 3 axes — linear positions in lab frame
    origins = segment_origins(record)
    for seg in SEGMENT_LABELS_EXPECTED:
        if seg not in origins:
            continue
        for ax_i, ax in enumerate(AXES_LIN):
            cols[f"{seg}_{ax}"] = origins[seg][ax_i]
    # COM whole-body sex-specific
    subj = SUBJECTS.get(record.subject)
    sex = subj.sex if subj else None
    com = whole_body_com(record, sex=sex)
    for ax_i, ax in enumerate(AXES_LIN):
        cols[f"com_{ax}"] = com[ax_i]
    # 12 joints × 3 axes — Cardan/Euler angles in degrees
    angles = joint_angles(record)
    for joint_name, _parent, _child, _seq in JOINT_DEFINITIONS:
        if joint_name not in angles:
            continue
        for ax_i, ax in enumerate(AXES_ANG):
            cols[f"{joint_name}_{ax}_deg"] = angles[joint_name][ax_i]
    return pd.DataFrame(cols)


def export_all(data_root: Path, output_dir: Path,
               prefer_filtered: bool = False) -> dict:
    """Export one CSV per trial. STATIC trials go to <output_dir>/static/."""
    trials = discover_trials(data_root, prefer_filtered=prefer_filtered)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "static").mkdir(exist_ok=True)
    n_dyn, n_sta, n_err = 0, 0, 0
    for i, path in enumerate(trials, 1):
        rec = read_c3d_trial(path)
        try:
            df = build_trial_df(rec)
            if rec.base == "STATIC":
                out = (output_dir / "static"
                       / f"{rec.subject}_STATIC_T{rec.trial}_kinematics.csv")
                n_sta += 1
            else:
                out = (output_dir
                       / f"{rec.subject}_{rec.base}_T{rec.trial}_kinematics.csv")
                n_dyn += 1
            df.to_csv(out, index=False, float_format="%.6f")
        except Exception as e:
            n_err += 1
            print(f"  ! {rec.subject} {rec.base} T{rec.trial}: {e}",
                  file=sys.stderr)
        if i % 20 == 0 or i == len(trials):
            print(f"  [{i}/{len(trials)}] {rec.subject} {rec.base} "
                  f"T{rec.trial}", flush=True)
    return {"dynamic": n_dyn, "static": n_sta, "errors": n_err,
            "n_trials": len(trials)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="kds.export_timeseries")
    ap.add_argument("--data-root", required=True,
                    help="Path to the Kinematic Data root with ID003.. subdirs.")
    ap.add_argument("--output-dir", default="./data/timeseries_raw",
                    help="Directory to write per-trial CSVs.")
    ap.add_argument("--filtered", action="store_true",
                    help="Use _pose_filt_0.c3d instead of raw _pose_0.c3d.")
    args = ap.parse_args(argv)
    print(f"[kds.export_timeseries] Reading from {args.data_root}", flush=True)
    print(f"[kds.export_timeseries] Writing to   {args.output_dir} "
          f"(filtered={args.filtered})", flush=True)
    summary = export_all(Path(args.data_root), Path(args.output_dir),
                         prefer_filtered=args.filtered)
    print(f"[kds.export_timeseries] Done. {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
