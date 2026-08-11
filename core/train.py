import numpy as np
import torch
import torch.nn as nn

from models.rnn_model import Net
from core.preprocess import (
    CapacityScaler,
    generate_one_step_predictions,
    generate_recursive_predictions,
    prepare_leave_one_out_split,
)
from core.prediction import predict_capacity_batch
from core.evaluate import calc_all_metrics, confidence_interval
from core.cancellation import check_cancelled
from utils.config import setup_seed


def evaluate_prediction_protocols(sequence, window_size, predict_batch,
                                  rated_capacity, threshold_ratio):
    """Evaluate observed-history one-step and future recursive forecasts separately."""
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


def _train_one_battery(config, battery_dict, name, stop_flag=None, log_callback=None, seed=None):
    """训练单个电池（留一法），返回 (pred_list, metrics_dict, detail_dict)

    pred_list: 预测容量序列（含 train_data 前缀），用于绘图
    metrics_dict: 该电池的 rmse/mae/r2/pearson/re
    """
    check_cancelled(stop_flag)
    feature_size = config.window_size
    hidden_dim = config.hidden_dim
    mode = config.mode
    epochs = config.epochs
    device = config.device
    rated_capacity = config.rated_capacity
    threshold_ratio = config.threshold_ratio

    if seed is not None:
        setup_seed(seed)

    split = prepare_leave_one_out_split(
        battery_dict, name, window_size=feature_size)
    train_x, train_y = split.train_x, split.train_y
    val_x, val_y = split.val_x, split.val_y
    train_data = list(split.initial_window)
    scaler_fit_values = np.concatenate((train_x.reshape(-1), train_y))
    scaler = CapacityScaler(
        method=config.norm_method,
        rated_capacity=rated_capacity,
    ).fit(scaler_fit_values)
    scaled_train_x = scaler.transform(train_x)
    scaled_train_y = scaler.transform(train_y)
    scaled_val_x = scaler.transform(val_x)
    scaled_val_y = scaler.transform(val_y)
    model_metadata = {
        'mode': mode,
        'window_size': feature_size,
        'rated_capacity': rated_capacity,
        'scaler': scaler.to_dict(),
    }

    if len(train_x) == 0 or len(split.test_x) == 0:
        if log_callback:
            log_callback(f'跳过 {name}，原因：训练/测试实例为空')
        return None, None, None

    if log_callback:
        log_callback(f'[{name}] 训练样本 {len(train_x)}，测试样本 {len(split.test_x)}')

    if mode in ('XGBoost', 'RF'):
        from models.XGBoost import train_xgboost
        from models.RF import train_rf

        use_seed = seed if seed is not None else config.seed
        if mode == 'XGBoost':
            model = train_xgboost(
                scaled_train_x, scaled_train_y, scaled_val_x, scaled_val_y,
                n_estimators=config.n_estimators,
                learning_rate=config.learning_rate,
                max_depth=config.max_depth,
                subsample=config.subsample,
                colsample_bytree=config.colsample_bytree,
                patience=config.patience,
                seed=use_seed,
                log_callback=log_callback,
                name=name,
                stop_flag=stop_flag,
            )
        else:
            model = train_rf(
                scaled_train_x, scaled_train_y, scaled_val_x, scaled_val_y,
                n_estimators=config.n_estimators,
                max_depth=config.max_depth,
                min_samples_leaf=config.min_samples_leaf,
                max_features=config.max_features,
                patience=config.patience,
                seed=use_seed,
                log_callback=log_callback,
                name=name,
                stop_flag=stop_flag,
            )
        check_cancelled(stop_flag)
        protocols = evaluate_prediction_protocols(
            split.target_sequence, feature_size,
            lambda windows: predict_capacity_batch(
                model, model_metadata, windows, device=device),
            rated_capacity, threshold_ratio)
        one_step = protocols['one_step']
        recursive = protocols['recursive']
        metrics = dict(one_step['metrics'])
        metrics['re'] = protocols['rul_re']
        pred_list = train_data + list(one_step['prediction'])
        return pred_list, metrics, {
            'training_batteries': split.training_batteries,
            'protocol': 'strict_zero_shot',
            'scaler': scaler.to_dict(),
            'one_step_prediction': one_step['prediction'].tolist(),
            'recursive_prediction': recursive['prediction'].tolist(),
            'one_step_metrics': one_step['metrics'],
            'recursive_metrics': recursive['metrics'],
            'rul_protocol': 'recursive_future',
        }

    # RNN / GRU / LSTM
    model = Net(hidden_dim=hidden_dim, num_layers=1, mode=mode)
    model = model.to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    criterion = nn.MSELoss()

    best_score = float('inf')
    counter = 0
    best_state = None
    best_epoch = 0

    X = np.reshape(scaled_train_x, (-1, feature_size, 1))
    y = np.reshape(scaled_train_y, (-1, 1))
    X, y = torch.from_numpy(X).to(device), torch.from_numpy(y).to(device)
    X_val = np.reshape(scaled_val_x, (-1, feature_size, 1))
    y_val = np.reshape(scaled_val_y, (-1, 1))
    X_val = torch.from_numpy(X_val).to(device)
    y_val = torch.from_numpy(y_val).to(device)

    for epoch in range(epochs):
        check_cancelled(stop_flag)

        model.train()
        output = model(X)
        output = output.reshape(-1, 1)
        loss = criterion(output, y)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        check_cancelled(stop_flag)

        model.eval()
        with torch.no_grad():
            val_output = model(X_val).reshape(-1, 1)
            current_score = criterion(val_output, y_val).item()

        if current_score < best_score:
            best_score = current_score
            counter = 0
            best_state = {
                key: value.detach().cpu().clone()
                for key, value in model.state_dict().items()
            }
            best_epoch = epoch + 1
        else:
            counter += 1

        if (epoch + 1) % 10 == 0 and log_callback:
            log_callback(
                f'[{name}] 第{epoch + 1}轮 损失={loss.item():.4f} '
                f'验证损失={current_score:.4f}')

        if counter >= config.patience:
            if log_callback:
                log_callback(f'[{name}] 第{epoch + 1}轮早停（仅依据训练电池验证集）')
            break

    check_cancelled(stop_flag)
    if best_state is not None:
        model.load_state_dict(best_state)
    model.eval()
    def predict_batch(windows):
        return predict_capacity_batch(
            model, model_metadata, windows, device=device)

    protocols = evaluate_prediction_protocols(
        split.target_sequence, feature_size, predict_batch,
        rated_capacity, threshold_ratio)
    one_step = protocols['one_step']
    recursive = protocols['recursive']
    metrics = dict(one_step['metrics'])
    metrics['re'] = protocols['rul_re']
    pred_list = train_data + list(one_step['prediction'])
    return pred_list, metrics, {
        'training_batteries': split.training_batteries,
        'validation_loss': best_score,
        'best_epoch': best_epoch,
        'protocol': 'strict_zero_shot',
        'scaler': scaler.to_dict(),
        'one_step_prediction': one_step['prediction'].tolist(),
        'recursive_prediction': recursive['prediction'].tolist(),
        'one_step_metrics': one_step['metrics'],
        'recursive_metrics': recursive['metrics'],
        'rul_protocol': 'recursive_future',
    }


