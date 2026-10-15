import numpy as np
from dataclasses import dataclass
from numpy.lib.stride_tricks import sliding_window_view


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


@dataclass(frozen=True)
class OutlierFilterResult:
    """Auditable result of capacity cleaning.

    ``mask`` / ``indices`` / ``removed_indices`` 反映**实际**处理结果；
    ``marked_indices`` 始终是「被判定为可疑」的原始下标，无论是否真的删除
    （A12：默认只标记不删除，因为容量再生是真实物理而不是噪声）。
    """

    indices: np.ndarray
    mask: np.ndarray
    removed_indices: np.ndarray
    protected_indices: np.ndarray
    reasons: dict
    marked_indices: np.ndarray = None

    @property
    def removed_count(self):
        return int(len(self.removed_indices))

    @property
    def marked_count(self):
        marked = self.marked_indices
        return 0 if marked is None else int(len(marked))

    @property
    def mode(self):
        """``'delete'``（真的删了）/ ``'mark'``（只标记）/ ``'off'``。"""
        if self.marked_count and not self.removed_count:
            return 'mark'
        return 'delete' if self.removed_count else 'off'


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


#: 离群点处理模式（A12）
#:   ``'mark'``  —— 只标记可疑点，**保留数据**（默认）。窗口均值对快速下降段和
#:                 NASA 的容量再生（真实物理，不是噪声）都会滞后，直接删会误伤。
#:   ``'delete'``—— 真的丢弃（旧行为，对含趋势序列容易误判）。
#:   ``'off'``   —— 完全不检测。
OUTLIER_MODES = ('off', 'mark', 'delete')


def filter_capacity_outliers(array, bins=40, enabled=True,
                             protect_knees=True, mode=None):
    """Causally filter local 2-sigma outliers without consulting future cycles.

    判定规则（只读历史窗口，不看未来）不变；``mode`` 决定**如何处理**判定结果
    （A12）：``'mark'``（默认）只标记并保留数据，``'delete'`` 才真的丢弃，
    ``'off'`` 不检测。``enabled=False`` 等价于 ``mode='off'``；
    显式给了 ``mode`` 时以 ``mode`` 为准。
    """
    values = np.asarray(array, dtype=np.float64).reshape(-1)
    if bins <= 0:
        raise ValueError('异常值窗口大小必须大于 0')
    if mode is None:
        mode = 'off' if not enabled else 'delete'
    if mode not in OUTLIER_MODES:
        raise ValueError(
            f'不支持的离群点模式: {mode}（可选 {OUTLIER_MODES}）')
    detect = mode in ('mark', 'delete')
    delete = mode == 'delete'

    finite = np.isfinite(values)
    mask = finite.copy()
    reasons = {
        int(index): '非有限容量值'
        for index in np.flatnonzero(~finite)
    }
    protected = set()
    marked = set(int(index) for index in np.flatnonzero(~finite))

    if detect:
        for index, value in enumerate(values):
            if not finite[index]:
                continue
            start = max(0, index - bins)
            history_indices = [
                item for item in range(start, index)
                if finite[item] and (mask[item] or not delete)
            ]
            if len(history_indices) < 5:
                continue
            history = values[history_indices]
            mean = float(np.mean(history))
            sigma = float(np.std(history))
            tolerance = max(1e-12, abs(mean) * 1e-12)
            scale = max(sigma, abs(mean) * 0.005, tolerance)
            lower = mean - 2 * scale
            upper = mean + 2 * scale
            if lower - tolerance <= value <= upper + tolerance:
                continue

            previous_index = history_indices[-1]
            previous = values[previous_index]
            drop_threshold = max(abs(previous) * 0.02, tolerance)
            follows_protected_drop = (
                previous_index in protected and value <= previous + tolerance)
            starts_degradation_knee = previous - value >= drop_threshold
            if protect_knees and (
                    starts_degradation_knee or follows_protected_drop):
                protected.add(index)
                continue

            marked.add(index)
            reasons[index] = (
                f'超出仅基于历史局部窗口的均值±2σ范围 '
                f'[{lower:.6g}, {upper:.6g}]')
            if delete:
                mask[index] = False

    indices = np.flatnonzero(mask).astype(int)
    removed = np.flatnonzero(~mask).astype(int)
    return OutlierFilterResult(
        indices=indices,
        mask=mask,
        removed_indices=removed,
        protected_indices=np.asarray(sorted(protected), dtype=int),
        reasons=reasons,
        marked_indices=np.asarray(sorted(marked), dtype=int),
    )


def drop_outlier(array, count, bins):
    """Backward-compatible index-only wrapper."""
    values = np.asarray(array).reshape(-1)[:count]
    return filter_capacity_outliers(values, bins=bins).indices


def build_instances(sequence, window_size):
    x, y = [], []
    for i in range(len(sequence) - window_size):
        features = sequence[i:i + window_size]
        target = sequence[i + window_size]
        x.append(features)
        y.append(target)
    return np.array(x).astype(np.float32), np.array(y).astype(np.float32)


