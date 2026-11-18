"""统一的「选超参 → 重训 → 滚动评估」协议。

目标：让**评估路径**和**部署路径**使用同一套流程，并且评估的是真正的未来预测。

  外层  留一电池 (LOBO)：目标电池全程不参与任何拟合 / 选择；
  内层  在训练电池里再做留一电池交叉验证，用「多步滚动预测误差」选超参
        （验证对象是一块没见过的电池，和最终使用场景一致）；
  定型  选定超参后，用全部训练电池的全部窗口重训一次，得到最终模型；
  评估  在多个预测起点（寿命的 40%~70%）做递归预测，报告 RMSE / RUL 误差。

这正是改进方案的 A2 / A3 / A4：旧流程把每块训练电池切成「前 80% 训练 +
后 20% 验证」，而寿命末段（膝点）恰好落在后 20%，于是模型从没见过寿命末段，
却被要求预测「什么时候越过失效阈值」。

本模块对「单特征容量序列」和「多特征 (T, F) 帧」都适用，容量恒为第 0 列。
"""

import numpy as np

from core.preprocess import build_instances, build_instances_mf
from core.result_semantics import (
    DEFAULT_DEBOUNCE_CYCLES,
    first_failure_index,
)


#: 滚动预测起点（占观测序列长度的比例）
DEFAULT_STARTS = (0.4, 0.5, 0.6, 0.7)


def capacity_of(data_dict, name):
    """从电池条目里取容量序列；兼容 DataFrame 与 ``{'capacity': ...}``。"""
    entry = data_dict[name]
    if hasattr(entry, 'columns'):
        if 'capacity' not in entry.columns:
            raise KeyError(f'电池 {name} 缺少 capacity 列')
        return np.asarray(entry['capacity'], dtype=np.float64).reshape(-1)
    return np.asarray(entry['capacity'], dtype=np.float64).reshape(-1)


def feature_frame(data_dict, name, columns, fill_values=None):
    """取某块电池的特征帧 ``(T, F)``，容量为第 0 列。

    ``columns`` 里不存在的列会被跳过；容量列始终保留。非容量列按因果前向填充
    与 ``fill_values`` 兜底，防止缺失的循环级特征触发预测异常。
    """
    from core.preprocess import fill_feature_frame

    entry = data_dict[name]
    if hasattr(entry, 'columns'):
        filled = fill_feature_frame(entry, cols=columns, fill_values=fill_values)
        return np.asarray(filled, dtype=np.float64)
    capacity = np.asarray(entry['capacity'], dtype=np.float64).reshape(-1)
    return capacity.reshape(-1, 1)


def _to_frame(values):
    """把 1-D 容量序列或 2-D 特征帧统一成 ``(T, F)``。"""
    array = np.asarray(values, dtype=np.float64)
    if array.ndim == 1:
        return array.reshape(-1, 1)
    if array.ndim == 2:
        return array
    raise ValueError('序列必须是容量序列或 (T, F) 特征帧')


def first_cross(values, threshold, debounce=DEFAULT_DEBOUNCE_CYCLES):
    """首次**持续**低于阈值的位置；从未低于则返回 ``None``（右删失）。

    委托给 :func:`core.result_semantics.first_failure_index`——全工程只有那一处
    失效判定实现。``debounce=1``（默认）是「首次下穿即失效」的旧语义；
    ``debounce=3`` 要求连续 3 个循环低于阈值（A12）。
    """
    return first_failure_index(values, threshold, debounce)


def _call_step(step_fn, window_rows):
    """调用 step_fn：单特征传 ``(1, W)``，多特征传 ``(1, W, F)``。"""
    if window_rows.shape[1] == 1:
        payload = window_rows[:, 0].reshape(1, -1).astype(np.float32)
    else:
        payload = window_rows.reshape(1, *window_rows.shape).astype(np.float32)
    values = np.asarray(step_fn(payload), dtype=np.float64).reshape(-1)
    if len(values) != 1 or not np.isfinite(values[0]):
        raise ValueError('递归预测器必须为单个窗口返回一个有限数值')
    return float(values[0])


