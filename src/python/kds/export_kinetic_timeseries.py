"""Export per-trial raw kinetic time-series CSVs.

For each acquired trial (subject × base × trial), write one CSV
containing the unprocessed force-platform records of both Bertec 3 and
Bertec 4 platforms, side-by-side at the native 1000 Hz sampling. No
filtering, no platform combination, no descriptors, no demographic
metadata. The COP coordinates are released in the laboratory frame as
exported by Qualisys QTM.

Output layout:
    <output_dir>/
    ├── <ID>_<BASE>_T<N>_kinetics.csv          dynamic trials
    ├── static/<ID>_STATIC_T1_kinetics.csv     STATIC references
    ├── kinetic_qc_report.csv                  per-trial QC flags
    └── kinetic_plate_corners.csv              4 corners of each plate
                                               (one entry per source TSV)

CLI:
    python -m kds.export_kinetic_timeseries \\
        --data-root "/path/to/Kinetic" \\
        --output-dir ./data/timeseries_kinetic_raw
"""

from __future__ import annotations
import argparse
import sys
from pathlib import Path
import numpy as np
import pandas as pd

from .loader_kinetic import (
    KineticTrial, iter_trials_by_key, read_kinetic_tsv, discover_kinetic_trials,
)


PLATE_COLS = [
    ("Fx_N", "force", 0),
    ("Fy_N", "force", 1),
    ("Fz_N", "force", 2),
    ("Mx_Nmm", "moment", 0),
    ("My_Nmm", "moment", 1),
    ("Mz_Nmm", "moment", 2),
    ("COPx_mm", "cop", 0),
    ("COPy_mm", "cop", 1),
    ("COPz_mm", "cop", 2),
]


def _plate_block(kt: KineticTrial, plate_id: int) -> dict[str, np.ndarray]:
    """Return a dict of named columns for one platform, prefixed by plate id.

    Column names follow the convention `FP<plate>_<variable>` (e.g.
    `FP3_Fx_N`). When the trial did not fire that platform, returns an
    empty dict; the caller fills with NaNs of matching length.
    """
    if kt is None:
        return {}
    out = {}
    for name, attr, axis in PLATE_COLS:
        out[f"FP{plate_id}_{name}"] = getattr(kt, attr)[axis]
    return out


def build_trial_df(group: list[KineticTrial]) -> pd.DataFrame:
    """Build the per-trial CSV from a list of 1 or 2 plate records.

    The two plates of a trial are stored side-by-side; if one plate is
    missing, its columns are filled with NaN values of matching length.
    The shared time axis is taken from the first available plate. The
    `frame` column is the integer sample index (0-based for Python
    convention; the raw export uses 1-based, which is documented in the
    README).
    """
    # Determine reference length and time
    ref = group[0]
    n = ref.n_samples
    rate = ref.rate_hz
    time = ref.time
    # Sanity: if both plates differ in n_samples we still align by the
    # shorter length (acquired trials are guaranteed to start at the
    # same trigger by the Qualisys system)
    if len(group) == 2:
        n = min(group[0].n_samples, group[1].n_samples)
        time = time[:n]

    cols: dict[str, np.ndarray] = {
        "frame": np.arange(n, dtype=np.int32),
        "time_s": time,
    }

    # Always emit columns for both plates 3 and 4, with NaN for missing
    for plate in (3, 4):
        kt = next((x for x in group if x.plate == plate), None)
        if kt is None:
            # Fill with NaN
            for name, _attr, _ax in PLATE_COLS:
                cols[f"FP{plate}_{name}"] = np.full(n, np.nan, dtype=np.float64)
        else:
            for name, attr, axis in PLATE_COLS:
                cols[f"FP{plate}_{name}"] = getattr(kt, attr)[axis, :n]
    return pd.DataFrame(cols)


def export_all(data_root: Path, output_dir: Path) -> dict:
    """Walk the kinetic root and emit one CSV per (subject, base, trial)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "static").mkdir(exist_ok=True)

    qc_rows = []
    corners_rows = []
    n_dyn, n_sta, n_err = 0, 0, 0
    n_keys = 0

    for key, group in iter_trials_by_key(data_root):
        n_keys += 1
        subject, base, trial = key
        try:
            df = build_trial_df(group)
            if base == "STATIC":
                out = (output_dir / "static"
                       / f"{subject}_STATIC_T{trial}_kinetics.csv")
                n_sta += 1
            else:
                out = (output_dir
                       / f"{subject}_{base}_T{trial}_kinetics.csv")
                n_dyn += 1
            df.to_csv(out, index=False, float_format="%.6f")
        except Exception as e:
            n_err += 1
            print(f"  ! {subject} {base} T{trial}: {e}", file=sys.stderr)
            continue

        # QC row
        has_3 = any(x.plate == 3 for x in group)
        has_4 = any(x.plate == 4 for x in group)
        ref = group[0]
        qc_rows.append({
            "subject": subject,
            "base": base,
            "trial": trial,
            "n_samples": ref.n_samples,
            "rate_hz": ref.rate_hz,
            "duration_s": float(ref.time[-1]) if len(ref.time) else 0.0,
            "has_plate_3": has_3,
            "has_plate_4": has_4,
            "n_plates": int(has_3) + int(has_4),
            "source_path_3": next((x.source_path for x in group if x.plate == 3), ""),
            "source_path_4": next((x.source_path for x in group if x.plate == 4), ""),
            "kuk_alias_applied": "KUK" in (
                next((x.source_path for x in group if x.plate in (3, 4)), "")),
        })

        # Corners (one row per plate per trial)
        for x in group:
            for ci, label in enumerate(("POSX_POSY", "NEGX_POSY",
                                        "NEGX_NEGY", "POSX_NEGY")):
                corners_rows.append({
                    "subject": subject,
                    "base": base,
                    "trial": trial,
                    "plate": x.plate,
                    "corner": label,
                    "x_mm": float(x.corners_mm[ci, 0]),
                    "y_mm": float(x.corners_mm[ci, 1]),
                    "z_mm": float(x.corners_mm[ci, 2]),
                })

        if n_keys % 20 == 0:
            print(f"  [{n_keys}] {subject} {base} T{trial} (plates={len(group)})",
                  flush=True)

    pd.DataFrame(qc_rows).to_csv(output_dir / "kinetic_qc_report.csv",
                                 index=False)
    pd.DataFrame(corners_rows).to_csv(
        output_dir / "kinetic_plate_corners.csv", index=False)

    return {"dynamic": n_dyn, "static": n_sta, "errors": n_err,
            "trials_total": n_keys}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="kds.export_kinetic_timeseries")
    ap.add_argument("--data-root", required=True,
                    help="Path to the Kinetic data root (containing *.tsv files).")
    ap.add_argument("--output-dir", default="./data/timeseries_kinetic_raw",
                    help="Directory to write per-trial CSVs.")
    args = ap.parse_args(argv)
    print(f"[kds.export_kinetic_timeseries] Reading from {args.data_root}", flush=True)
    print(f"[kds.export_kinetic_timeseries] Writing to   {args.output_dir}",
          flush=True)
    summary = export_all(Path(args.data_root), Path(args.output_dir))
    print(f"[kds.export_kinetic_timeseries] Done. {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
