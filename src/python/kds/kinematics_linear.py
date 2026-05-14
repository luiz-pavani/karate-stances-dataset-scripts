"""Linear kinematics: segment-origin positions, whole-body COM, velocities,
accelerations.

Theia3D delivers, for each frame and each of 19 segments, a 4x4 homogeneous
transformation matrix that maps the segment-fixed frame into the laboratory
frame. The position of the segment origin in the lab is the translation
component (the fourth column, rows 1-3). The whole-body centre of mass is the
mass-percentage-weighted sum of the per-segment COM expressed in the lab frame.

The per-segment COM is given by Theia3D in segment-fixed coordinates, alongside
mass percentage and radius of gyration, gender-specifically. Pelvis and pelvis-
shifted are not assigned mass in the Theia inertia table; we therefore exclude
them from the whole-body COM sum (their inertia is distributed among the
adjacent segments per the Theia model).
"""

from __future__ import annotations
import numpy as np
from .loader import TrialRecord


# Map between THEIA3D inertia-key segment names and the rotations-label names.
INERTIA_TO_SEGMENT = {
    "l_thigh": "l_thigh", "l_shank": "l_shank", "l_foot": "l_foot",
    "r_thigh": "r_thigh", "r_shank": "r_shank", "r_foot": "r_foot",
    "head": "head", "thorax": "torso",
    "l_uarm": "l_uarm", "l_larm": "l_larm", "l_hand": "l_hand",
    "r_uarm": "r_uarm", "r_larm": "r_larm", "r_hand": "r_hand",
}


def segment_origins(record: TrialRecord) -> dict[str, np.ndarray]:
    """Return the position of each segment origin in the lab frame.

    Output: dict mapping segment label to (3, n_frames) array in metres.
    """
    out: dict[str, np.ndarray] = {}
    for label, T in record.segments.items():
        # T shape: (4, 4, n_frames). Translation is T[0:3, 3, :]
        out[label] = T[0:3, 3, :].copy()
    return out


def transform_point(T: np.ndarray, p_local: np.ndarray) -> np.ndarray:
    """Apply homogeneous transform T (4, 4, n_frames) to a point p (3,) in the
    segment-fixed frame, returning its trajectory in the lab frame (3, n_frames)."""
    R = T[0:3, 0:3, :]                       # (3, 3, n_frames)
    t = T[0:3, 3, :]                         # (3, n_frames)
    # rotated = R @ p, broadcast over frames
    rotated = np.einsum("ijk,j->ik", R, p_local)
    return rotated + t


def whole_body_com(record: TrialRecord, sex: str | None = None) -> np.ndarray:
    """Compute the whole-body centre of mass in the lab frame.

    Parameters
    ----------
    record : TrialRecord
    sex : str | None
        'M', 'F', or None. If None, the female and male inertial parameters
        from the C3D are averaged. (Theia stores gender-specific inertia in
        the same parameter block.)

    Returns
    -------
    np.ndarray  (3, n_frames)
    """
    if sex is not None:
        sex = sex.upper()
        if sex not in ("M", "F"):
            raise ValueError("sex must be 'M', 'F', or None")

    com_lab = np.zeros((3, record.n_frames))
    total_mass_pct = 0.0
    for inertia_key, segment_label in INERTIA_TO_SEGMENT.items():
        ip = record.inertia.get(inertia_key)
        if ip is None or segment_label not in record.segments:
            continue
        if sex == "F":
            m = ip["mass_pct_female"]
            p_local = np.asarray(ip["com_female"], dtype=float)
        elif sex == "M":
            m = ip["mass_pct_male"]
            p_local = np.asarray(ip["com_male"], dtype=float)
        else:
            m = 0.5 * (ip["mass_pct_female"] + ip["mass_pct_male"])
            p_local = 0.5 * (np.asarray(ip["com_female"], dtype=float)
                             + np.asarray(ip["com_male"], dtype=float))
        T = record.segments[segment_label]
        com_seg_lab = transform_point(T, p_local)   # (3, n_frames)
        com_lab += m * com_seg_lab
        total_mass_pct += m
    if total_mass_pct == 0.0:
        raise RuntimeError("No segment inertias available — cannot compute COM.")
    com_lab /= total_mass_pct
    return com_lab


def linear_velocity(position: np.ndarray, rate_hz: float) -> np.ndarray:
    """Compute linear velocity by central differences along the last axis."""
    return np.gradient(position, 1.0 / rate_hz, axis=-1)


def linear_acceleration(position: np.ndarray, rate_hz: float,
                        fc_smooth_hz: float | None = 6.0) -> np.ndarray:
    """Compute linear acceleration as second time derivative of position.

    A short low-pass smoothing (4th-order Butterworth, zero-lag) is applied
    before differentiation to suppress quantisation noise that is amplified
    by double differentiation. Pass `fc_smooth_hz=None` to disable.
    """
    from scipy.signal import butter, filtfilt
    if fc_smooth_hz is not None:
        b, a = butter(4, fc_smooth_hz / (0.5 * rate_hz), btype="low")
        pos_s = filtfilt(b, a, position, axis=-1)
    else:
        pos_s = position
    vel = np.gradient(pos_s, 1.0 / rate_hz, axis=-1)
    acc = np.gradient(vel, 1.0 / rate_hz, axis=-1)
    return acc


def end_effector_speed(record: TrialRecord, segment: str) -> np.ndarray:
    """Scalar speed (magnitude of velocity) of a segment origin, in m/s."""
    pos = record.segments[segment][0:3, 3, :]
    vel = linear_velocity(pos, record.rate_hz)
    return np.linalg.norm(vel, axis=0)
