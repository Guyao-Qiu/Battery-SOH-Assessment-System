import os
import json
import hashlib
import platform
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from models.rnn_model import Net
from core.preprocess import build_instances, CapacityScaler
from core.cancellation import (
    check_cancelled,
    xgboost_stop_callbacks,
)
from utils.config import normalize_model_name


MODEL_FORMAT_VERSION = 2
MAX_MODEL_FILE_BYTES = 512 * 1024 * 1024
MAX_METADATA_FILE_BYTES = 1024 * 1024
RECURRENT_MODES = ('RNN', 'GRU', 'LSTM')
TREE_MODES = ('XGBoost', 'RF')


def _sha256_file(filepath):
    digest = hashlib.sha256()
    with open(filepath, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _library_versions():
    versions = {
        'python': platform.python_version(),
        'numpy': np.__version__,
        'torch': torch.__version__,
    }
    try:
        import sklearn
        versions['scikit_learn'] = sklearn.__version__
    except ImportError:
        pass
    try:
        import xgboost
        versions['xgboost'] = xgboost.__version__
    except ImportError:
        pass
    return versions


def _complete_metadata(metadata):
    if not isinstance(metadata, dict):
        raise ValueError('模型元数据必须是对象')
    completed = dict(metadata)
    mode = normalize_model_name(completed.get('mode', ''))
    model_type = normalize_model_name(completed.get('model_type', mode))
    if model_type != mode:
        raise ValueError('模型类型与运行模式不匹配')

    completed['format_version'] = MODEL_FORMAT_VERSION
    completed['mode'] = mode
    completed['model_type'] = model_type
    completed.setdefault('threshold_ratio', 0.8)
    completed.setdefault('feature_schema', {
        'feature': 'capacity',
        'dtype': 'float32',
        'shape': ['batch', 'window_size'],
    })
    completed.setdefault('training_params', {})
    completed.setdefault('library_versions', _library_versions())
    completed.setdefault('data_hash', hashlib.sha256(b'').hexdigest())
    completed.setdefault(
        'created_at', datetime.now(timezone.utc).isoformat())
    return completed


def _validate_metadata(metadata, extension, require_file_hash=True):
    if not isinstance(metadata, dict):
        raise ValueError('模型元数据必须是 JSON 对象')
    required = {
        'format_version', 'mode', 'model_type', 'window_size',
        'rated_capacity', 'threshold_ratio', 'scaler', 'feature_schema',
        'training_params', 'library_versions', 'data_hash', 'created_at',
    }
    if require_file_hash:
        required.add('file_sha256')
    missing = sorted(required.difference(metadata))
    if missing:
        raise ValueError(f'模型元数据缺少字段：{", ".join(missing)}')
    if metadata['format_version'] != MODEL_FORMAT_VERSION:
        raise ValueError(
            f'不支持的模型格式版本：{metadata["format_version"]}')

    mode = normalize_model_name(metadata['mode'])
    model_type = normalize_model_name(metadata['model_type'])
    if mode != model_type:
        raise ValueError('模型类型与运行模式不匹配')
    if extension in ('.pt', '.pth') and mode not in RECURRENT_MODES:
        raise ValueError('模型类型与文件扩展名不匹配')
    if extension == '.joblib' and mode not in TREE_MODES:
        raise ValueError('模型类型与文件扩展名不匹配')

    window_size = metadata['window_size']
    if isinstance(window_size, bool) or not isinstance(window_size, int) or window_size <= 0:
        raise ValueError('模型元数据中的窗口大小无效')
    rated_capacity = metadata['rated_capacity']
    if (isinstance(rated_capacity, bool) or
            not isinstance(rated_capacity, (int, float)) or
            not np.isfinite(rated_capacity) or rated_capacity <= 0):
        raise ValueError('模型元数据中的额定容量无效')
    threshold = metadata['threshold_ratio']
    if (isinstance(threshold, bool) or
            not isinstance(threshold, (int, float)) or
            not np.isfinite(threshold) or not 0 < threshold <= 1):
        raise ValueError('模型元数据中的失效阈值无效')
    if not isinstance(metadata['feature_schema'], dict):
        raise ValueError('模型特征结构元数据无效')
    if not isinstance(metadata['training_params'], dict):
        raise ValueError('模型训练参数元数据无效')
    if not isinstance(metadata['library_versions'], dict):
        raise ValueError('模型依赖版本元数据无效')
    try:
        CapacityScaler.from_dict(metadata['scaler'])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f'模型归一化元数据无效：{exc}') from exc
    if mode in RECURRENT_MODES:
        hidden_dim = metadata.get('hidden_dim')
        if (isinstance(hidden_dim, bool) or
                not isinstance(hidden_dim, int) or hidden_dim <= 0):
            raise ValueError('循环模型隐藏层大小元数据无效')

    hashes = [metadata['data_hash']]
    if require_file_hash:
        hashes.append(metadata['file_sha256'])
    if any(not isinstance(value, str) or len(value) != 64 or
           any(char not in '0123456789abcdef' for char in value)
           for value in hashes):
        raise ValueError('模型哈希元数据无效')
    if not isinstance(metadata['created_at'], str) or not metadata['created_at']:
        raise ValueError('模型创建时间元数据无效')
    return mode