def build_instances_fast(sequence, window_size):
    """与 :func:`build_instances` 等价的向量化实现。

    零拷贝滑窗，再各复制一次得到 (X, y)；含「长度不足」的边界处理。
    """
    seq = np.asarray(sequence, dtype=np.float32).reshape(-1)
    if len(seq) <= window_size:
        return (np.empty((0, window_size), np.float32),
                np.empty((0,), np.float32))
    view = sliding_window_view(seq, window_size + 1)          # (N, W+1)
    return view[:, :-1].copy(), view[:, -1].copy()


#: 多特征输入默认使用的列。
#:
#: 注意 ``dq_v`` 就是适配器里原来叫 ``'SoH'`` 的那一列（电压窗口内放电的容量
#: 差），它是**健康指标 HI**，不是 SOH（SOH = C / C_rated）。改名以避免混淆。
FEATURE_COLS = ('capacity', 'dq_v', 'CCCT', 'CVCT', 'resistance')


def build_instances_mf(frame, window, cols=FEATURE_COLS, fill_values=None):
    """多特征滑窗。返回 ``X:(N, W, F)``、``y:(N,)``（下一个循环的容量，永远是第 0 列）。

    缺失值只做**因果前向填充**（只用过去），剩余缺失用训练集统计量
    ``fill_values`` 填充，不会把未来信息泄漏回窗口。
    """

    cols = [c for c in cols if c in frame.columns]
    if not cols or 'capacity' not in cols:
        raise ValueError('多特征滑窗至少需要 capacity 列')
    # 容量永远是第 0 列，y 从它取
    if cols[0] != 'capacity':
        cols = ['capacity'] + [c for c in cols if c != 'capacity']

    selected = frame.loc[:, cols].astype('float32')
    # 先用「仅列」的前向填充（不跨列），再按列用训练集统计量兜底
    selected = selected.ffill()
    if fill_values is not None:
        selected = selected.fillna(
            {c: fill_values.get(c, 0.0) for c in cols})
    selected = selected.fillna(0.0)
    array = selected.to_numpy(dtype=np.float32)
    features = array.shape[1]
    if len(array) <= window:
        return (np.empty((0, window, features), np.float32),
                np.empty((0,), np.float32))
    view = sliding_window_view(array, (window + 1, features))[:, 0]   # (N, W+1, F)
    return view[:, :-1, :].copy(), view[:, -1, 0].copy()


def feature_fill_values(frame, cols=FEATURE_COLS):
    """用训练集统计量（均值）填充剩余缺失；只允许在训练电池上拟合。"""
    values = {}
    for column in cols:
        if column not in frame.columns:
            continue
        series = frame[column].astype('float64')
        mean = series.mean(skipna=True)
        values[column] = float(mean) if np.isfinite(mean) else 0.0
    return values


class FeatureScaler:
    """逐特征 z-score；只用训练电池的窗口拟合，可 JSON 序列化后随模型保存。"""

    def __init__(self, mean=None, std=None):
        self.mean = None if mean is None else np.asarray(mean, dtype=np.float64)
        self.std = None if std is None else np.asarray(std, dtype=np.float64)

    def fit(self, features):
        array = np.asarray(features, dtype=np.float64)
        if array.ndim == 2:
            array = array.reshape(array.shape[0], 1, -1)
        flat = array.reshape(-1, array.shape[-1])
        self.mean = np.nanmean(flat, axis=0)
        std = np.nanstd(flat, axis=0)
        self.mean = np.where(np.isfinite(self.mean), self.mean, 0.0)
        self.std = np.where(
            np.isfinite(std) & (std > 1e-8), std, 1.0)
        return self

    def transform(self, features):
        if self.mean is None or self.std is None:
            raise RuntimeError('FeatureScaler 尚未拟合')
        array = np.asarray(features, dtype=np.float32)
        return ((array - self.mean) / self.std).astype(np.float32)

    def to_dict(self):
        if self.mean is None:
            raise RuntimeError('FeatureScaler 尚未拟合')
        return {'mean': self.mean.tolist(), 'std': self.std.tolist()}

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict) or 'mean' not in data or 'std' not in data:
            raise ValueError('FeatureScaler 元数据缺少 mean/std')
        return cls(mean=data['mean'], std=data['std'])


def fit_persistence_blend(windows, targets, model_prediction):
    """Fit validation-only shrinkage toward the last observed capacity."""
    windows = np.asarray(windows, dtype=np.float64)
    targets = np.asarray(targets, dtype=np.float64).reshape(-1)
    prediction = np.asarray(model_prediction, dtype=np.float64).reshape(-1)
    if windows.ndim != 2 or windows.shape[1] == 0:
        raise ValueError('校准窗口必须是非空二维数组')
    if len(windows) != len(targets) or len(targets) != len(prediction):
        raise ValueError('校准窗口、标签和预测长度必须一致')
    if not (np.all(np.isfinite(windows[:, -1])) and
            np.all(np.isfinite(targets)) and
            np.all(np.isfinite(prediction))):
        raise ValueError('校准数据必须全部为有限数值')

    persistence = windows[:, -1]
    model_delta = prediction - persistence
    target_delta = targets - persistence
    denominator = float(np.dot(model_delta, model_delta))
    if denominator <= 1e-12:
        return 0.0
    blend = float(np.dot(model_delta, target_delta) / denominator)
    return float(np.clip(blend, 0.0, 1.0))


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
