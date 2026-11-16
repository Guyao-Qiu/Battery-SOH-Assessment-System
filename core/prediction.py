import numpy as np
import torch

from core.preprocess import CapacityScaler, FeatureScaler


RECURRENT_MODELS = ('RNN', 'GRU', 'LSTM')


def resolve_inference_device(device):
    """Resolve a supported inference device and fall back safely to CPU."""
    try:
        requested = torch.device(device)
    except (TypeError, RuntimeError) as exc:
        raise ValueError(f'无效的预测设备：{device}') from exc
    if requested.type == 'cuda':
        if not torch.cuda.is_available():
            return torch.device('cpu')
        if requested.index is not None and requested.index >= torch.cuda.device_count():
            return torch.device('cpu')
        return requested
    if requested.type != 'cpu':
        return torch.device('cpu')
    return requested


def scaler_from_metadata(metadata):
    """Restore the fitted scaler, with a rated-capacity fallback for old models."""
    scaler_data = metadata.get('scaler')
    if scaler_data is not None:
        return CapacityScaler.from_dict(scaler_data)
    rated_capacity = (
        metadata.get('rated_capacity', 1.1)
        if metadata.get('mode') in RECURRENT_MODELS else 1.0
    )
    return CapacityScaler(
        method='rated', rated_capacity=rated_capacity).fit([rated_capacity])


def feature_names_from_metadata(metadata):
    """模型使用的特征名列表；旧模型（无 feature_schema）按单特征容量处理。"""
    schema = metadata.get('feature_schema')
    if isinstance(schema, dict):
        names = schema.get('features')
        if isinstance(names, (list, tuple)) and names:
            return [str(item) for item in names]
        if schema.get('feature') == 'capacity':
            return ['capacity']
    return ['capacity']


def feature_count_from_metadata(metadata):
    return len(feature_names_from_metadata(metadata))


def feature_scaler_from_metadata(metadata):
    """多特征模型随模型保存的 FeatureScaler；单特征模型返回 None。"""
    schema = metadata.get('feature_schema')
    if isinstance(schema, dict) and isinstance(schema.get('feature_scaler'), dict):
        return FeatureScaler.from_dict(schema['feature_scaler'])
    return None


def prepare_windows(windows, metadata):
    """把原始窗口整理成模型输入形状，并返回 (容量窗口, 模型输入)。

    单特征：``(N, W)`` -> 输入 ``(N, W)``；
    多特征：``(N, W, F)`` 或 ``(N, W)``（此时其余特征用窗口末值占位）-> 输入
    ``(N, W, F)``。
    """
    names = feature_names_from_metadata(metadata)
    window_size = int(metadata['window_size'])
    array = np.asarray(windows, dtype=np.float32)

    if array.ndim == 1:
        array = array.reshape(1, -1)
    if array.ndim == 3:
        if array.shape[1] != window_size:
            raise ValueError(
                f'预测窗口长度应为 {window_size}，实际为 {array.shape[1]}')
        if array.shape[2] != len(names):
            raise ValueError(
                f'预测特征数应为 {len(names)}，实际为 {array.shape[2]}')
        capacity_windows = array[:, :, 0]
        return capacity_windows, array

    if array.ndim != 2:
        raise ValueError('预测输入必须是二维窗口或三维多特征窗口')
    if array.shape[1] != window_size:
        raise ValueError(
            f'预测窗口长度应为 {window_size}，实际为 {array.shape[1]}')

    capacity_windows = array
    if len(names) == 1:
        return capacity_windows, array

    # 只给了容量窗口但模型是多特征的：其余特征用窗口末值沿时间轴占位。
    # 这是「未来工况未知」时的保守假设，调用方应在结果里标注。
    expanded = np.repeat(
        capacity_windows[:, :, None], len(names), axis=2).astype(np.float32)
    return capacity_windows, expanded


def scale_model_input(model_input, metadata):
    """按模型保存的 scaler 归一化**模型输入**（训练与预测共用这一处逻辑）。

    ``model_input`` 形状 ``(N, W)`` 或 ``(N, W, F)``，值是原始 Ah / 原始特征量纲。
    单特征：整块按 ``CapacityScaler`` 归一化；
    多特征：容量通道用 ``CapacityScaler``，其余通道用随模型保存的
    ``FeatureScaler``（z-score）。这样训练与推理的预处理**完全一致**。
    """
    array = np.asarray(model_input, dtype=np.float32)
    if array.ndim == 2:
        array = array[:, :, None]
    names = feature_names_from_metadata(metadata)
    scaler = scaler_from_metadata(metadata)

    if len(names) == 1:
        return scaler.transform(array[:, :, 0]).astype(np.float32)

    scaled = np.array(array, dtype=np.float32, copy=True)
    scaled[:, :, 0] = scaler.transform(array[:, :, 0])
    feature_scaler = feature_scaler_from_metadata(metadata)
    if feature_scaler is not None:
        scaled = feature_scaler.transform(scaled)
    return scaled


def predict_capacity_batch(model, metadata, windows, device='cpu'):
    """Use the model's persisted scaler for both batch and real-time prediction."""
    capacity_windows, model_input = prepare_windows(windows, metadata)
    mode = metadata['mode']
    scaled_input = scale_model_input(model_input, metadata)

    is_torch_model = (
        mode in RECURRENT_MODELS
        or str(metadata.get('backbone', 'default')).strip().lower()
        in ('transformer', 'detransformer')
        or str(mode).strip().lower() in ('transformer', 'detransformer')
        or (hasattr(model, 'forward') and not hasattr(model, 'predict'))
    )
    if is_torch_model:
        resolved_device = resolve_inference_device(device)
        if not hasattr(model, 'to'):
            raise ValueError('循环模型不支持设备切换')
        model_on_device = model.to(resolved_device)
        tensor = torch.from_numpy(
            scaled_input.reshape(len(scaled_input), scaled_input.shape[1], -1)
        ).to(resolved_device)
        if hasattr(model_on_device, 'eval'):
            model_on_device.eval()
        with torch.no_grad():
            scaled_prediction = model_on_device(tensor)
            if isinstance(scaled_prediction, tuple):
                scaled_prediction = scaled_prediction[0]
        scaled_prediction = np.asarray(
            scaled_prediction.detach().cpu().numpy(),
            dtype=np.float32).reshape(-1)
    else:
        flat = scaled_input.reshape(len(scaled_input), -1)
        scaled_prediction = np.asarray(
            model.predict(flat), dtype=np.float32).reshape(-1)

    scaler = scaler_from_metadata(metadata)
    prediction = scaler.inverse_transform(scaled_prediction).reshape(-1)
    blend = float(metadata.get('persistence_blend', 1.0))
    if not np.isfinite(blend) or not 0.0 <= blend <= 1.0:
        raise ValueError('持久性基线校准系数必须在 0 和 1 之间')
    persistence = capacity_windows[:, -1].astype(np.float32)
    return persistence + blend * (prediction - persistence)
