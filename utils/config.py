import os
import json
import random
import numpy as np
import torch
from dataclasses import dataclass, asdict, fields
from typing import Optional
from utils.paths import CONFIG_FILE


SUPPORTED_MODELS = ('RNN', 'GRU', 'LSTM', 'XGBoost', 'RF')
_MODEL_ALIASES = {name.lower(): name for name in SUPPORTED_MODELS}


def normalize_model_name(value):
    key = str(value).strip().lower()
    if key not in _MODEL_ALIASES:
        supported = '、'.join(SUPPORTED_MODELS)
        raise ValueError(f'不支持的模型类型: {value}；可选值为 {supported}')
    return _MODEL_ALIASES[key]


def normalize_norm_method(value):
    key = str(value).strip().lower()
    aliases = {
        'rated': 'rated',
        '额定容量归一化': 'rated',
        'minmax': 'minmax',
        'zscore': 'zscore',
    }
    if key not in aliases:
        raise ValueError(f'不支持的归一化方式: {value}')
    return aliases[key]


def normalize_metric_name(value):
    key = str(value).strip().lower()
    aliases = {
        'rmse': 'rmse', 'mae': 'mae', 'r2': 'r2', 'r²': 'r2',
        'pearson': 'pearson', 're': 're', 'all': 'all', '全部': 'all',
    }
    if key not in aliases:
        raise ValueError(f'不支持的评估指标: {value}')
    return aliases[key]


# ── 配置里只存"规范键"，界面文本只在界面层转换（改进方案 A11） ──────

DEVICE_UI = {'cpu': 'CPU', 'cuda': 'GPU (CUDA)'}
NORM_UI = {
    'rated': '额定容量归一化',
    'zscore': 'Z-score 标准化',
    'minmax': 'Min-Max 归一化',
}
ADAPTER_UI = {'CALCE': 'CALCE (.xlsx/.csv)', 'NASA': 'NASA (.mat)'}
THEME_UI = {'light': '宣纸（浅色）', 'dark': '墨夜（深色）'}

_DEVICE_ALIASES = {
    'cpu': 'cpu',
    'cuda': 'cuda',
    'gpu': 'cuda',
    'gpu (cuda)': 'cuda',
}


def normalize_device(value, default='cpu'):
    """``'GPU (CUDA)'`` / ``'gpu'`` / ``'cuda'`` -> ``'cuda'``；未知值回退 default。

    旧配置文件把界面文本直接写进了 JSON，所以这里必须同时接受两种写法。
    """
    return _DEVICE_ALIASES.get(str(value).strip().lower(), default)


def to_ui(mapping, key):
    """规范键 -> 界面文本。"""
    return mapping.get(key, next(iter(mapping.values())))


def from_ui(mapping, text, default=None):
    """界面文本 -> 规范键；也接受已经是规范键的输入（兼容旧配置文件）。"""
    text = str(text).strip()
    if text in mapping:
        return text
    for key, shown in mapping.items():
        if shown == text:
            return key
    return default if default is not None else next(iter(mapping))


#: 多特征输入的候选列（capacity 永远是第 0 列 / 预测目标）。
#: 纯文本写法：配置、日志、无障碍名称等不支持富文本的位置使用。
FEATURE_OPTIONS = {
    'capacity': '容量（必选）',
    'dq_v': '电压窗口放电容量 dq_v',
    'CCCT': '恒流充电时长 CCCT',
    'CVCT': '恒压充电时长 CVCT',
    'resistance': '内阻 resistance',
}
#: 界面上的分段写法：``(中文说明, 数学符号富文本)``。
#: 变量用斜体、下标用 <sub>（数学排版习惯），避免 dq_v 这种下划线写法。
#: QCheckBox 只渲染纯文本，所以数学符号由旁边的 QLabel 承载。
FEATURE_LABELS = {
    'capacity': ('容量（必选）', ''),
    'dq_v': ('电压窗口放电容量', '<i>dq</i><sub>v</sub>'),
    'CCCT': ('恒流充电时长', '<i>CCCT</i>'),
    'CVCT': ('恒压充电时长', '<i>CVCT</i>'),
    'resistance': ('内阻', '<i>resistance</i>'),
}
DEFAULT_FEATURES = ('capacity',)


def normalize_feature_list(value):
    """把特征配置规范成元组；容量永远在内、且排第一。"""
    if value is None:
        return DEFAULT_FEATURES
    if isinstance(value, str):
        items = [item for item in value.replace('，', ',').split(',') if item.strip()]
    else:
        items = list(value)
    normalized = []
    for item in items:
        name = str(item).strip()
        if name in FEATURE_OPTIONS and name not in normalized:
            normalized.append(name)
    if 'capacity' not in normalized:
        normalized.insert(0, 'capacity')
    else:
        normalized.remove('capacity')
        normalized.insert(0, 'capacity')
    return tuple(normalized)


