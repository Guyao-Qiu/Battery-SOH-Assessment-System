import os
import json
import hashlib
import platform
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
from models.rnn_model import Net
from core.preprocess import (
    build_instances,
    build_instances_mf,
    CapacityScaler,
    FeatureScaler,
)
from core.model_factory import (
    config_default_hp,
    hparam_grid,
    make_fit_fn,
)
from core.protocol import fit_final
from core.cancellation import check_cancelled
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


def _infer_input_size(state_dict):
    """从权重形状推断输入特征数（兼容没有 ``input_size`` 字段的旧模型）。

    循环单元的 ``weight_ih_l0`` 形状是 ``(gate_count * hidden, input_size)``。
    """
    for key in ('cell.weight_ih_l0', 'cell.weight_ih_l0_reverse'):
        tensor = state_dict.get(key)
        if tensor is not None and getattr(tensor, 'dim', lambda: 0)() == 2:
            return int(tensor.shape[1])
    return 1


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
        # 多特征模型需要重建正确的 input_size；旧模型（无该字段）回退为 1
        input_size = metadata.get('input_size')
        if isinstance(input_size, bool) or not isinstance(input_size, int) \
                or input_size < 1:
            input_size = _infer_input_size(state_dict)
        if input_size == 1:
            model = Net(hidden_dim=metadata['hidden_dim'], num_layers=1, mode=mode)
        else:
            model = Net(hidden_dim=metadata['hidden_dim'], num_layers=1,
                        mode=mode, input_size=input_size)
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
                             sample_count, selected_parameters,
                             feature_scaler=None, columns=None):
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
    columns = tuple(columns or ('capacity',))
    multifeature = len(columns) > 1
    metadata = {
        'mode': config.mode,
        'model_type': config.mode,
        'window_size': config.window_size,
        'rated_capacity': config.rated_capacity,
        'threshold_ratio': getattr(config, 'threshold_ratio', 0.8),
        'norm_method': scaler.method,
        'scaler': scaler.to_dict(),
        'feature_schema': {
            'features': list(columns),
            'feature': 'capacity' if not multifeature else 'multifeature',
            'dtype': 'float32',
            'shape': (['batch', config.window_size, len(columns)]
                      if multifeature
                      else ['batch', config.window_size]),
            'feature_scaler': (
                feature_scaler.to_dict() if feature_scaler is not None
                else None),
            'multifeature_recursive_policy': (
                '非容量通道在递归预测时保持窗口末值（未来工况未知）'
                if multifeature else None),
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
        metadata['input_size'] = int(len(columns))
    return _complete_metadata(metadata)


def _prepare_final_training_data(config, battery_dict, battery_list):
    """收集全部有效电池的全部窗口（不再切出「训练电池的后 20%」作验证）。

    改进方案 A2：验证集必须是**一块没见过的电池**（由 ``core.protocol`` 的内层
    留一电池交叉验证提供），而不是「训练电池的最后一段」——后者恰好是寿命末段，
    会让模型永远见不到膝点。
    """
    battery_x, battery_y = {}, {}
    valid_names = []
    columns = _feature_columns(config)
    multifeature = len(columns) > 1
    for name in battery_list:
        if name in battery_x or name not in battery_dict:
            continue
        entry = battery_dict[name]
        capacity = np.asarray(
            entry['capacity'], dtype=np.float32).reshape(-1)
        if len(capacity) <= config.window_size:
            continue
        if multifeature and hasattr(entry, 'columns'):
            available = [c for c in columns if c in entry.columns]
            if 'capacity' not in available:
                available = ['capacity'] + available
            x, y = build_instances_mf(
                entry.loc[:, available], config.window_size,
                cols=available)
        else:
            x, y = build_instances(capacity, config.window_size)
        if len(x) == 0:
            continue
        battery_x[name] = x
        battery_y[name] = y
        valid_names.append(name)
    if not valid_names:
        raise ValueError('没有足够的数据训练最终模型')

    all_x = np.vstack([battery_x[name] for name in valid_names])
    all_y = np.concatenate([battery_y[name] for name in valid_names])
    if len(all_x) < 2:
        raise ValueError('最终模型至少需要两个训练样本')

    return {
        'valid_names': valid_names,
        'battery_x': battery_x,
        'battery_y': battery_y,
        'all_x': all_x,
        'all_y': all_y,
    }


def train_model_on_all_data(config, battery_dict, battery_list, stop_flag=None,
                            log_callback=None):
    """用**全部**有效电池的全部窗口定型（与评估路径共用 ``fit_final``）。

    最初样式：不做内层交叉验证，直接用配置默认超参；不做 α 收缩标定
    （``persistence_blend`` 固定 1.0，预测即原始模型输出）。
    """
    check_cancelled(stop_flag)
    mode = normalize_model_name(config.mode)
    data = _prepare_final_training_data(config, battery_dict, battery_list)
    valid_names = data['valid_names']
    all_x = data['all_x']
    columns = _feature_columns(config)
    multifeature = len(columns) > 1
    rated = float(config.rated_capacity)

    # ── scaler 只用全部有效电池拟合；fit_fn 内部会用它归一化，因此这里传原始量纲 ──
    final_scaler, feature_scaler = _fit_final_scalers(
        config, data, columns, multifeature, rated)
    fit_fn = make_fit_fn(
        config, stop_flag=stop_flag, log_callback=log_callback,
        name='最终模型', net_class=Net, feature_scaler=feature_scaler)
    grid = hparam_grid(config, mode)
    hp = config_default_hp(config, mode, grid)
    if log_callback:
        log_callback(
            f'[最终模型] 使用配置默认超参 {hp}（最初样式：跳过内层交叉验证）')

    check_cancelled(stop_flag)

    # ── 定型：用全部有效电池的全部窗口重训 ──
    # 走的是与评估路径**同一个** core.protocol.fit_final（而不是各写一遍），
    # 因此「报告的评估指标」与「最终部署的模型」是同一套流程的产物。
    final_model = fit_final(
        battery_dict, valid_names, config.window_size, fit_fn, hp, rated,
        columns=columns if multifeature else None)
    check_cancelled(stop_flag)

    if mode in RECURRENT_MODES:
        final_model = final_model.to('cpu')

    metadata = _final_training_metadata(
        config, final_scaler, valid_names, battery_dict, len(all_x), hp,
        feature_scaler=feature_scaler, columns=columns)
    metadata['persistence_blend'] = 1.0
    if log_callback:
        log_callback(
            f'[最终模型] 已用全部 {len(valid_names)} 块电池、'
            f'{len(all_x)} 个样本重训，超参={hp}')
    return final_model, metadata


def _fit_final_scalers(config, data, columns, multifeature, rated):
    """最终 scaler：只用全部有效电池的窗口拟合。"""

    scaler = CapacityScaler(
        method=config.norm_method,
        rated_capacity=rated,
    ).fit(np.concatenate(
        [data['all_x'][:, :, 0].reshape(-1) if multifeature
         else data['all_x'].reshape(-1),
         data['all_y'].reshape(-1)]))

    feature_scaler = None
    if multifeature:
        frames = []
        for name in data['valid_names']:
            x = data['battery_x'][name]
            frames.append(x.reshape(-1, x.shape[-1]))
        combined = np.vstack(frames)
        feature_scaler = FeatureScaler().fit(combined)
    return scaler, feature_scaler


def _feature_columns(config):
    columns = getattr(config, 'feature_columns', None)
    if columns is None:
        return ('capacity',)
    return tuple(columns)
