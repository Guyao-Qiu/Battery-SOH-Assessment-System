"""留一电池评估：统一的「选超参 → 重训 → 滚动起点评估」协议。

改进方案 A2 / A3 / A4 的落地：

- **A2**：评估用的模型与部署用的模型走同一个 ``fit_final``——用**全部训练电池的
  全部窗口**训练。旧流程把每块训练电池切成「前 80% 训练 + 后 20% 验证」，
  而寿命末段（膝点）恰好落在后 20%，模型从没见过寿命末段却被要求预测失效点。
- **A3**：持久性混合系数 α 用**多步滚动误差**标定，且只用「没见过该验证电池」的
  内层折模型，避免一步误差标定、递归多步使用造成的坍缩。
- **A4**：头条指标改为**滚动预测起点**（40%–70%）上的递归预测误差，一步指标
  降级为诊断信息；同时并排给出「平推 / 线性外推 / 双指数」三条基线。
"""

import numpy as np
import time

from core.preprocess import (
    CapacityScaler,
    FeatureScaler,
    build_instances,
    build_instances_mf,
    feature_fill_values,
    generate_one_step_predictions,
    generate_recursive_predictions,
)
from core.prediction import predict_capacity_batch
from core.evaluate import calc_all_metrics, confidence_interval
from core.cancellation import check_cancelled
from core.progress import make_progress_event
from core.model_factory import (
    hparam_grid,
    make_fit_fn,
    make_step_fn,
)
from core.protocol import model_step_for
from core import protocol as protocol_module
from core.protocol import (
    DEFAULT_STARTS,
    choose_blend_by_rollout,
    fit_final,
    inner_fold_models,
    baseline_rmse_by_start,
    rolling_origin_eval,
    select_hparams,
    skill_vs_persistence,
    summarize_rolling_rows,
)
from core.baselines import BASELINES
#: 模块级 ``Net``：保持既有测试/扩展点可用（可被 mock 替换）
from models.rnn_model import Net  # noqa: F401


#: 头条指标使用的预测起点（寿命的 50%）
PRIMARY_START = 0.5


def _feature_columns(config):
    columns = getattr(config, 'feature_columns', None)
    if columns is None:
        return ('capacity',)
    return tuple(columns)


def _uses_multifeature(config):
    return len(_feature_columns(config)) > 1


def _frames_for(config, battery_dict, name):
    """取某块电池的输入帧（单特征时为容量序列）。"""
    entry = battery_dict[name]
    columns = _feature_columns(config)
    if not _uses_multifeature(config) or not hasattr(entry, 'columns'):
        return protocol_module.capacity_of(battery_dict, name)
    available = [c for c in columns if c in entry.columns]
    if 'capacity' not in available:
        available = ['capacity'] + available
    return entry.loc[:, available]


def _build_windows(config, values, window):
    """把帧 / 序列切成 (X, y)。"""
    columns = _feature_columns(config)
    if _uses_multifeature(config) and getattr(values, 'columns', None) is not None:
        return build_instances_mf(values, window, cols=list(columns))
    return build_instances(np.asarray(values, dtype=np.float32).reshape(-1), window)


def evaluate_prediction_protocols(sequence, window_size, predict_batch,
                                  rated_capacity, threshold_ratio):
    """评估「用真实历史的一步预测」与「从初始窗口起的完全递归预测」。

    这两个协议**分开报告**：一步预测每一步都用真实历史，误差不累积，天然接近
    「平推」的好成绩，区分不出模型好坏；递归预测才是真实使用场景。

    头条指标请看 :func:`rolling_origin_eval` 的滚动起点结果。
    """
    one_truth, one_prediction = generate_one_step_predictions(
        sequence, window_size, predict_batch)
    recursive_truth, recursive_prediction = generate_recursive_predictions(
        sequence, window_size, predict_batch)
    one_metrics = calc_all_metrics(
        one_truth, one_prediction, rated_capacity, threshold_ratio)
    recursive_metrics = calc_all_metrics(
        recursive_truth, recursive_prediction, rated_capacity, threshold_ratio)
    return {
        'one_step': {
            'truth': one_truth,
            'prediction': one_prediction,
            'metrics': one_metrics,
        },
        'recursive': {
            'truth': recursive_truth,
            'prediction': recursive_prediction,
            'metrics': recursive_metrics,
        },
        'rul_re': recursive_metrics['re'],
    }


