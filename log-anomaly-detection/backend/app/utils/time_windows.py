"""
time_windows.py

Pure, log-agnostic helpers for fixed-size time bucketing. Kept separate from
feature_engineering.py so this logic is reusable (e.g. by the live detection
scheduler in core/scheduler.py) and independently testable.
"""

import pandas as pd


def floor_to_window(timestamps: pd.Series, window_seconds: int) -> pd.Series:
    """
    Floor a series of datetime values down to the start of their containing
    fixed-size window.

    Example: with window_seconds=60, 09:14:37 -> 09:14:00
    """
    return timestamps.dt.floor(f"{window_seconds}s")


def full_window_range(start: pd.Timestamp, end: pd.Timestamp, window_seconds: int) -> pd.DatetimeIndex:
    """
    Build the complete, gap-free sequence of window_start timestamps spanning
    [start, end], inclusive. Used to ensure every window is represented in the
    output feature table, even ones with zero logs (see docs/ml_design.md,
    section 4.3 - "Handling empty windows").
    """
    range_start = start.floor(f"{window_seconds}s")
    range_end = end.floor(f"{window_seconds}s")
    return pd.date_range(start=range_start, end=range_end, freq=f"{window_seconds}s")


def window_end(window_start: pd.Series, window_seconds: int) -> pd.Series:
    """Compute window_end = window_start + window_seconds for a series of window starts."""
    return window_start + pd.Timedelta(seconds=window_seconds)