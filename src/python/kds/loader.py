"""Load Theia3D-exported C3D trials and Visual3D POS txt files.

The Theia3D output stores 19 rigid-body segments as 4x4 transformation
matrices (rotation 3x3 + translation 3x1) sampled at 180 Hz. Per-segment
inertial parameters (mass percentage, COM in segment frame, radius of
gyration) are stored gender-specifically in the THEIA3D parameter group
of the C3D file.

The accompanying Visual3D pipelines export, for each trial, a tab-separated
text file with proximal/distal endpoints of each foot, two custom lateral
foot landmarks, and the whole-body COM. We load both sources and provide
a single TrialRecord container that downstream stages consume.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Optional
import numpy as np
import pandas as pd
import ezc3d


SEGMENT_LABELS_EXPECTED = [
    "worldbody", "pelvis", "l_thigh", "l_shank", "l_foot", "l_toes",
    "r_thigh", "r_shank", "r_foot", "r_toes",
    "head", "torso",
    "l_uarm", "l_larm", "l_hand", "r_uarm", "r_larm", "r_hand",
    "pelvis_shifted",
]

FNAME_RE = re.compile(
    r"^(?P<id>ID\d{3})_(?P<base>ZEN|KOK|KUK|KIB|STATIC)_T(?P<trial>\d+)_pose(?P<flt>_filt)?_0\.c3d$"
)

# ID009 has a base directory named "KUK" (acquisition-time typo for KOK).
# We map it to KOK at load time without renaming the source files.
BASE_CANONICAL = {"KUK": "KOK"}


@dataclass
class TrialRecord:
    """Container for one Theia3D-processed trial."""
    subject: str               # e.g. "ID003"
    base: str                  # "ZEN" | "KOK" | "KIB" | "STATIC"
    trial: int                 # 1..5  (STATIC always 1)
    filtered: bool             # True if loaded from *_pose_filt_0.c3d
    rate_hz: float             # 180.0
    n_frames: int              # 1620 for dynamic, variable for STATIC
    time: np.ndarray           # (n_frames,) seconds since trial start
    segments: dict[str, np.ndarray]
    # segments[label] -> (4, 4, n_frames) homogeneous transforms (lab frame)
    inertia: dict[str, dict]   # per-segment inertia parameters
    metadata: dict             # raw metadata from C3D header
    pos_com_df: Optional[pd.DataFrame] = field(default=None)
    # Optional Visual3D POS export (per-frame COM + landmarks)


def _strip_underscore_suffix(label: str) -> str:
    """worldbody_4X4 -> worldbody"""
    return label.replace("_4X4", "")


def _parse_inertia_params(theia_group: dict) -> dict[str, dict]:
    """Extract per-segment inertia parameters from the THEIA3D parameter group.

    The THEIA3D group stores keys like INERTIA_L_THIGH with vectors that follow the
    schema `length; mass% female; COM_xyz female; radius_of_gyration_xyz female;
    mass% male; COM_xyz male; radius_of_gyration_xyz male`. We parse them into a
    dict keyed by segment label.
    """
    inertia: dict[str, dict] = {}
    for key, payload in theia_group.items():
        if not key.startswith("INERTIA_"):
            continue
        seg = key.replace("INERTIA_", "").lower()
        vals = np.asarray(payload.get("value", []), dtype=float).flatten()
        # Schema: [length, m%_f, COMx_f, COMy_f, COMz_f, kx_f, ky_f, kz_f,
        #                    m%_m, COMx_m, COMy_m, COMz_m, kx_m, ky_m, kz_m]
        # head/thorax keys have only one block (length sentinel -1 in head).
        if vals.size >= 8:
            inertia[seg] = {
                "length": float(vals[0]),
                "mass_pct_female": float(vals[1]),
                "com_female": vals[2:5].tolist(),
                "radius_gyration_female": vals[5:8].tolist() if vals.size >= 8 else [],
                "mass_pct_male": float(vals[8]) if vals.size >= 9 else float(vals[1]),
                "com_male": vals[9:12].tolist() if vals.size >= 12 else vals[2:5].tolist(),
                "radius_gyration_male": vals[12:15].tolist() if vals.size >= 15 else vals[5:8].tolist(),
            }
    return inertia


def read_c3d_trial(path: str | Path) -> TrialRecord:
    """Read a Theia3D C3D file and return a TrialRecord."""
    path = Path(path)
    fn = path.name
    m = FNAME_RE.match(fn)
    if not m:
        raise ValueError(f"Filename does not match expected pattern: {fn}")
    subject = m.group("id")
    base_raw = m.group("base")
    base = BASE_CANONICAL.get(base_raw, base_raw)
    trial = int(m.group("trial"))
    filtered = m.group("flt") is not None

    c = ezc3d.c3d(str(path))
    rate = float(c["parameters"]["POINT"]["RATE"]["value"][0])
    n_frames = int(c["parameters"]["POINT"]["FRAMES"]["value"][0])
    rotations = c["data"]["rotations"]
    # rotations shape: (4, 4, n_segments, n_frames)
    rot_labels = [_strip_underscore_suffix(s)
                  for s in c["parameters"]["ROTATION"]["LABELS"]["value"]]
    if rot_labels != SEGMENT_LABELS_EXPECTED:
        # Tolerate ordering differences; rebuild dict by label
        pass

    segments = {lab: rotations[:, :, i, :] for i, lab in enumerate(rot_labels)}
    inertia = _parse_inertia_params(c["parameters"].get("THEIA3D", {}))
    time = np.arange(n_frames) / rate

    metadata = {
        "manufacturer": c["parameters"]["MANUFACTURER"].get("COMPANY", {}).get("value", []),
        "software": c["parameters"]["MANUFACTURER"].get("SOFTWARE", {}).get("value", []),
        "theia_version": c["parameters"]["MANUFACTURER"].get("VERSION", {}).get("value", []),
        "filt_freq_hz": float(c["parameters"]["THEIA3D"]["FILT_FREQ"]["value"][0]),
        "filtered_flag": bool(c["parameters"]["THEIA3D"]["FILTERED"]["value"][0]),
        "model_version": c["parameters"]["THEIA3D"]["MODEL_VERSION"]["value"].tolist(),
        "detector_version": int(c["parameters"]["THEIA3D"]["DETECTOR_VERSION"]["value"][0]),
        "source_path": str(path),
    }
    return TrialRecord(
        subject=subject, base=base, trial=trial, filtered=filtered,
        rate_hz=rate, n_frames=n_frames, time=time,
        segments=segments, inertia=inertia, metadata=metadata,
    )


def read_pos_com_txt(path: str | Path) -> pd.DataFrame:
    """Read a Visual3D-exported Marker_Pos_COM.txt file.

    The file has 5 header rows (file path, target name, signal type, source
    type, axis) followed by data rows starting at row 6 with columns:
        ITEM (frame index)  +  21 spatial coordinates
        [LFT DistEnd XYZ, LFT ProxEnd XYZ, Lateral_left_foot XYZ,
         RFT DistEnd XYZ, RFT ProxEnd XYZ, Lateral_right_foot XYZ,
         CenterOfMass XYZ]
    """
    df = pd.read_csv(path, sep="\t", skiprows=5, header=None)
    columns = [
        "frame",
        "LFT_DistEnd_x", "LFT_DistEnd_y", "LFT_DistEnd_z",
        "LFT_ProxEnd_x", "LFT_ProxEnd_y", "LFT_ProxEnd_z",
        "Lateral_left_foot_x", "Lateral_left_foot_y", "Lateral_left_foot_z",
        "RFT_DistEnd_x", "RFT_DistEnd_y", "RFT_DistEnd_z",
        "RFT_ProxEnd_x", "RFT_ProxEnd_y", "RFT_ProxEnd_z",
        "Lateral_right_foot_x", "Lateral_right_foot_y", "Lateral_right_foot_z",
        "CenterOfMass_x", "CenterOfMass_y", "CenterOfMass_z",
    ]
    df.columns = columns[: df.shape[1]]
    df = df.dropna(axis=0, how="all").reset_index(drop=True)
    return df


def discover_trials(root: str | Path, prefer_filtered: bool = True) -> list[Path]:
    """Walk the dataset root and return list of trial C3D paths.

    Each subject has 15 dynamic trials (3 bases x 5 reps) and optionally 1
    STATIC trial. By default we return the filtered (`_pose_filt_0`) variant
    of each trial; pass `prefer_filtered=False` to get the raw variant.
    """
    root = Path(root)
    suffix = "_pose_filt_0.c3d" if prefer_filtered else "_pose_0.c3d"
    files: list[Path] = []
    for subject_dir in sorted(root.glob("ID*")):
        if not subject_dir.is_dir():
            continue
        for base in ("ZEN", "KOK", "KUK", "KIB", "STATIC"):
            base_dir = subject_dir / base
            if not base_dir.exists():
                continue
            for trial_dir in sorted(base_dir.glob("T*")):
                for f in sorted(trial_dir.glob(f"*{suffix}")):
                    files.append(f)
    return files


def discover_pos_txt(root: str | Path) -> dict[tuple[str, str, int], Path]:
    """Map (subject, base, trial) to the Visual3D POS export, if present."""
    root = Path(root)
    out: dict[tuple[str, str, int], Path] = {}
    for txt in root.rglob("*_Marker_Pos_COM.txt"):
        # Filename pattern: IDxxx_BASE_Tn_pose_filt_0.c3d_Marker_Pos_COM.txt
        m = re.match(r"^(ID\d{3})_(ZEN|KOK|KUK|KIB)_T(\d+)_", txt.name)
        if m:
            base = BASE_CANONICAL.get(m.group(2), m.group(2))
            out[(m.group(1), base, int(m.group(3)))] = txt
    return out