def _baseline_one_step_metrics(one_step, target_frames, window, multifeature,
                               rated_capacity, threshold_ratio):
    """「平推」基线的一步预测指标（供结果表并排展示，A3/A9）。

    平推的一步预测就是窗口末值，因此与 ``one_step['truth']`` 逐位对齐。
    """
    truth = np.asarray(one_step.get('truth', []), dtype=np.float64).reshape(-1)
    if len(truth) == 0:
        return {}
    frames = np.asarray(target_frames, dtype=np.float64)
    if multifeature:
        frames = frames[:, 0]
    windows = frames[:-1] if len(frames) == len(truth) + 1 else frames[:len(truth)]
    persistence = windows if len(windows) == len(truth) else np.full(
        len(truth), frames[0] if len(frames) else 0.0)
    try:
        return calc_all_metrics(
            truth, persistence, rated_capacity, threshold_ratio)
    except ValueError:
        return {}


def _capacity_only_step(step_fn):
    """把「逐步」基线包装成只吃容量通道的 step_fn。

    基线（平推 / 线性外推）只关心容量序列，但多特征帧的窗口是 ``(1, W, F)``；
    这里统一截出容量列，让基线在多特征配置下也能评估。
    """
    def wrapped(windows):
        array = np.asarray(windows)
        if array.ndim == 3:
            array = array[:, :, 0]
        return step_fn(array)

    return wrapped


def _baseline_table(config, frames, window, threshold, rated_capacity,
                    starts=DEFAULT_STARTS, name='', debounce=1):
    """在同一组滚动起点上评估三条经验基线（平推 / 线性外推 / 双指数）。"""
    table = {}
    for baseline_name, spec in BASELINES.items():
        try:
            if spec['kind'] == 'step':
                rows = rolling_origin_eval(
                    frames, window, _capacity_only_step(spec['fn']), threshold,
                    starts, battery=name, debounce=debounce)
            else:
                rows = _direct_baseline_rows(
                    spec['fn'], frames, window, threshold, starts, name,
                    debounce)
        except (ValueError, FloatingPointError):
            continue
        if rows:
            table[baseline_name] = {
                'kind': spec['kind'],
                'rows': rows,
                'rmse': float(np.mean([row['rmse'] for row in rows])),
                'mean_abs_rul_err': _mean_rul_error(rows),
                'detected': len([row for row in rows if row['status'] == 'ok']),
            }
    return table


def _direct_baseline_rows(direct_fn, frames, window, threshold, starts, name,
                          debounce=1):
    """直接多步基线：在起点拟合一次，整段外推（不逐步重拟合）。"""
    array = np.asarray(frames, dtype=np.float64)
    if array.ndim == 1:
        array = array.reshape(-1, 1)
    rows = []
    for frac in starts:
        start = int(len(array) * frac)
        if start < window or start >= len(array) - 1:
            continue
        truth = array[start:, 0]
        prediction = np.asarray(
            direct_fn(array[start - window:start, 0], len(truth)),
            dtype=np.float64).reshape(-1)
        rows.append(_score_row(
            frac, start, name, truth, prediction, threshold, debounce))
    return rows


