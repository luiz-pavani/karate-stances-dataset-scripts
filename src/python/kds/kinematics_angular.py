"""Joint angles by decomposition of the relative orientation between
adjacent segments, following the International Society of Biomechanics
(ISB) recommendations (Wu et al. 2002, 2005) where applicable.

Each segment is described in the lab frame by a 4x4 homogeneous transform
T_seg = [R_seg t_seg; 0 1]. The orientation of a distal segment with respect
to its parent (proximal) segment is
    R_rel = R_parent.T @ R_distal
We decompose R_rel into a Cardan/Euler sequence appropriate for the joint:

  - Lower limb: Z-X-Y  (flexion/extension, abduction/adduction, internal/external rot.)
  - Upper limb: Y-X-Z  (Wu et al. 2005)
  - Pelvis (vs world): Z-X-Y (tilt, obliquity, rotation)
  - Trunk (torso vs pelvis): Z-X-Y

This file emits, per trial, a dict[joint_name -> (3, n_frames) array of
angles in degrees], plus angular velocities (deg/s) and ROM scalars.
"""

from __future__ import annotations
import numpy as np
from .loader import TrialRecord
from .kinematics_linear import linear_velocity


# (joint_name, parent_label, child_label, euler_sequence)
# Sequences follow ISB conventions; output components correspond to:
#   flexion/extension, abduction/adduction, internal/external rotation
JOINT_DEFINITIONS = [
    # Lower limb
    ("hip_right",    "pelvis", "r_thigh", "zxy"),
    ("hip_left",     "pelvis", "l_thigh", "zxy"),
    ("knee_right",   "r_thigh", "r_shank", "zxy"),
    ("knee_left",    "l_thigh", "l_shank", "zxy"),
    ("ankle_right",  "r_shank", "r_foot",  "zxy"),
    ("ankle_left",   "l_shank", "l_foot",  "zxy"),
    # Upper limb
    ("shoulder_right", "torso", "r_uarm", "yxz"),
    ("shoulder_left",  "torso", "l_uarm", "yxz"),
    ("elbow_right",    "r_uarm", "r_larm", "yxz"),
    ("elbow_left",     "l_uarm", "l_larm", "yxz"),
    # Axial
    ("pelvis_world", "worldbody", "pelvis", "zxy"),
    ("trunk",        "pelvis",    "torso",  "zxy"),
]


def _euler_from_matrix(R: np.ndarray, seq: str = "zxy") -> np.ndarray:
    """Decompose a stack of 3x3 rotation matrices into Cardan angles.

    Parameters
    ----------
    R : np.ndarray
        (3, 3, n_frames) rotation matrices.
    seq : str
        Intrinsic rotation sequence, e.g. 'zxy', 'yxz', 'xyz'.

    Returns
    -------
    angles : np.ndarray (3, n_frames) in radians
    """
    # We use scipy's Rotation for numerical robustness across the time series.
    from scipy.spatial.transform import Rotation
    # scipy expects (n, 3, 3); transpose
    Rmat = np.transpose(R, (2, 0, 1))
    rot = Rotation.from_matrix(Rmat)
    # Capital letters in scipy 'as_euler' mean intrinsic (matches ISB convention)
    angles = rot.as_euler(seq.upper(), degrees=False)  # (n_frames, 3)
    return angles.T


def joint_angles(record: TrialRecord) -> dict[str, np.ndarray]:
    """Compute Cardan joint angles for the joints defined in JOINT_DEFINITIONS.

    Returns
    -------
    dict mapping joint name to (3, n_frames) array of angles in degrees.
    """
    out: dict[str, np.ndarray] = {}
    for joint, parent, child, seq in JOINT_DEFINITIONS:
        if parent not in record.segments or child not in record.segments:
            continue
        Rp = record.segments[parent][0:3, 0:3, :]   # (3,3,n)
        Rc = record.segments[child][0:3, 0:3, :]
        # Relative rotation: R_rel = R_parent^T @ R_child
        # einsum over frame axis
        Rp_T = np.transpose(Rp, (1, 0, 2))            # transpose 3x3 in place
        Rrel = np.einsum("ijk,jlk->ilk", Rp_T, Rc)
        angles_rad = _euler_from_matrix(Rrel, seq)
        out[joint] = np.degrees(angles_rad)
    return out


def angular_velocity(angles_deg: np.ndarray, rate_hz: float) -> np.ndarray:
    """Angular velocity from joint angle time-series (central differences).

    Output: (3, n_frames) in deg/s.
    """
    # Unwrap to avoid 360° jumps before differentiating
    angles_rad = np.deg2rad(angles_deg)
    unwrapped = np.unwrap(angles_rad, axis=-1)
    return np.degrees(np.gradient(unwrapped, 1.0 / rate_hz, axis=-1))


def angular_range_of_motion(angles_deg: np.ndarray,
                            window: slice | None = None) -> np.ndarray:
    """Return ROM (max − min) per axis over the given window.

    Output: shape (3,) — ROM for each rotation component, in degrees.
    """
    a = angles_deg if window is None else angles_deg[:, window]
    return a.max(axis=-1) - a.min(axis=-1)