def _write_metadata_sidecar(filepath, metadata):
    sidecar = filepath + '.meta.json'
    with open(sidecar, 'w', encoding='utf-8') as stream:
        json.dump(metadata, stream, ensure_ascii=False, indent=2)


def _read_validated_metadata(filepath, extension):
    if not os.path.isfile(filepath):
        raise ValueError('模型文件不存在')
    size = os.path.getsize(filepath)
    if size <= 0:
        raise ValueError('模型文件为空')
    if size > MAX_MODEL_FILE_BYTES:
        raise ValueError('模型文件过大，已拒绝加载')

    sidecar = filepath + '.meta.json'
    if not os.path.isfile(sidecar):
        raise ValueError('缺少模型元数据文件，旧格式需先安全迁移')
    metadata_size = os.path.getsize(sidecar)
    if metadata_size <= 0 or metadata_size > MAX_METADATA_FILE_BYTES:
        raise ValueError('模型元数据文件大小无效')
    try:
        with open(sidecar, 'r', encoding='utf-8') as stream:
            metadata = json.load(stream)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f'模型元数据无法解析：{exc}') from exc

    _validate_metadata(metadata, extension)
    actual_hash = _sha256_file(filepath)
    if actual_hash != metadata['file_sha256']:
        raise ValueError('模型文件哈希校验失败，文件可能已损坏或被篡改')
    return metadata


def save_model(model, metadata, filepath):
    """保存模型；权重与经过校验的元数据分离存放。"""
    filepath = os.fspath(filepath)
    extension = Path(filepath).suffix.lower()
    completed = _complete_metadata(metadata)
    mode = _validate_metadata(
        completed, extension, require_file_hash=False)
    if mode in RECURRENT_MODES:
        if extension not in ('.pt', '.pth'):
            raise ValueError('循环模型必须保存为 .pt 或 .pth 文件')
        state_dict = model.state_dict()
        if not state_dict or not all(
                isinstance(key, str) and torch.is_tensor(value)
                for key, value in state_dict.items()):
            raise ValueError('PyTorch 模型权重无效')
        torch.save(state_dict, filepath)
    elif mode in TREE_MODES:
        if extension != '.joblib':
            raise ValueError('树模型必须保存为 .joblib 文件')
        import joblib
        joblib.dump(model, filepath)
    else:
        raise ValueError(f'不支持的模型类型：{mode}')

    completed['file_sha256'] = _sha256_file(filepath)
    _write_metadata_sidecar(filepath, completed)


def load_model(filepath, allow_unsafe_joblib=False):
    """加载模型；joblib 仅能在用户明确知情同意后启用。"""
    filepath = os.fspath(filepath)
    ext = os.path.splitext(filepath)[1].lower()
    if ext in ('.pt', '.pth'):
        metadata = _read_validated_metadata(filepath, ext)
        try:
            state_dict = torch.load(
                filepath, map_location='cpu', weights_only=True)
        except Exception as exc:
            raise ValueError(f'模型权重文件无法安全读取：{exc}') from exc
        if not isinstance(state_dict, dict) or not state_dict or not all(
                isinstance(key, str) and torch.is_tensor(value)
                for key, value in state_dict.items()):
            raise ValueError('模型权重必须是仅包含张量的 state_dict')
        mode = metadata['mode']
        model = Net(hidden_dim=metadata['hidden_dim'], num_layers=1, mode=mode)
        try:
            model.load_state_dict(state_dict, strict=True)
        except (KeyError, RuntimeError, TypeError) as exc:
            raise ValueError(f'模型权重键与元数据不匹配：{exc}') from exc
        model.eval()
        return model, metadata
    elif ext == '.pkl':
        raise ValueError('禁止加载 .pkl 模型；请使用受控格式重新导出')
    elif ext == '.joblib':
        if not allow_unsafe_joblib:
            raise PermissionError(
                'joblib 反序列化可能执行代码，必须经用户明确确认后加载')
        metadata = _read_validated_metadata(filepath, ext)
        import joblib
        try:
            model = joblib.load(filepath)
        except Exception as exc:
            raise ValueError(f'joblib 模型加载失败：{exc}') from exc
        expected_name = {
            'RF': 'RandomForestRegressor',
            'XGBoost': 'XGBRegressor',
        }[metadata['mode']]
        if type(model).__name__ != expected_name:
            raise ValueError('反序列化后的模型类型与元数据不匹配')
        return model, metadata
    else:
        raise ValueError(
            f'不支持的模型文件格式：{ext}，请选择 .pt/.pth 或 .joblib 文件')


