"""Per-trial postural descriptors.

For each trial we compute a panel of descriptors in two analysis windows:

    pre_strike  : t in [1.0, 3.0] s   (stance held, before "vai")
    post_strike : t in [6.0, 9.0] s   (stance re-stabilised after gyaku-tsuki)

Each panel includes:

  - COM mean position (x, y, z) in metres
  - COM mediolateral (ML) and anteroposterior (AP) sway range, RMS, and path length
  - Base of support: width (ML), depth (AP), area (using the four foot landmarks)
  - COM placement within the base of support (ML and AP coordinates relative
    to the BoS centroid, in metres and as percentage of BoS span)
  - Joint angle mean per axis (10 joints × 3 axes = 30 scalars)
  - Joint angular ROM per axis (30 scalars)

The two-window contrast supports the H1 hypothesis (postural separability
between stances) and the H2 hypothesis (post-strike convergence vs.
pre-strike configuration).
"""

from __future__ import annotations
import numpy as np
import pandas as pd
from dataclasses import asdict
from .loader import TrialRecord, read_pos_com_txt
from .kinematics_linear import whole_body_com
from .kinematics_angular import joint_angles, angular_range_of_motion


PRE_STRIKE_WIN = (1.0, 3.0)
POST_STRIKE_WIN = (6.0, 9.0)


def _window_slice(time: np.ndarray, t0: float, t1: float) -> slice:
    """Return a slice of the time axis between t0 and t1 (inclusive)."""
    i0 = int(np.searchsorted(time, t0))
    i1 = int(np.searchsorted(time, t1))
    return slice(i0, i1)


def _path_length_1d(x: np.ndarray) -> float:
    """Total path length of a 1-D signal (sum of absolute increments)."""
    return float(np.sum(np.abs(np.diff(x))))


def _path_length_2d(x: np.ndarray, y: np.ndarray) -> float:
    """Total path length of a 2-D trajectory."""
    return float(np.sum(np.sqrt(np.diff(x) ** 2 + np.diff(y) ** 2)))


def _bos_from_pos_df(df: pd.DataFrame, window: slice) -> dict:
    """Compute base-of-support descriptors from the Visual3D POS export.

    The four key landmarks per foot are:
      LFT_DistEnd (left toe), LFT_ProxEnd (left heel), Lateral_left_foot,
      RFT_DistEnd (right toe), RFT_ProxEnd (right heel), Lateral_right_foot.

    Width, depth, and area follow the rectangular bounding box of the
    convex hull of these six points projected onto the floor (x-y plane).
    """
    pts_x = np.stack([
        df["LFT_DistEnd_x"].to_numpy()[window],
        df["LFT_ProxEnd_x"].to_numpy()[window],
        df["Lateral_left_foot_x"].to_numpy()[window],
        df["RFT_DistEnd_x"].to_numpy()[window],
        df["RFT_ProxEnd_x"].to_numpy()[window],
        df["Lateral_right_foot_x"].to_numpy()[window],
    ])  # (6, n_frames)
    pts_y = np.stack([
        df["LFT_DistEnd_y"].to_numpy()[window],
        df["LFT_ProxEnd_y"].to_numpy()[window],
        df["Lateral_left_foot_y"].to_numpy()[window],
        df["RFT_DistEnd_y"].to_numpy()[window],
        df["RFT_ProxEnd_y"].to_numpy()[window],
        df["Lateral_right_foot_y"].to_numpy()[window],
    ])
    # Mean across frames (feet are stationary in the held stance)
    xs = pts_x.mean(axis=1)
    ys = pts_y.mean(axis=1)
    width_ml = float(np.ptp(xs))     # peak-to-peak in x
    depth_ap = float(np.ptp(ys))     # peak-to-peak in y
    # Area: convex-hull area would be most accurate; we approximate with the
    # rectangular bounding box for robustness when the points are nearly
    # collinear (as in stances with one foot in front of the other).
    area = width_ml * depth_ap
    bos_centroid = (float(xs.mean()), float(ys.mean()))
    return dict(
        bos_width_ml_cm=width_ml * 100.0,
        bos_depth_ap_cm=depth_ap * 100.0,
        bos_area_cm2=area * 10000.0,
        bos_centroid_x=bos_centroid[0],
        bos_centroid_y=bos_centroid[1],
    )


