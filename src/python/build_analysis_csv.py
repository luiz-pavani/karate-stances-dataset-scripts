"""Build the consolidated kinematic analysis CSV.

Reads the pipeline summary outputs and joins them with the demographic
table to produce a single, self-contained, analysis-ready CSV with:

  - identification (subject, base, trial)
  - demographic + stylistic metadata (sex, age, height, mass, BMI,
    style, modality, level, years of practice, grade, dominant guard)
  - the full kinematic descriptor panel (180+ columns)
  - convenience columns (com_height_normalised_by_height,
    bos_area_normalised_by_height_squared, etc.)

Outputs two files:
  - kinematic_analysis_wide.csv  : one row per trial, full descriptor panel
  - kinematic_analysis_long.csv  : tidy/long format for stats packages
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import numpy as np
import sys

REPO = Path(__file__).resolve().parents[2]
SUMMARY = REPO / "data" / "processed_summary" / "KDS_summary_all_trials.csv"

sys.path.insert(0, str(REPO / "src" / "python"))
from kds.demographics import SUBJECTS  # noqa: E402


def demographics_df() -> pd.DataFrame:
    rows = []
    for sid, s in SUBJECTS.items():
        rows.append({
            "subject": sid,
            "sex": s.sex,
            "age_years": s.age_years,
            "height_cm": s.height_cm,
            "mass_kg": s.mass_kg,
            "bmi_kg_m2": s.bmi,
            "practice_years": s.practice_years,
            "grade": s.grade,
            "style": s.style,
            "modality": s.modality,
            "level": s.level,
            "weekly_days": s.weekly_days,
            "weekly_hours": s.weekly_hours,
            "upper_dominant": s.upper_dominant,
            "lower_dominant": s.lower_dominant,
            "dominant_guard": s.dominant_guard,
        })
    return pd.DataFrame(rows)


def build_wide(out_path: Path) -> pd.DataFrame:
    df = pd.read_csv(SUMMARY)
    demo = demographics_df()
    df = df.merge(demo, on=["subject", "sex"], how="left")

    # Reorder columns: identifiers + demographics first, then descriptors
    id_cols = ["subject", "base", "trial", "filtered", "rate_hz", "n_frames",
               "duration_s"]
    demo_cols = ["sex", "age_years", "height_cm", "mass_kg", "bmi_kg_m2",
                 "practice_years", "grade", "style", "modality", "level",
                 "weekly_days", "weekly_hours", "upper_dominant",
                 "lower_dominant", "dominant_guard"]
    other = [c for c in df.columns if c not in id_cols + demo_cols]
    df = df[id_cols + demo_cols + other]

    # Convenience derived columns (height-normalised)
    df["com_height_norm_by_height"] = df["pre_com_z_mean_m"] / (df["height_cm"] / 100.0)
    df["bos_area_norm_by_height_sq_pct"] = df["bos_area_cm2"] / ((df["height_cm"]) ** 2) * 100.0
    df["bos_width_norm_by_height_pct"] = df["bos_width_ml_cm"] / df["height_cm"] * 100.0
    df["bos_depth_norm_by_height_pct"] = df["bos_depth_ap_cm"] / df["height_cm"] * 100.0
    df["strike_peak_speed_norm_by_height_sqrt"] = (
        df["strike_peak_speed_mps"] / np.sqrt(df["height_cm"] / 100.0)
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"  Wrote {out_path}  shape={df.shape}")
    return df


def build_long(df_wide: pd.DataFrame, out_path: Path) -> pd.DataFrame:
    id_vars = ["subject", "base", "trial", "sex", "style", "modality",
               "level", "age_years", "height_cm", "mass_kg", "bmi_kg_m2",
               "practice_years", "grade", "dominant_guard"]
    # Keep only metric columns
    metric_cols = [c for c in df_wide.columns
                   if c not in id_vars
                   and pd.api.types.is_numeric_dtype(df_wide[c])
                   and c not in ("trial", "filtered", "rate_hz", "n_frames",
                                 "duration_s", "age_years", "height_cm",
                                 "mass_kg", "bmi_kg_m2", "practice_years",
                                 "weekly_days", "weekly_hours")]
    long = df_wide.melt(id_vars=id_vars, value_vars=metric_cols,
                        var_name="metric", value_name="value")
    # Annotate metric with parsed components where possible
    def _parse(metric: str) -> dict:
        parts = {"window": None, "family": None, "joint": None,
                 "axis": None, "stat": None, "unit": None}
        m = metric
        if m.startswith("pre_"):
            parts["window"] = "pre_strike"
            m = m[4:]
        elif m.startswith("post_"):
            parts["window"] = "post_strike"
            m = m[5:]
        if m.startswith("com_"):
            parts["family"] = "com"
        elif m.startswith("bos_"):
            parts["family"] = "bos"
        elif m.startswith("strike_"):
            parts["family"] = "strike"
        elif any(j in m for j in ("hip_", "knee_", "ankle_", "shoulder_",
                                   "elbow_", "trunk", "pelvis_world")):
            parts["family"] = "joint"
            # Extract joint name and axis (flx/abd/rot) and stat (mean/rom)
            for axis in ("flx", "abd", "rot"):
                if f"_{axis}_" in m:
                    parts["axis"] = axis
                    break
            for stat in ("mean", "rom"):
                if f"_{stat}_" in m:
                    parts["stat"] = stat
                    break
            # Joint is what's left of the first underscore segment
            parts["joint"] = m.rsplit("_" + (parts["axis"] or ""), 1)[0] if parts["axis"] else None
        if m.endswith("_m"):
            parts["unit"] = "m"
        elif m.endswith("_cm"):
            parts["unit"] = "cm"
        elif m.endswith("_cm2"):
            parts["unit"] = "cm2"
        elif m.endswith("_deg"):
            parts["unit"] = "deg"
        elif m.endswith("_mps"):
            parts["unit"] = "m_per_s"
        elif m.endswith("_s"):
            parts["unit"] = "s"
        elif m.endswith("_mm"):
            parts["unit"] = "mm"
        return parts

    parsed = long["metric"].apply(_parse).apply(pd.Series)
    long = pd.concat([long, parsed], axis=1)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    long.to_csv(out_path, index=False)
    print(f"  Wrote {out_path}  shape={long.shape}")
    return long


def write_codebook(df_wide: pd.DataFrame, out_path: Path) -> None:
    """Emit a column codebook for the wide CSV."""
    descriptions = {
        # Identifiers
        "subject": "Participant code (ID003-ID014).",
        "base": "Postural base mechanic category: ZEN (anteriorised), KOK (posteriorised), KIB (lateralised).",
        "trial": "Repetition index 1..5 within each base block.",
        "filtered": "True if Theia-filtered (pose_filt_0.c3d) variant was used.",
        "rate_hz": "Kinematic sampling rate, Hz.",
        "n_frames": "Number of frames in the trial (1620 = 9.00 s at 180 Hz).",
        "duration_s": "Trial duration in seconds.",
        # Demographics
        "sex": "Participant sex (M/F) used for gender-specific COM inertia.",
        "age_years": "Age in years at acquisition.",
        "height_cm": "Stature in centimetres.",
        "mass_kg": "Body mass in kilograms.",
        "bmi_kg_m2": "Body mass index.",
        "practice_years": "Self-reported karate practice in years.",
        "grade": "Karate grade (kyu/dan or 'Branca' for white belt).",
        "style": "Karate style lineage (Shotokan / Goju-Ryu / Wado-Ryu).",
        "modality": "Primary competitive modality (Kata / Kumite / None).",
        "level": "Competitive level (International / National / Regional / None).",
        "weekly_days": "Self-reported training days per week.",
        "weekly_hours": "Self-reported training hours per week.",
        "upper_dominant": "Upper-limb dominance.",
        "lower_dominant": "Lower-limb dominance.",
        "dominant_guard": "Self-reported dominant fighting guard (left/right).",
        # Conveniences
        "com_height_norm_by_height": "Pre-strike mean COM Z divided by participant height (dimensionless).",
        "bos_area_norm_by_height_sq_pct": "BoS area as percentage of (participant height)^2.",
        "bos_width_norm_by_height_pct": "BoS mediolateral width as percentage of participant height.",
        "bos_depth_norm_by_height_pct": "BoS anteroposterior depth as percentage of participant height.",
        "strike_peak_speed_norm_by_height_sqrt": "Strike peak speed (m/s) divided by sqrt(height in m).",
    }

    families = {
        "pre_com_": "Pre-strike (1-3 s) whole-body COM descriptor.",
        "post_com_": "Post-strike (6-9 s) whole-body COM descriptor.",
        "pre_hip_": "Pre-strike hip joint angle descriptor (deg).",
        "post_hip_": "Post-strike hip joint angle descriptor (deg).",
        "pre_knee_": "Pre-strike knee joint angle descriptor (deg).",
        "post_knee_": "Post-strike knee joint angle descriptor (deg).",
        "pre_ankle_": "Pre-strike ankle joint angle descriptor (deg).",
        "post_ankle_": "Post-strike ankle joint angle descriptor (deg).",
        "pre_shoulder_": "Pre-strike shoulder joint angle descriptor (deg).",
        "post_shoulder_": "Post-strike shoulder joint angle descriptor (deg).",
        "pre_elbow_": "Pre-strike elbow joint angle descriptor (deg).",
        "post_elbow_": "Post-strike elbow joint angle descriptor (deg).",
        "pre_pelvis_world": "Pre-strike pelvis-world Cardan angle descriptor (deg).",
        "post_pelvis_world": "Post-strike pelvis-world Cardan angle descriptor (deg).",
        "pre_trunk_": "Pre-strike trunk-vs-pelvis Cardan angle descriptor (deg).",
        "post_trunk_": "Post-strike trunk-vs-pelvis Cardan angle descriptor (deg).",
        "bos_": "Base-of-support descriptor (from Visual3D foot landmarks).",
        "strike_": "Detected gyaku-tsuki strike event.",
        "v3d_": "Cross-pipeline validation against Visual3D.",
    }

    rows = []
    for col in df_wide.columns:
        desc = descriptions.get(col)
        if not desc:
            for prefix, family_desc in families.items():
                if col.startswith(prefix):
                    suffix = col[len(prefix):]
                    if suffix.endswith("_mean_deg"):
                        what = f"mean of {suffix[:-9].replace('_',' ')} axis"
                    elif suffix.endswith("_rom_deg"):
                        what = f"range of motion of {suffix[:-8].replace('_',' ')} axis"
                    else:
                        what = suffix.replace('_',' ')
                    desc = f"{family_desc} {what}".strip()
                    break
        if not desc:
            desc = "Pipeline-generated descriptor."
        rows.append({"column": col, "description": desc,
                     "dtype": str(df_wide[col].dtype)})
    pd.DataFrame(rows).to_csv(out_path, index=False)
    print(f"  Wrote codebook -> {out_path}  ({len(rows)} columns documented)")


def main() -> None:
    out_dir = REPO / "data" / "processed_summary"
    print(f"[build_analysis_csv] Reading {SUMMARY}")
    df_wide = build_wide(out_dir / "kinematic_analysis_wide.csv")
    build_long(df_wide, out_dir / "kinematic_analysis_long.csv")
    write_codebook(df_wide, out_dir / "kinematic_analysis_codebook.csv")
    print("[build_analysis_csv] Done.")


if __name__ == "__main__":
    main()