def _config_snapshot(config):
    if hasattr(config, 'to_dict'):
        return config.to_dict()
    names = (
        'mode', 'window_size', 'hidden_dim', 'epochs', 'rated_capacity',
        'threshold_ratio', 'norm_method', 'device', 'seed', 'patience',
        'n_estimators', 'learning_rate', 'max_depth', 'subsample',
        'colsample_bytree', 'min_samples_leaf', 'max_features',
    )
    return {name: getattr(config, name) for name in names if hasattr(config, name)}


def _battery_capacity_hash(values):
    capacity = np.ascontiguousarray(values, dtype=np.float64)
    return hashlib.sha256(capacity.tobytes()).hexdigest()


def _final_training_metadata(config, scaler, valid_names, battery_dict,
                             sample_count, selected_parameters):
    battery_hashes = {
        name: _battery_capacity_hash(battery_dict[name]['capacity'])
        for name in valid_names
    }
    data_digest = hashlib.sha256()
    for name in sorted(battery_hashes):
        data_digest.update(name.encode('utf-8'))
        data_digest.update(battery_hashes[name].encode('ascii'))
    training_params = _config_snapshot(config)
    training_params.update(selected_parameters)
    metadata = {
        'mode': config.mode,
        'model_type': config.mode,
        'window_size': config.window_size,
        'rated_capacity': config.rated_capacity,
        'threshold_ratio': getattr(config, 'threshold_ratio', 0.8),
        'norm_method': scaler.method,
        'scaler': scaler.to_dict(),
        'feature_schema': {
            'feature': 'capacity',
            'dtype': 'float32',
            'shape': ['batch', config.window_size],
        },
        'training_params': training_params,
        'data_hash': data_digest.hexdigest(),
        'training_batteries': list(valid_names),
        'battery_hashes': battery_hashes,
        'final_training_sample_count': int(sample_count),
        'final_training_scope': 'all_valid_batteries',
    }
    if config.mode in RECURRENT_MODES:
        metadata['hidden_dim'] = config.hidden_dim
    return _complete_metadata(metadata)


def _prepare_final_training_data(config, battery_dict, battery_list):
    battery_x, battery_y = {}, {}
    valid_names = []
    for name in battery_list:
        if name in battery_x or name not in battery_dict:
            continue
        capacity = np.asarray(
            battery_dict[name]['capacity'], dtype=np.float32).reshape(-1)
        if len(capacity) <= config.window_size:
            continue
        x, y = build_instances(capacity.tolist(), config.window_size)
        battery_x[name] = x
        battery_y[name] = y
        valid_names.append(name)
    if not valid_names:
        raise ValueError('没有足够的数据训练最终模型')

    all_x = np.vstack([battery_x[name] for name in valid_names])
    all_y = np.hstack([battery_y[name] for name in valid_names])
    if len(all_x) < 2:
        raise ValueError('最终模型至少需要两个训练样本')

    if len(valid_names) >= 2:
        validation_name = valid_names[-1]
        tuning_names = valid_names[:-1]
        tuning_x = np.vstack([battery_x[name] for name in tuning_names])
        tuning_y = np.hstack([battery_y[name] for name in tuning_names])
        validation_x = battery_x[validation_name]
        validation_y = battery_y[validation_name]
    else:
        validation_name = None
        split = min(max(int(len(all_x) * 0.9), 1), len(all_x) - 1)
        tuning_x, validation_x = all_x[:split], all_x[split:]
        tuning_y, validation_y = all_y[:split], all_y[split:]

    tuning_scaler = CapacityScaler(
        method=config.norm_method,
        rated_capacity=config.rated_capacity,
    ).fit(np.concatenate((tuning_x.reshape(-1), tuning_y)))
    final_scaler = CapacityScaler(
        method=config.norm_method,
        rated_capacity=config.rated_capacity,
    ).fit(np.concatenate((all_x.reshape(-1), all_y)))
    return {
        'valid_names': valid_names,
        'validation_name': validation_name,
        'tuning_x': tuning_scaler.transform(tuning_x),
        'tuning_y': tuning_scaler.transform(tuning_y),
        'validation_x': tuning_scaler.transform(validation_x),
        'validation_y': tuning_scaler.transform(validation_y),
        'all_x': final_scaler.transform(all_x),
        'all_y': final_scaler.transform(all_y),
        'final_scaler': final_scaler,
    }


