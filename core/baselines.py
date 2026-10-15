"""经验基线：任何模型都必须先赢过它们。

每次评估都并排输出三条基线：

- **持久性（平推）**：下一个循环 = 上一个循环；
- **线性外推**：用窗口内最小二乘斜率向前推一步；
- **双指数**：``C(k) = a·e^{bk} + c·e^{dk}``，电池预测文献里最常用的经验基线。

前两条是「逐步」基线（可以放进递归预测器，每步重新拟合）；双指数是**直接多步**
基线——它在预测起点上对历史拟合一次，然后整段外推（每步重拟合既慢又没有意义）。
"""

import warnings

import numpy as np
from scipy.optimize import OptimizeWarning, curve_fit


def persistence_step(windows):
    """平推：下一个循环 = 上一个循环。任何模型都必须先赢过它。"""
    windows = np.asarray(windows, dtype=np.float64)
    return windows[:, -1]


def linear_step(windows):
    """线性外推：用窗口内最小二乘斜率向前推一步（按行独立拟合）。"""
    windows = np.asarray(windows, dtype=np.float64)
    if windows.ndim == 1:
        windows = windows.reshape(1, -1)
    x = np.arange(windows.shape[1], dtype=np.float64)
    out = np.empty(len(windows), dtype=np.float64)
    for row, values in enumerate(windows):
        slope = np.polyfit(x, values, 1)[0]
        out[row] = values[-1] + slope
    return out


def _dexp(k, a, b, c, d):
    return a * np.exp(b * k) + c * np.exp(d * k)


def double_exp_forecast(history, steps):
    """双指数经验退化模型 ``C(k) = a·e^{bk} + c·e^{dk}``。

    只用 ``history``（预测起点之前的数据）拟合；拟合失败或外推结果**不可信**时
    自动回退为线性外推。返回长度为 ``steps`` 的预测序列。

    「不可信」的判据：外推值出现非有限数、跑到负数、或高于历史最大值的 1.5 倍
    （电池容量不会越用越高，双指数在长程外推时容易发散）。
    """
    history = np.asarray(history, dtype=np.float64).reshape(-1)
    if steps <= 0:
        return np.empty(0, dtype=np.float64)
    if len(history) < 4:
        return np.full(steps, history[-1] if len(history) else 0.0)

    y = history
    k = np.arange(len(y), dtype=np.float64)
    try:
        p0 = (max(y[0], 1e-6) * 0.95, -1e-3, max(y[0], 1e-6) * 0.05, 1e-2)
        lo = (0.0, -0.1, -5.0, -0.1)
        hi = (5.0, 0.0, 5.0, 0.1)
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', OptimizeWarning)
            popt, _ = curve_fit(_dexp, k, y, p0=p0, bounds=(lo, hi), maxfev=20000)
        future = _dexp(np.arange(len(y), len(y) + steps, dtype=np.float64), *popt)
        if (np.all(np.isfinite(future))
                and np.all(future >= 0.0)
                and float(np.max(future)) <= 1.5 * float(np.max(y))):
            return future
    except (RuntimeError, ValueError, TypeError):
        pass

    tail = min(len(k), 16)
    slope = np.polyfit(k[-tail:], y[-tail:], 1)[0]
    return y[-1] + slope * np.arange(1, steps + 1, dtype=np.float64)


def double_exp_direct(history, steps):
    """直接多步基线：在预测起点上拟合一次，然后整段外推。"""
    return double_exp_forecast(history, steps)


#: 基线注册表：名称 -> 规格
#:   kind='step'   : step_fn(windows) -> 下一步容量（可放进递归预测器）
#:   kind='direct' : direct_fn(history, steps) -> 整段预测（只拟合一次）
BASELINES = {
    '平推基线': {'kind': 'step', 'fn': persistence_step},
    '线性外推': {'kind': 'step', 'fn': linear_step},
    '双指数': {'kind': 'direct', 'fn': double_exp_direct},
}


def baseline_step(name):
    """取「逐步」基线的 step_fn。"""
    spec = BASELINES[name]
    if spec['kind'] != 'step':
        raise ValueError(f'{name} 是直接多步基线，不能作为 step_fn 使用')
    return spec['fn']


def baseline_direct(name):
    """取「直接多步」基线的 direct_fn。"""
    spec = BASELINES[name]
    if spec['kind'] != 'direct':
        raise ValueError(f'{name} 是逐步基线，不能作为 direct_fn 使用')
    return spec['fn']
