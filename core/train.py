"""留一电池评估：最初的「一步预测」协议。

- 评估用的模型与部署用的模型走同一个 ``fit_final``——用**全部训练电池的
  全部窗口**定型。
- 头条指标 = **一步预测**（每个点都用截至该点的真实历史），递归预测仅作为
  诊断信息一并报告；不再做 α 收缩标定与滚动起点评估。
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
    get_train_test,
)
from core.prediction import predict_capacity_batch
from core.evaluate import calc_all_metrics, confidence_interval
from core.cancellation import check_cancelled
from core.progress import make_progress_event
from core.model_factory import (
    config_default_hp,
    hparam_grid,
    make_fit_fn,
)
from core.protocol import fit_final
from core import protocol as protocol_module
#: 模块级 ``Net``：保持既有测试/扩展点可用（可被 mock 替换）
from models.rnn_model import Net  # noqa: F401


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

    这两个协议**分开报告**：一步预测每一步都用真实历史，误差不累积；
    递归预测从初始窗口一路外推，用于观察误差累积形态。头条指标取一步预测。
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

    # ── 超参：最初样式——不做内层交叉验证，直接用配置里的值 ──
    fit_config = _config_with_seed(config, fit_seed)
    fit_fn = make_fit_fn(
        fit_config, stop_flag=stop_flag, log_callback=log_callback, name=name,
        net_class=Net, progress_callback=progress_callback,
        feature_scaler=feature_scaler)
    grid = hparam_grid(config, mode)
    hp = config_default_hp(config, mode, grid)
    if log_callback:
        log_callback(f'[{name}] 使用配置默认超参 {hp}（最初样式：跳过内层交叉验证）')

    check_cancelled(stop_flag)

    if mode in ('RNN', 'GRU', 'LSTM') and not multifeature:
        # ── 循环模型评估：旧项目口径 ──
        # 训练集 = 目标电池前 window+1 个点 + 其他电池全部窗口；
        # 训练时每 10 轮在目标电池测试序列上挑最优 epoch。
        train_x, train_y, train_data, test_data = get_train_test(
            battery_dict, name, window)
        if len(train_x) == 0 or len(test_data) == 0:
            if log_callback:
                log_callback(f'跳过 {name}，原因：训练/测试实例为空')
            return None, None, None
        test_x, test_y = build_instances(
            np.asarray(test_data, dtype=np.float32), window)
        if len(test_x) == 0:
            if log_callback:
                log_callback(f'跳过 {name}，原因：测试窗口为空')
            return None, None, None
        model = fit_fn(
            train_x, train_y, hp, test_x=test_x, test_y=test_y)
        check_cancelled(stop_flag)
    else:
        # ── 其他模型 / 多特征：用全部训练电池的全部窗口定型（当前行为） ──
        model = fit_final(
            battery_dict, train_names, window, fit_fn, hp, rated_capacity,
            columns=columns if multifeature else None)
        check_cancelled(stop_flag)

    metadata = _model_metadata(
        config, window, rated_capacity, scaler, feature_scaler, columns,
        multifeature, hp)

    # ── 诊断信息：一步预测与从初始窗口起的完全递归预测 ──
    protocols = evaluate_prediction_protocols(
        np.asarray(target_frames)[:, 0] if multifeature else target_frames,
        window,
        lambda windows: predict_capacity_batch(
            model, metadata, windows, device=device),
        rated_capacity, threshold_ratio)
    one_step = protocols['one_step']
    recursive = protocols['recursive']

    # ── 头条指标 = 一步预测（最初样式） ──
    metrics = dict(one_step['metrics'])
    metrics['re'] = protocols['rul_re']
    metrics['re_status'] = recursive['metrics'].get('re_status')

    train_data = list(np.asarray(target_frames)[:window, 0]) if multifeature \
        else list(np.asarray(target_frames)[:window])
    pred_list = train_data + list(one_step['prediction'])

    detail = {
        'battery': name,
        'cycles': int(len(target_frames)),
        'model': mode,
        'training_batteries': tuple(train_names),
        'protocol': 'strict_zero_shot',
        'rul_protocol': 'recursive_future',
        'selected_hparams': dict(hp),
        'scaler': scaler.to_dict(),
        'feature_columns': list(columns),
        'feature_scaler': (
            feature_scaler.to_dict() if feature_scaler is not None else None),
        'one_step_prediction': one_step['prediction'].tolist(),
        'recursive_prediction': recursive['prediction'].tolist(),
        'one_step_metrics': one_step['metrics'],
        'recursive_metrics': recursive['metrics'],
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
        if mode in ('RNN', 'GRU', 'LSTM'):
            # 旧项目口径：多种子取 RMSE 最优种子的预测画图（不平均）
            best_idx = int(np.argmin([
                float(m.get('rmse') or np.inf) for m in all_metrics]))
            best_prediction = all_predictions[best_idx]
            best_metrics = all_metrics[best_idx]
            best_run_detail = run_details[best_idx]
            if n_seeds > 1 and log_callback:
                log_callback(
                    f'[{name}] 多种子：取 RMSE 最优种子 '
                    f'{seeds[best_idx]}（RMSE={best_metrics["rmse"]:.4f}）')
        else:
            best_prediction = np.mean(np.vstack(all_predictions), axis=0)
            best_metrics = mean_metrics
            best_run_detail = None
        detail = _aggregate_detail(
            name, mode, battery_dict, ci_info, mean_metrics, run_details,
            best_run_detail=best_run_detail)

        selected_metric = getattr(config, 'metric', 'rmse')
        selected_score = best_metrics.get(
            selected_metric, best_metrics.get('rmse'))
        results[name] = {
            'score': (float(selected_score)
                      if selected_score is not None else None),
            'prediction': best_prediction.tolist(),
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
                      run_details, best_run_detail=None):
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
        'seed_policy': ('best_seed' if mode in ('RNN', 'GRU', 'LSTM')
                        else 'all_seed_mean'),
        'protocol': 'strict_zero_shot',
        'rul_protocol': 'recursive_future',
        'one_step_prediction': (
            best_run_detail['one_step_prediction']
            if best_run_detail is not None and best_run_detail
            else mean_protocol_prediction('one_step_prediction')),
        'recursive_prediction': (
            best_run_detail['recursive_prediction']
            if best_run_detail is not None and best_run_detail
            else mean_protocol_prediction('recursive_prediction')),
        'one_step_metrics': (
            best_run_detail['one_step_metrics']
            if best_run_detail is not None and best_run_detail
            else mean_protocol_metrics('one_step_metrics')),
        'recursive_metrics': (
            best_run_detail['recursive_metrics']
            if best_run_detail is not None and best_run_detail
            else mean_protocol_metrics('recursive_metrics')),
        'selected_hparams': first.get('selected_hparams', {}),
        'feature_columns': first.get('feature_columns', ['capacity']),
        'threshold': first.get('threshold'),
        'training_batteries': first.get('training_batteries', ()),
        'run_details': run_details,
    }
    return detail
