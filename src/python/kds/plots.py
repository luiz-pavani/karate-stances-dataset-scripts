"""Diagnostic plots for the pipeline output.

Generates a small set of multi-panel figures from the summary CSVs:
  - strike_timing_distribution.png  (histogram of peak time + peak speed)
  - bos_by_stance.png                (BoS width / depth / area boxplots)
  - com_descriptors_by_stance.png    (COM ML range, AP range, path length)
  - subject_means_grid.png           (per-subject means by stance)

These figures are intended for the QC report and for the data paper figures.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl


def _style():
    mpl.rcParams.update({
        "figure.dpi": 110,
        "savefig.dpi": 180,
        "font.size": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
    })


def strike_timing_distribution(df: pd.DataFrame, out: Path) -> None:
    _style()
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    bases = ["ZEN", "KOK", "KIB"]
    colors = {"ZEN": "#1f77b4", "KOK": "#ff7f0e", "KIB": "#2ca02c"}
    for b in bases:
        sub = df[df["base"] == b]
        axes[0].hist(sub["strike_peak_time_s"], bins=20, alpha=0.55,
                     label=b, color=colors[b])
        axes[1].hist(sub["strike_peak_speed_mps"], bins=20, alpha=0.55,
                     label=b, color=colors[b])
    axes[0].axvline(3.0, color="k", ls="--", lw=0.8, label='"vai" cue (nominal)')
    axes[0].set_xlabel("Peak strike time (s)")
    axes[0].set_ylabel("Count of trials")
    axes[0].set_title("Strike timing")
    axes[0].legend(loc="upper right", fontsize=8)
    axes[1].set_xlabel("Peak hand speed (m/s)")
    axes[1].set_ylabel("Count of trials")
    axes[1].set_title("Strike intensity")
    axes[1].legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)


def bos_by_stance(df: pd.DataFrame, out: Path) -> None:
    _style()
    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    bases = ["ZEN", "KOK", "KIB"]
    metrics = [
        ("bos_width_ml_cm",  "BoS mediolateral width (cm)"),
        ("bos_depth_ap_cm",  "BoS anteroposterior depth (cm)"),
        ("bos_area_cm2",     "BoS area (cm²)"),
    ]
    for ax, (col, label) in zip(axes, metrics):
        data = [df[df["base"] == b][col].dropna() for b in bases]
        bp = ax.boxplot(data, tick_labels=bases, patch_artist=True)
        for patch, c in zip(bp["boxes"], ["#1f77b4", "#ff7f0e", "#2ca02c"]):
            patch.set_facecolor(c)
            patch.set_alpha(0.55)
        ax.set_ylabel(label)
    fig.suptitle("Base of support by stance (5 trials × 12 subjects)")
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)


def com_descriptors_by_stance(df: pd.DataFrame, out: Path) -> None:
    _style()
    fig, axes = plt.subplots(2, 3, figsize=(13, 7))
    bases = ["ZEN", "KOK", "KIB"]
    metrics = [
        ("pre_com_ml_range_cm",   "Pre-strike COM ML range (cm)"),
        ("pre_com_ap_range_cm",   "Pre-strike COM AP range (cm)"),
        ("pre_com_path_length_cm","Pre-strike COM path length (cm)"),
        ("post_com_ml_range_cm",  "Post-strike COM ML range (cm)"),
        ("post_com_ap_range_cm",  "Post-strike COM AP range (cm)"),
        ("post_com_path_length_cm","Post-strike COM path length (cm)"),
    ]
    for ax, (col, label) in zip(axes.flatten(), metrics):
        data = [df[df["base"] == b][col].dropna() for b in bases]
        bp = ax.boxplot(data, tick_labels=bases, patch_artist=True)
        for patch, c in zip(bp["boxes"], ["#1f77b4", "#ff7f0e", "#2ca02c"]):
            patch.set_facecolor(c)
            patch.set_alpha(0.55)
        ax.set_ylabel(label, fontsize=9)
    fig.suptitle("Whole-body COM postural descriptors by stance (pre- and post-strike windows)")
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)


def subject_means_grid(df_subj: pd.DataFrame, out: Path) -> None:
    _style()
    bases = ["ZEN", "KOK", "KIB"]
    metric = "pre_com_z_mean_m"
    fig, ax = plt.subplots(figsize=(11, 5))
    width = 0.27
    subjects = sorted(df_subj["subject"].unique())
    x = np.arange(len(subjects))
    for i, b in enumerate(bases):
        vals = [
            df_subj[(df_subj["subject"] == s) & (df_subj["base"] == b)][metric].mean()
            for s in subjects
        ]
        ax.bar(x + (i - 1) * width, vals, width, label=b, alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels(subjects, rotation=45, ha="right")
    ax.set_ylabel("COM height (m)")
    ax.set_title("Per-subject mean COM height by stance (pre-strike window)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)


def generate_all(output_dir: str | Path) -> None:
    output_dir = Path(output_dir)
    figs = output_dir / "figures"
    figs.mkdir(exist_ok=True)
    df = pd.read_csv(output_dir / "summary_all_trials.csv")
    df_subj = pd.read_csv(output_dir / "subject_means.csv")
    strike_timing_distribution(df, figs / "strike_timing_distribution.png")
    bos_by_stance(df, figs / "bos_by_stance.png")
    com_descriptors_by_stance(df, figs / "com_descriptors_by_stance.png")
    subject_means_grid(df_subj, figs / "subject_means_com_height.png")
    print(f"[kds.plots] Wrote 4 figures to {figs}")


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "output"
    generate_all(out)