def recursive_forecast(step_fn, window_values, steps):
    """递归预测。

    ``window_values`` 可以是 ``(W,)`` 容量窗口或 ``(W, F)`` 特征帧。多特征时
    **只有容量通道自回归**：其余特征保持为窗口内最后一个观测值（未来工况未知
    时的保守假设）。
    """
    if steps <= 0:
        return np.empty(0, dtype=np.float64)
    window = _to_frame(window_values)
    if len(window) == 0:
        raise ValueError('递归预测的初始窗口不能为空')
    width, features = window.shape
    held = window[-1, 1:].copy()          # 非容量通道的占位值
    history = window.copy()
    out = []
    for _ in range(steps):
        value = _call_step(step_fn, history[-width:])
        out.append(value)
        row = np.empty(features, dtype=np.float64)
        row[0] = value
        if features > 1:
            row[1:] = held
        history = np.vstack([history, row])
    return np.asarray(out, dtype=np.float64)


def rolling_origin_eval(sequence, window, step_fn, threshold,
                        starts=DEFAULT_STARTS, battery=None, debounce=None):
    """在多个预测起点上做真正的未来预测（递归），而不是「用真实历史的一步预测」。

    ``sequence`` 可以是容量序列 ``(T,)`` 或特征帧 ``(T, F)``。
    ``debounce`` 是失效判定所需的连续低于阈值循环数（A12，默认 1）。
    返回每个起点一行：rmse / mae / true_rul / pred_rul / rul_err /
    rul_rel_err / within_20pct / status
    （rul 以「预测起点之后的第几个循环」计，None 表示观测期内没有越过阈值）。
    """
    if debounce is None:
        debounce = DEFAULT_DEBOUNCE_CYCLES
    frame = _to_frame(sequence)
    rows = []
    for frac in starts:
        start = int(len(frame) * frac)
        if start < window or start >= len(frame) - 1:
            continue
        truth = frame[start:, 0]
        prediction = recursive_forecast(
            step_fn, frame[start - window:start], len(truth))
        true_eol = first_cross(truth, threshold, debounce)
        pred_eol = first_cross(prediction, threshold, debounce)
        row = {
            'start_frac': float(frac),
            'start': int(start),
            'battery': battery,
            'rmse': float(np.sqrt(np.mean((prediction - truth) ** 2))),
            'mae': float(np.mean(np.abs(prediction - truth))),
            'true_rul': true_eol,
            'pred_rul': pred_eol,
            'rul_err': None,
            'rul_rel_err': None,
            'within_20pct': None,
        }
        if true_eol is None:
            row['status'] = 'true_censored'       # 真实电池在观测期内没失效
        elif pred_eol is None:
            row['status'] = 'pred_censored'       # 模型预测「不会失效」
        else:
            row['status'] = 'ok'
            row['rul_err'] = int(pred_eol - true_eol)
            row['rul_rel_err'] = abs(pred_eol - true_eol) / max(true_eol, 1)
            row['within_20pct'] = bool(
                abs(pred_eol - true_eol) <= 0.2 * max(true_eol, 1))
        rows.append(row)
    return rows


def persistence_rows(sequence, window, threshold, starts=DEFAULT_STARTS,
                     battery=None):
    """同一组起点上「平推」基线的滚动评估行。"""
    return rolling_origin_eval(
        sequence, window, lambda w: w[:, -1], threshold, starts, battery)


def baseline_rmse_by_start(rows):
    """把基线行压成 ``{start_frac: rmse}``（技能分的分母）。"""
    return {row['start_frac']: row['rmse'] for row in rows}


def skill_vs_persistence(rows, baseline_by_start):
    """技能分 = 1 − RMSE模型 / RMSE平推；> 0 表示比平推好。"""
    values = []
    for row in rows:
        baseline = baseline_by_start.get(row['start_frac'])
        if baseline is None or baseline <= 1e-12:
            continue
        values.append(1.0 - row['rmse'] / baseline)
    if not values:
        return None
    return float(np.mean(values))


# ── 窗口构造（单特征 / 多特征共用） ────────────────────────────────