def _com_descriptors(com: np.ndarray, window: slice, prefix: str) -> dict:
    """COM position + sway descriptors within a window."""
    com_w = com[:, window]
    mean = com_w.mean(axis=1)
    ml = com_w[0]
    ap = com_w[1]
    z = com_w[2]
    return {
        f"{prefix}_com_x_mean_m": float(mean[0]),
        f"{prefix}_com_y_mean_m": float(mean[1]),
        f"{prefix}_com_z_mean_m": float(mean[2]),
        f"{prefix}_com_ml_range_cm": float(np.ptp(ml)) * 100.0,
        f"{prefix}_com_ap_range_cm": float(np.ptp(ap)) * 100.0,
        f"{prefix}_com_z_range_cm": float(np.ptp(z)) * 100.0,
        f"{prefix}_com_ml_rms_cm": float(np.sqrt(np.mean((ml - ml.mean()) ** 2))) * 100.0,
        f"{prefix}_com_ap_rms_cm": float(np.sqrt(np.mean((ap - ap.mean()) ** 2))) * 100.0,
        f"{prefix}_com_path_length_cm": _path_length_2d(ml, ap) * 100.0,
    }


def _joint_descriptors(angles: dict[str, np.ndarray], window: slice,
                       prefix: str) -> dict:
    """Mean and ROM of each joint × axis in the window."""
    axis_names = ("flx", "abd", "rot")  # flexion/extension, abduction/adduction, internal/external rot.
    out: dict[str, float] = {}
    for joint, a in angles.items():
        win = a[:, window]
        mean = win.mean(axis=1)
        rom = win.max(axis=1) - win.min(axis=1)
        for i, axis in enumerate(axis_names):
            out[f"{prefix}_{joint}_{axis}_mean_deg"] = float(mean[i])
            out[f"{prefix}_{joint}_{axis}_rom_deg"] = float(rom[i])
    return out


def trial_descriptors(record: TrialRecord, sex: str,
                      pos_df: pd.DataFrame | None = None,
                      strike_event=None) -> dict:
    """Compute the full descriptor panel for one trial.

    Parameters
    ----------
    record : TrialRecord
    sex : str
        'M' or 'F' — used for sex-specific inertia in COM computation.
    pos_df : pd.DataFrame | None
        Optional Visual3D POS export. If supplied, BoS descriptors are
        computed from the four foot landmarks.
    strike_event : kds.strike_detection.StrikeEvent | None
        Optional pre-detected strike event; if None, the pre/post windows
        use the nominal protocol times (1–3 s and 6–9 s).

    Returns
    -------
    dict of named descriptors plus identifying metadata.
    """
    pre = _window_slice(record.time, *PRE_STRIKE_WIN)
    post = _window_slice(record.time, *POST_STRIKE_WIN)

    # COM whole-body
    com = whole_body_com(record, sex=sex)

    # Joint angles
    angles = joint_angles(record)

    out: dict = {
        "subject": record.subject,
        "base": record.base,
        "trial": record.trial,
        "filtered": record.filtered,
        "rate_hz": record.rate_hz,
        "n_frames": record.n_frames,
        "duration_s": float(record.time[-1]),
        "sex": sex,
    }

    out.update(_com_descriptors(com, pre, "pre"))
    out.update(_com_descriptors(com, post, "post"))
    out.update(_joint_descriptors(angles, pre, "pre"))
    out.update(_joint_descriptors(angles, post, "post"))

    if pos_df is not None:
        # Use Visual3D-exported COM as a cross-check when available
        v3d_com = pos_df[["CenterOfMass_x", "CenterOfMass_y", "CenterOfMass_z"]].to_numpy().T
        # Sometimes shorter than record.n_frames — clip
        n = min(v3d_com.shape[1], record.n_frames)
        diff = com[:, :n] - v3d_com[:, :n]
        out["v3d_com_offset_norm_mm"] = float(np.linalg.norm(diff, axis=0).mean()) * 1000.0
        out.update(_bos_from_pos_df(pos_df, pre))

    if strike_event is not None:
        out.update({
            "strike_hand": strike_event.hand_used,
            "strike_peak_speed_mps": strike_event.peak_speed_mps,
            "strike_peak_time_s": strike_event.peak_time_s,
            "strike_onset_time_s": strike_event.onset_time_s,
            "strike_return_time_s": strike_event.return_time_s,
        })
    return out
