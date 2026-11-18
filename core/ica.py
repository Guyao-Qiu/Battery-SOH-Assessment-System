"""因果增量容量分析（ICA, dQ/dV）特征提取模块。

每个循环仅使用该循环自身的恒流充电电压-电流-时间片段独立计算，严格满足因果性，
不读取未来循环或整条寿命轨迹统计量。数据缺失或曲线过短时返回 ``NaN``。
"""

from __future__ import annotations

import numpy as np
from scipy.signal import savgol_filter


DEFAULT_DV = 0.005
DEFAULT_SMOOTH_WINDOW = 15
DEFAULT_POLYORDER = 3
DEFAULT_PEAK_HALF_WIDTH = 0.15
DEFAULT_MIN_POINTS = 10
DEFAULT_MIN_V_SPAN = 0.05


def compute_ica_curve(
    voltage,
    current,
    time_s,
    *,
    dv: float = DEFAULT_DV,
    smooth_window: int = DEFAULT_SMOOTH_WINDOW,
    polyorder: int = DEFAULT_POLYORDER,
    min_points: int = DEFAULT_MIN_POINTS,
    min_v_span: float = DEFAULT_MIN_V_SPAN,
) -> tuple[np.ndarray, np.ndarray]:
    """从单个循环的恒流充电片段计算均匀电压网格上的平滑 ``dQ/dV`` 曲线。

    参数仅包含当前循环序列；数据缺失、有效充电点不足或压升跨度过小时返回一对空数组。
    """
    v_arr = np.asarray(voltage, dtype=np.float64).reshape(-1)
    i_arr = np.asarray(current, dtype=np.float64).reshape(-1)
    t_arr = np.asarray(time_s, dtype=np.float64).reshape(-1)

    n = min(len(v_arr), len(i_arr), len(t_arr))
    if n < min_points:
        return np.empty(0, dtype=np.float64), np.empty(0, dtype=np.float64)

    v_arr = v_arr[:n]
    i_arr = i_arr[:n]
    t_arr = t_arr[:n]

    finite = np.isfinite(v_arr) & np.isfinite(i_arr) & np.isfinite(t_arr) & (i_arr > 1e-3)
    if int(np.sum(finite)) < min_points:
        return np.empty(0, dtype=np.float64), np.empty(0, dtype=np.float64)

    v_cc = v_arr[finite]
    i_cc = i_arr[finite]
    t_cc = t_arr[finite]

    dt = np.diff(t_cc)
    if len(dt) == 0 or np.all(dt <= 0):
        return np.empty(0, dtype=np.float64), np.empty(0, dtype=np.float64)

    dt_pos = np.maximum(dt, 0.0)
    q_cc = np.concatenate([[0.0], np.cumsum(dt_pos * i_cc[1:] / 3600.0)])
    if not np.isfinite(q_cc[-1]) or q_cc[-1] <= 0.0:
        return np.empty(0, dtype=np.float64), np.empty(0, dtype=np.float64)

    order = np.argsort(v_cc, kind='mergesort')
    v_sorted = v_cc[order]
    q_sorted = q_cc[order]
    v_unique, unique_idx, counts = np.unique(v_sorted, return_index=True, return_counts=True)
    if len(v_unique) < 5 or (float(v_unique[-1]) - float(v_unique[0])) < min_v_span:
        return np.empty(0, dtype=np.float64), np.empty(0, dtype=np.float64)

    # 对重复电压采样点取容量均值，避免微小电压抖动产生阶跃伪峰
    q_sums = np.add.reduceat(q_sorted, unique_idx)
    q_unique = q_sums / counts

    v_start = float(v_unique[0])
    v_end = float(v_unique[-1])
    grid = np.arange(v_start, v_end + 1e-9, dv, dtype=np.float64)
    grid = grid[grid <= v_end + 1e-12]
    if len(grid) < 7:
        return np.empty(0, dtype=np.float64), np.empty(0, dtype=np.float64)

    q_grid = np.interp(grid, v_unique, q_unique)
    win = min(int(smooth_window), len(grid) if len(grid) % 2 == 1 else len(grid) - 1)
    if win < 5:
        return np.empty(0, dtype=np.float64), np.empty(0, dtype=np.float64)
    poly = min(int(polyorder), win - 2)
    if poly < 1:
        return np.empty(0, dtype=np.float64), np.empty(0, dtype=np.float64)

    dq_dv = savgol_filter(q_grid, window_length=win, polyorder=poly, deriv=1, delta=dv)
    return grid, dq_dv