def train_model_on_all_data(config, battery_dict, battery_list, stop_flag=None,
                            log_callback=None):
    """Tune on a held-out validation set, then refit on every valid battery."""
    check_cancelled(stop_flag)
    mode = normalize_model_name(config.mode)
    data = _prepare_final_training_data(
        config, battery_dict, battery_list)
    tuning_x = data['tuning_x']
    tuning_y = data['tuning_y']
    validation_x = data['validation_x']
    validation_y = data['validation_y']
    all_x = data['all_x']
    all_y = data['all_y']
    seed = config.seed

    if mode in RECURRENT_MODES:
        torch.manual_seed(seed)
        tuning_model = Net(
            hidden_dim=config.hidden_dim, num_layers=1, mode=mode).to(config.device)
        optimizer = torch.optim.Adam(tuning_model.parameters(), lr=0.001)
        criterion = nn.MSELoss()
        x_train_tensor = torch.from_numpy(np.reshape(
            tuning_x, (-1, config.window_size, 1))).to(config.device)
        y_train_tensor = torch.from_numpy(np.reshape(
            tuning_y, (-1, 1))).to(config.device)
        x_val_tensor = torch.from_numpy(np.reshape(
            validation_x, (-1, config.window_size, 1))).to(config.device)
        y_val_tensor = torch.from_numpy(np.reshape(
            validation_y, (-1, 1))).to(config.device)

        best_loss = float('inf')
        best_epoch = 1
        counter = 0
        for epoch in range(max(1, config.epochs)):
            check_cancelled(stop_flag)
            tuning_model.train()
            output = tuning_model(x_train_tensor).reshape(-1, 1)
            loss = criterion(output, y_train_tensor)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            tuning_model.eval()
            with torch.no_grad():
                val_loss = criterion(
                    tuning_model(x_val_tensor).reshape(-1, 1),
                    y_val_tensor).item()
            if val_loss < best_loss:
                best_loss = val_loss
                best_epoch = epoch + 1
                counter = 0
            else:
                counter += 1
            if (epoch + 1) % 10 == 0 and log_callback:
                log_callback(
                    f'[参数选择] 第{epoch + 1}轮 损失={loss.item():.4f} '
                    f'验证损失={val_loss:.4f}')
            if counter >= config.patience:
                break

        torch.manual_seed(seed)
        final_model = Net(
            hidden_dim=config.hidden_dim, num_layers=1, mode=mode).to(config.device)
        final_optimizer = torch.optim.Adam(final_model.parameters(), lr=0.001)
        all_x_tensor = torch.from_numpy(np.reshape(
            all_x, (-1, config.window_size, 1))).to(config.device)
        all_y_tensor = torch.from_numpy(np.reshape(
            all_y, (-1, 1))).to(config.device)
        for _ in range(best_epoch):
            check_cancelled(stop_flag)
            final_model.train()
            final_output = final_model(all_x_tensor).reshape(-1, 1)
            final_loss = criterion(final_output, all_y_tensor)
            final_optimizer.zero_grad()
            final_loss.backward()
            final_optimizer.step()
        final_model.eval()
        check_cancelled(stop_flag)
        final_model = final_model.to('cpu')
        metadata = _final_training_metadata(
            config, data['final_scaler'], data['valid_names'], battery_dict,
            len(all_x), {'selected_epochs': best_epoch})
        if log_callback:
            log_callback(
                f'[最终模型] 已用全部 {len(data["valid_names"])} 块电池、'
                f'{len(all_x)} 个样本重训 {best_epoch} 轮')
        return final_model, metadata

    if mode == 'XGBoost':
        from xgboost import XGBRegressor
        tuning_options = dict(
            n_estimators=config.n_estimators,
            learning_rate=config.learning_rate,
            max_depth=config.max_depth,
            subsample=config.subsample,
            colsample_bytree=config.colsample_bytree,
            early_stopping_rounds=config.patience,
            random_state=seed,
            verbosity=0,
        )
        callbacks = xgboost_stop_callbacks(stop_flag)
        if callbacks is not None:
            tuning_options['callbacks'] = callbacks
        tuning_model = XGBRegressor(**tuning_options)
        if log_callback:
            log_callback('[参数选择] XGBoost 验证中...')
        tuning_model.fit(
            tuning_x, tuning_y,
            eval_set=[(validation_x, validation_y)], verbose=False)
        check_cancelled(stop_flag)
        best_iteration = getattr(
            tuning_model.get_booster(), 'best_iteration', None)
        selected_trees = (
            int(best_iteration) + 1
            if best_iteration is not None else config.n_estimators)
        final_options = dict(
            n_estimators=selected_trees,
            learning_rate=config.learning_rate,
            max_depth=config.max_depth,
            subsample=config.subsample,
            colsample_bytree=config.colsample_bytree,
            random_state=seed,
            verbosity=0,
        )
        if callbacks is not None:
            final_options['callbacks'] = xgboost_stop_callbacks(stop_flag)
        final_model = XGBRegressor(**final_options)
        final_model.fit(all_x, all_y)
        check_cancelled(stop_flag)
        metadata = _final_training_metadata(
            config, data['final_scaler'], data['valid_names'], battery_dict,
            len(all_x), {'selected_n_estimators': selected_trees})
        if log_callback:
            log_callback(
                f'[最终模型] XGBoost 已用全部 {len(data["valid_names"])} 块电池、'
                f'{len(all_x)} 个样本重训，树数={selected_trees}')
        return final_model, metadata

    if mode == 'RF':
        from math import sqrt
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.metrics import mean_squared_error

        batch_size = max(1, min(10, config.n_estimators // 10))
        best_score = float('inf')
        selected_trees = min(batch_size, config.n_estimators)
        counter = 0
        total_trees = 0
        tuning_model = RandomForestRegressor(
            n_estimators=selected_trees,
            max_depth=config.max_depth,
            min_samples_leaf=config.min_samples_leaf,
            max_features=config.max_features,
            random_state=seed,
            n_jobs=-1,
            warm_start=True,
        )
        if log_callback:
            log_callback('[参数选择] RF 验证中...')
        while total_trees < config.n_estimators:
            check_cancelled(stop_flag)
            next_trees = min(total_trees + batch_size, config.n_estimators)
            tuning_model.n_estimators = next_trees
            tuning_model.fit(tuning_x, tuning_y)
            check_cancelled(stop_flag)
            rmse = sqrt(mean_squared_error(
                validation_y, tuning_model.predict(validation_x)))
            if rmse < best_score:
                best_score = rmse
                selected_trees = next_trees
                counter = 0
            else:
                counter += 1
            total_trees = next_trees
            if log_callback:
                log_callback(
                    f'[参数选择] RF 树数={total_trees}/{config.n_estimators}，'
                    f'RMSE={rmse:.4f}')
            if counter >= config.patience:
                break

        final_batch_size = min(batch_size, selected_trees)
        final_model = RandomForestRegressor(
            n_estimators=final_batch_size,
            max_depth=config.max_depth,
            min_samples_leaf=config.min_samples_leaf,
            max_features=config.max_features,
            random_state=seed,
            n_jobs=-1,
            warm_start=True,
        )
        fitted_trees = 0
        while fitted_trees < selected_trees:
            check_cancelled(stop_flag)
            fitted_trees = min(
                fitted_trees + batch_size, selected_trees)
            final_model.n_estimators = fitted_trees
            final_model.fit(all_x, all_y)
            check_cancelled(stop_flag)
        metadata = _final_training_metadata(
            config, data['final_scaler'], data['valid_names'], battery_dict,
            len(all_x), {'selected_n_estimators': selected_trees})
        if log_callback:
            log_callback(
                f'[最终模型] RF 已用全部 {len(data["valid_names"])} 块电池、'
                f'{len(all_x)} 个样本重训，树数={selected_trees}')
        return final_model, metadata

    raise ValueError(f'不支持的模型类型: {mode}')