def _windows_for(data_dict, name, window, columns, fill_values):
    entry = data_dict[name]
    if columns is None or len(columns) <= 1:
        capacity = capacity_of(data_dict, name)
        return build_instances(capacity, window)
    if hasattr(entry, 'columns'):
        return build_instances_mf(
            entry, window, cols=columns, fill_values=fill_values)
    # 字典条目没有额外特征列，退化为单特征
    capacity = capacity_of(data_dict, name)
    return build_instances(capacity, window)


def make_windows(data_dict, names, window, columns=None, fill_values=None):
    """把若干块电池的窗口拼成 ``(X, y)``；多特征时 X 为 ``(N, W, F)``。

    返回的是**原始量纲**（Ah / 原始特征），归一化由 ``fit_fn`` / step_fn 内部负责。
    """
    xs, ys = [], []
    for name in names:
        try:
            x, y = _windows_for(data_dict, name, window, columns, fill_values)
        except (KeyError, ValueError):
            continue
        if len(x):
            xs.append(x)
            ys.append(y)
    if not xs:
        raise ValueError('没有可用的训练窗口')
    return np.vstack(xs), np.concatenate(ys)


def training_fill_values(data_dict, names, columns):
    """用**训练电池**统计量计算缺失填充值（不得使用目标电池）。"""
    if columns is None or len(columns) <= 1:
        return None
    from core.preprocess import feature_fill_values

    frames = []
    for name in names:
        entry = data_dict[name]
        if hasattr(entry, 'columns'):
            frames.append(entry)
    if not frames:
        return None
    import pandas as pd

    return feature_fill_values(pd.concat(frames, ignore_index=True), columns)


def batched_rollout_rmse(step_fn, frame, window, start_frac):
    """一次前向跑完整条递归轨迹（每步只调用一次 ``step_fn``，传单行窗口）。

    sklearn 的单次 ``predict`` 开销基本固定，所以「逐步调用」与「批量调用」在
    单位成本上差别不大，但这里避免了 Python 层的重复构造。
    """
    start = int(len(frame) * start_frac)
    if start < window or start >= len(frame) - 1:
        return None
    steps = len(frame) - start
    truth = frame[start:, 0]
    history = frame[start - window:start].copy()
    features = history.shape[1]
    errors = np.empty(steps, dtype=np.float64)
    for step in range(steps):
        value = _call_step(step_fn, history[-window:])
        errors[step] = (value - truth[step]) ** 2
        row = np.empty(features, dtype=np.float64)
        row[0] = value
        if features > 1:
            row[1:] = history[-1, 1:]
        history = np.vstack([history, row])
    return float(np.sqrt(np.mean(errors)))


def _rolling_rmse(step_fn, frame, window, start_frac):
    return batched_rollout_rmse(step_fn, frame, window, start_frac)


def is_recurrent(model):
    """判断是否为 PyTorch 循环模型（而不是 sklearn 树模型）。"""
    return hasattr(model, 'forward') and not hasattr(model, 'predict')


def model_step_for(model, rated, device='cpu', feature_scaler=None):
    """给「原始量纲进出」的模型造递归预测 step_fn。

    ``fit_fn``（见 :func:`core.model_factory.make_fit_fn`）内部已经把输入按
    ``/rated`` 归一化，多特征时再叠加 ``FeatureScaler``。因此 step_fn 必须还原
    **同一套映射**：先把原始窗口归一化，再把输出乘回 ``rated``。

    单特征与多特征共用这一处实现，避免两条路径量纲不一致（多特征路径曾经就是
    这样：训练除以 rated，推理却用 z-score，导致误差大到不可用）。
    """
    def step(windows):
        array = np.asarray(windows, dtype=np.float32)
        if array.ndim == 2:
            array = array[:, :, None]
        scaled = np.array(array, dtype=np.float32, copy=True)
        scaled[:, :, 0] = array[:, :, 0] / rated
        if scaled.shape[2] > 1 and feature_scaler is not None:
            scaled = feature_scaler.transform(scaled)

        if is_recurrent(model):
            import torch

            tensor = torch.from_numpy(scaled).to(device)
            if hasattr(model, 'eval'):
                model.eval()
            with torch.no_grad():
                output = model(tensor)
            raw = np.asarray(output.detach().cpu().numpy(),
                             dtype=np.float64).reshape(-1)
        else:
            raw = np.asarray(
                model.predict(scaled.reshape(len(scaled), -1)),
                dtype=np.float64).reshape(-1)
        return raw * rated

    return step


