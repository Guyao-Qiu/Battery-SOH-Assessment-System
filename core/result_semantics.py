"""Interpret failure-cycle results without losing original cycle identifiers."""

import numpy as np


def _first_failure(values, threshold):
    array = np.asarray(values, dtype=np.float64).reshape(-1)
    positions = np.flatnonzero(array < threshold)
    return int(positions[0]) if len(positions) else None


def _cycle_value(cycle_ids, position):
    if position is None:
        return None
    value = np.asarray(cycle_ids).reshape(-1)[position]
    return value.item() if isinstance(value, np.generic) else value


def analyze_failure_cycles(cycle_ids, measured, predicted, threshold):
    """Return measured/predicted failure states using original cycle IDs."""
    cycle_ids = np.asarray(cycle_ids).reshape(-1)
    measured = np.asarray(measured, dtype=np.float64).reshape(-1)
    predicted = np.asarray(predicted, dtype=np.float64).reshape(-1)
    if len(cycle_ids) != len(measured) or len(predicted) != len(measured):
        raise ValueError('循环编号、实测容量和预测容量长度必须一致')

    measured_position = _first_failure(measured, threshold)
    predicted_position = _first_failure(predicted, threshold)

    def status(position):
        if position is None:
            return 'not_observed'
        if position == 0:
            return 'initial_failure'
        return 'failed'

    return {
        'measured_failure_cycle': _cycle_value(
            cycle_ids, measured_position),
        'predicted_failure_cycle': _cycle_value(
            cycle_ids, predicted_position),
        'measured_failure_position': measured_position,
        'predicted_failure_position': predicted_position,
        'measured_failure_status': status(measured_position),
        'predicted_failure_status': status(predicted_position),
    }