def _score_row(frac, start, name, truth, prediction, threshold, debounce=1):
    """把一段真实 / 预测序列打分（与 ``rolling_origin_eval`` 同一口径）。"""
    true_eol = protocol_module.first_cross(truth, threshold, debounce)
    pred_eol = protocol_module.first_cross(prediction, threshold, debounce)
    row = {
        'start_frac': float(frac),
        'start': int(start),
        'battery': name,
        'rmse': float(np.sqrt(np.mean((prediction - truth) ** 2))),
        'mae': float(np.mean(np.abs(prediction - truth))),
        'true_rul': true_eol,
        'pred_rul': pred_eol,
        'rul_err': None,
        'rul_rel_err': None,
        'within_20pct': None,
    }
    if true_eol is None:
        row['status'] = 'true_censored'
    elif pred_eol is None:
        row['status'] = 'pred_censored'
    else:
        row['status'] = 'ok'
        row['rul_err'] = int(pred_eol - true_eol)
        row['rul_rel_err'] = abs(pred_eol - true_eol) / max(true_eol, 1)
        row['within_20pct'] = bool(
            abs(pred_eol - true_eol) <= 0.2 * max(true_eol, 1))
    return row


def _mean_rul_error(rows):
    detected = [abs(row['rul_err']) for row in rows if row['status'] == 'ok']
    return float(np.mean(detected)) if detected else None


