"""Load Bertec force-platform TSV files exported by Qualisys QTM.

Each acquired trial yields one TSV per platform (Bertec 3 = front foot,
Bertec 4 = rear foot in ZEN/KOK; arbitrary left/right in symmetric KIB).
The TSV carries a 26-line header with platform metadata (sampling rate,
4 corner positions in the lab frame, plate length/width, offsets) followed
by N rows of either 11 or 9 numeric columns sampled at 1000 Hz.

The data block exists in two variants in this dataset (depending on export
batch); both are handled here by counting columns at parse time:

    11-column variant (subjects ID003, ID004):
        col 0: sample index (1..N)
        col 1: time (s)
        col 2-4: Fx, Fy, Fz (N)        — lab frame
        col 5-7: Mx, My, Mz (N.mm)     — free moments about plate centre
        col 8-10: COPx, COPy, COPz (mm) — centre of pressure in lab frame

    9-column variant (subjects ID005-ID014):
        col 0-2: Fx, Fy, Fz (N)        — lab frame
        col 3-5: Mx, My, Mz (N.mm)
        col 6-8: COPx, COPy, COPz (mm)
        (sample index and time are not stored; reconstructed as
         arange(N)/rate using the NO_OF_SAMPLES and FREQUENCY header fields)

No filtering or transformation is performed at load time. The acquisition-
time typo `KUK` (ID009 posteriorised base) is mapped to `KOK` at load time
without modifying the source files.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Iterator
import numpy as np

from .loader import BASE_CANONICAL


FNAME_RE_KIN = re.compile(
    r"^(?P<id>ID\d{3})_(?P<base>ZEN|KOK|KUK|KIB|STATIC)"
    r"_T(?P<trial>\d+)_f_(?P<plate>\d+)\.tsv$"
)


@dataclass
class KineticTrial:
    """Container for one force-platform record (one plate of one trial)."""
    subject: str                # 'ID003'..'ID014'
    base: str                   # 'ZEN' | 'KOK' | 'KIB' | 'STATIC'  (KUK -> KOK)
    trial: int                  # 1..5 (STATIC always 1)
    plate: int                  # 3 or 4
    rate_hz: float              # 1000.0
    n_samples: int              # 9000 for dynamic, variable for STATIC
    time: np.ndarray            # (n_samples,) seconds
    force: np.ndarray           # (3, n_samples) Fx, Fy, Fz in N
    moment: np.ndarray          # (3, n_samples) Mx, My, Mz in N·mm
    cop: np.ndarray             # (3, n_samples) COPx, COPy, COPz in mm (lab frame)
    corners_mm: np.ndarray      # (4, 3) plate corners in lab frame, mm
    plate_name: str             # e.g. 'BERTEC 3'
    timestamp: str              # ISO-ish timestamp from header
    source_path: str
    extra_header: dict = field(default_factory=dict)


def _parse_header(lines: list[str]) -> tuple[dict, int]:
    """Return (header_dict, n_lines_consumed)."""
    h: dict[str, list[str]] = {}
    n = 0
    for ln in lines:
        if not ln or ln[0].isdigit() or ln[0] == "-":
            break
        parts = ln.rstrip("\n").split("\t")
        key, vals = parts[0], parts[1:]
        h[key] = vals
        n += 1
    return h, n


def read_kinetic_tsv(path: str | Path) -> KineticTrial:
    """Read a single Bertec force-platform TSV file."""
    path = Path(path)
    m = FNAME_RE_KIN.match(path.name)
    if not m:
        raise ValueError(f"Filename does not match expected pattern: {path.name}")
    subject = m.group("id")
    base_raw = m.group("base")
    base = BASE_CANONICAL.get(base_raw, base_raw)
    trial = int(m.group("trial"))
    plate = int(m.group("plate"))

    with open(path, "r") as f:
        text = f.read()
    lines = text.split("\n")
    header, n_header = _parse_header(lines)
    data = np.loadtxt(path, skiprows=n_header)
    if data.ndim == 1:
        data = data[None, :]
    rate = float(header["FREQUENCY"][0])

    # Two export variants: 11-col (frame, time, F×3, M×3, COP×3) or
    # 9-col (F×3, M×3, COP×3). Identify by column count.
    if data.shape[1] == 11:
        time_col = data[:, 1]
        force = data[:, 2:5].T
        moment = data[:, 5:8].T
        cop = data[:, 8:11].T
    elif data.shape[1] == 9:
        time_col = np.arange(data.shape[0]) / rate
        force = data[:, 0:3].T
        moment = data[:, 3:6].T
        cop = data[:, 6:9].T
    else:
        raise ValueError(
            f"Unexpected column count in {path.name}: {data.shape[1]} "
            "(expected 9 or 11)"
        )

    corners = np.array([
        [float(header["FORCE_PLATE_CORNER_POSX_POSY_X"][0]),
         float(header["FORCE_PLATE_CORNER_POSX_POSY_Y"][0]),
         float(header["FORCE_PLATE_CORNER_POSX_POSY_Z"][0])],
        [float(header["FORCE_PLATE_CORNER_NEGX_POSY_X"][0]),
         float(header["FORCE_PLATE_CORNER_NEGX_POSY_Y"][0]),
         float(header["FORCE_PLATE_CORNER_NEGX_POSY_Z"][0])],
        [float(header["FORCE_PLATE_CORNER_NEGX_NEGY_X"][0]),
         float(header["FORCE_PLATE_CORNER_NEGX_NEGY_Y"][0]),
         float(header["FORCE_PLATE_CORNER_NEGX_NEGY_Z"][0])],
        [float(header["FORCE_PLATE_CORNER_POSX_NEGY_X"][0]),
         float(header["FORCE_PLATE_CORNER_POSX_NEGY_Y"][0]),
         float(header["FORCE_PLATE_CORNER_POSX_NEGY_Z"][0])],
    ])
    plate_name = header.get("FORCE_PLATE_NAME", [""])[0]
    timestamp = ", ".join(header.get("TIME_STAMP", [""]))

    return KineticTrial(
        subject=subject, base=base, trial=trial, plate=plate,
        rate_hz=rate, n_samples=int(header["NO_OF_SAMPLES"][0]),
        time=time_col,
        force=force,
        moment=moment,
        cop=cop,
        corners_mm=corners,
        plate_name=plate_name,
        timestamp=timestamp,
        source_path=str(path),
        extra_header={
            "force_plate_type": header.get("FORCE_PLATE_TYPE", [""])[0],
            "force_plate_model": header.get("FORCE_PLATE_MODEL", [""])[0],
            "plate_length_mm": float(header.get("FORCE_PLATE_LENGTH", [0])[0]),
            "plate_width_mm": float(header.get("FORCE_PLATE_WIDTH", [0])[0]),
            "offset_xyz_mm": [
                float(header.get("FORCE_PLATE_OFFSET_X", [0])[0]),
                float(header.get("FORCE_PLATE_OFFSET_Y", [0])[0]),
                float(header.get("FORCE_PLATE_OFFSET_Z", [0])[0]),
            ],
        },
    )


def discover_kinetic_trials(root: str | Path) -> list[Path]:
    """Return all kinetic TSV file paths in the dataset root."""
    root = Path(root)
    return sorted(p for p in root.glob("*.tsv") if FNAME_RE_KIN.match(p.name))


def iter_trials_by_key(root: str | Path
                       ) -> Iterator[tuple[tuple[str, str, int], list[KineticTrial]]]:
    """Group plates per (subject, base, trial) and yield as a list.

    Each yielded list carries 1 or 2 KineticTrial objects (depending on
    whether both plates fired for that trial).
    """
    by_key: dict[tuple[str, str, int], list[KineticTrial]] = {}
    for p in discover_kinetic_trials(root):
        kt = read_kinetic_tsv(p)
        key = (kt.subject, kt.base, kt.trial)
        by_key.setdefault(key, []).append(kt)
    for key in sorted(by_key):
        yield key, sorted(by_key[key], key=lambda x: x.plate)
