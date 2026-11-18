#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""从 utils/config.py 与 config.json 同步 README 默认参数表。

用法::

    python tools/sync_readme_defaults.py          # 写入 README.md / README_EN.md
    python tools/sync_readme_defaults.py --check  # 校验是否与代码/config.json 一致
"""

from __future__ import annotations

import argparse
from dataclasses import fields
import inspect
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.adapters import CALCEAdapter, NASAAdapter  # noqa: E402
from core.dataload import load_battery_from_paths  # noqa: E402
from core.result_semantics import DEFAULT_DEBOUNCE_CYCLES  # noqa: E402
from utils.config import TrainConfig  # noqa: E402

BEGIN_MARKER = '<!-- DEFAULTS:BEGIN -->'
END_MARKER = '<!-- DEFAULTS:END -->'

# 字段说明与代码位置：(中文说明, 英文说明, 代码位置)
FIELD_NOTES = {
    'rated_capacity': ('额定容量 (Ah)', 'Rated capacity (Ah)', '`config.json`, `utils/config.py`'),
    'threshold_ratio': (
        '失效阈值比例（UI 启动加载 `config.json` 的 `0.7`；历史 `5681172` 基准与未加载配置时的 `TrainConfig`/模型保存回退为 `0.8`）',
        'Failure threshold ratio (UI loads `0.7` from `config.json`; `TrainConfig` / persistence fallback and historical `5681172` benchmark use `0.8`)',
        '`config.json`, `utils/config.py`, `ui/main_window.py`',
    ),
    'voltage_upper': ('健康指标 `dq_v` 上电压 (V)', 'Upper voltage for `dq_v` (V)', '`config.json`, `utils/config.py`'),
    'voltage_lower': ('健康指标 `dq_v` 下电压 (V)', 'Lower voltage for `dq_v` (V)', '`config.json`, `utils/config.py`'),
    'window_size': ('历史输入滑窗长度（循环数）', 'Sliding input window length (cycles)', '`config.json`, `utils/config.py`'),
    'epochs': ('深度学习训练轮数', 'Deep-learning training epochs', '`config.json`, `utils/config.py`'),
    'hidden_dim': ('RNN / DeTransformer 隐层维度', 'Hidden dimension for RNN / DeTransformer', '`config.json`, `utils/config.py`'),
    'mode': ('默认评估模型', 'Default evaluation model', '`config.json`, `utils/config.py`'),
    'metric': (
        '默认展示指标（`config.json` 为 `all`，类默认为 `rmse`）',
        'Default display metric (`all` in `config.json`; `rmse` on `TrainConfig`)',
        '`config.json`, `utils/config.py`',
    ),
    'device': ('默认计算设备（`cpu` / `cuda`）', 'Default compute device (`cpu` / `cuda`)', '`config.json`, `utils/config.py`'),
    'seed': ('起始随机种子', 'Base random seed', '`config.json`, `utils/config.py`'),
    'n_seeds': (
        '多种子重复次数（UI 启动加载 `config.json` 的 `1`；类默认 `5`；基准测试用 `5`）',
        'Number of random seeds (UI loads `1` from `config.json`; `TrainConfig` defaults to `5`; benchmarks use `5`)',
        '`config.json`, `utils/config.py`',
    ),
    'patience': ('XGBoost 早停轮数（保留配置项）', 'XGBoost early-stopping rounds', '`config.json`, `utils/config.py`'),
    'norm_method': ('容量归一化方式（`rated` / `minmax` / `zscore`）', 'Capacity scaling method (`rated` / `minmax` / `zscore`)', '`config.json`, `utils/config.py`'),
    'n_estimators': ('树模型集成数量（XGBoost / RF）', 'Number of trees (XGBoost / RF)', '`config.json`, `utils/config.py`'),
    'learning_rate': ('XGBoost 学习率', 'XGBoost learning rate', '`config.json`, `utils/config.py`'),
    'max_depth': ('树最大深度（XGBoost / RF）', 'Maximum tree depth (XGBoost / RF)', '`config.json`, `utils/config.py`'),
    'subsample': ('XGBoost 样本采样比例', 'XGBoost row subsample ratio', '`config.json`, `utils/config.py`'),
    'colsample_bytree': ('XGBoost 特征采样比例', 'XGBoost column subsample ratio', '`config.json`, `utils/config.py`'),
    'min_samples_leaf': ('RF 叶子节点最小样本数', 'RF minimum samples per leaf', '`config.json`, `utils/config.py`'),
    'max_features': ('RF 分裂最大特征比例', 'RF max features ratio', '`config.json`, `utils/config.py`'),
    'rnn_lr': ('深度学习 Adam 学习率（仅 `TrainConfig`）', 'Deep-learning Adam learning rate (`TrainConfig` only)', '`utils/config.py`'),
    'rnn_dropout': ('深度学习 Dropout 比例（仅 `TrainConfig`）', 'Deep-learning dropout rate (`TrainConfig` only)', '`utils/config.py`'),
    'feature_columns': ('输入特征列（默认仅容量，保持纯自回归）', 'Input feature columns (capacity-only autoregression by default)', '`config.json`, `utils/config.py`'),
    'eol_debounce': (
        'EOL 连续低于阈值确认循环数（仅 `TrainConfig` / `core/result_semantics.py`）',
        'Consecutive cycles below threshold for EOL confirmation (`TrainConfig` / `core/result_semantics.py`)',
        '`utils/config.py`, `core/result_semantics.py`',
    ),
    'adapter_type': ('默认数据适配器（`CALCE` / `NASA`）', 'Default data adapter (`CALCE` / `NASA`)', '`config.json`, `utils/config.py`'),
    'cc_step': ('CALCE 恒流充电工步序号', 'CALCE constant-current charge step index', '`config.json`, `utils/config.py`'),
    'cv_step': ('CALCE 恒压充电工步序号', 'CALCE constant-voltage charge step index', '`config.json`, `utils/config.py`'),
    'discharge_step': ('CALCE 放电工步序号', 'CALCE discharge step index', '`config.json`, `utils/config.py`'),
    'outlier_mode': (
        '离群点处理：UI/评估运行时由 `TrainConfig` 与 `ui/worker.py` 传入 `chunked`；直接调用 `adapters.py`/`dataload.py` 未传参时签名默认为 `mark`',
        'Outlier handling: UI/evaluation runtime passes `chunked` via `TrainConfig` and `ui/worker.py`; direct calls to `adapters.py`/`dataload.py` default to `mark` in function signatures',
        '`config.json`, `utils/config.py`, `ui/worker.py`, `core/adapters.py`',
    ),
    'backbone': ('神经网络主干（`default` / `Transformer` / `DeTransformer`）', 'Neural backbone (`default` / `Transformer` / `DeTransformer`)', '`config.json`, `utils/config.py`, `core/model_factory.py`'),
    'num_layers': ('循环/Transformer 层数', 'Number of recurrent / Transformer layers', '`config.json`, `utils/config.py`'),
    'nhead': ('Transformer 注意力头数', 'Number of Transformer attention heads', '`config.json`, `utils/config.py`'),
    'transformer_k': ('DeTransformer 单变量通道复制系数 K', 'DeTransformer univariate channel replication factor K', '`config.json`, `utils/config.py`'),
    'alpha': ('DeTransformer 自编码器重构损失权重 α', 'DeTransformer autoencoder reconstruction loss weight α', '`config.json`, `utils/config.py`'),
    'noise_level': ('DeTransformer 自编码器输入噪声强度', 'DeTransformer autoencoder input noise level', '`config.json`, `utils/config.py`'),
    'weight_decay': ('深度学习 Adam 权重衰减', 'Deep-learning Adam weight decay', '`config.json`, `utils/config.py`'),
    'prediction_mode': (
        'UI 默认展示指标口径：`one_step`（一步预测拟合指标 + 递归 RUL/RE）；可选 `rolling`',
        'UI headline prediction mode: `one_step` (one-step fit metrics + recursive RUL/RE); optional `rolling`',
        '`config.json`, `utils/config.py`, `core/train.py`',
    ),
}


def _format_value(value):
    if isinstance(value, (list, tuple)):
        return f'`{list(value)!r}`'
    if value is None:
        return '`None`'
    if isinstance(value, str):
        return f'`{value}`'
    return f'`{value}`'


def _signature_outlier_defaults():
    dataload_default = inspect.signature(load_battery_from_paths).parameters['outlier_mode'].default
    calce_default = inspect.signature(CALCEAdapter.load_battery_data).parameters['outlier_mode'].default
    nasa_default = inspect.signature(NASAAdapter.load_battery_data).parameters['outlier_mode'].default
    return {
        'load_battery_from_paths': dataload_default,
        'CALCEAdapter': calce_default,
        'NASAAdapter': nasa_default,
    }


def collect_defaults(root: Path = ROOT):
    """收集 config.json、TrainConfig 与底层签名默认值。"""
    config_path = root / 'config.json'
    config_json = json.loads(config_path.read_text(encoding='utf-8'))
    defaults_obj = TrainConfig()

    rows = []
    for field in fields(TrainConfig):
        cls_default = getattr(defaults_obj, field.name)
        if field.name == 'eol_debounce':
            cls_default = DEFAULT_DEBOUNCE_CYCLES
        has_json = field.name in config_json
        json_value = config_json[field.name] if has_json else cls_default
        rows.append({
            'name': field.name,
            'runtime_value': json_value,
            'in_config_json': has_json,
            'class_default': cls_default,
        })
    return rows, _signature_outlier_defaults()


def render_defaults_block(lang: str = 'zh', root: Path = ROOT) -> str:
    """渲染用于插入 README 标记之间的默认参数表。"""
    rows, sig_defaults = collect_defaults(root)
    if lang == 'en':
        lines = [
            '> Auto-generated from `config.json` and `utils/config.py::TrainConfig` via `python tools/sync_readme_defaults.py` (`--check` enforced in CI).',
            '',
            '| Parameter | Runtime Default (`config.json` / UI) | `TrainConfig` Default | Notes & Code Location |',
            '|---|---|---|---|',
        ]
        for row in rows:
            name = row['name']
            _, note_en, loc = FIELD_NOTES.get(name, (name, name, '`utils/config.py`'))
            runtime_str = _format_value(row['runtime_value'])
            if not row['in_config_json']:
                runtime_str += ' *(via `TrainConfig`)*'
            cls_str = _format_value(row['class_default'])
            lines.append(f'| `{name}` | {runtime_str} | {cls_str} | {note_en} ({loc}) |')
        lines.extend([
            '',
            (
                '> **Note on `outlier_mode` runtime resolution**: `config.json` and `TrainConfig` default to `chunked`, '
                f'and `ui/worker.py` passes `config.outlier_mode` (`chunked`) at runtime. Function signatures in '
                f'`core/dataload.py` (`{sig_defaults["load_battery_from_paths"]}`), '
                f'`core/adapters.py::CALCEAdapter` (`{sig_defaults["CALCEAdapter"]}`), and '
                f'`core/adapters.py::NASAAdapter` (`{sig_defaults["NASAAdapter"]}`) keep `mark` as their direct-call default.'
            ),
        ])
        return '\n'.join(lines)

    lines = [
        '> 本表由 `python tools/sync_readme_defaults.py` 自动从 `config.json` 与 `utils/config.py::TrainConfig` 生成（CI 通过 `--check` 校验一致性）。',
        '',
        '| 参数 | 实际运行时默认值 (`config.json` / UI) | `TrainConfig` 类默认值 | 说明与代码位置 |',
        '|---|---|---|---|',
    ]
    for row in rows:
        name = row['name']
        note_zh, _, loc = FIELD_NOTES.get(name, (name, name, '`utils/config.py`'))
        runtime_str = _format_value(row['runtime_value'])
        if not row['in_config_json']:
            runtime_str += ' *（继承自 `TrainConfig`）*'
        cls_str = _format_value(row['class_default'])
        lines.append(f'| `{name}` | {runtime_str} | {cls_str} | {note_zh}（{loc}） |')
    lines.extend([
        '',
        (
            f'> **关于 `outlier_mode` 的实际调用路径**：`config.json` 与 `TrainConfig` 默认均为 `chunked`，'
            f'UI 与训练线程 `ui/worker.py` 运行时显式传入 `config.outlier_mode`，因此**实际运行走 `chunked`**；'
            f'仅当绕过 `TrainConfig` 直接调用 `core/dataload.py`（`{sig_defaults["load_battery_from_paths"]}`）、'
            f'`CALCEAdapter.load_battery_data`（`{sig_defaults["CALCEAdapter"]}`）或 '
            f'`NASAAdapter.load_battery_data`（`{sig_defaults["NASAAdapter"]}`）且不传参时，才使用函数签名默认值 `mark`。'
        ),
    ])
    return '\n'.join(lines)


def _replace_marker_block(text: str, replacement: str) -> str:
    if BEGIN_MARKER not in text or END_MARKER not in text:
        raise ValueError(f'缺少标记 {BEGIN_MARKER} / {END_MARKER}')
    before, rest = text.split(BEGIN_MARKER, 1)
    _, after = rest.split(END_MARKER, 1)
    return f'{before}{BEGIN_MARKER}\n{replacement}\n{END_MARKER}{after}'


def _extract_marker_block(text: str) -> str | None:
    if BEGIN_MARKER not in text or END_MARKER not in text:
        return None
    _, rest = text.split(BEGIN_MARKER, 1)
    current, _ = rest.split(END_MARKER, 1)
    return current.strip('\r\n')


def check_readme_defaults(root: Path = ROOT) -> list[str]:
    """检查中英文 README 的默认参数表是否与代码一致，返回问题列表。"""
    problems = []
    targets = (
        ('README.md', 'zh'),
        ('README_EN.md', 'en'),
    )
    for filename, lang in targets:
        path = root / filename
        if not path.is_file():
            problems.append(f'缺少文件: {filename}')
            continue
        text = path.read_text(encoding='utf-8')
        current = _extract_marker_block(text)
        if current is None:
            problems.append(f'{filename} 缺少 {BEGIN_MARKER} / {END_MARKER} 标记')
            continue
        expected = render_defaults_block(lang=lang, root=root).strip('\r\n')
        if current.replace('\r\n', '\n') != expected.replace('\r\n', '\n'):
            problems.append(f'{filename} 默认参数表与 config.json / utils/config.py 不一致')
    return problems


def sync_readme_defaults(root: Path = ROOT) -> list[Path]:
    """更新 README.md 与 README_EN.md 中的默认参数表。"""
    updated = []
    for filename, lang in (('README.md', 'zh'), ('README_EN.md', 'en')):
        path = root / filename
        text = path.read_text(encoding='utf-8')
        block = render_defaults_block(lang=lang, root=root)
        new_text = _replace_marker_block(text, block)
        if new_text != text:
            path.write_text(new_text, encoding='utf-8')
            updated.append(path)
    return updated


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='同步或校验 README 默认参数表')
    parser.add_argument(
        '--check', action='store_true',
        help='只检查 README 是否与代码/config.json 一致，不一致返回非 0',
    )
    args = parser.parse_args(argv)

    if args.check:
        problems = check_readme_defaults(ROOT)
        if problems:
            for item in problems:
                print(f'ERROR: {item}', file=sys.stderr)
            return 1
        print('README 默认参数表与代码/config.json 一致')
        return 0

    updated = sync_readme_defaults(ROOT)
    if updated:
        for path in updated:
            print(f'已更新 {path.name}')
    else:
        print('README 默认参数表无需更新')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