def train(config, battery_dict, battery_list, stop_flag=None, log_callback=None):
    feature_size = config.window_size
    mode = config.mode
    base_seed = config.seed
    n_seeds = max(1, getattr(config, 'n_seeds', 1))

    results = {}

    # 生成种子列表：以 base_seed 为起点，每次 +1
    seeds = [base_seed + i for i in range(n_seeds)]

    if n_seeds > 1 and log_callback:
        log_callback(
            f"<span style='color:#FFD54F; font-weight:bold;'>"
            f'多种子评估：共 {n_seeds} 个种子 {seeds}，'
            f'计算 95% 置信区间'
            f'</span>')

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

        # 收集多种子结果
        all_metrics = []  # 每个种子的 metrics dict
        all_predictions = []
        run_details = []

        for s_idx, sd in enumerate(seeds):
            check_cancelled(stop_flag)

            if n_seeds > 1 and log_callback:
                log_callback(f'[{name}] 种子 {s_idx + 1}/{n_seeds} (seed={sd})')

            pred_list, metrics, run_detail = _train_one_battery(
                config, battery_dict, name,
                stop_flag=stop_flag, log_callback=log_callback, seed=sd)

            if metrics is None:
                continue

            all_metrics.append(metrics)
            all_predictions.append(np.asarray(pred_list, dtype=np.float64))
            run_details.append(run_detail or {})

        if not all_metrics or not all_predictions:
            continue

        # 计算置信区间
        ci_info = {}
        for key in ('rmse', 'mae', 'r2', 'pearson', 're'):
            vals = [m[key] for m in all_metrics if key in m]
            if not vals:
                continue
            mean, lo, hi, std = confidence_interval(vals, confidence=0.95)
            ci_info[key] = {
                'mean': mean, 'lower': lo, 'upper': hi, 'std': std,
                'values': vals,
            }

        mean_metrics = {
            key: ci_info[key]['mean'] for key in ci_info
        }
        mean_prediction = np.mean(np.vstack(all_predictions), axis=0)

        def mean_protocol_metrics(field):
            protocol_metrics = [
                item[field] for item in run_details if field in item
            ]
            if not protocol_metrics:
                return {}
            keys = set.intersection(
                *(set(item) for item in protocol_metrics))
            return {
                key: float(np.mean([item[key] for item in protocol_metrics]))
                for key in keys
            }

        def mean_protocol_prediction(field):
            values = [item[field] for item in run_details if field in item]
            if not values:
                return []
            return np.mean(
                np.vstack([np.asarray(value, dtype=np.float64)
                           for value in values]), axis=0).tolist()

        one_step_metrics = mean_protocol_metrics('one_step_metrics')
        recursive_metrics = mean_protocol_metrics('recursive_metrics')

        detail = {
            'battery': name,
            'cycles': len(battery_dict[name]['capacity']),
            'model': mode,
            'rmse': mean_metrics['rmse'],
            'mae': mean_metrics['mae'],
            'r2': mean_metrics['r2'],
            'pearson': mean_metrics['pearson'],
            're': mean_metrics.get('re', 0.0),
            'n_seeds': len(all_metrics),
            'ci': ci_info,
            'ci_statistical_object': '同一留一折内的随机种子波动',
            'seed_policy': 'all_seed_mean',
            'one_step_prediction': mean_protocol_prediction(
                'one_step_prediction'),
            'recursive_prediction': mean_protocol_prediction(
                'recursive_prediction'),
            'one_step_metrics': one_step_metrics,
            'recursive_metrics': recursive_metrics,
            'rul_protocol': 'recursive_future',
            'run_details': run_details,
        }
        selected_metric = getattr(config, 'metric', 'rmse')
        selected_score = mean_metrics.get(
            selected_metric, mean_metrics['rmse'])
        results[name] = {
            'score': float(selected_score),
            'prediction': mean_prediction.tolist(),
            'detail': detail,
        }

        if n_seeds > 1 and log_callback:
            log_callback(
                f'[{name}] 多种子汇总：'
                f'RMSE={ci_info["rmse"]["mean"]:.4f}±{ci_info["rmse"]["std"]:.4f} '
                f'95%CI=[{ci_info["rmse"]["lower"]:.4f}, {ci_info["rmse"]["upper"]:.4f}]')

    return results
