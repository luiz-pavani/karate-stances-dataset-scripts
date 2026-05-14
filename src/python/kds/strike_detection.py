"""Detect the *gyaku-tsuki* (reverse-punch) strike instant from hand
end-effector velocity.

Each 9-second trial is structured as:
  t = 0–3 s  pre-strike quasi-static window (stance assumed, no movement)
  t = 3 s    "vai" verbal cue, gyaku-tsuki executed
  t = 3–6 s  strike + transient (hand accelerates, hits target, returns)
  t = 6–9 s  post-strike re-stabilised window

The dominant guard is recorded per subject (see demographics.py). The
dominant attacking hand is the **rear** hand in karate (the hand whose
side is opposite to the front-leg side); we use the participant's dominant
guard as a proxy and fall back to detecting which hand had the highest
peak speed.
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


def detect_strike(record: TrialRecord, hand: str | None = None,
                  onset_threshold: float = 0.10) -> StrikeEvent:
    """Detect the strike event in a single dynamic trial.

    Parameters
    ----------
    record : TrialRecord
    hand : str | None
        'r_hand', 'l_hand', or None. If None, the hand with the higher peak
        speed within the trial is chosen automatically.
    onset_threshold : float
        Fraction of peak speed at which strike onset and return are marked.
    """
    speeds = {h: end_effector_speed(record, h) for h in ("r_hand", "l_hand")}
    if hand is None:
        # Pick the hand with the larger peak speed
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
