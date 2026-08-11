"""Shared progress-event schema for workers and training code."""

import time


def make_progress_event(phase, *, started_at, battery=None, seed=None,
                        epoch=None, current=0, total=0):
    return {
        'phase': str(phase),
        'battery': battery,
        'seed': seed,
        'epoch': epoch,
        'current': int(current),
        'total': int(total),
        'elapsed_seconds': max(0.0, time.monotonic() - started_at),
    }
