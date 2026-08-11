import numpy as np
from dataclasses import dataclass


@dataclass(frozen=True)
class LeaveOneOutSplit:
    """A strict fold whose target battery is used only for final evaluation."""

    train_x: np.ndarray
    train_y: np.ndarray
    val_x: np.ndarray
    val_y: np.ndarray
    test_x: np.ndarray
    test_y: np.ndarray
    target_sequence: np.ndarray
    initial_window: np.ndarray
    training_values: np.ndarray
    training_batteries: tuple


class CapacityScaler:
    """Capacity scaling fitted once on training data and safe to serialize as JSON."""

    METHODS = ('rated', 'minmax', 'zscore')

    def __init__(self, method='rated', rated_capacity=1.1):
        method = str(method).lower()
        if method not in self.METHODS:
            raise ValueError(f'不支持的归一化方式: {method}')
        if not np.isfinite(rated_capacity) or rated_capacity <= 0:
            raise ValueError('额定容量必须是有限正数')
        self.method = method
        self.rated_capacity = float(rated_capacity)
        self.minimum = None
        self.maximum = None
        self.mean = None
        self.std = None
        self._fitted = False

    def fit(self, values):
        values = np.asarray(values, dtype=np.float64).reshape(-1)
        if len(values) == 0 or not np.all(np.isfinite(values)):
            raise ValueError('scaler 训练数据必须包含有限数值')
        self.minimum = float(np.min(values))
        self.maximum = float(np.max(values))
        self.mean = float(np.mean(values))
        self.std = float(np.std(values))
        self._fitted = True
        return self

    def _check_fitted(self):
        if not self._fitted:
            raise RuntimeError('scaler 尚未拟合')

    def transform(self, values):
        self._check_fitted()
        values = np.asarray(values, dtype=np.float32)
        if self.method == 'rated':
            return values / self.rated_capacity
        if self.method == 'minmax':
            scale = self.maximum - self.minimum
            if scale <= 1e-12:
                return np.zeros_like(values, dtype=np.float32)
            return (values - self.minimum) / scale
        scale = self.std if self.std > 1e-12 else 1.0
        return (values - self.mean) / scale

    def inverse_transform(self, values):
        self._check_fitted()
        values = np.asarray(values, dtype=np.float32)
        if self.method == 'rated':
            return values * self.rated_capacity
        if self.method == 'minmax':
            return values * (self.maximum - self.minimum) + self.minimum
        scale = self.std if self.std > 1e-12 else 1.0
        return values * scale + self.mean

    def to_dict(self):
        self._check_fitted()
        return {
            'method': self.method,
            'rated_capacity': self.rated_capacity,
            'minimum': self.minimum,
            'maximum': self.maximum,
            'mean': self.mean,
            'std': self.std,
        }

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            raise ValueError('scaler 元数据必须是对象')
        scaler = cls(
            method=data.get('method', 'rated'),
            rated_capacity=data.get('rated_capacity', 1.1),
        )
        required = ('minimum', 'maximum', 'mean', 'std')
        if any(key not in data for key in required):
            raise ValueError('scaler 元数据缺少拟合参数')
        for key in required:
            value = data[key]
            if value is None or not np.isfinite(value):
                raise ValueError(f'scaler 元数据字段无效: {key}')
            setattr(scaler, key, float(value))
        scaler._fitted = True
        return scaler


def drop_outlier(array, count, bins):
    index = []
    for start in range(0, count, bins):
        end = min(start + bins, count)
        array_lim = array[start:end]
        if len(array_lim) < 3:
            index.extend(list(range(start, end)))
            continue
        sigma = np.std(array_lim)
        mean = np.mean(array_lim)
        th_max, th_min = mean + sigma * 2, mean - sigma * 2
        idx = np.where((array_lim < th_max) & (array_lim > th_min))
        idx = idx[0] + start
        index.extend(list(idx))
    return np.array(index)


def build_instances(sequence, window_size):
    x, y = [], []
    for i in range(len(sequence) - window_size):
        features = sequence[i:i + window_size]
        target = sequence[i + window_size]
        x.append(features)
        y.append(target)
    return np.array(x).astype(np.float32), np.array(y).astype(np.float32)