def extract_cycle_ica(
    voltage,
    current,
    time_s,
    *,
    dv: float = DEFAULT_DV,
    smooth_window: int = DEFAULT_SMOOTH_WINDOW,
    polyorder: int = DEFAULT_POLYORDER,
    peak_half_width: float = DEFAULT_PEAK_HALF_WIDTH,
    min_points: int = DEFAULT_MIN_POINTS,
    min_v_span: float = DEFAULT_MIN_V_SPAN,
) -> tuple[float, float, float]:
    """提取单循环 ICA 主峰特征 ``(ica_peak_v, ica_peak_h, ica_peak_area)``。

    - ``ica_peak_v``：主峰电压位置 (V)
    - ``ica_peak_h``：主峰峰值高度 (Ah/V)
    - ``ica_peak_area``：主峰邻域 ``[V_peak - w, V_peak + w]`` 正向积分面积 (Ah)
    """
    grid, dq_dv = compute_ica_curve(
        voltage,
        current,
        time_s,
        dv=dv,
        smooth_window=smooth_window,
        polyorder=polyorder,
        min_points=min_points,
        min_v_span=min_v_span,
    )
    if len(grid) == 0 or not np.any(np.isfinite(dq_dv)):
        return (np.nan, np.nan, np.nan)

    # 跳过边界 2 个网格点，防止数值求导边界效应产生伪峰
    margin = 2 if len(grid) > 6 else 0
    view = dq_dv[margin : len(grid) - margin]
    if len(view) == 0 or not np.any(np.isfinite(view)):
        return (np.nan, np.nan, np.nan)

    local_idx = int(np.nanargmax(view))
    peak_idx = margin + local_idx
    peak_h = float(dq_dv[peak_idx])
    if not np.isfinite(peak_h) or peak_h <= 0.0:
        return (np.nan, np.nan, np.nan)

    peak_v = float(grid[peak_idx])
    band = (grid >= peak_v - peak_half_width) & (grid <= peak_v + peak_half_width)
    if int(np.sum(band)) < 2:
        peak_area = np.nan
    else:
        peak_area = float(np.trapz(np.maximum(dq_dv[band], 0.0), grid[band]))
    return (peak_v, peak_h, peak_area)


def extract_tabular_ica_features(
    df,
    cc_step: int,
    discharge_step: int,
) -> tuple[list[float], list[float], list[float]]:
    """按与 ``_extract_capacity_lists_fast`` 相同的有效循环顺序提取 CALCE 逐循环 ICA 特征。"""
    peak_vs: list[float] = []
    peak_hs: list[float] = []
    peak_areas: list[float] = []

    for _, g in df.groupby('Cycle_Index', sort=True):
        step = g['Step_Index'].to_numpy()
        is_d = step == discharge_step
        td = g['Test_Time(s)'].to_numpy(dtype=float)[is_d]
        idd = g['Current(A)'].to_numpy(dtype=float)[is_d]
        if len(idd) == 0 or len(td) <= 1:
            continue

        is_cc = step == cc_step
        if not is_cc.any():
            peak_vs.append(np.nan)
            peak_hs.append(np.nan)
            peak_areas.append(np.nan)
            continue

        pv, ph, pa = extract_cycle_ica(
            g['Voltage(V)'].to_numpy(dtype=float)[is_cc],
            g['Current(A)'].to_numpy(dtype=float)[is_cc],
            g['Test_Time(s)'].to_numpy(dtype=float)[is_cc],
        )
        peak_vs.append(pv)
        peak_hs.append(ph)
        peak_areas.append(pa)

    return peak_vs, peak_hs, peak_areas


def extract_nasa_charge_ica(
    charge_data: dict,
    *,
    v_cv: float = 4.2,
) -> tuple[float, float, float]:
    """从 NASA ``charge`` 循环结构体中切出恒流段并提取 ICA 特征。"""
    t = np.asarray(charge_data.get('Time', []), dtype=float).reshape(-1)
    v = np.asarray(charge_data.get('Voltage_measured', []), dtype=float).reshape(-1)
    i = np.asarray(charge_data.get('Current_measured', []), dtype=float).reshape(-1)
    n = min(len(t), len(v), len(i))
    if n < DEFAULT_MIN_POINTS:
        return (np.nan, np.nan, np.nan)
    t, v, i = t[:n], v[:n], i[:n]

    # 仅保留达到恒压平台前的恒流充电段（留 10 mV 余量以避开 CV 切换平台堆叠）
    cc_mask = np.isfinite(t) & np.isfinite(v) & np.isfinite(i) & (v < float(v_cv) - 0.01) & (i > 0.05)
    return extract_cycle_ica(v[cc_mask], i[cc_mask], t[cc_mask])