def _train_one_battery(config, battery_dict, name, stop_flag=None,
                       log_callback=None, seed=None, progress_callback=None):
    """训练单个电池（留一法），返回 ``(pred_list, metrics_dict, detail_dict)``。

    评估与部署共用 :func:`core.protocol.fit_final`：用全部训练电池的全部窗口
    定型，因此模型**见过寿命末段**，也才可能预测出失效。
    """
    check_cancelled(stop_flag)
    window = int(config.window_size)
    mode = config.mode
    device = getattr(config, 'device', 'cpu')
    rated_capacity = float(config.rated_capacity)
    threshold_ratio = float(config.threshold_ratio)
    threshold = rated_capacity * threshold_ratio
    columns = _feature_columns(config)
    multifeature = _uses_multifeature(config)

    if seed is not None:
        from utils.config import setup_seed
        setup_seed(seed)
    fit_seed = int(seed if seed is not None else getattr(config, 'seed', 2))

    train_names = [
        item for item in battery_dict
        if item != name and len(battery_dict[item].get('capacity', ())) > window + 1
    ]
    if not train_names:
        if log_callback:
            log_callback(f'跳过 {name}，原因：没有可用的训练电池')
        return None, None, None

    target_frames = _frames_for(config, battery_dict, name)
    if len(target_frames) <= window + 1:
        if log_callback:
            log_callback(f'跳过 {name}，原因：循环数不足（需>{window}）')
        return None, None, None

    # ── scaler 只用训练电池拟合（目标电池不得参与） ──
    # 必须在构造 fit_fn 之前算好：多特征时 fit_fn 与 step_fn 共用同一个
    # FeatureScaler，否则训练与推理的量纲会不一致。
    scaler, feature_scaler, fill_values = _fit_scalers(
        config, battery_dict, train_names, window, columns, multifeature,
        rated_capacity)

    # ── 内层留一电池交叉验证：选超参（验证对象是一块没见过的电池） ──
    fit_config = _config_with_seed(config, fit_seed)
    fit_fn = make_fit_fn(
        fit_config, stop_flag=stop_flag, log_callback=log_callback, name=name,
        net_class=Net, progress_callback=progress_callback,
        feature_scaler=feature_scaler)
    grid = hparam_grid(config, mode)
    use_cv = bool(getattr(config, 'inner_cv', True)) and len(train_names) >= 2
    if use_cv:
        hp, cv_score, fold_models = select_hparams(
            battery_dict, train_names, window, fit_fn, grid, rated_capacity,
            start_frac=PRIMARY_START, stop_flag=stop_flag,
            columns=columns if multifeature else None, return_folds=True,
            device=device, feature_scaler=feature_scaler)
        if log_callback:
            score_text = (
                'N/A' if cv_score is None or not np.isfinite(cv_score)
                else f'{cv_score:.4f} Ah')
            log_callback(
                f'[{name}] 内层留一电池交叉验证（{len(train_names)} 折）：'
                f'选定超参 {hp}，滚动 RMSE@50%={score_text}')
    else:
        hp = grid[0]
        cv_score = float('nan')
        # None（而不是空 dict）=「尚未计算」，让 _calibrate_blend 自己去建内层折
        fold_models = None
        if log_callback:
            log_callback(f'[{name}] 快速模式：跳过内层交叉验证，使用 {hp}')

    check_cancelled(stop_flag)

    # ── 定型：用全部训练电池的全部窗口重训（评估与部署共用同一函数） ──
    model = fit_final(
        battery_dict, train_names, window, fit_fn, hp, rated_capacity,
        columns=columns if multifeature else None)
    check_cancelled(stop_flag)

    metadata = _model_metadata(
        config, window, rated_capacity, scaler, feature_scaler, columns,
        multifeature, hp)
    step_fn = make_step_fn(model, metadata, device=device)

    # ── A3：α 用多步滚动误差标定，且只用「没见过验证电池」的内层折模型 ──
    blend, blend_rmse = _calibrate_blend(
        config, battery_dict, train_names, window, fit_fn, hp, rated_capacity,
        columns, multifeature, scaler=scaler, feature_scaler=feature_scaler,
        fold_models=fold_models, stop_flag=stop_flag, log_callback=log_callback,
        name=name)
    metadata['persistence_blend'] = blend

    # ── A4：头条指标 = 滚动起点上的递归预测（A12：失效判定可去抖） ──
    starts = tuple(getattr(config, 'rolling_starts', DEFAULT_STARTS))
    debounce = int(getattr(config, 'eol_debounce', 1) or 1)
    rows = rolling_origin_eval(
        target_frames, window, step_fn, threshold, starts, battery=name,
        debounce=debounce)
    baseline_table = _baseline_table(
        config, target_frames, window, threshold, rated_capacity, starts, name,
        debounce)
    persistence = baseline_table.get('平推基线', {})
    baseline_by_start = (
        baseline_rmse_by_start(persistence['rows'])
        if persistence.get('rows') else {})
    rolling_summary = summarize_rolling_rows(rows, baseline_by_start)
    skill = skill_vs_persistence(rows, baseline_by_start)

    # ── 诊断信息：一步预测与从初始窗口起的完全递归预测 ──
    protocols = evaluate_prediction_protocols(
        np.asarray(target_frames)[:, 0] if multifeature else target_frames,
        window,
        lambda windows: predict_capacity_batch(
            model, metadata, windows, device=device),
        rated_capacity, threshold_ratio)
    one_step = protocols['one_step']
    recursive = protocols['recursive']

    primary = _primary_row(rows, PRIMARY_START) or (rows[0] if rows else None)
    metrics = _metrics_from_row(primary)
    metrics['r2'] = one_step['metrics'].get('r2')
    metrics['pearson'] = one_step['metrics'].get('pearson')
    metrics['re'] = protocols['rul_re']
    metrics['re_status'] = recursive['metrics'].get('re_status')

    forecast = _forecast_for_plot(step_fn, target_frames, window, primary)
    baseline_metrics = _baseline_one_step_metrics(
        one_step, target_frames, window, multifeature, rated_capacity,
        threshold_ratio)

    train_data = list(np.asarray(target_frames)[:window, 0]) if multifeature \
        else list(np.asarray(target_frames)[:window])
    pred_list = train_data + list(one_step['prediction'])

    detail = {
        'battery': name,
        'cycles': int(len(target_frames)),
        'model': mode,
        'training_batteries': tuple(train_names),
        'protocol': 'strict_zero_shot',
        'rul_protocol': 'rolling_origin',
        'selected_hparams': dict(hp),
        'inner_cv_rmse': (None if not np.isfinite(cv_score) else float(cv_score)),
        'scaler': scaler.to_dict(),
        'feature_columns': list(columns),
        'feature_scaler': (
            feature_scaler.to_dict() if feature_scaler is not None else None),
        'one_step_prediction': one_step['prediction'].tolist(),
        'recursive_prediction': recursive['prediction'].tolist(),
        'one_step_metrics': one_step['metrics'],
        'recursive_metrics': recursive['metrics'],
        'persistence_blend': float(blend),
        'persistence_blend_rmse': (
            None if blend_rmse is None or not np.isfinite(blend_rmse)
            else float(blend_rmse)),
        'persistence_baseline_metrics': baseline_metrics,
        'rmse_skill_vs_persistence': skill,
        'rolling': rolling_summary,
        'rolling_rows': rows,
        'baselines': {
            key: {k: v for k, v in value.items() if k != 'rows'}
            for key, value in baseline_table.items()
        },
        'baseline_rows': {
            key: value['rows'] for key, value in baseline_table.items()
        },
        'primary_start_frac': PRIMARY_START,
        'forecast_start': (primary['start'] if primary else None),
        'forecast': forecast,
        'threshold': float(threshold),
    }
    return pred_list, metrics, detail


