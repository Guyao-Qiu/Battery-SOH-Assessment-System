import numpy as np
import torch

from core.preprocess import CapacityScaler


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


def predict_capacity_batch(model, metadata, windows, device='cpu'):
    """Use the model's persisted scaler for both batch and real-time prediction."""
    windows = np.asarray(windows, dtype=np.float32)
    if windows.ndim == 1:
        windows = windows.reshape(1, -1)
    if windows.ndim != 2:
        raise ValueError('预测输入必须是二维窗口数组')

    window_size = int(metadata['window_size'])
    if windows.shape[1] != window_size:
        raise ValueError(
            f'预测窗口长度应为 {window_size}，实际为 {windows.shape[1]}')

    scaler = scaler_from_metadata(metadata)
    scaled_windows = scaler.transform(windows).astype(np.float32)
    mode = metadata['mode']

    if mode in RECURRENT_MODELS:
        resolved_device = resolve_inference_device(device)
        if not hasattr(model, 'to'):
            raise ValueError('循环模型不支持设备切换')
        model_on_device = model.to(resolved_device)
        tensor = torch.from_numpy(
            scaled_windows.reshape(-1, window_size, 1)).to(resolved_device)
        if hasattr(model_on_device, 'eval'):
            model_on_device.eval()
        with torch.no_grad():
            scaled_prediction = model_on_device(tensor)
        scaled_prediction = np.asarray(
            scaled_prediction.detach().cpu().numpy(),
            dtype=np.float32).reshape(-1)
    else:
        scaled_prediction = np.asarray(
            model.predict(scaled_windows), dtype=np.float32).reshape(-1)

    return scaler.inverse_transform(scaled_prediction).reshape(-1)