_CONFIG_ALIASES = {
    'mode': ('model', 'MODEL'),
    'threshold_ratio': ('THRESHOLD_RATIO',),
    'window_size': ('Feature Size',),
    'seed': ('random_seed',),
    'epochs': ('num_epochs',),
    'norm_method': ('normalization',),
    'n_estimators': ('xgb_n_estimators', 'rf_n_estimators'),
    'learning_rate': ('xgb_learning_rate',),
    'max_depth': ('xgb_max_depth', 'rf_max_depth'),
    'subsample': ('xgb_subsample',),
    'colsample_bytree': ('xgb_colsample_bytree',),
    'min_samples_leaf': ('rf_min_samples_leaf',),
    'max_features': ('rf_max_features',),
    'patience': ('early_stopping_rounds', 'rf_patience'),
    'feature_columns': ('features', 'FEATURES'),
    'rnn_lr': ('learning_rate_rnn',),
    'eol_debounce': ('failure_debounce', 'debounce'),
}


@dataclass
class TrainConfig:
    rated_capacity: float = 1.1
    threshold_ratio: float = 0.8
    voltage_upper: float = 3.8
    voltage_lower: float = 3.4
    window_size: int = 64
    epochs: int = 100
    hidden_dim: int = 64
    mode: str = 'RNN'
    metric: str = 'rmse'
    device: str = 'cpu'
    seed: int = 2
    n_seeds: int = 5
    patience: int = 20
    norm_method: str = 'rated'
    n_estimators: int = 100
    learning_rate: float = 0.1
    max_depth: int = 6
    subsample: float = 1.0
    colsample_bytree: float = 1.0
    min_samples_leaf: int = 1
    max_features: float = 1.0
    # RNN 专用（改进方案 A8：此前学习率写死 0.001，配置里没有这一项）
    rnn_lr: float = 0.001
    rnn_dropout: float = 0.1
    # 多特征输入（改进方案 A5）
    feature_columns: tuple = DEFAULT_FEATURES
    # 失效判定去抖（改进方案 A12）：需要连续多少个循环低于阈值才算失效。
    # 1 = 旧的「首次下穿即失效」，保持向后兼容；3 = 抗单点噪声。
    eol_debounce: int = 1
    # 数据源配置
    adapter_type: str = 'CALCE'
    cc_step: Optional[int] = None
    cv_step: Optional[int] = None
    discharge_step: Optional[int] = None

    def __post_init__(self):
        self.mode = normalize_model_name(self.mode)
        self.metric = normalize_metric_name(self.metric)
        self.norm_method = normalize_norm_method(self.norm_method)
        # A11：旧配置把界面文本（'GPU (CUDA)'）写进 JSON，这里必须规范化
        self.device = normalize_device(self.device)
        self.feature_columns = normalize_feature_list(self.feature_columns)
        # A12：去抖必须是 >=1 的整数；非法值回落到兼容默认 1
        try:
            self.eol_debounce = max(1, int(self.eol_debounce))
        except (TypeError, ValueError):
            self.eol_debounce = 1
        if self.adapter_type not in ADAPTER_UI:
            raise ValueError(f'不支持的数据源适配器: {self.adapter_type}')

    def to_dict(self):
        data = asdict(self)
        data['feature_columns'] = list(self.feature_columns)
        return data

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            raise ValueError('配置必须是 JSON 对象')
        values = {}
        for field in fields(cls):
            keys = (field.name,) + _CONFIG_ALIASES.get(field.name, ())
            for key in keys:
                if key in data:
                    values[field.name] = data[key]
                    break
        return cls(**values)


def load_config():
    if not CONFIG_FILE.exists():
        return {}
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_config(data):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def setup_seed(seed, deterministic=None):
    """设置随机种子，返回是否达成了**严格**确定性（A12）。

    关于 ``PYTHONHASHSEED``：解释器在启动时就读完了它，因此进程内赋值
    **对当前进程无效**，只影响之后 spawn 出来的子进程。要真正复现哈希随机化
    带来的差异，请在启动前设置环境变量，例如：

    ```powershell
    $env:PYTHONHASHSEED = '2'; python -X utf8 battery_soh_app.py
    ```

    ``deterministic``：为 ``True`` 时额外调用
    ``torch.use_deterministic_algorithms(True)`` 并设置
    ``CUBLAS_WORKSPACE_CONFIG``。后者必须在 **CUDA 上下文创建之前**设好；
    如果 CUDA 已经初始化，返回值会是 ``False``，表示本次运行无法保证严格确定性
    （而不是悄悄假装已经确定）。
    """
    np.random.seed(seed)
    random.seed(seed)
    # 对当前进程无效（解释器启动时已读取），仅对后续子进程生效
    os.environ.setdefault('PYTHONHASHSEED', str(seed))
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True

    if deterministic is None:
        deterministic = os.environ.get('SOH_DETERMINISTIC') == '1'
    if not deterministic:
        return not torch.cuda.is_available()

    strict = True
    if torch.cuda.is_available():
        # cublas 的工作区配置只在其初始化前生效；初始化后再设就没用了
        if 'CUBLAS_WORKSPACE_CONFIG' not in os.environ:
            os.environ['CUBLAS_WORKSPACE_CONFIG'] = ':4096:8'
            strict = not torch.cuda.is_initialized()
    try:
        torch.use_deterministic_algorithms(True, warn_only=False)
    except (RuntimeError, AttributeError):
        # 某些算子没有确定性实现，此时退回「尽力而为」并如实返回 False
        strict = False
    return strict