def _config_with_seed(config, seed):
    """返回一个 seed 被覆盖的配置副本（不改动调用方对象）。"""
    try:
        from dataclasses import replace
        return replace(config, seed=seed)
    except (TypeError, ValueError):
        return config


def _primary_row(rows, start_frac):
    for row in rows:
        if abs(row['start_frac'] - start_frac) < 1e-9:
            return row
    return None


def _metrics_from_row(row):
    """把滚动起点的一行转成指标字典。"""
    if row is None:
        return {'rmse': None, 'mae': None, 'r2': None, 'pearson': None,
                're': None, 're_status': 'unavailable'}
    return {
        'rmse': float(row['rmse']),
        'mae': float(row['mae']),
        'r2': None,
        'pearson': None,
        're': (
            abs(row['rul_err']) / max(row['true_rul'], 1)
            if row['status'] == 'ok' and row['true_rul'] else None),
        're_status': {
            'ok': 'observed',
            'true_censored': 'observed_censored',
            'pred_censored': 'prediction_censored',
        }.get(row['status'], 'unavailable'),
    }


def _fit_scalers(config, battery_dict, train_names, window, columns,
                 multifeature, rated_capacity):
    """scaler 只用训练电池拟合（目标电池不得参与）。"""
    import pandas as pd

    capacity_parts = []
    frames = []
    for item in train_names:
        entry = battery_dict[item]
        if multifeature and hasattr(entry, 'columns'):
            frame = entry
            available = [c for c in columns if c in frame.columns]
            if 'capacity' not in available:
                available = ['capacity'] + available
            frames.append(frame.loc[:, available])
        capacity = np.asarray(entry['capacity'], dtype=np.float32).reshape(-1)
        capacity_parts.append(capacity)

    scaler = CapacityScaler(
        method=config.norm_method,
        rated_capacity=rated_capacity,
    ).fit(np.concatenate(capacity_parts) if capacity_parts else np.array([1.0]))

    feature_scaler = None
    fill_values = None
    if multifeature and frames:
        combined = pd.concat(frames, ignore_index=True)
        fill_values = feature_fill_values(combined, list(columns))
        filled = combined.ffill().fillna(fill_values).fillna(0.0)
        feature_scaler = FeatureScaler().fit(filled.to_numpy(dtype=np.float32))
    return scaler, feature_scaler, fill_values


def _model_metadata(config, window, rated_capacity, scaler, feature_scaler,
                    columns, multifeature, hp):
    """构造用于**评估内部**递归预测的元数据（与最终模型保存的 schema 一致）。"""
    schema = {
        'features': list(columns),
        'feature': 'capacity' if not multifeature else 'multifeature',
        'dtype': 'float32',
        'shape': (['batch', 'window_size', 'features'] if multifeature
                  else ['batch', 'window_size']),
        'feature_scaler': (
            feature_scaler.to_dict() if feature_scaler is not None else None),
        'selected_hparams': dict(hp),
        'multifeature_recursive_policy': (
            '非容量通道在递归预测时保持窗口末值（未来工况未知）'
            if multifeature else None),
    }
    metadata = {
        'mode': config.mode,
        'window_size': int(window),
        'rated_capacity': float(rated_capacity),
        'threshold_ratio': float(config.threshold_ratio),
        'scaler': scaler.to_dict(),
        'feature_schema': schema,
        'persistence_blend': 1.0,
    }
    if config.mode in ('RNN', 'GRU', 'LSTM'):
        metadata['hidden_dim'] = int(getattr(config, 'hidden_dim', 64))
        metadata['input_size'] = int(len(columns))
    return metadata


