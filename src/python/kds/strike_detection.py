"""Detect the *gyaku-tsuki* (reverse-punch) strike instant from hand
end-effector velocity.

Each 9-second trial is structured as:
  t = 0–3 s  pre-strike quasi-static window (stance assumed, no movement)
  t = 3 s    "vai" verbal cue, gyaku-tsuki executed
  t = 3–6 s  strike + transient (hand accelerates, hits target, returns)
  t = 6–9 s  post-strike re-stabilised window

The dominant guard is recorded per subject (see demographics.py). The
attacking hand in the *gyaku-tsuki* is the **rear** hand (opposite to the
front-leg side), while the contralateral hand performs *hikite* — a
simultaneous pull-back to the hip whose peak speed can exceed the punch's.

Up to v0.5.0 the automatic fallback chose "the hand with the highest peak
speed", which selects the *hikite* hand in 60/180 trials of the released
dataset (audited 2026-11-03). Since v0.6.0 the punching hand is identified
by its **forward excursion along the stance's facing axis** (KIB faces
lab +X; ZEN/KOK face lab +Y): the punch travels toward the virtual
opponent, the *hikite* does not. In the 120 ZEN/KOK trials this criterion
agrees 100% with the foot-geometry rule (punching hand opposite to the
front foot). The peak-speed rule is retained only as a last-resort
fallback when the excursion windows are unavailable.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass
from .loader import TrialRecord
from .kinematics_linear import end_effector_speed


@dataclass
class StrikeEvent:
    hand_used: str        # 'r_hand' or 'l_hand'
    peak_speed_mps: float
    peak_time_s: float
    onset_time_s: float   # time at which hand speed first exceeds 10% of peak
    return_time_s: float  # time at which hand speed re-falls below 10% of peak


def punch_hand(record: TrialRecord) -> str:
    """Identify the punching hand by forward excursion along the stance's
    facing axis (v0.6.0 criterion; see module docstring).

    Excursion = (max position during the strike window, 3–6 s) minus
    (mean position during the pre-strike hold, 1–3 s), measured on the
    lab axis the stance faces (KIB: +X; ZEN/KOK: +Y). The punching hand
    is the one with the larger forward excursion.
    """
    ax = 0 if record.base == "KIB" else 1
    tm = record.time
    pre = (tm >= 1.0) & (tm <= 3.0)
    win = (tm >= 3.0) & (tm <= 6.0)
    if not pre.any() or not win.any():
        raise ValueError("strike/pre windows unavailable for excursion criterion")
    exc = {}
    for h in ("r_hand", "l_hand"):
        pos = record.segments[h][ax, 3, :]
        exc[h] = float(pos[win].max() - pos[pre].mean())
    return max(exc, key=exc.get)


def detect_strike(record: TrialRecord, hand: str | None = None,
                  onset_threshold: float = 0.10) -> StrikeEvent:
    """Detect the strike event in a single dynamic trial.

    Parameters
    ----------
    record : TrialRecord
    hand : str | None
        'r_hand', 'l_hand', or None. If None, the punching hand is
        identified by forward excursion along the stance's facing axis
        (``punch_hand``; v0.6.0 — the pre-v0.6.0 peak-speed rule selected
        the *hikite* hand in 60/180 released trials and is kept only as a
        last-resort fallback).
    onset_threshold : float
        Fraction of peak speed at which strike onset and return are marked.
    """
    speeds = {h: end_effector_speed(record, h) for h in ("r_hand", "l_hand")}
    if hand is None:
        try:
            hand = punch_hand(record)
        except Exception:
            # Last-resort fallback: hand with the larger peak speed
            hand = max(speeds, key=lambda h: speeds[h].max())
    s = speeds[hand]
    peak_idx = int(np.argmax(s))
    peak = float(s[peak_idx])
    threshold = onset_threshold * peak
    # Onset = last frame before peak where speed crosses threshold ascending
    pre = np.where(s[:peak_idx] < threshold)[0]
    onset_idx = int(pre[-1]) if pre.size else 0
    # Return = first frame after peak where speed falls below threshold
    post = np.where(s[peak_idx:] < threshold)[0]
    return_idx = int(peak_idx + (post[0] if post.size else len(s) - peak_idx - 1))
    return StrikeEvent(
        hand_used=hand,
        peak_speed_mps=peak,
        peak_time_s=float(record.time[peak_idx]),
        onset_time_s=float(record.time[onset_idx]),
        return_time_s=float(record.time[return_idx]),
    )
