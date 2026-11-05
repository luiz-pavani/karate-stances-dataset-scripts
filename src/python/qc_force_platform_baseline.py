"""Force-platform baseline fluctuation (Technical Validation of the Data Note).

For each dynamic trial and each platform that fired, computes the standard
deviation of the centre-of-pressure coordinates over the first second of the
trial (t < 1 s), then summarises across platform-trials.

Usage: python src/python/qc_force_platform_baseline.py <timeseries_kinetic_raw dir>
"""
import glob
import os
import sys

import numpy as np
import pandas as pd


def main(folder: str) -> None:
    rows = []
    for path in sorted(glob.glob(os.path.join(folder, "*_kinetics.csv"))):
        df = pd.read_csv(path)
        first = df[df["time_s"] < 1.0]
        for plate in ("FP3", "FP4"):
            x, y = first[f"{plate}_COPx_mm"], first[f"{plate}_COPy_mm"]
            if x.notna().sum() == 0:
                continue
            rows.append({"trial": os.path.basename(path).replace("_kinetics.csv", ""),
                         "plate": plate, "sd_x_mm": x.std(), "sd_y_mm": y.std()})
    out = pd.DataFrame(rows)
    print(f"platform-trials: {len(out)} (trials: {out['trial'].nunique()})")
    for col in ("sd_x_mm", "sd_y_mm"):
        v = out[col]
        print(f"{col}: mean {v.mean():.2f}, SD {v.std():.2f}, median {v.median():.2f}, "
              f"IQR {v.quantile(.25):.2f}-{v.quantile(.75):.2f}, max {v.max():.2f}, "
              f"n>10mm {(v > 10).sum()}")
    print(out.sort_values("sd_x_mm", ascending=False).head(4).to_string(index=False))


if __name__ == "__main__":
    main(sys.argv[1])