def _calibrate_blend(config, battery_dict, train_names, window, fit_fn, hp,
                     rated_capacity, columns, multifeature, scaler=None,
                     feature_scaler=None, fold_models=None, stop_flag=None,
                     log_callback=None, name=''):
    """A3：用多步滚动误差 + 内层折模型标定持久性混合系数 α。

    ``fold_models`` 由 :func:`core.protocol.select_hparams` 的
    ``return_folds=True`` 提供（每个折模型没见过对应留出电池），因此 α 不会被
    「模型见过验证电池」这件事偏向 1。
    """
    if fold_models is None:
        try:
            fold_models = inner_fold_models(
                battery_dict, train_names, window, fit_fn, hp, rated_capacity,
                columns=columns if multifeature else None)
        except (ValueError, KeyError):
            fold_models = {}

    if not fold_models:
        if log_callback:
            log_callback(f'[{name}] 无法建立内层折模型，α 取 1.0（不做收缩）')
        return 1.0, None

    if scaler is None:
        scaler = _fit_scalers(
            config, battery_dict, train_names, window, columns, multifeature,
            rated_capacity)[0]
    device = getattr(config, 'device', 'cpu')

    # 每个验证电池用自己的内层折模型（该模型没见过它）。
    # 折模型是用「原始量纲 + 内部归一化」训练的，所以 step 必须走同一套
    # 映射（model_step_for），与 select_hparams 内部保持一致。
    blend_by_name = {}
    for val_name, fold_model in fold_models.items():
        step_raw = model_step_for(
            fold_model, rated_capacity, device=device,
            feature_scaler=feature_scaler)
        alpha, _ = choose_blend_by_rollout(
            step_raw, battery_dict, [val_name], window,
            starts=(0.5, 0.6), columns=columns if multifeature else None)
        blend_by_name[val_name] = alpha

    blend = float(np.mean(list(blend_by_name.values()))) if blend_by_name else 1.0
    if log_callback:
        detail = '，'.join(
            f'{key}={value:.2f}' for key, value in blend_by_name.items())
        log_callback(
            f'[{name}] 防过拟合校准系数 α={blend:.3f}'
            f'（多步滚动标定；{detail}；0=平推，1=原模型）')
        if blend < 0.05:
            log_callback(
                f'[{name}] ⚠ 模型未超越持久性基线（α≈0）：'
                '递归预测退化为平推，请以滚动起点指标为准。')
    return blend, None


def _forecast_for_plot(step_fn, frames, window, primary):
    """为图表准备递归预测序列（从主预测起点起，直到观测末端）。"""
    if primary is None:
        return []
    start = primary['start']
    steps = len(frames) - start
    if steps <= 0:
        return []
    window_values = frames[start - window:start]
    try:
        forecast = protocol_module.recursive_forecast(
            step_fn, window_values, steps)
    except (ValueError, FloatingPointError):
        return []
    return forecast.tolist()