def select_hparams(data_dict, train_names, window, fit_fn, grid, rated,
                   start_frac=0.5, stop_flag=None, columns=None,
                   return_folds=False, device='cpu', feature_scaler=None):
    """内层留一电池交叉验证：用滚动预测 RMSE（单位 Ah）选超参。

    ``fit_fn(X, y, hp) -> model``，其中 X、y 是**原始量纲**（``fit_fn`` 内部
    负责归一化）。至少需要 2 块训练电池，否则退化为直接取 ``grid[0]``。

    ``return_folds=True`` 时额外返回选定超参下的折模型
    ``{held_out_name: model}``——这些模型**没见过**对应的留出电池，正好用来
    无偏地标定 α（A3），无需再拟合一遍。
    """
    if len(train_names) < 2:
        return (grid[0], float('nan'), {}) if return_folds else (
            grid[0], float('nan'))
    best_hp, best_score = None, np.inf
    best_folds = {}
    for hp in grid:
        if stop_flag is not None and stop_flag():
            break
        scores = []
        folds = {}
        for val_name in train_names:
            train_subset = [n for n in train_names if n != val_name]
            try:
                fill = training_fill_values(data_dict, train_subset, columns)
                x, y = make_windows(
                    data_dict, train_subset, window, columns, fill)
                model = fit_fn(x, y, hp)
            except (ValueError, KeyError):
                continue
            folds[val_name] = model
            step = model_step_for(
                model, rated, device=device, feature_scaler=feature_scaler)
            score = _rolling_rmse(
                step, feature_frame(data_dict, val_name, columns or ['capacity']),
                window, start_frac)
            if score is not None:
                scores.append(score)
        if not scores:
            continue
        score = float(np.mean(scores))
        if score < best_score:
            best_hp, best_score, best_folds = hp, score, folds
    if best_hp is None:
        return (grid[0], float('nan'), {}) if return_folds else (
            grid[0], float('nan'))
    if return_folds:
        return best_hp, best_score, best_folds
    return best_hp, best_score


def fit_final(data_dict, train_names, window, fit_fn, hp, rated, columns=None):
    """用全部训练电池的全部窗口定型（评估与部署共用这一个函数）。

    X、y 传**原始量纲**；归一化由 ``fit_fn`` 内部完成（见
    :func:`core.model_factory.make_fit_fn`）。这里**不能**再除一次 ``rated``，
    否则训练输入被归一化两遍，模型连训练集都拟合不上。
    """
    fill = training_fill_values(data_dict, train_names, columns)
    x, y = make_windows(data_dict, train_names, window, columns, fill)
    return fit_fn(x, y, hp)


def inner_fold_models(data_dict, train_names, window, fit_fn, hp, rated,
                      columns=None):
    """内层留一电池的折模型：``{held_out_name: model}``。

    这些模型**没见过**对应的留出电池，因此可以用来无偏地标定 α（A3）。
    X、y 传**原始量纲**，归一化由 ``fit_fn`` 内部负责。
    """
    models = {}
    for val_name in train_names:
        train_subset = [n for n in train_names if n != val_name]
        if not train_subset:
            continue
        try:
            fill = training_fill_values(data_dict, train_subset, columns)
            x, y = make_windows(data_dict, train_subset, window, columns, fill)
            models[val_name] = fit_fn(x, y, hp)
        except (ValueError, KeyError):
            continue
    return models


