import numpy as np


def _resample_to_1hz(time_s, watts):
    if len(time_s) < 2:
        return np.array([])
    t = np.asarray(time_s, dtype=float)
    w = np.asarray(watts, dtype=float)
    full_t = np.arange(t[0], t[-1] + 1)
    return np.interp(full_t, t, w)


def peak_powers(time_s, watts, durations_s):
    series = _resample_to_1hz(time_s, watts)
    if len(series) == 0:
        return {d: None for d in durations_s}

    cumsum = np.cumsum(np.insert(series, 0, 0.0))
    peaks = {}
    for d in durations_s:
        if len(series) < d:
            peaks[d] = None
            continue
        window_sums = cumsum[d:] - cumsum[:-d]
        peaks[d] = float(window_sums.max() / d)
    return peaks