def train(config, battery_dict, battery_list, stop_flag=None, log_callback=None,
          progress_callback=None):
    """留一电池评估主循环；主结果是所有有效种子的**均值**（不挑最好种子）。"""
    feature_size = config.window_size
    mode = config.mode
    base_seed = config.seed
    n_seeds = max(1, getattr(config, 'n_seeds', 1))

    results = {}
    progress_started_at = time.monotonic()
    seeds = [base_seed + i for i in range(n_seeds)]

    if n_seeds > 1 and log_callback:
        log_callback(
            f'多种子评估：共 {n_seeds} 个种子 {seeds}，'
            f'计算 95% 置信区间（仅同一留一折内的种子波动）')

    for i in range(len(battery_list)):
        check_cancelled(stop_flag)
        name = battery_list[i]
        if name not in battery_dict:
            continue
        capacity = battery_dict[name].get('capacity', ())
        if len(capacity) <= feature_size + 2:
            if log_callback:
                log_callback(f'跳过 {name}：循环数不足（需>{feature_size}）')
            continue

        if progress_callback:
            progress_callback(make_progress_event(
                'battery', started_at=progress_started_at, battery=name,
                current=i + 1, total=len(battery_list)))

        all_metrics = []
        all_predictions = []
        run_details = []

        for s_idx, sd in enumerate(seeds):
            check_cancelled(stop_flag)
            if progress_callback:
                progress_callback(make_progress_event(
                    'seed', started_at=progress_started_at, battery=name,
                    seed=sd, current=s_idx + 1, total=len(seeds)))
            if n_seeds > 1 and log_callback:
                log_callback(f'[{name}] 种子 {s_idx + 1}/{n_seeds} (seed={sd})')

            pred_list, metrics, run_detail = _train_one_battery(
                config, battery_dict, name, stop_flag=stop_flag,
                log_callback=log_callback, seed=sd,
                progress_callback=progress_callback)
            if metrics is None:
                continue
            all_metrics.append(metrics)
            all_predictions.append(np.asarray(pred_list, dtype=np.float64))
            run_details.append(run_detail or {})

        if not all_metrics or not all_predictions:
            continue

        ci_info = {}
        for key in ('rmse', 'mae', 'r2', 'pearson', 're'):
            values = [
                float(item[key]) for item in all_metrics
                if item.get(key) is not None and np.isfinite(item[key])
            ]
            if not values:
                continue
            mean, lo, hi, std = confidence_interval(values, confidence=0.95)
            ci_info[key] = {
                'mean': mean, 'lower': lo, 'upper': hi, 'std': std,
                'values': values,
            }

        mean_metrics = {key: ci_info[key]['mean'] for key in ci_info}
        mean_prediction = np.mean(np.vstack(all_predictions), axis=0)
        detail = _aggregate_detail(
            name, mode, battery_dict, ci_info, mean_metrics, run_details)

        selected_metric = getattr(config, 'metric', 'rmse')
        selected_score = mean_metrics.get(
            selected_metric, mean_metrics.get('rmse'))
        results[name] = {
            'score': (float(selected_score)
                      if selected_score is not None else None),
            'prediction': mean_prediction.tolist(),
            'detail': detail,
        }

        if n_seeds > 1 and log_callback and 'rmse' in ci_info:
            log_callback(
                f'[{name}] 多种子汇总：'
                f'RMSE={ci_info["rmse"]["mean"]:.4f}±{ci_info["rmse"]["std"]:.4f} '
                f'95%CI=[{ci_info["rmse"]["lower"]:.4f}, '
                f'{ci_info["rmse"]["upper"]:.4f}]')
    return results