def choose_blend_by_rollout(step_raw, data_dict, val_names, window,
                            starts=(0.5, 0.6), grid=None, columns=None):
    """用多步滚动误差（而不是一步误差）选持久性混合系数 α。

    ``step_raw`` 必须来自「没见过 val_names 里电池」的模型（例如内层交叉验证
    得到的模型），否则 α 会偏向 1。若返回的 α < 0.05，应在界面上提示
    「模型没有超越持久性基线」。

    实现上把**所有候选 α 的递归轨迹并行推进**：每一步只调用一次 ``step_raw``
    处理一个 ``(len(grid), W)`` 批次。sklearn 的单次 ``predict`` 开销基本固定，
    因此这比「逐 α 逐个窗口调用」快一个数量级。
    """
    grid = (np.linspace(0.0, 1.0, 21) if grid is None
            else np.asarray(grid, dtype=np.float64))
    if len(grid) == 0:
        return 1.0, float('nan')

    errors = [[] for _ in grid]
    for name in val_names:
        frame = feature_frame(data_dict, name, columns or ['capacity'])
        for frac in starts:
            start = int(len(frame) * frac)
            if start < window or start >= len(frame) - 1:
                continue
            steps = len(frame) - start
            truth = frame[start:, 0]
            window_rows = frame[start - window:start]
            _rollout_blend_errors(
                step_raw, window_rows, truth, steps, grid, errors)

    scores = [float(np.mean(values)) if values else np.inf for values in errors]
    best = int(np.argmin(scores))
    best_score = scores[best]
    return float(grid[best]), (
        float(np.sqrt(best_score)) if np.isfinite(best_score) else float('nan'))


def _rollout_blend_errors(step_raw, window_rows, truth, steps, grid, errors):
    """并行推进所有 α 的递归轨迹，把每步平方误差累加到 ``errors``。"""
    n_alpha = len(grid)
    features = window_rows.shape[1]
    width = len(window_rows)
    # 每个 α 一份历史副本
    histories = [window_rows.copy() for _ in range(n_alpha)]
    for step in range(steps):
        # 每次把「全部 α 的当前窗口」拼成一个批次，一次 predict 处理完
        batch = np.stack(
            [history[-width:] for history in histories]).astype(np.float32)
        raw = np.asarray(step_raw(batch), dtype=np.float64).reshape(-1)
        if len(raw) != n_alpha:
            raise ValueError('step_raw 必须为每个窗口返回一个数值')
        target = float(truth[step])
        for index, alpha in enumerate(grid):
            last = float(histories[index][-1, 0])
            value = last + float(alpha) * (raw[index] - last)
            errors[index].append((value - target) ** 2)
            row = np.empty(features, dtype=np.float64)
            row[0] = value
            if features > 1:
                row[1:] = histories[index][-1, 1:]
            histories[index] = np.vstack([histories[index], row])


def summarize_rolling_rows(rows, baseline_by_start=None):
    """把多折 / 多起点的滚动评估行汇总成表格与跨电池统计。

    返回 ``{'per_start': {...}, 'overall': {...}}``；``n`` 是**电池数**，
    这才是泛化不确定性的来源（不是随机种子）。
    """
    per_start = {}
    for frac in sorted({row['start_frac'] for row in rows}):
        subset = [row for row in rows if row['start_frac'] == frac]
        detected = [row for row in subset if row['status'] == 'ok']
        needs_detection = [row for row in subset
                           if row['status'] in ('ok', 'pred_censored')]
        entry = {
            'n': len(subset),
            'rmse': float(np.mean([row['rmse'] for row in subset])),
            'mae': float(np.mean([row['mae'] for row in subset])),
            'detected': len(detected),
            'needs_detection': len(needs_detection),
            'mean_abs_rul_err': (
                float(np.mean([abs(row['rul_err']) for row in detected]))
                if detected else None),
        }
        if baseline_by_start:
            entry['skill'] = skill_vs_persistence(subset, baseline_by_start)
        per_start[frac] = entry

    all_detected = [row for row in rows if row['status'] == 'ok']
    batteries = {row.get('battery') for row in rows if row.get('battery')}
    overall = {
        'n': len(batteries),
        'rmse': float(np.mean([row['rmse'] for row in rows])) if rows else None,
        'mae': float(np.mean([row['mae'] for row in rows])) if rows else None,
        'detected': len(all_detected),
        'needs_detection': len(
            [row for row in rows if row['status'] in ('ok', 'pred_censored')]),
        'mean_abs_rul_err': (
            float(np.mean([abs(row['rul_err']) for row in all_detected]))
            if all_detected else None),
    }
    if baseline_by_start:
        overall['skill'] = skill_vs_persistence(rows, baseline_by_start)
    return {'per_start': per_start, 'overall': overall}
