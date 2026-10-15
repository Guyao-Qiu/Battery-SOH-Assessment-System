"""Interpret failure-cycle results without losing original cycle identifiers."""

import numpy as np

#: 判定「真正失效」所需的连续低于阈值循环数（A12）。
#: 默认 1 = 旧行为（首次下穿即失效），保持向后兼容；设为 3 可避免单点噪声
#: 下穿阈值就被当成失效。
DEFAULT_DEBOUNCE_CYCLES = 1


def first_failure_index(values, threshold, debounce=DEFAULT_DEBOUNCE_CYCLES):
    """首次**持续**下穿的位置；从未下穿返回 None（右删失）。

    这是全工程**唯一**的失效判定实现：``core.protocol.first_cross``、
    ``core.evaluate`` 与 ``core.train`` 都委托到这里，避免多份逻辑各自漂移。

    ``debounce`` 是需要连续低于阈值的循环数：
    ``1``（默认）＝「首次下穿即失效」；``3`` 则要求连续 3 个循环低于阈值。
    返回值仍是**连续区间的第一个位置**，因此开启去抖也不会让报告的失效循环
    比真实下穿更晚。
    """
    array = np.asarray(values, dtype=np.float64).reshape(-1)
    below = array < threshold
    run = int(max(1, debounce))
    if run == 1:
        positions = np.flatnonzero(below)
        return int(positions[0]) if len(positions) else None

    if len(below) < run:
        return None
    # 长度为 run 的滑窗内是否全为 True。
    # 注意：``mode='valid'`` 的输出下标 i 正好对应该窗口的**起点** i，
    # 所以命中的第一个下标就是「首次下穿处」，不需要再偏移。
    window_ok = np.convolve(
        below.astype(np.int64), np.ones(run, dtype=np.int64), mode='valid')
    hits = np.flatnonzero(window_ok == run)
    return int(hits[0]) if len(hits) else None


def _cycle_value(cycle_ids, position):
    if position is None:
        return None
    value = np.asarray(cycle_ids).reshape(-1)[position]
    return value.item() if isinstance(value, np.generic) else value


def analyze_failure_cycles(cycle_ids, measured, predicted, threshold,
                           prediction_start=0):
    """Return measured/predicted failure states using the supplied cycle IDs."""
    cycle_ids = np.asarray(cycle_ids).reshape(-1)
    measured = np.asarray(measured, dtype=np.float64).reshape(-1)
    predicted = np.asarray(predicted, dtype=np.float64).reshape(-1)
    if (isinstance(prediction_start, bool) or
            not isinstance(prediction_start, (int, np.integer)) or
            not 0 <= int(prediction_start) <= len(measured)):
        raise ValueError('预测起始位置必须位于实测序列范围内')
    prediction_start = int(prediction_start)
    if (len(cycle_ids) != len(measured) or
            len(predicted) != len(measured) - prediction_start):
        raise ValueError('循环编号、实测容量和预测区间长度不匹配')

    measured_position = first_failure_index(measured, threshold)
    predicted_local_position = first_failure_index(predicted, threshold)
    predicted_position = (
        None if predicted_local_position is None
        else prediction_start + predicted_local_position)

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
