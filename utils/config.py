import os
import json
import random
import numpy as np
import torch
from dataclasses import dataclass, asdict, fields


CONFIG_FILE = 'config.json'

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
    # 数据源配置
    adapter_type: str = 'CALCE'
    cc_step: int = 2
    cv_step: int = 4
    discharge_step: int = 7

    def __post_init__(self):
        self.mode = normalize_model_name(self.mode)
        self.metric = normalize_metric_name(self.metric)
        self.norm_method = normalize_norm_method(self.norm_method)

    def to_dict(self):
        return asdict(self)

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
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_config(data):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass

def setup_seed(seed):
    np.random.seed(seed)
    random.seed(seed)
    os.environ['PYTHONHASHSEED'] = str(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