def _aggregate_detail(name, mode, battery_dict, ci_info, mean_metrics,
                      run_details):
    """把每个种子的 detail 汇总成电池级 detail。"""
    def mean_protocol_metrics(field):
        protocol_metrics = [item[field] for item in run_details if field in item]
        if not protocol_metrics:
            return {}
        result = {}
        for key in ('rmse', 'mae', 'r2', 'pearson', 're'):
            values = [
                float(item[key]) for item in protocol_metrics
                if item.get(key) is not None and np.isfinite(item[key])
            ]
            if values:
                result[key] = float(np.mean(values))
        statuses = [item.get('re_status') for item in protocol_metrics
                    if item.get('re_status')]
        if statuses:
            result['re_status'] = (
                statuses[0] if len(set(statuses)) == 1 else 'mixed')
        return result

    def mean_protocol_prediction(field):
        values = [item[field] for item in run_details if field in item]
        if not values:
            return []
        return np.mean(
            np.vstack([np.asarray(value, dtype=np.float64)
                       for value in values]), axis=0).tolist()

    def mean_scalar(field):
        values = [
            float(item[field]) for item in run_details
            if item.get(field) is not None
            and np.isfinite(item[field])
        ]
        return float(np.mean(values)) if values else None

    def mean_dict_of_floats(field):
        collected = {}
        for item in run_details:
            for key, value in (item.get(field) or {}).items():
                if isinstance(value, (int, float)) and np.isfinite(value):
                    collected.setdefault(key, []).append(float(value))
        return {key: float(np.mean(values)) for key, values in collected.items()}

    # 滚动起点汇总：把各种子的行按起点取均值
    rows_by_start = {}
    for item in run_details:
        for row in item.get('rolling_rows', []) or []:
            rows_by_start.setdefault(row['start_frac'], []).append(row)

    aggregated_rows = []
    for frac, rows in sorted(rows_by_start.items()):
        merged = {
            'start_frac': frac,
            'start': rows[0]['start'],
            'battery': name,
            'rmse': float(np.mean([r['rmse'] for r in rows])),
            'mae': float(np.mean([r['mae'] for r in rows])),
            'true_rul': rows[0]['true_rul'],
            'pred_rul': (
                float(np.mean([r['pred_rul'] for r in rows
                               if r['pred_rul'] is not None]))
                if any(r['pred_rul'] is not None for r in rows) else None),
            'status': rows[0]['status'],
            'rul_err': (
                float(np.mean([r['rul_err'] for r in rows
                               if r['rul_err'] is not None]))
                if any(r['rul_err'] is not None for r in rows) else None),
        }
        aggregated_rows.append(merged)

    baseline_by_start = {}
    for item in run_details:
        for key, value in (item.get('baselines') or {}).items():
            baseline_by_start.setdefault(key, []).append(value.get('rmse'))

    baselines = {}
    for key, values in baseline_by_start.items():
        finite = [v for v in values if v is not None and np.isfinite(v)]
        if finite:
            baselines[key] = {'rmse': float(np.mean(finite))}

    blends = [
        float(item['persistence_blend']) for item in run_details
        if item.get('persistence_blend') is not None
    ]
    first = run_details[0] if run_details else {}

    detail = {
        'battery': name,
        'cycles': int(len(battery_dict[name]['capacity'])),
        'model': mode,
        'rmse': mean_metrics.get('rmse'),
        'mae': mean_metrics.get('mae'),
        'r2': mean_metrics.get('r2'),
        'pearson': mean_metrics.get('pearson'),
        're': mean_metrics.get('re'),
        're_status': mean_protocol_metrics('recursive_metrics').get(
            're_status', 'unavailable'),
        'n_seeds': len(run_details),
        'ci': ci_info,
        'ci_statistical_object': '同一留一折内的随机种子波动',
        'seed_policy': 'all_seed_mean',
        'protocol': 'strict_zero_shot',
        'rul_protocol': 'rolling_origin',
        'one_step_prediction': mean_protocol_prediction('one_step_prediction'),
        'recursive_prediction': mean_protocol_prediction('recursive_prediction'),
        'one_step_metrics': mean_protocol_metrics('one_step_metrics'),
        'recursive_metrics': mean_protocol_metrics('recursive_metrics'),
        'persistence_blend': float(np.mean(blends)) if blends else 1.0,
        'rmse_skill_vs_persistence': mean_scalar('rmse_skill_vs_persistence'),
        'inner_cv_rmse': mean_scalar('inner_cv_rmse'),
        'selected_hparams': first.get('selected_hparams', {}),
        'feature_columns': first.get('feature_columns', ['capacity']),
        'rolling_rows': aggregated_rows,
        'rolling': summarize_rolling_rows(aggregated_rows),
        'baselines': baselines,
        'primary_start_frac': first.get('primary_start_frac', PRIMARY_START),
        'forecast_start': first.get('forecast_start'),
        'forecast': mean_protocol_prediction('forecast'),
        'threshold': first.get('threshold'),
        'training_batteries': first.get('training_batteries', ()),
        'run_details': run_details,
    }
    # 平推基线的一步指标（供结果表并排展示）
    baseline_metrics = first.get('persistence_baseline_metrics')
    if isinstance(baseline_metrics, dict):
        detail['persistence_baseline_metrics'] = baseline_metrics
    return detail