def generate_one_step_predictions(sequence, window_size, predict_batch):
    """Predict every next point using the observed history available at that step."""
    test_x, test_y = build_instances(sequence, window_size)
    if len(test_x) == 0:
        raise ValueError('序列长度不足，无法执行一步预测')
    prediction = np.asarray(predict_batch(test_x), dtype=np.float64).reshape(-1)
    if len(prediction) != len(test_y):
        raise ValueError('一步预测结果长度与测试标签不一致')
    return test_y.astype(np.float64), prediction


def generate_recursive_predictions(sequence, window_size, predict_batch):
    """Forecast the future from one observed window, feeding predictions back in."""
    sequence = np.asarray(sequence, dtype=np.float64).reshape(-1)
    if len(sequence) <= window_size:
        raise ValueError('序列长度不足，无法执行递归未来预测')

    history = sequence[:window_size].tolist()
    prediction = []
    for _ in range(len(sequence) - window_size):
        window = np.asarray(history[-window_size:], dtype=np.float32).reshape(1, -1)
        next_values = np.asarray(
            predict_batch(window), dtype=np.float64).reshape(-1)
        if len(next_values) != 1 or not np.isfinite(next_values[0]):
            raise ValueError('递归预测器必须为单个窗口返回一个有限数值')
        next_value = float(next_values[0])
        prediction.append(next_value)
        history.append(next_value)

    truth = sequence[window_size:]
    return truth, np.asarray(prediction, dtype=np.float64)


def prepare_leave_one_out_split(data_dict, name, window_size=8,
                                validation_fraction=0.2):
    """Build a zero-shot cross-battery train/validation/test fold.

    The held-out battery contributes no label or feature to model fitting,
    preprocessing fitting, early stopping, or model selection. Validation is a
    deterministic trailing period taken separately from every training battery.
    """
    if name not in data_dict:
        raise KeyError(f'目标电池不存在: {name}')
    if window_size < 1:
        raise ValueError('窗口大小必须大于 0')
    if not 0.0 < validation_fraction < 1.0:
        raise ValueError('验证集比例必须在 0 和 1 之间')

    train_x_parts, train_y_parts = [], []
    val_x_parts, val_y_parts = [], []
    training_values = []
    training_batteries = []

    for battery_name, battery_data in data_dict.items():
        if battery_name == name:
            continue
        sequence = np.asarray(battery_data['capacity'], dtype=np.float32)
        data_x, data_y = build_instances(sequence, window_size)
        if len(data_x) < 2:
            continue

        val_count = max(1, int(np.ceil(len(data_x) * validation_fraction)))
        train_count = len(data_x) - val_count
        if train_count < 1:
            continue

        train_x_parts.append(data_x[:train_count])
        train_y_parts.append(data_y[:train_count])
        val_x_parts.append(data_x[train_count:])
        val_y_parts.append(data_y[train_count:])
        training_values.append(sequence)
        training_batteries.append(battery_name)

    if not train_x_parts or not val_x_parts:
        raise ValueError('训练电池不足，无法建立独立训练集和验证集')

    target_sequence = np.asarray(
        data_dict[name]['capacity'], dtype=np.float32)
    test_x, test_y = build_instances(target_sequence, window_size)
    if len(test_x) == 0:
        raise ValueError(f'目标电池 {name} 的循环数不足')

    return LeaveOneOutSplit(
        train_x=np.vstack(train_x_parts).astype(np.float32),
        train_y=np.concatenate(train_y_parts).astype(np.float32),
        val_x=np.vstack(val_x_parts).astype(np.float32),
        val_y=np.concatenate(val_y_parts).astype(np.float32),
        test_x=test_x,
        test_y=test_y,
        target_sequence=target_sequence,
        initial_window=target_sequence[:window_size].copy(),
        training_values=np.concatenate(training_values).astype(np.float32),
        training_batteries=tuple(training_batteries),
    )


def get_train_test(data_dict, name, window_size=8):
    """Backward-compatible strict split without target-battery training labels."""
    split = prepare_leave_one_out_split(data_dict, name, window_size)
    train_x = np.vstack((split.train_x, split.val_x))
    train_y = np.concatenate((split.train_y, split.val_y))
    train_data = list(split.initial_window)
    test_data = list(split.target_sequence[window_size:])
    return train_x, train_y, train_data, test_data


def normalize_data(data, method='rated', rated_capacity=1.1):
    return CapacityScaler(method, rated_capacity).fit(data).transform(data)
