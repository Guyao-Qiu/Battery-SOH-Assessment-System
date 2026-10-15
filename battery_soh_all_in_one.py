# -*- coding: utf-8 -*-
# ===========================================================================
#  Battery SOH Assessment System —— 单文件整合版 (All-in-One)
# ===========================================================================
#  本文件由 scripts/build_all_in_one.py 自动生成，请勿手工编辑。
#  生成时间: 2026-10-15 14:23:49
#  内嵌模块: 41 个（原 core/ models/ ui/ utils/ 全部源码）
#
#  运行方式:
#      python battery_soh_all_in_one.py
#
#  依赖（需自行安装）:
#      PyQt6 numpy pandas matplotlib torch scikit-learn xgboost scipy joblib openpyxl
#
#  行为说明:
#      * 内嵌模块在运行时按原名（core.xxx / ui.xxx / ...）注册进 sys.modules，
#        因此模块间导入（含相对导入）与多文件版本完全一致，逻辑零改动。
#      * 静态资源（SOH.ico、assets/）与初始 config.json 以 base64 内嵌；
#        脚本同级目录已有同名文件时优先使用本地文件，绝不覆盖。
#      * config.json 与 outputs/ 始终落在脚本所在目录，配置与报告可持久化。
#      * 自检模式: python battery_soh_all_in_one.py --check
# ===========================================================================

import atexit as _atexit
import base64 as _base64
import os as _os
import shutil as _shutil
import sys as _sys
import tempfile as _tempfile
import types as _types
from pathlib import Path as _Path

if _sys.version_info < (3, 10):
    _sys.stderr.write(
        '本程序需要 Python 3.10 或更高版本，当前为 %s\n' % _sys.version.split()[0])
    raise SystemExit(1)

_BASE_DIR = _Path(_os.path.dirname(_os.path.abspath(__file__)))
_PACKAGE_NAMES = ('core', 'models', 'ui', 'utils')

# ---------------------------------------------------------------------------
# 内嵌静态资源（base64）
# ---------------------------------------------------------------------------
_EMBEDDED_STATIC = {
    'SOH.ico': (
        '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'
        'kUQVBPTV6r4AAAAASUVORK5CYII='
    ),
    'assets/icons/combo-down-arrow.svg': (
        'PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMiIgaGVpZ2h0'
        'PSI4IiB2aWV3Qm94PSIwIDAgMTIgOCIgZmlsbD0ibm9uZSI+CiAgPHBhdGggZD0iTTEuNSAxLjVM'
        'NiA2TDEwLjUgMS41IiBzdHJva2U9IiMzMTVCNUEiIHN0cm9rZS13aWR0aD0iMS41IiBzdHJva2Ut'
        'bGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiLz4KPC9zdmc+Cg=='
    ),
}

_EMBEDDED_CONFIG = (
        'ew0KICAicmF0ZWRfY2FwYWNpdHkiOiAyLjAsDQogICJ0aHJlc2hvbGRfcmF0aW8iOiAwLjcsDQog'
        'ICJ2b2x0YWdlX3VwcGVyIjogMy44LA0KICAidm9sdGFnZV9sb3dlciI6IDMuNCwNCiAgIndpbmRv'
        'd19zaXplIjogMTYsDQogICJlcG9jaHMiOiAxMDAsDQogICJoaWRkZW5fZGltIjogNjQsDQogICJz'
        'ZWVkIjogMywNCiAgIm5fc2VlZHMiOiAxLA0KICAibW9kZSI6ICJSRiIsDQogICJtZXRyaWMiOiAi'
        'TUFFIiwNCiAgImRldmljZSI6ICJHUFUgKENVREEpIiwNCiAgIm5vcm1fbWV0aG9kIjogIumineWu'
        'muWuuemHj+W9kuS4gOWMliIsDQogICJuX2VzdGltYXRvcnMiOiAxMDAsDQogICJsZWFybmluZ19y'
        'YXRlIjogMC4wNSwNCiAgIm1heF9kZXB0aCI6IDYsDQogICJzdWJzYW1wbGUiOiAxLjAsDQogICJj'
        'b2xzYW1wbGVfYnl0cmVlIjogMS4wLA0KICAibWluX3NhbXBsZXNfbGVhZiI6IDEsDQogICJtYXhf'
        'ZmVhdHVyZXMiOiAxLjAsDQogICJwYXRpZW5jZSI6IDIwLA0KICAiYWRhcHRlcl90eXBlIjogIk5B'
        'U0EiLA0KICAiY2Nfc3RlcCI6IG51bGwsDQogICJjdl9zdGVwIjogbnVsbCwNCiAgImRpc2NoYXJn'
        'ZV9zdGVwIjogbnVsbA0KfQ=='
)

# ---------------------------------------------------------------------------
# 运行时装配：把内嵌源码还原成模块并注册进 sys.modules
# ---------------------------------------------------------------------------
_ASSET_ROOT_MODULES = {
    'ui.style': 'ui/style.py',
    'utils.icon_generator': 'utils/icon_generator.py',
    'battery_soh_app': 'battery_soh_app.py',
}

_ASSET_ROOT_CACHE = None
_TEMP_ASSET_DIR = None


def _cleanup_temp_assets():
    global _TEMP_ASSET_DIR
    if _TEMP_ASSET_DIR:
        _shutil.rmtree(_TEMP_ASSET_DIR, ignore_errors=True)
        _TEMP_ASSET_DIR = None


def _ensure_config_file():
    # 首次运行时把内嵌的初始配置释放到脚本同级目录；已存在则绝不覆盖
    target = _BASE_DIR / 'config.json'
    if not target.is_file():
        try:
            target.write_bytes(_base64.b64decode(_EMBEDDED_CONFIG))
        except OSError:
            pass
    return target


def _asset_root():
    # 脚本同级目录已有静态资源就直接用；否则释放到临时目录
    global _ASSET_ROOT_CACHE, _TEMP_ASSET_DIR
    if _ASSET_ROOT_CACHE is not None:
        return _ASSET_ROOT_CACHE
    if all((_BASE_DIR / rel).is_file() for rel in _EMBEDDED_STATIC):
        _ASSET_ROOT_CACHE = _BASE_DIR
        return _ASSET_ROOT_CACHE
    temp_dir = _tempfile.mkdtemp(prefix='battery_soh_assets_')
    for rel, payload in _EMBEDDED_STATIC.items():
        target = _Path(temp_dir) / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(_base64.b64decode(payload))
    _TEMP_ASSET_DIR = temp_dir
    _atexit.register(_cleanup_temp_assets)
    _ASSET_ROOT_CACHE = _Path(temp_dir)
    return _ASSET_ROOT_CACHE


def _virtual_module_file(name):
    # 让基于 __file__ 的资源定位在单文件环境下依然指向正确位置
    special = _ASSET_ROOT_MODULES.get(name)
    if special is not None:
        return str(_asset_root() / special)
    if name in _PACKAGE_NAMES:
        return str(_BASE_DIR / name / '__init__.py')
    return str(_BASE_DIR / (name.replace('.', '/') + '.py'))


def _register_module(name, source):
    module = _types.ModuleType(name)
    filename = _virtual_module_file(name)
    module.__file__ = filename
    if name in _PACKAGE_NAMES:
        module.__package__ = name
        module.__path__ = [str(_Path(filename).parent)]
    else:
        module.__package__ = name.rpartition('.')[0]
    _sys.modules[name] = module

    # 注册包壳时先把已就绪的子模块挂到包上（在 __init__.py 执行前），
    # 以还原标准导入机制「导入子模块会 setattr 到父包」的行为
    if name in _PACKAGE_NAMES:
        prefix = name + '.'
        for mod_name, mod_obj in list(_sys.modules.items()):
            if mod_name.startswith(prefix):
                child = mod_name[len(prefix):]
                if child and '.' not in child:
                    setattr(module, child, mod_obj)

    try:
        exec(compile(source, filename, 'exec'), module.__dict__)
    except BaseException:
        # 普通模块失败即移除，避免留下半成品；包壳保留（子模块仍可独立导入）
        if name not in _PACKAGE_NAMES:
            _sys.modules.pop(name, None)
        raise

    parent_name, _, child = name.rpartition('.')
    if parent_name and parent_name in _sys.modules:
        setattr(_sys.modules[parent_name], child, module)
    return module


def _load_all_modules():
    # 迭代加载：依赖尚未就绪的模块留到下一轮，直到全部成功或确认失败
    pending = list(_MODULE_SOURCES.items())
    while pending:
        remaining = []
        errors = {}
        for name, source in pending:
            try:
                _register_module(name, source)
            except ImportError as exc:
                missing = getattr(exc, 'name', None)
                if missing and missing in _MODULE_SOURCES:
                    remaining.append((name, source))
                    errors[name] = exc
                    continue
                raise
        if not remaining:
            return
        if len(remaining) == len(pending):
            raise errors[remaining[0][0]]
        pending = remaining


def _run_self_check():
    try:
        _sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    _load_all_modules()
    print('[check] 内嵌模块加载成功: %d 个' % len(_MODULE_SOURCES))
    print('[check] 资源根目录: %s' % _asset_root())
    print('[check] 配置文件: %s' % _ensure_config_file())
    from ui.main_window import MainWindow  # noqa: F401
    print('[check] ui.main_window.MainWindow 可导入')
    print('[check] 全部通过')



# ---------------------------------------------------------------------------
# 内嵌模块源码
# ---------------------------------------------------------------------------
_MODULE_SOURCES = {}

# ---- theme_tokens.py ----
_MODULE_SOURCES['theme_tokens'] = (
    '"""唯一的"颜色真相来源"（浅色 宣纸 / 深色 墨夜）。\n'
    '\n'
    '放在工程根目录，**不要**放进 ``ui/`` 或 ``utils/``：这两个包的 ``__init__.py``\n'
    '会连带导入 matplotlib / torch，而启动闪屏需要在重库加载**之前**就拿到颜色，\n'
    '否则「闪屏秒开」就被破坏了。\n'
    '\n'
    '本模块只依赖标准库（纯字典 + 纯函数），不 import 任何第三方库。\n'
    '\n'
    '设计语言：宣纸水墨\n'
    '- 事实用中性墨色，模型输出用黛青强调，失效用朱砂；\n'
    '- 任何状态都要有**非颜色**的冗余（图标 / 文字），见 ``ui/style.py`` 的 QSS。\n'
    '"""\n'
    '\n'
    '# ── 浅色：宣纸 ────────────────────────────────────────────────\n'
    'LIGHT = {\n'
    '    # 背景层级\n'
    "    'bg_deep': '#E8E0D1', 'bg_base': '#F3EDE0', 'bg_surface': '#FAF6EC',\n"
    "    'bg_elevated': '#E1D8C8', 'bg_hover': '#D6CDBC', 'bg_focus': '#FFFDF7',\n"
    '    # 描边\n'
    "    'border': '#7C8179', 'border_soft': '#C5BBAA',\n"
    '    # 文字\n'
    "    'text': '#202724', 'text_muted': '#4F5953', 'text_dim': '#6B726C',\n"
    '    # 主强调：黛青\n'
    "    'primary': '#315B5A', 'primary_d': '#244743', 'primary_l': '#52766E',\n"
    "    'on_accent': '#FFF9ED',\n"
    '    # 语义状态\n'
    "    'success': '#4F6B4F', 'success_d': '#3C533C', 'success_l': '#3F6045',\n"
    "    'warning': '#7A4E22', 'danger': '#9E3D2F', 'danger_d': '#7F2F26',\n"
    "    'on_danger': '#FFF9ED',\n"
    '    # 兼容旧 token（ui/style.py 的 COLORS 键名）\n'
    "    'paper': '#F3EDE0', 'ink': '#202724', 'cinnabar': '#9E3D2F',\n"
    "    'spin_selection': '#76563A', 'on_selection': '#FFF9ED',\n"
    "    'shadow': 'rgba(32, 39, 36, 0.14)',\n"
    '    # 图表专用\n'
    "    'chart_bg': '#F7F1E5', 'chart_measured': '#202724',\n"
    "    'chart_forecast': '#2B7A75', 'chart_threshold': '#9E3D2F',\n"
    "    'chart_grid': '#C5BBAA', 'chart_spine': '#7C8179',\n"
    "    'chart_band_alpha': 0.18,\n"
    '    # 多电池叠加分类色：对图表底 ≥ 3.57:1，最小两两 ΔE 28.5（含色觉缺陷模拟）\n'
    "    'chart_series': ['#1F4E9E', '#C04F00', '#00805A', '#0F8C99', '#202724'],\n"
    '}\n'
    '\n'
    '# ── 深色：墨夜（不是简单反色，底偏冷青灰，与宣纸呼应） ──────────\n'
    'DARK = {\n'
    "    'bg_deep': '#101415', 'bg_base': '#151B1C', 'bg_surface': '#1B2224',\n"
    "    'bg_elevated': '#232C2E', 'bg_hover': '#2B3638', 'bg_focus': '#202829',\n"
    "    'border': '#687776', 'border_soft': '#323E3F',\n"
    "    'text': '#E9E4D8', 'text_muted': '#A9B2AD', 'text_dim': '#7C8682',\n"
    "    'primary': '#6FB3A8', 'primary_d': '#4C8F85', 'primary_l': '#8CC7BD',\n"
    "    'on_accent': '#0F1A19',\n"
    "    'success': '#86B58B', 'success_d': '#6FA076', 'success_l': '#86B58B',\n"
    "    'warning': '#D9A441', 'danger': '#E07A68', 'danger_d': '#C7634F',\n"
    "    'on_danger': '#0F1A19',\n"
    "    'paper': '#151B1C', 'ink': '#E9E4D8', 'cinnabar': '#E07A68',\n"
    "    'spin_selection': '#C9A87C', 'on_selection': '#0F1A19',\n"
    "    'shadow': 'rgba(0, 0, 0, 0.45)',\n"
    "    'chart_bg': '#151B1C', 'chart_measured': '#E9E4D8',\n"
    "    'chart_forecast': '#6FB3A8', 'chart_threshold': '#E07A68',\n"
    "    'chart_grid': '#2B3638', 'chart_spine': '#687776',\n"
    "    'chart_band_alpha': 0.28,\n"
    "    'chart_series': ['#8FA8F0', '#FF7A66', '#F2D16B', '#D894B8', '#E9E4D8'],\n"
    '}\n'
    '\n'
    "THEMES = {'light': LIGHT, 'dark': DARK}\n"
    '#: 产品默认外观 = 深色（墨夜）；浅色（宣纸）可选，切换后由 QSettings 记住。\n'
    "DEFAULT_THEME = 'dark'\n"
    '\n'
    '#: QSettings 里保存主题用的键名。\n'
    '#: 带版本号是**有意的迁移**：旧版本每次启动都会把当时的默认值（浅色）写进\n'
    '#: ``theme``，于是「改成深色为默认」对老用户不会生效。换用新键后，新默认值\n'
    '#: 能真正落到每个人身上；此后用户自己的选择照常被记住。\n'
    "THEME_SETTINGS_KEY = 'theme_v2'\n"
    '\n'
    '# 图表中文字体回退链：Windows → macOS → Linux。\n'
    '# 注意 matplotlib 对 .ttc 字体登记的家族名可能与系统不同（例如某些环境里\n'
    "# Noto Sans CJK 只登记成 'Noto Sans CJK JP'），所以把几种写法都列上。\n"
    'CJK_FONTS = [\n'
    "    'Microsoft YaHei', 'PingFang SC', 'Noto Sans CJK SC', 'Noto Sans CJK JP',\n"
    "    'Source Han Sans SC', 'WenQuanYi Micro Hei', 'SimHei', 'DejaVu Sans',\n"
    ']\n'
    '\n'
    "LINESTYLES = ['-', '--', '-.', ':']\n"
    "MARKERS = ['o', 's', '^', 'D', 'v']\n"
    '\n'
    '\n'
    'def get_theme(mode):\n'
    '    """按名称取 token；未知名称回退默认主题。"""\n'
    '    return THEMES.get(str(mode).strip().lower(), THEMES[DEFAULT_THEME])\n'
    '\n'
    '\n'
    'def rgba(hex_color, alpha):\n'
    '    """``\'#315B5A\', 0.08`` -> ``\'rgba(49, 91, 90, 0.08)\'``。\n'
    '\n'
    '    QSS 里所有半透明色都用它，不再手写 ``rgba(49, 91, 90, ...)``。\n'
    '    """\n'
    "    h = str(hex_color).lstrip('#')\n"
    '    if len(h) == 3:\n'
    "        h = ''.join(ch * 2 for ch in h)\n"
    '    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))\n'
    "    return f'rgba({r}, {g}, {b}, {alpha})'\n"
    '\n'
    '\n'
    'def _lin(c):\n'
    '    c /= 255.0\n'
    '    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4\n'
    '\n'
    '\n'
    'def luminance(hex_color):\n'
    '    """WCAG 2.1 相对亮度。"""\n'
    "    h = str(hex_color).lstrip('#')\n"
    '    if len(h) == 3:\n'
    "        h = ''.join(ch * 2 for ch in h)\n"
    '    r, g, b = (_lin(int(h[i:i + 2], 16)) for i in (0, 2, 4))\n'
    '    return 0.2126 * r + 0.7152 * g + 0.0722 * b\n'
    '\n'
    '\n'
    'def contrast(fg, bg):\n'
    '    """WCAG 2.1 对比度（1.0–21.0）。"""\n'
    '    hi, lo = sorted((luminance(fg), luminance(bg)), reverse=True)\n'
    '    return (hi + 0.05) / (lo + 0.05)\n'
    '\n'
    '\n'
    'def usable_colors(palette, bg, minimum=3.0):\n'
    '    """图形对象（线条 / 标记）按 WCAG 需要 ≥ 3:1；只保留满足要求的颜色。"""\n'
    '    return [c for c in palette if contrast(c, bg) >= minimum]\n'
    '\n'
    '\n'
    'def series_style(index, tokens):\n'
    '    """前 5 条线靠颜色区分；更多条时轮换线型 / 标记，色觉缺陷下也能分辨。"""\n'
    "    colors = tokens['chart_series']\n"
    '    return {\n'
    "        'color': colors[index % len(colors)],\n"
    "        'linestyle': LINESTYLES[(index // len(colors)) % len(LINESTYLES)],\n"
    "        'marker': MARKERS[index % len(MARKERS)],\n"
    "        'markersize': 3,\n"
    '    }\n'
)

# ---- utils/paths.py ----
_MODULE_SOURCES['utils.paths'] = (
    '"""Stable runtime paths independent of the process working directory."""\n'
    '\n'
    'from pathlib import Path\n'
    '\n'
    '\n'
    'PROJECT_ROOT = Path(__file__).resolve().parents[1]\n'
    "CONFIG_FILE = PROJECT_ROOT / 'config.json'\n"
    "OUTPUTS_DIR = PROJECT_ROOT / 'outputs'\n"
    'LOG_DIR = OUTPUTS_DIR\n'
    'MODEL_DIR = OUTPUTS_DIR\n'
    "FIGURE_DIR = OUTPUTS_DIR / 'figures'\n"
    "REPORT_DIR = OUTPUTS_DIR / 'runs'\n"
)

# ---- utils/logger.py ----
_MODULE_SOURCES['utils.logger'] = (
    'import logging\n'
    'import os\n'
    'from logging.handlers import RotatingFileHandler\n'
    'from utils.paths import LOG_DIR\n'
    '\n'
    '\n'
    'def setup_logger(log_dir=None):\n'
    '    log_dir = os.fspath(LOG_DIR if log_dir is None else log_dir)\n'
    '    os.makedirs(log_dir, exist_ok=True)\n'
    "    logger = logging.getLogger('battery_soh')\n"
    '    logger.setLevel(logging.INFO)\n'
    '    if logger.handlers:\n'
    '        return logger\n'
    '\n'
    '    fh = RotatingFileHandler(\n'
    "        os.path.join(log_dir, 'app.log'), encoding='utf-8',\n"
    '        maxBytes=10 * 1024 * 1024, backupCount=5\n'
    '    )\n'
    '    fh.setLevel(logging.INFO)\n'
    "    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')\n"
    '    fh.setFormatter(formatter)\n'
    '    logger.addHandler(fh)\n'
    '\n'
    '    ch = logging.StreamHandler()\n'
    '    ch.setLevel(logging.INFO)\n'
    '    ch.setFormatter(formatter)\n'
    '    logger.addHandler(ch)\n'
    '\n'
    '    return logger\n'
)

# ---- utils/config.py ----
_MODULE_SOURCES['utils.config'] = (
    'import os\n'
    'import json\n'
    'import random\n'
    'import numpy as np\n'
    'import torch\n'
    'from dataclasses import dataclass, asdict, fields\n'
    'from typing import Optional\n'
    'from utils.paths import CONFIG_FILE\n'
    '\n'
    '\n'
    "SUPPORTED_MODELS = ('RNN', 'GRU', 'LSTM', 'XGBoost', 'RF')\n"
    '_MODEL_ALIASES = {name.lower(): name for name in SUPPORTED_MODELS}\n'
    '\n'
    '\n'
    'def normalize_model_name(value):\n'
    '    key = str(value).strip().lower()\n'
    '    if key not in _MODEL_ALIASES:\n'
    "        supported = '、'.join(SUPPORTED_MODELS)\n"
    "        raise ValueError(f'不支持的模型类型: {value}；可选值为 {supported}')\n"
    '    return _MODEL_ALIASES[key]\n'
    '\n'
    '\n'
    'def normalize_norm_method(value):\n'
    '    key = str(value).strip().lower()\n'
    '    aliases = {\n'
    "        'rated': 'rated',\n"
    "        '额定容量归一化': 'rated',\n"
    "        'minmax': 'minmax',\n"
    "        'zscore': 'zscore',\n"
    '    }\n'
    '    if key not in aliases:\n'
    "        raise ValueError(f'不支持的归一化方式: {value}')\n"
    '    return aliases[key]\n'
    '\n'
    '\n'
    'def normalize_metric_name(value):\n'
    '    key = str(value).strip().lower()\n'
    '    aliases = {\n'
    "        'rmse': 'rmse', 'mae': 'mae', 'r2': 'r2', 'r²': 'r2',\n"
    "        'pearson': 'pearson', 're': 're', 'all': 'all', '全部': 'all',\n"
    '    }\n'
    '    if key not in aliases:\n'
    "        raise ValueError(f'不支持的评估指标: {value}')\n"
    '    return aliases[key]\n'
    '\n'
    '\n'
    '# ── 配置里只存"规范键"，界面文本只在界面层转换（改进方案 A11） ──────\n'
    '\n'
    "DEVICE_UI = {'cpu': 'CPU', 'cuda': 'GPU (CUDA)'}\n"
    'NORM_UI = {\n'
    "    'rated': '额定容量归一化',\n"
    "    'zscore': 'Z-score 标准化',\n"
    "    'minmax': 'Min-Max 归一化',\n"
    '}\n'
    "ADAPTER_UI = {'CALCE': 'CALCE (.xlsx/.csv)', 'NASA': 'NASA (.mat)'}\n"
    "THEME_UI = {'light': '宣纸（浅色）', 'dark': '墨夜（深色）'}\n"
    '\n'
    '_DEVICE_ALIASES = {\n'
    "    'cpu': 'cpu',\n"
    "    'cuda': 'cuda',\n"
    "    'gpu': 'cuda',\n"
    "    'gpu (cuda)': 'cuda',\n"
    '}\n'
    '\n'
    '\n'
    "def normalize_device(value, default='cpu'):\n"
    '    """``\'GPU (CUDA)\'`` / ``\'gpu\'`` / ``\'cuda\'`` -> ``\'cuda\'``；未知值回退 default。\n'
    '\n'
    '    旧配置文件把界面文本直接写进了 JSON，所以这里必须同时接受两种写法。\n'
    '    """\n'
    '    return _DEVICE_ALIASES.get(str(value).strip().lower(), default)\n'
    '\n'
    '\n'
    'def to_ui(mapping, key):\n'
    '    """规范键 -> 界面文本。"""\n'
    '    return mapping.get(key, next(iter(mapping.values())))\n'
    '\n'
    '\n'
    'def from_ui(mapping, text, default=None):\n'
    '    """界面文本 -> 规范键；也接受已经是规范键的输入（兼容旧配置文件）。"""\n'
    '    text = str(text).strip()\n'
    '    if text in mapping:\n'
    '        return text\n'
    '    for key, shown in mapping.items():\n'
    '        if shown == text:\n'
    '            return key\n'
    '    return default if default is not None else next(iter(mapping))\n'
    '\n'
    '\n'
    '#: 多特征输入的候选列（capacity 永远是第 0 列 / 预测目标）\n'
    'FEATURE_OPTIONS = {\n'
    "    'capacity': '容量（必选）',\n"
    "    'dq_v': '电压窗口放电容量 dq_v',\n"
    "    'CCCT': '恒流充电时长 CCCT',\n"
    "    'CVCT': '恒压充电时长 CVCT',\n"
    "    'resistance': '内阻 resistance',\n"
    '}\n'
    "DEFAULT_FEATURES = ('capacity',)\n"
    '\n'
    '\n'
    'def normalize_feature_list(value):\n'
    '    """把特征配置规范成元组；容量永远在内、且排第一。"""\n'
    '    if value is None:\n'
    '        return DEFAULT_FEATURES\n'
    '    if isinstance(value, str):\n'
    "        items = [item for item in value.replace('，', ',').split(',') if item.strip()]\n"
    '    else:\n'
    '        items = list(value)\n'
    '    normalized = []\n'
    '    for item in items:\n'
    '        name = str(item).strip()\n'
    '        if name in FEATURE_OPTIONS and name not in normalized:\n'
    '            normalized.append(name)\n'
    "    if 'capacity' not in normalized:\n"
    "        normalized.insert(0, 'capacity')\n"
    '    else:\n'
    "        normalized.remove('capacity')\n"
    "        normalized.insert(0, 'capacity')\n"
    '    return tuple(normalized)\n'
    '\n'
    '\n'
    '_CONFIG_ALIASES = {\n'
    "    'mode': ('model', 'MODEL'),\n"
    "    'threshold_ratio': ('THRESHOLD_RATIO',),\n"
    "    'window_size': ('Feature Size',),\n"
    "    'seed': ('random_seed',),\n"
    "    'epochs': ('num_epochs',),\n"
    "    'norm_method': ('normalization',),\n"
    "    'n_estimators': ('xgb_n_estimators', 'rf_n_estimators'),\n"
    "    'learning_rate': ('xgb_learning_rate',),\n"
    "    'max_depth': ('xgb_max_depth', 'rf_max_depth'),\n"
    "    'subsample': ('xgb_subsample',),\n"
    "    'colsample_bytree': ('xgb_colsample_bytree',),\n"
    "    'min_samples_leaf': ('rf_min_samples_leaf',),\n"
    "    'max_features': ('rf_max_features',),\n"
    "    'patience': ('early_stopping_rounds', 'rf_patience'),\n"
    "    'feature_columns': ('features', 'FEATURES'),\n"
    "    'rnn_lr': ('learning_rate_rnn',),\n"
    "    'eol_debounce': ('failure_debounce', 'debounce'),\n"
    '}\n'
    '\n'
    '\n'
    '@dataclass\n'
    'class TrainConfig:\n'
    '    rated_capacity: float = 1.1\n'
    '    threshold_ratio: float = 0.8\n'
    '    voltage_upper: float = 3.8\n'
    '    voltage_lower: float = 3.4\n'
    '    window_size: int = 64\n'
    '    epochs: int = 100\n'
    '    hidden_dim: int = 64\n'
    "    mode: str = 'RNN'\n"
    "    metric: str = 'rmse'\n"
    "    device: str = 'cpu'\n"
    '    seed: int = 2\n'
    '    n_seeds: int = 5\n'
    '    patience: int = 20\n'
    "    norm_method: str = 'rated'\n"
    '    n_estimators: int = 100\n'
    '    learning_rate: float = 0.1\n'
    '    max_depth: int = 6\n'
    '    subsample: float = 1.0\n'
    '    colsample_bytree: float = 1.0\n'
    '    min_samples_leaf: int = 1\n'
    '    max_features: float = 1.0\n'
    '    # RNN 专用（改进方案 A8：此前学习率写死 0.001，配置里没有这一项）\n'
    '    rnn_lr: float = 0.001\n'
    '    rnn_dropout: float = 0.1\n'
    '    # 多特征输入（改进方案 A5）\n'
    '    feature_columns: tuple = DEFAULT_FEATURES\n'
    '    # 失效判定去抖（改进方案 A12）：需要连续多少个循环低于阈值才算失效。\n'
    '    # 1 = 旧的「首次下穿即失效」，保持向后兼容；3 = 抗单点噪声。\n'
    '    eol_debounce: int = 1\n'
    '    # 数据源配置\n'
    "    adapter_type: str = 'CALCE'\n"
    '    cc_step: Optional[int] = None\n'
    '    cv_step: Optional[int] = None\n'
    '    discharge_step: Optional[int] = None\n'
    '\n'
    '    def __post_init__(self):\n'
    '        self.mode = normalize_model_name(self.mode)\n'
    '        self.metric = normalize_metric_name(self.metric)\n'
    '        self.norm_method = normalize_norm_method(self.norm_method)\n'
    "        # A11：旧配置把界面文本（'GPU (CUDA)'）写进 JSON，这里必须规范化\n"
    '        self.device = normalize_device(self.device)\n'
    '        self.feature_columns = normalize_feature_list(self.feature_columns)\n'
    '        # A12：去抖必须是 >=1 的整数；非法值回落到兼容默认 1\n'
    '        try:\n'
    '            self.eol_debounce = max(1, int(self.eol_debounce))\n'
    '        except (TypeError, ValueError):\n'
    '            self.eol_debounce = 1\n'
    '        if self.adapter_type not in ADAPTER_UI:\n'
    "            raise ValueError(f'不支持的数据源适配器: {self.adapter_type}')\n"
    '\n'
    '    def to_dict(self):\n'
    '        data = asdict(self)\n'
    "        data['feature_columns'] = list(self.feature_columns)\n"
    '        return data\n'
    '\n'
    '    @classmethod\n'
    '    def from_dict(cls, data):\n'
    '        if not isinstance(data, dict):\n'
    "            raise ValueError('配置必须是 JSON 对象')\n"
    '        values = {}\n'
    '        for field in fields(cls):\n'
    '            keys = (field.name,) + _CONFIG_ALIASES.get(field.name, ())\n'
    '            for key in keys:\n'
    '                if key in data:\n'
    '                    values[field.name] = data[key]\n'
    '                    break\n'
    '        return cls(**values)\n'
    '\n'
    '\n'
    'def load_config():\n'
    '    if not CONFIG_FILE.exists():\n'
    '        return {}\n'
    '    try:\n'
    "        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:\n"
    '            return json.load(f)\n'
    '    except (json.JSONDecodeError, OSError):\n'
    '        return {}\n'
    '\n'
    '\n'
    'def save_config(data):\n'
    "    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:\n"
    '        json.dump(data, f, ensure_ascii=False, indent=2)\n'
    '\n'
    'def setup_seed(seed, deterministic=None):\n'
    '    """设置随机种子，返回是否达成了**严格**确定性（A12）。\n'
    '\n'
    '    关于 ``PYTHONHASHSEED``：解释器在启动时就读完了它，因此进程内赋值\n'
    '    **对当前进程无效**，只影响之后 spawn 出来的子进程。要真正复现哈希随机化\n'
    '    带来的差异，请在启动前设置环境变量，例如：\n'
    '\n'
    '    ```powershell\n'
    "    $env:PYTHONHASHSEED = '2'; python -X utf8 battery_soh_app.py\n"
    '    ```\n'
    '\n'
    '    ``deterministic``：为 ``True`` 时额外调用\n'
    '    ``torch.use_deterministic_algorithms(True)`` 并设置\n'
    '    ``CUBLAS_WORKSPACE_CONFIG``。后者必须在 **CUDA 上下文创建之前**设好；\n'
    '    如果 CUDA 已经初始化，返回值会是 ``False``，表示本次运行无法保证严格确定性\n'
    '    （而不是悄悄假装已经确定）。\n'
    '    """\n'
    '    np.random.seed(seed)\n'
    '    random.seed(seed)\n'
    '    # 对当前进程无效（解释器启动时已读取），仅对后续子进程生效\n'
    "    os.environ.setdefault('PYTHONHASHSEED', str(seed))\n"
    '    torch.manual_seed(seed)\n'
    '    if torch.cuda.is_available():\n'
    '        torch.cuda.manual_seed(seed)\n'
    '        torch.cuda.manual_seed_all(seed)\n'
    '        torch.backends.cudnn.benchmark = False\n'
    '        torch.backends.cudnn.deterministic = True\n'
    '\n'
    '    if deterministic is None:\n'
    "        deterministic = os.environ.get('SOH_DETERMINISTIC') == '1'\n"
    '    if not deterministic:\n'
    '        return not torch.cuda.is_available()\n'
    '\n'
    '    strict = True\n'
    '    if torch.cuda.is_available():\n'
    '        # cublas 的工作区配置只在其初始化前生效；初始化后再设就没用了\n'
    "        if 'CUBLAS_WORKSPACE_CONFIG' not in os.environ:\n"
    "            os.environ['CUBLAS_WORKSPACE_CONFIG'] = ':4096:8'\n"
    '            strict = not torch.cuda.is_initialized()\n'
    '    try:\n'
    '        torch.use_deterministic_algorithms(True, warn_only=False)\n'
    '    except (RuntimeError, AttributeError):\n'
    '        # 某些算子没有确定性实现，此时退回「尽力而为」并如实返回 False\n'
    '        strict = False\n'
    '    return strict\n'
)

# ---- utils/crash_guard.py ----
_MODULE_SOURCES['utils.crash_guard'] = (
    '"""全局异常兜底：把「闪退」变成「日志 + 一条非阻塞提示」。\n'
    '\n'
    '背景：按 PyQt 的文档行为，回调（包括 ``QThread.run``）里未处理的 Python\n'
    '异常在默认钩子下会触发 ``qFatal()`` 终止进程。项目此前没有安装\n'
    '``sys.excepthook``，所以一个小笔误的后果不是「面板报错」，而是**整个程序闪退**。\n'
    '\n'
    '用法（在创建 ``QApplication`` 之后、创建主窗口之前）::\n'
    '\n'
    '    from utils.crash_guard import install_excepthooks, bridge\n'
    '    install_excepthooks()\n'
    '    bridge.error.connect(window.show_error_toast)\n'
    '"""\n'
    '\n'
    'import contextlib\n'
    'import logging\n'
    'import sys\n'
    'import threading\n'
    'import traceback\n'
    '\n'
    'from PyQt6.QtCore import QObject, pyqtSignal\n'
    '\n'
    '\n'
    'def _logger():\n'
    '    # 延迟取 logger：crash_guard 会被启动引导在重库加载前导入，\n'
    '    # 因此这里不在模块级 import utils.logger（它会拉起 utils 包链）。\n'
    '    try:\n'
    '        from utils.logger import setup_logger\n'
    '        return setup_logger()\n'
    '    except Exception:                     # noqa: BLE001 —— 兜底代码自身不能再抛\n'
    "        return logging.getLogger('battery_soh')\n"
    '\n'
    '\n'
    'class CrashBridge(QObject):\n'
    '    """任何线程里的异常 → 信号 → 主线程弹窗。\n'
    '\n'
    '    不要在子线程里直接创建 QMessageBox，所以统一走信号。\n'
    '    """\n'
    '\n'
    '    error = pyqtSignal(str)\n'
    '\n'
    '\n'
    '#: 进程级单例；启动引导连接它的 ``error`` 信号即可\n'
    'bridge = CrashBridge()\n'
    '\n'
    '\n'
    "def report_exception(exc_type, exc, tb, context='未处理的异常'):\n"
    '    """记录完整 traceback 并发出提示信号。"""\n'
    '    if issubclass(exc_type, KeyboardInterrupt):\n'
    '        return\n'
    '    try:\n'
    '        _logger().error(\n'
    "            '%s\\n%s', context,\n"
    "            ''.join(traceback.format_exception(exc_type, exc, tb)))\n"
    '    except Exception:                     # noqa: BLE001\n'
    '        traceback.print_exception(exc_type, exc, tb)\n'
    '    # 信号未连接 / 已被销毁时也必须静默：这里是崩溃兜底路径，不能再抛异常\n'
    '    with contextlib.suppress(RuntimeError, TypeError):\n'
    "        bridge.error.emit(f'{exc_type.__name__}: {exc}')\n"
    '\n'
    '\n'
    'def install_excepthooks():\n'
    '    """安装主线程与子线程的全局异常钩子。"""\n'
    '    def hook(exc_type, exc, tb):\n'
    '        if issubclass(exc_type, KeyboardInterrupt):\n'
    '            sys.__excepthook__(exc_type, exc, tb)\n'
    '            return\n'
    '        report_exception(exc_type, exc, tb)\n'
    '\n'
    '    sys.excepthook = hook\n'
    '    threading.excepthook = lambda args: hook(\n'
    '        args.exc_type, args.exc_value, args.exc_traceback)\n'
    '    return hook\n'
    '\n'
    '\n'
    "def guarded_run(error_signal=None, log_context='线程异常'):\n"
    '    """装饰器：让 ``QThread.run`` 优雅失败，而不是把异常抛给 Qt。\n'
    '\n'
    '    用法::\n'
    '\n'
    '        class Worker(QThread):\n'
    '            error_signal = pyqtSignal(str)\n'
    '\n'
    '            @guarded_run()\n'
    '            def run(self):\n'
    '                ...\n'
    '    """\n'
    '    def decorator(func):\n'
    '        def wrapper(self, *args, **kwargs):\n'
    '            try:\n'
    '                return func(self, *args, **kwargs)\n'
    '            except Exception as exc:      # noqa: BLE001 —— 线程边界必须兜底\n'
    '                report_exception(type(exc), exc, exc.__traceback__, log_context)\n'
    '                signal = error_signal\n'
    '                if signal is None:\n'
    "                    signal = getattr(self, 'error_signal', None)\n"
    '                if signal is not None:\n'
    '                    with contextlib.suppress(RuntimeError, TypeError):\n'
    "                        signal.emit(f'{type(exc).__name__}: {exc}')\n"
    '                return None\n'
    "        wrapper.__name__ = getattr(func, '__name__', 'run')\n"
    '        wrapper.__doc__ = func.__doc__\n'
    '        return wrapper\n'
    '    return decorator\n'
)

# ---- utils/icon_generator.py ----
_MODULE_SOURCES['utils.icon_generator'] = (
    '"""\n'
    '图标生成器：app 图标 + 各对话框个性化图标 + QMessageBox 统一封装\n'
    '\n'
    '设计原则：\n'
    '  - 颜色只有一个来源：工程根目录的 ``theme_tokens.py``。线条取主题的淡墨色，\n'
    '    状态点取语义色，浅色（宣纸）/ 深色（墨夜）自动跟随，不再自带调色板\n'
    '  - 状态类图标（错误/警告/成功/信息）右下角叠加小色点作为语义提示，\n'
    '    但保持低饱和度，避免抢眼\n'
    '  - 同一图标仅生成一次并缓存，重复调用零开销\n'
    '"""\n'
    'import sys\n'
    '\n'
    'from PyQt6.QtCore import Qt, QRectF, QPointF, QSize\n'
    'from PyQt6.QtGui import (\n'
    '    QPainter, QPen, QBrush, QColor, QLinearGradient, QPainterPath,\n'
    '    QPolygonF, QPixmap, QIcon,\n'
    ')\n'
    'from PyQt6.QtWidgets import QMessageBox\n'
    '\n'
    'from theme_tokens import get_theme\n'
    '\n'
    '\n'
    '# ─── 调色板（token 名，取值全部来自 theme_tokens） ────────────\n'
    '_LINE_STROKE  = 2.2                     # 对话框图标的描边略粗，便于在标题栏中识别\n'
    '_ACCENT_STROKE = 2.4\n'
    '_ACCENT_R     = 4.0                     # 角落小色点半径\n'
    '\n'
    '#: 线条主色所用的 token：淡墨，浅 / 深主题下都不会被背景吞掉。\n'
    "_LINE_COLOR_KEY = 'text_muted'\n"
    '\n'
    '#: 状态点 / 强调色所用的语义 token。\n'
    "_ACCENT_INFO    = 'primary'     # info / 通用\n"
    "_ACCENT_INFO_D  = 'primary_d'   # 次要强调（坐标轴、图表）\n"
    "_ACCENT_SUCCESS = 'success'\n"
    "_ACCENT_WARNING = 'warning'\n"
    "_ACCENT_DANGER  = 'danger'\n"
    "_ACCENT_MODEL   = 'primary_d'   # model / NN\n"
    '\n'
    '#: 本模块记录的主题模式，仅在拿不到 ``ui.style`` 时兜底。\n'
    "_current_theme_mode = 'light'\n"
    '\n'
    '\n'
    'def set_icon_theme(mode):\n'
    '    """设置图标生成器跟随的主题（``\'light\'`` / ``\'dark\'``）。"""\n'
    '    global _current_theme_mode\n'
    '    _current_theme_mode = str(mode).strip().lower()\n'
    '\n'
    '\n'
    'def _tokens():\n'
    '    """当前主题 token：优先问**已加载**的 ``ui.style``。\n'
    '\n'
    '    这里刻意用 ``sys.modules`` 而不是 ``import ui.style``：``ui/__init__.py``\n'
    '    会连带导入 main_window（进而 torch / matplotlib），而图标必须在启动早期\n'
    '    就能画出来，所以本模块不主动触发 ``ui`` 包的导入；``ui.style`` 尚未加载时\n'
    '    回退到 :func:`set_icon_theme` 记录的模式。\n'
    '    """\n'
    "    style = sys.modules.get('ui.style')\n"
    '    if style is not None:\n'
    '        try:\n'
    '            return style.theme_tokens()\n'
    '        except (AttributeError, KeyError, ImportError):\n'
    '            # ui.style 已加载但没有 theme_tokens（例如版本不匹配）时回退\n'
    '            return get_theme(_current_theme_mode)\n'
    '    return get_theme(_current_theme_mode)\n'
    '\n'
    '\n'
    'def _color(token):\n'
    '    """token 名 → QColor（token 里的 ``\'#RRGGBB\'`` 可直接构造 QColor）。"""\n'
    '    return QColor(_tokens()[token])\n'
    '\n'
    '\n'
    '# ─── 1. App 图标（电池 + 心电图风格的 SOH 曲线） ─────────────\n'
    'def _create_battery_icon(size=256):\n'
    '    """生成 app 主图标：电池外框 + SOH 渐变填充 + 内部退化曲线。"""\n'
    '    pixmap = QPixmap(size, size)\n'
    '    pixmap.fill(Qt.GlobalColor.transparent)\n'
    '\n'
    '    painter = QPainter(pixmap)\n'
    '    painter.setRenderHint(QPainter.RenderHint.Antialiasing)\n'
    '\n'
    '    s = size\n'
    '    m = s * 0.08\n'
    '\n'
    '    # 电池主体\n'
    '    body_left = m * 1.5\n'
    '    body_top = m * 1.8 + s * 0.12\n'
    '    body_w = s - m * 3\n'
    '    body_h = s - m * 4 - s * 0.12\n'
    '    body_radius = s * 0.06\n'
    '    body_rect = QRectF(body_left, body_top, body_w, body_h)\n'
    '\n'
    '    # 顶端电极\n'
    '    terminal_w = s * 0.18\n'
    '    terminal_h = s * 0.10\n'
    '    terminal_left = body_left + body_w * 0.35\n'
    '    terminal_top = m * 1.2\n'
    '    terminal_path = QPainterPath()\n'
    '    terminal_rect = QRectF(terminal_left, terminal_top, terminal_w, terminal_h)\n'
    '    terminal_path.addRoundedRect(terminal_rect, s * 0.02, s * 0.02)\n'
    "    painter.fillPath(terminal_path, _color('border'))\n"
    '\n'
    '    # 内部绿色渐变填充（健康→衰减）\n'
    '    fill_margin = s * 0.025\n'
    '    fill_left = body_left + fill_margin\n'
    '    fill_top = body_top + fill_margin\n'
    '    fill_w = body_w - fill_margin * 2\n'
    '    fill_h = body_h - fill_margin * 2\n'
    '    fill_radius = body_radius - fill_margin * 0.5\n'
    '    fill_rect = QRectF(fill_left, fill_top, fill_w, fill_h)\n'
    '\n'
    '    gradient = QLinearGradient(fill_rect.topLeft(), fill_rect.bottomLeft())\n'
    "    gradient.setColorAt(0.0, _color('success_l'))\n"
    "    gradient.setColorAt(0.6, _color('success'))\n"
    "    gradient.setColorAt(1.0, _color('success_d'))\n"
    '    fill_path = QPainterPath()\n'
    '    fill_path.addRoundedRect(fill_rect, fill_radius, fill_radius)\n'
    '    painter.fillPath(fill_path, gradient)\n'
    '\n'
    '    # 内部 SOH 退化曲线（浅色折线，从左上降到右下）\n'
    "    curve_pen = QPen(_color('on_accent'), max(2.0, s * 0.018))\n"
    '    curve_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)\n'
    '    curve_pen.setCapStyle(Qt.PenCapStyle.RoundCap)\n'
    '    painter.setPen(curve_pen)\n'
    '    pts = [\n'
    '        QPointF(fill_left + fill_w * 0.04, fill_top + fill_h * 0.18),\n'
    '        QPointF(fill_left + fill_w * 0.28, fill_top + fill_h * 0.30),\n'
    '        QPointF(fill_left + fill_w * 0.50, fill_top + fill_h * 0.55),\n'
    '        QPointF(fill_left + fill_w * 0.74, fill_top + fill_h * 0.62),\n'
    '        QPointF(fill_left + fill_w * 0.96, fill_top + fill_h * 0.86),\n'
    '    ]\n'
    '    painter.drawPolyline(pts)\n'
    '\n'
    '    # 主体外框\n'
    '    body_path = QPainterPath()\n'
    '    body_path.addRoundedRect(body_rect, body_radius, body_radius)\n'
    "    pen = QPen(_color('text_muted'), s * 0.025)\n"
    '    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)\n'
    '    painter.setPen(pen)\n'
    '    painter.setBrush(Qt.BrushStyle.NoBrush)\n'
    '    painter.drawPath(body_path)\n'
    '\n'
    "    pen2 = QPen(_color('text_muted'), s * 0.022)\n"
    '    painter.setPen(pen2)\n'
    '    painter.drawPath(terminal_path)\n'
    '\n'
    '    painter.end()\n'
    '    return pixmap\n'
    '\n'
    '\n'
    '_DEFAULT_ICON = None\n'
    '\n'
    '\n'
    'def get_app_icon():\n'
    '    """返回 app 主图标（优先加载 SOH.ico，不存在时回退到代码生成）。"""\n'
    '    global _DEFAULT_ICON\n'
    '    if _DEFAULT_ICON is None:\n'
    '        import os\n'
    "        ico_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'SOH.ico')\n"
    '        if os.path.exists(ico_path):\n'
    '            _DEFAULT_ICON = QIcon(ico_path)\n'
    '        else:\n'
    '            _DEFAULT_ICON = QIcon(_create_battery_icon(256))\n'
    '    return _DEFAULT_ICON\n'
    '\n'
    '\n'
    '# ─── 2. 各对话框个性化图标（64×64，slate-400 线条 + 角落彩色点） ──\n'
    '_DIALOG_SIZE = QSize(64, 64)\n'
    '\n'
    '\n'
    'def _accent_dot(p, accent, x, y):\n'
    '    """在 (x, y) 画一个填充小圆点（accent 为 None 时跳过）。"""\n'
    '    if accent is None:\n'
    '        return\n'
    '    p.save()\n'
    '    p.setPen(Qt.PenStyle.NoPen)\n'
    '    p.setBrush(accent)\n'
    '    p.drawEllipse(QPointF(x, y), _ACCENT_R, _ACCENT_R)\n'
    '    p.restore()\n'
    '\n'
    '\n'
    'def _new_dialog_pixmap(draw_func, accent=None):\n'
    '    """生成一个 64×64 对话框图标。"""\n'
    '    pix = QPixmap(_DIALOG_SIZE)\n'
    '    pix.fill(Qt.GlobalColor.transparent)\n'
    '    p = QPainter(pix)\n'
    '    p.setRenderHint(QPainter.RenderHint.Antialiasing)\n'
    '    p.setPen(QPen(_color(_LINE_COLOR_KEY), _LINE_STROKE))\n'
    '    p.setBrush(Qt.BrushStyle.NoBrush)\n'
    '    draw_func(p, _DIALOG_SIZE.width(), accent)\n'
    '    p.end()\n'
    '    return pix\n'
    '\n'
    '\n'
    '# 每个绘制函数签名： (p, size: int, accent: QColor|None)\n'
    '# 统一约定：圆点放在右上角 (size-7, 7)\n'
    '\n'
    'def _draw_help(p, s, accent):\n'
    '    """问号圆圈 — 帮助/参数说明。"""\n'
    '    cx, cy = s / 2, s / 2\n'
    '    r = s * 0.34\n'
    '    p.drawEllipse(QPointF(cx, cy), r, r)\n'
    '    # ? 上弧\n'
    '    p.drawArc(int(cx - r * 0.32), int(cy - r * 0.72),\n'
    '              int(r * 0.64), int(r * 0.50),\n'
    '              int(45 * 16), int(200 * 16))\n'
    '    # ? 立柱\n'
    '    p.drawLine(int(cx), int(cy - r * 0.18),\n'
    '               int(cx), int(cy + r * 0.05))\n'
    '    # ? 圆点\n'
    '    p.drawPoint(QPointF(cx, cy + r * 0.32))\n'
    '    _accent_dot(p, accent, s - 7, 7)\n'
    '\n'
    '\n'
    'def _draw_tcp(p, s, accent):\n'
    '    """TCP/网络 — 中央节点 + 三层扇形波 + 端点小点。"""\n'
    '    cx, cy = s / 2, s * 0.62\n'
    '    # 三个端点\n'
    '    p.drawPoint(QPointF(cx, cy))\n'
    '    p.drawPoint(QPointF(cx - s * 0.30, cy - s * 0.04))\n'
    '    p.drawPoint(QPointF(cx + s * 0.30, cy - s * 0.04))\n'
    '    # 三层弧\n'
    '    for r in (s * 0.18, s * 0.30, s * 0.42):\n'
    '        p.drawArc(int(cx - r), int(cy - r * 0.95),\n'
    '                  int(r * 2), int(r * 1.9),\n'
    '                  int(35 * 16), int(110 * 16))\n'
    '    # 底部接收端水平线\n'
    '    p.drawLine(int(s * 0.20), int(cy + s * 0.22),\n'
    '               int(s * 0.80), int(cy + s * 0.22))\n'
    '    _accent_dot(p, accent, s - 7, 7)\n'
    '\n'
    '\n'
    'def _draw_error(p, s, accent):\n'
    '    """错误 — 圆 + 红色加粗 X。"""\n'
    '    cx, cy = s / 2, s / 2\n'
    '    r = s * 0.34\n'
    '    p.drawEllipse(QPointF(cx, cy), r, r)\n'
    '    k = r * 0.55\n'
    '    p.drawLine(int(cx - k), int(cy - k), int(cx + k), int(cy + k))\n'
    '    p.drawLine(int(cx + k), int(cy - k), int(cx - k), int(cy + k))\n'
    '    _accent_dot(p, accent, s - 7, 7)\n'
    '\n'
    '\n'
    'def _draw_warning(p, s, accent):\n'
    '    """警告 — 三角 + !。"""\n'
    '    cx = s / 2\n'
    '    top_y = s * 0.16\n'
    '    base_y = s * 0.84\n'
    '    base_half = s * 0.32\n'
    '    tri = QPolygonF([\n'
    '        QPointF(cx, top_y),\n'
    '        QPointF(cx - base_half, base_y),\n'
    '        QPointF(cx + base_half, base_y),\n'
    '    ])\n'
    '    p.drawPolygon(tri)\n'
    '    # ! 立柱\n'
    '    p.drawLine(int(cx), int(s * 0.40), int(cx), int(s * 0.65))\n'
    '    # ! 圆点\n'
    '    p.drawPoint(QPointF(cx, s * 0.74))\n'
    '    _accent_dot(p, accent, s - 7, 7)\n'
    '\n'
    '\n'
    'def _draw_info(p, s, accent):\n'
    '    """信息 — 圆 + i。"""\n'
    '    cx, cy = s / 2, s / 2\n'
    '    r = s * 0.34\n'
    '    p.drawEllipse(QPointF(cx, cy), r, r)\n'
    '    p.drawPoint(QPointF(cx, s * 0.30))   # i 顶\n'
    '    p.drawLine(int(cx), int(s * 0.42),\n'
    '               int(cx), int(s * 0.66))    # i 身\n'
    '    _accent_dot(p, accent, s - 7, 7)\n'
    '\n'
    '\n'
    'def _draw_success(p, s, accent):\n'
    '    """成功 — 圆 + 勾。"""\n'
    '    cx, cy = s / 2, s / 2\n'
    '    r = s * 0.34\n'
    '    p.drawEllipse(QPointF(cx, cy), r, r)\n'
    '    # 勾\n'
    '    p.drawPolyline([\n'
    '        QPointF(cx - r * 0.50, cy + r * 0.05),\n'
    '        QPointF(cx - r * 0.10, cy + r * 0.40),\n'
    '        QPointF(cx + r * 0.55, cy - r * 0.35),\n'
    '    ])\n'
    '    _accent_dot(p, accent, s - 7, 7)\n'
    '\n'
    '\n'
    'def _draw_folder(p, s, accent):\n'
    '    """文件夹 — 经典文件柜造型。"""\n'
    '    m = s * 0.18\n'
    '    # 标签片\n'
    '    p.drawPolyline([\n'
    '        QPointF(m, m + s * 0.04),\n'
    '        QPointF(m + s * 0.30, m + s * 0.04),\n'
    '        QPointF(m + s * 0.38, m + s * 0.14),\n'
    '        QPointF(m + s * 0.38, m + s * 0.18),\n'
    '    ])\n'
    '    # 主体\n'
    '    p.drawPolyline([\n'
    '        QPointF(m + s * 0.38, m + s * 0.18),\n'
    '        QPointF(s - m, m + s * 0.18),\n'
    '        QPointF(s - m, s - m),\n'
    '        QPointF(m, s - m),\n'
    '        QPointF(m, m + s * 0.04),\n'
    '    ])\n'
    '    # 中线\n'
    '    p.drawLine(int(m + s * 0.05), int(m + s * 0.55),\n'
    '               int(s - m - s * 0.05), int(m + s * 0.55))\n'
    '    _accent_dot(p, accent, s - 7, 7)\n'
    '\n'
    '\n'
    'def _draw_save(p, s, accent):\n'
    '    """保存 — 软盘 + 下箭头（与工具栏一致但放大）。"""\n'
    '    m = s * 0.18\n'
    '    # 主体\n'
    '    p.drawRect(int(m), int(m), int(s - 2 * m), int(s - 2 * m))\n'
    '    # 右上角折角缺口\n'
    '    p.drawLine(int(s - m - 9), int(m), int(s - m), int(m + 9))\n'
    '    p.drawLine(int(s - m - 9), int(m), int(s - m - 9), int(m + 9))\n'
    '    p.drawLine(int(s - m - 9), int(m + 9), int(s - m), int(m + 9))\n'
    '    # 金属读写片\n'
    '    p.drawRect(int(m + 6), int(s - m - 12), int(s - 2 * m - 12), 6)\n'
    '    # 中央向下箭头\n'
    '    cx = s / 2\n'
    '    p.drawLine(int(cx), int(m + 12), int(cx), int(s - m - 4))\n'
    '    p.drawPolyline([\n'
    '        QPointF(cx - 4, s - m - 8),\n'
    '        QPointF(cx, s - m - 4),\n'
    '        QPointF(cx + 4, s - m - 8),\n'
    '    ])\n'
    '    _accent_dot(p, accent, s - 7, 7)\n'
    '\n'
    '\n'
    'def _draw_color(p, s, accent):\n'
    '    """颜色 — 调色板 + 多色点。"""\n'
    '    cx, cy = s / 2, s * 0.55\n'
    '    r = s * 0.34\n'
    '    # 调色板外轮廓（椭圆）\n'
    '    p.drawEllipse(QPointF(cx, cy), r, r * 0.85)\n'
    '    # 拇指孔\n'
    '    p.setBrush(Qt.GlobalColor.transparent)\n'
    '    p.drawEllipse(QPointF(cx + r * 0.45, cy + r * 0.20), r * 0.18, r * 0.18)\n'
    '    # 色点\n'
    '    p.setPen(Qt.PenStyle.NoPen)\n'
    '    p.setBrush(_color(_ACCENT_DANGER))\n'
    '    p.drawEllipse(QPointF(cx - r * 0.45, cy - r * 0.35), 3, 3)\n'
    '    p.setBrush(_color(_ACCENT_WARNING))\n'
    '    p.drawEllipse(QPointF(cx - r * 0.10, cy - r * 0.65), 3, 3)\n'
    '    p.setBrush(_color(_ACCENT_SUCCESS))\n'
    '    p.drawEllipse(QPointF(cx + r * 0.30, cy - r * 0.45), 3, 3)\n'
    '    p.setBrush(_color(_ACCENT_INFO))\n'
    '    p.drawEllipse(QPointF(cx + r * 0.55, cy + r * 0.05), 3, 3)\n'
    '    p.setBrush(Qt.BrushStyle.NoBrush)\n'
    '    p.setPen(QPen(_color(_LINE_COLOR_KEY), _LINE_STROKE))\n'
    '    _accent_dot(p, accent, s - 7, 7)\n'
    '\n'
    '\n'
    'def _draw_line(p, s, accent):\n'
    '    """线条样式 — 实线/虚线/点线 三种。"""\n'
    '    m = s * 0.16\n'
    '    # 实线\n'
    '    p.drawLine(int(m), int(s * 0.30), int(s - m), int(s * 0.30))\n'
    '    # 虚线\n'
    '    pen = p.pen()\n'
    '    pen.setStyle(Qt.PenStyle.DashLine)\n'
    '    p.setPen(pen)\n'
    '    p.drawLine(int(m), int(s * 0.52), int(s - m), int(s * 0.52))\n'
    '    # 点线\n'
    '    pen.setStyle(Qt.PenStyle.DotLine)\n'
    '    p.setPen(pen)\n'
    '    p.drawLine(int(m), int(s * 0.74), int(s - m), int(s * 0.74))\n'
    '    p.setPen(QPen(_color(_LINE_COLOR_KEY), _LINE_STROKE))\n'
    '    _accent_dot(p, accent, s - 7, 7)\n'
    '\n'
    '\n'
    'def _draw_subplot(p, s, accent):\n'
    '    """子图 — 2×2 网格。"""\n'
    '    m = s * 0.18\n'
    '    p.drawRect(int(m), int(m), int(s - 2 * m), int(s - 2 * m))\n'
    '    p.drawLine(int(s / 2), int(m), int(s / 2), int(s - m))\n'
    '    p.drawLine(int(m), int(s / 2), int(s - m), int(s / 2))\n'
    '    _accent_dot(p, accent, s - 7, 7)\n'
    '\n'
    '\n'
    'def _draw_axis(p, s, accent):\n'
    '    """坐标轴 — X/Y 轴 + 折线（带色高亮）。"""\n'
    '    m = s * 0.18\n'
    '    # Y\n'
    '    p.drawLine(int(m), int(m), int(m), int(s - m))\n'
    '    # X\n'
    '    p.drawLine(int(m), int(s - m), int(s - m), int(s - m))\n'
    '    # Y 箭头\n'
    '    p.drawPolyline([\n'
    '        QPointF(m - 3, m + 5),\n'
    '        QPointF(m, m),\n'
    '        QPointF(m + 3, m + 5),\n'
    '    ])\n'
    '    # X 箭头\n'
    '    p.drawPolyline([\n'
    '        QPointF(s - m - 5, s - m - 3),\n'
    '        QPointF(s - m, s - m),\n'
    '        QPointF(s - m - 5, s - m + 3),\n'
    '    ])\n'
    '    # 折线（用 accent 突出）\n'
    '    if accent is not None:\n'
    '        pen = p.pen()\n'
    '        pen.setColor(accent)\n'
    '        pen.setWidthF(_ACCENT_STROKE)\n'
    '        p.setPen(pen)\n'
    '        p.drawPolyline([\n'
    '            QPointF(m + 3, s - m - 3),\n'
    '            QPointF(s * 0.35, s * 0.55),\n'
    '            QPointF(s * 0.55, s * 0.68),\n'
    '            QPointF(s * 0.75, s * 0.32),\n'
    '            QPointF(s - m - 3, s * 0.45),\n'
    '        ])\n'
    '        p.setPen(QPen(_color(_LINE_COLOR_KEY), _LINE_STROKE))\n'
    '    _accent_dot(p, accent, s - 7, 7)\n'
    '\n'
    '\n'
    'def _draw_legend(p, s, accent):\n'
    '    """图例 — 色块 + 文本行。"""\n'
    '    m = s * 0.20\n'
    '    p.drawRect(int(m), int(m), int(s - 2 * m), int(s - 2 * m))\n'
    '    # 三行色块 + 文本线\n'
    '    rows = [(0.18, _color(_ACCENT_INFO)), (0.45, _color(_ACCENT_SUCCESS)),\n'
    '            (0.72, _color(_ACCENT_WARNING))]\n'
    '    for ry, color in rows:\n'
    '        y = int(m + (s - 2 * m) * ry)\n'
    '        p.fillRect(int(m + 4), y, int(s * 0.16), 4, color)\n'
    '        p.drawLine(int(m + s * 0.24), y + 2,\n'
    '                   int(s - m - 4), y + 2)\n'
    '    _accent_dot(p, accent, s - 7, 7)\n'
    '\n'
    '\n'
    'def _draw_chart(p, s, accent):\n'
    '    """图表 — 折线图（与 toolbar 中 _chart 风格保持一致）。"""\n'
    '    m = s * 0.18\n'
    '    # 坐标轴\n'
    '    p.drawLine(int(m), int(s - m), int(s - m), int(s - m))\n'
    '    p.drawLine(int(m), int(m), int(m), int(s - m))\n'
    '    # 折线\n'
    '    pen = p.pen()\n'
    '    pen.setWidthF(_ACCENT_STROKE)\n'
    '    p.setPen(pen)\n'
    '    p.drawPolyline([\n'
    '        QPointF(m + 2, s - m - 2),\n'
    '        QPointF(s * 0.30, s * 0.55),\n'
    '        QPointF(s * 0.50, s * 0.70),\n'
    '        QPointF(s * 0.70, s * 0.30),\n'
    '        QPointF(s - m - 2, s * 0.45),\n'
    '    ])\n'
    '    p.setPen(QPen(_color(_LINE_COLOR_KEY), _LINE_STROKE))\n'
    '    _accent_dot(p, accent, s - 7, 7)\n'
    '\n'
    '\n'
    'def _draw_model(p, s, accent):\n'
    '    """模型 — 3-2-1 全连接神经网络。"""\n'
    '    m = s * 0.18\n'
    '    left_x  = m + 4\n'
    '    mid_x   = s / 2\n'
    '    right_x = s - m - 4\n'
    '    left_ys  = [m + 6, s / 2, s - m - 6]\n'
    '    mid_ys   = [s * 0.32, s * 0.68]\n'
    '    right_ys = [s / 2]\n'
    '\n'
    '    # 浅色连接线\n'
    '    pen = p.pen()\n'
    '    pen.setWidthF(0.9)\n'
    '    p.setPen(pen)\n'
    '    for y1 in left_ys:\n'
    '        for y2 in mid_ys:\n'
    '            p.drawLine(QPointF(left_x, y1), QPointF(mid_x, y2))\n'
    '    for y1 in mid_ys:\n'
    '        for y2 in right_ys:\n'
    '            p.drawLine(QPointF(mid_x, y1), QPointF(right_x, y2))\n'
    '\n'
    '    # 节点\n'
    '    p.setPen(QPen(_color(_LINE_COLOR_KEY), _LINE_STROKE))\n'
    '    for x, ys in [(left_x, left_ys), (mid_x, mid_ys), (right_x, right_ys)]:\n'
    '        for y in ys:\n'
    '            p.drawEllipse(QPointF(x, y), 3.2, 3.2)\n'
    '\n'
    '    _accent_dot(p, accent, s - 7, 7)\n'
    '\n'
    '\n'
    'def _draw_import(p, s, accent):\n'
    '    """导入 — 文件 + 向下箭头。"""\n'
    '    m = s * 0.18\n'
    '    # 文件\n'
    '    p.drawRect(int(m + 6), int(m), int(s * 0.55), int(s * 0.62))\n'
    '    p.drawLine(int(m + 6 + s * 0.10), int(m),\n'
    '               int(m + 6 + s * 0.10), int(m - 4))\n'
    '    p.drawLine(int(m + 6 + s * 0.10), int(m - 4),\n'
    '               int(m + 6 + s * 0.32), int(m - 4))\n'
    '    p.drawLine(int(m + 6 + s * 0.32), int(m - 4),\n'
    '               int(m + 6 + s * 0.32), int(m))\n'
    '    # 向下箭头\n'
    '    cx = s * 0.78\n'
    '    p.drawLine(int(cx), int(m + s * 0.10),\n'
    '               int(cx), int(s - m))\n'
    '    p.drawPolyline([\n'
    '        QPointF(cx - 5, s - m - 6),\n'
    '        QPointF(cx, s - m),\n'
    '        QPointF(cx + 5, s - m - 6),\n'
    '    ])\n'
    '    _accent_dot(p, accent, s - 7, 7)\n'
    '\n'
    '\n'
    'def _draw_export(p, s, accent):\n'
    '    """导出 — 文件 + 向上箭头。"""\n'
    '    m = s * 0.18\n'
    '    # 文件\n'
    '    p.drawRect(int(m + 6), int(m + s * 0.30), int(s * 0.55), int(s * 0.62))\n'
    '    p.drawLine(int(m + 6 + s * 0.10), int(m + s * 0.30),\n'
    '               int(m + 6 + s * 0.10), int(m + s * 0.30 - 4))\n'
    '    p.drawLine(int(m + 6 + s * 0.10), int(m + s * 0.30 - 4),\n'
    '               int(m + 6 + s * 0.32), int(m + s * 0.30 - 4))\n'
    '    p.drawLine(int(m + 6 + s * 0.32), int(m + s * 0.30 - 4),\n'
    '               int(m + 6 + s * 0.32), int(m + s * 0.30))\n'
    '    # 向上箭头\n'
    '    cx = s * 0.78\n'
    '    p.drawLine(int(cx), int(m),\n'
    '               int(cx), int(s - m - s * 0.10))\n'
    '    p.drawPolyline([\n'
    '        QPointF(cx - 5, m + 6),\n'
    '        QPointF(cx, m),\n'
    '        QPointF(cx + 5, m + 6),\n'
    '    ])\n'
    '    _accent_dot(p, accent, s - 7, 7)\n'
    '\n'
    '\n'
    '_DIALOG_DRAW_FUNCS = {\n'
    "    'help':        _draw_help,\n"
    "    'tcp':         _draw_tcp,\n"
    "    'error':       _draw_error,\n"
    "    'warning':     _draw_warning,\n"
    "    'info':        _draw_info,\n"
    "    'success':     _draw_success,\n"
    "    'question':    _draw_help,\n"
    "    'folder':      _draw_folder,\n"
    "    'save':        _draw_save,\n"
    "    'color':       _draw_color,\n"
    "    'line':        _draw_line,\n"
    "    'subplot':     _draw_subplot,\n"
    "    'axis':        _draw_axis,\n"
    "    'legend':      _draw_legend,\n"
    "    'chart':       _draw_chart,\n"
    "    'model':       _draw_model,\n"
    "    'import':      _draw_import,\n"
    "    'export':      _draw_export,\n"
    '}\n'
    '\n'
    '# 状态 → 角落小色点（柔和，不抢眼）；值仍是 token 名，绘制时才取色\n'
    '_ACCENT_FOR_KIND = {\n'
    "    'help':        _ACCENT_INFO,\n"
    "    'tcp':         _ACCENT_INFO,\n"
    "    'error':       _ACCENT_DANGER,\n"
    "    'warning':     _ACCENT_WARNING,\n"
    "    'info':        _ACCENT_INFO,\n"
    "    'success':     _ACCENT_SUCCESS,\n"
    "    'question':    _ACCENT_INFO,\n"
    "    'folder':      _ACCENT_INFO,\n"
    "    'save':        _ACCENT_INFO,\n"
    "    'color':       _ACCENT_INFO,\n"
    "    'line':        _ACCENT_INFO,\n"
    "    'subplot':     _ACCENT_INFO,\n"
    "    'axis':        _ACCENT_INFO_D,\n"
    "    'legend':      _ACCENT_INFO,\n"
    "    'chart':       _ACCENT_INFO_D,\n"
    "    'model':       _ACCENT_MODEL,\n"
    "    'import':      _ACCENT_INFO,\n"
    "    'export':      _ACCENT_SUCCESS,\n"
    '}\n'
    '\n'
    '_dialog_icon_cache = {}\n'
    '\n'
    '\n'
    'def get_dialog_icon(kind):\n'
    '    """根据对话框类型返回对应的 QIcon（按主题 + kind 缓存）。\n'
    '\n'
    '    支持的 kind：\n'
    '      app / help / tcp / error / warning / info / success / question /\n'
    '      folder / save / color / line / subplot / axis / legend / chart /\n'
    '      model / import / export\n'
    '    """\n'
    "    if kind == 'app':\n"
    '        return get_app_icon()\n'
    '    # 主题不同则像素不同，缓存键必须带上主题，否则切换明暗后会残留旧色。\n'
    '    key = (id(_tokens()), kind)\n'
    '    if key not in _dialog_icon_cache:\n'
    '        token = _ACCENT_FOR_KIND.get(kind)\n'
    '        accent = _color(token) if token else None\n'
    '        fn = _DIALOG_DRAW_FUNCS[kind]\n'
    '        pix = _new_dialog_pixmap(fn, accent)\n'
    '        _dialog_icon_cache[key] = QIcon(pix)\n'
    '    return _dialog_icon_cache[key]\n'
    '\n'
    '\n'
    '# 简化别名：只取回 pixmap（用于 QMessageBox.setIconPixmap）\n'
    'def get_dialog_pixmap(kind, size=48):\n'
    '    """获取指定 kind 的对话框图标 pixmap（用于嵌入到 QMessageBox 内部）。"""\n'
    '    icon = get_dialog_icon(kind)\n'
    '    return icon.pixmap(QSize(size, size))\n'
    '\n'
    '\n'
    '# ─── 3. QMessageBox 统一封装（自动应用主题色 + 个性化图标） ──────\n'
    '_ICON_ROLE_MAP = {\n'
    "    'error':    QMessageBox.Icon.Critical,\n"
    "    'warning':  QMessageBox.Icon.Warning,\n"
    "    'info':     QMessageBox.Icon.Information,\n"
    "    'success':  QMessageBox.Icon.Information,\n"
    "    'question': QMessageBox.Icon.Question,\n"
    '}\n'
    '\n'
    '# 中文按钮文案\n'
    '_BTN_TEXT = {\n'
    "    'ok': '确定',\n"
    "    'cancel': '取消',\n"
    "    'yes': '是',\n"
    "    'no': '否',\n"
    "    'save': '保存',\n"
    "    'discard': '不保存',\n"
    "    'open': '打开',\n"
    "    'close': '关闭',\n"
    "    'apply': '应用',\n"
    "    'reset': '重置',\n"
    '}\n'
    '\n'
    '\n'
    'def show_message(parent, kind, title, text, *, buttons=None, default=None):\n'
    '    """弹出 QMessageBox，自动设置标题栏 + 内部图标为个性化版本。\n'
    '\n'
    '    参数：\n'
    '        parent  : 父窗口\n'
    "        kind    : 'error' / 'warning' / 'info' / 'success' / 'question'\n"
    '        title   : 标题\n'
    '        text    : 正文\n'
    '        buttons : 可选，QMessageBox.StandardButton 组合；默认只显示"确定"\n'
    '        default : 默认按钮\n'
    '\n'
    '    返回：QMessageBox.StandardButton（即用户点击的按钮）\n'
    '    """\n'
    '    mb = QMessageBox(parent)\n'
    '    mb.setIcon(_ICON_ROLE_MAP.get(kind, QMessageBox.Icon.Information))\n'
    '    mb.setWindowTitle(title)\n'
    '    mb.setText(text)\n'
    '\n'
    '    # 内部图标用个性化版本\n'
    '    pixmap = get_dialog_pixmap(kind, 48)\n'
    '    mb.setIconPixmap(pixmap)\n'
    '\n'
    '    # 标题栏图标\n'
    '    mb.setWindowIcon(get_dialog_icon(kind))\n'
    '\n'
    '    # 按钮\n'
    '    if buttons is not None:\n'
    '        mb.setStandardButtons(buttons)\n'
    '        if default is not None:\n'
    '            mb.setDefaultButton(default)\n'
    '\n'
    '    # 中文化按钮（仅识别 PyQt6 内置角色，不破坏其他自定义按钮）\n'
    '    _translate_msgbox_buttons(mb)\n'
    '\n'
    '    return mb.exec()\n'
    '\n'
    '\n'
    'def _translate_msgbox_buttons(mb):\n'
    '    """将 QMessageBox 的标准按钮文案改为中文。"""\n'
    '    mapping = {\n'
    "        QMessageBox.StandardButton.Ok: '确定',\n"
    "        QMessageBox.StandardButton.Cancel: '取消',\n"
    "        QMessageBox.StandardButton.Yes: '是',\n"
    "        QMessageBox.StandardButton.No: '否',\n"
    "        QMessageBox.StandardButton.Save: '保存',\n"
    "        QMessageBox.StandardButton.Discard: '不保存',\n"
    "        QMessageBox.StandardButton.Open: '打开',\n"
    "        QMessageBox.StandardButton.Close: '关闭',\n"
    "        QMessageBox.StandardButton.Apply: '应用',\n"
    "        QMessageBox.StandardButton.Reset: '重置',\n"
    "        QMessageBox.StandardButton.YesToAll: '全部是',\n"
    "        QMessageBox.StandardButton.NoToAll: '全部否',\n"
    "        QMessageBox.StandardButton.Abort: '中止',\n"
    "        QMessageBox.StandardButton.Retry: '重试',\n"
    "        QMessageBox.StandardButton.Ignore: '忽略',\n"
    "        QMessageBox.StandardButton.Help: '帮助',\n"
    '    }\n'
    '    for btn in mb.buttons():\n'
    '        std = mb.standardButton(btn)\n'
    '        if std in mapping:\n'
    '            btn.setText(mapping[std])\n'
    '\n'
    '\n'
    '# ─── 4. QInputDialog 包装（个性化图标 + 中文化按钮） ──────────────\n'
    "def input_get_item(parent, title, label, items, current=0, editable=False, icon_kind='axis'):\n"
    '    """替代 QInputDialog.getItem，自动应用个性化图标。"""\n'
    '    from PyQt6.QtWidgets import QInputDialog\n'
    '    dlg = QInputDialog(parent)\n'
    '    dlg.setWindowTitle(title)\n'
    '    dlg.setLabelText(label)\n'
    '    dlg.setComboBoxEditable(editable)\n'
    '    dlg.setComboBoxItems(list(items))\n'
    '    if 0 <= current < len(items):\n'
    '        dlg.setCurrentIndex(current)\n'
    '    dlg.setWindowIcon(get_dialog_icon(icon_kind))\n'
    '    if dlg.exec() == QMessageBox.StandardButton.Ok:\n'
    '        return dlg.currentText(), True\n'
    "    return '', False\n"
)

# ---- core/progress.py ----
_MODULE_SOURCES['core.progress'] = (
    '"""Shared progress-event schema for workers and training code."""\n'
    '\n'
    'import time\n'
    '\n'
    '\n'
    'def make_progress_event(phase, *, started_at, battery=None, seed=None,\n'
    '                        epoch=None, current=0, total=0):\n'
    '    return {\n'
    "        'phase': str(phase),\n"
    "        'battery': battery,\n"
    "        'seed': seed,\n"
    "        'epoch': epoch,\n"
    "        'current': int(current),\n"
    "        'total': int(total),\n"
    "        'elapsed_seconds': max(0.0, time.monotonic() - started_at),\n"
    '    }\n'
)

# ---- core/cancellation.py ----
_MODULE_SOURCES['core.cancellation'] = (
    'import time\n'
    '\n'
    'from core.progress import make_progress_event\n'
    '\n'
    '\n'
    'class TrainingCancelled(RuntimeError):\n'
    '    """Raised when a cooperative training stop reaches a safe checkpoint."""\n'
    '\n'
    '\n'
    'def stop_requested(stop_flag):\n'
    '    return bool(stop_flag is not None and stop_flag())\n'
    '\n'
    '\n'
    'def check_cancelled(stop_flag):\n'
    '    if stop_requested(stop_flag):\n'
    "        raise TrainingCancelled('训练已由用户取消')\n"
    '\n'
    '\n'
    'def xgboost_stop_callbacks(stop_flag, progress_callback=None, *,\n'
    '                           battery=None, seed=None, total=None,\n'
    '                           started_at=None):\n'
    '    """Create an XGBoost per-iteration cooperative stop callback."""\n'
    '    if stop_flag is None and progress_callback is None:\n'
    '        return None\n'
    '    from xgboost.callback import TrainingCallback\n'
    '    progress_started_at = started_at or time.monotonic()\n'
    '\n'
    '    class CooperativeStopCallback(TrainingCallback):\n'
    '        def after_iteration(self, model, epoch, evals_log):\n'
    '            if progress_callback:\n'
    '                progress_callback(make_progress_event(\n'
    "                    'xgboost_tree',\n"
    '                    started_at=progress_started_at,\n'
    '                    battery=battery,\n'
    '                    seed=seed,\n'
    '                    epoch=None,\n'
    '                    current=epoch + 1,\n'
    '                    total=total or epoch + 1,\n'
    '                ))\n'
    '            return stop_requested(stop_flag)\n'
    '\n'
    '    return [CooperativeStopCallback()]\n'
)

# ---- core/batching.py ----
_MODULE_SOURCES['core.batching'] = (
    '"""CPU-backed mini-batch helpers for recurrent-model training."""\n'
    '\n'
    'import numpy as np\n'
    'import torch\n'
    'from torch.utils.data import DataLoader, TensorDataset\n'
    '\n'
    'from core.cancellation import check_cancelled\n'
    '\n'
    '\n'
    'DEFAULT_BATCH_SIZE = 64\n'
    '\n'
    '\n'
    'def make_tensor_loader(features, targets, *, batch_size=DEFAULT_BATCH_SIZE,\n'
    '                       shuffle=False, seed=0):\n'
    '    if batch_size < 1:\n'
    "        raise ValueError('批次大小必须大于 0')\n"
    '    features = np.asarray(features, dtype=np.float32)\n'
    '    targets = np.asarray(targets, dtype=np.float32)\n'
    '    if len(features) != len(targets):\n'
    "        raise ValueError('特征和标签数量必须一致')\n"
    '    dataset = TensorDataset(\n'
    '        torch.from_numpy(features), torch.from_numpy(targets))\n'
    '    generator = torch.Generator()\n'
    '    generator.manual_seed(int(seed))\n'
    '    return DataLoader(\n'
    '        dataset,\n'
    '        batch_size=min(batch_size, max(1, len(dataset))),\n'
    '        shuffle=shuffle,\n'
    '        generator=generator,\n'
    '        num_workers=0,\n'
    '        pin_memory=False,\n'
    '    )\n'
    '\n'
    '\n'
    'def train_recurrent_epoch(model, loader, optimizer, criterion, device,\n'
    '                          stop_flag=None):\n'
    '    model.train()\n'
    '    weighted_loss = 0.0\n'
    '    sample_count = 0\n'
    '    for features, targets in loader:\n'
    '        check_cancelled(stop_flag)\n'
    '        features = features.to(device)\n'
    '        targets = targets.to(device)\n'
    '        output = model(features).reshape(-1, 1)\n'
    '        loss = criterion(output, targets.reshape(-1, 1))\n'
    '        optimizer.zero_grad()\n'
    '        loss.backward()\n'
    '        # RNN 容易梯度爆炸，加梯度裁剪（改进方案 A8）\n'
    '        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)\n'
    '        optimizer.step()\n'
    '        count = len(features)\n'
    '        weighted_loss += float(loss.item()) * count\n'
    '        sample_count += count\n'
    '    return weighted_loss / max(1, sample_count)\n'
    '\n'
    '\n'
    'def evaluate_recurrent_loss(model, loader, criterion, device,\n'
    '                            stop_flag=None):\n'
    '    model.eval()\n'
    '    weighted_loss = 0.0\n'
    '    sample_count = 0\n'
    '    with torch.no_grad():\n'
    '        for features, targets in loader:\n'
    '            check_cancelled(stop_flag)\n'
    '            features = features.to(device)\n'
    '            targets = targets.to(device)\n'
    '            output = model(features).reshape(-1, 1)\n'
    '            loss = criterion(output, targets.reshape(-1, 1))\n'
    '            count = len(features)\n'
    '            weighted_loss += float(loss.item()) * count\n'
    '            sample_count += count\n'
    '    return weighted_loss / max(1, sample_count)\n'
)

# ---- core/evaluate.py ----
_MODULE_SOURCES['core.evaluate'] = (
    'from math import sqrt\n'
    'import numpy as np\n'
    'from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score\n'
    '\n'
    'from core.result_semantics import first_failure_index\n'
    '\n'
    '\n'
    'def _first_failure_index(values, threshold):\n'
    '    """失效判定委托给 ``core.result_semantics``，全工程只有一处实现。"""\n'
    '    return first_failure_index(values, threshold)\n'
    '\n'
    '\n'
    'def relative_error_details(y_test, y_predict, threshold):\n'
    '    """Return RE with an explicit observed/censored status."""\n'
    '    true_re = _first_failure_index(y_test, threshold)\n'
    '    pred_re = _first_failure_index(y_predict, threshold)\n'
    '\n'
    '    if true_re == 0:\n'
    "        status = 'observed_initial_failure'\n"
    '        value = None\n'
    '    elif true_re is None and pred_re is None:\n'
    "        status = 'both_censored'\n"
    '        value = None\n'
    '    elif true_re is None:\n'
    "        status = 'observed_censored'\n"
    '        value = None\n'
    '    elif pred_re is None:\n'
    "        status = 'prediction_censored'\n"
    '        value = None\n'
    '    elif pred_re == 0:\n'
    "        status = 'prediction_initial_failure'\n"
    '        value = None\n'
    '    else:\n'
    "        status = 'observed'\n"
    '        value = abs(true_re - pred_re) / true_re\n'
    '\n'
    '    return {\n'
    "        'value': value,\n"
    "        'status': status,\n"
    "        'true_crossing_index': true_re,\n"
    "        'predicted_crossing_index': pred_re,\n"
    '    }\n'
    '\n'
    '\n'
    'def relative_error(y_test, y_predict, threshold):\n'
    "    return relative_error_details(y_test, y_predict, threshold)['value']\n"
    '\n'
    '\n'
    'def evaluation(y_test, y_predict):\n'
    '    """RMSE"""\n'
    '    return sqrt(mean_squared_error(y_test, y_predict))\n'
    '\n'
    '\n'
    'def calc_mae(y_test, y_predict):\n'
    '    """平均绝对误差"""\n'
    '    return mean_absolute_error(y_test, y_predict)\n'
    '\n'
    '\n'
    'def calc_r2(y_test, y_predict):\n'
    '    """决定系数 R²"""\n'
    '    if len(y_test) < 2:\n'
    '        return 0.0\n'
    '    return r2_score(y_test, y_predict)\n'
    '\n'
    '\n'
    'def calc_pearson(y_test, y_predict):\n'
    '    """Pearson 相关系数"""\n'
    '    y_test = np.asarray(y_test, dtype=np.float64)\n'
    '    y_predict = np.asarray(y_predict, dtype=np.float64)\n'
    '    if len(y_test) < 2:\n'
    '        return 0.0\n'
    '    std_t = np.std(y_test)\n'
    '    std_p = np.std(y_predict)\n'
    '    if std_t < 1e-12 or std_p < 1e-12:\n'
    '        return 0.0\n'
    '    return float(np.corrcoef(y_test, y_predict)[0, 1])\n'
    '\n'
    '\n'
    'def calc_all_metrics(y_test, y_predict, rated_capacity=None, threshold_ratio=None):\n'
    '    """一次性计算全部指标，返回 dict"""\n'
    '    y_test = np.asarray(y_test, dtype=np.float64).reshape(-1)\n'
    '    y_predict = np.asarray(y_predict, dtype=np.float64).reshape(-1)\n'
    '    if len(y_test) == 0 or len(y_predict) == 0:\n'
    "        raise ValueError('真实值和预测值必须为非空序列')\n"
    '    if len(y_test) != len(y_predict):\n'
    "        raise ValueError('真实值和预测值长度必须一致')\n"
    '    if not np.all(np.isfinite(y_test)) or not np.all(np.isfinite(y_predict)):\n'
    "        raise ValueError('真实值和预测值必须全部为有限数值')\n"
    '    metrics = {\n'
    "        'rmse': evaluation(y_test, y_predict),\n"
    "        'mae': calc_mae(y_test, y_predict),\n"
    "        'r2': calc_r2(y_test, y_predict),\n"
    "        'pearson': calc_pearson(y_test, y_predict),\n"
    '    }\n'
    '    if rated_capacity is not None and threshold_ratio is not None:\n'
    '        re_result = relative_error_details(\n'
    '            y_test, y_predict, rated_capacity * threshold_ratio)\n'
    "        metrics['re'] = re_result['value']\n"
    "        metrics['re_status'] = re_result['status']\n"
    "        metrics['true_eol_index'] = re_result['true_crossing_index']\n"
    "        metrics['predicted_eol_index'] = re_result[\n"
    "            'predicted_crossing_index']\n"
    '    return metrics\n'
    '\n'
    '\n'
    'def confidence_interval(values, confidence=0.95):\n'
    '    """计算置信区间 [mean - margin, mean + margin]\n'
    '\n'
    '    values: 多次实验的指标值列表\n'
    '    confidence: 置信水平，默认 0.95\n'
    '    返回 (mean, lower, upper, std)\n'
    '\n'
    '    注意：这是**同一留一折内、不同随机种子**之间的区间，它不代表泛化不确定性。\n'
    '    跨电池的泛化不确定性请用 :func:`bootstrap_ci`。\n'
    '    """\n'
    '    values = np.asarray(values, dtype=np.float64)\n'
    '    n = len(values)\n'
    '    if n == 0:\n'
    '        return 0.0, 0.0, 0.0, 0.0\n'
    '    mean = float(np.mean(values))\n'
    '    std = float(np.std(values, ddof=1)) if n > 1 else 0.0\n'
    '    if n > 1 and std > 1e-12:\n'
    '        # 使用 t 分布\n'
    '        from scipy import stats\n'
    '        t_val = stats.t.ppf((1 + confidence) / 2, df=n - 1)\n'
    '        margin = t_val * std / sqrt(n)\n'
    '    else:\n'
    '        margin = 0.0\n'
    '    return mean, mean - margin, mean + margin, std\n'
    '\n'
    '\n'
    'def bootstrap_ci(values, n_boot=2000, level=0.95, seed=0):\n'
    '    """对「每块电池一个数」的指标做 bootstrap，返回 (均值, 下界, 上界)。\n'
    '\n'
    '    ``n = 电池数`` 才是泛化不确定性的来源（而不是随机种子）。电池只有 4–5 块\n'
    '    时区间会很宽——这是诚实的，也正是读者最想看到的。\n'
    '    """\n'
    '    array = np.asarray(\n'
    '        [value for value in values\n'
    '         if value is not None and np.isfinite(value)],\n'
    '        dtype=np.float64)\n'
    '    if len(array) == 0:\n'
    "        return float('nan'), float('nan'), float('nan')\n"
    '    if len(array) == 1:\n'
    '        value = float(array[0])\n'
    '        return value, value, value\n'
    '    rng = np.random.default_rng(seed)\n'
    '    means = rng.choice(\n'
    '        array, size=(int(n_boot), len(array)), replace=True).mean(axis=1)\n'
    '    lo, hi = np.percentile(\n'
    '        means, [(1 - level) / 2 * 100, (1 + level) / 2 * 100])\n'
    '    return float(array.mean()), float(lo), float(hi)\n'
)

# ---- core/preprocess.py ----
_MODULE_SOURCES['core.preprocess'] = (
    'import numpy as np\n'
    'from dataclasses import dataclass\n'
    'from numpy.lib.stride_tricks import sliding_window_view\n'
    '\n'
    '\n'
    '@dataclass(frozen=True)\n'
    'class LeaveOneOutSplit:\n'
    '    """A strict fold whose target battery is used only for final evaluation."""\n'
    '\n'
    '    train_x: np.ndarray\n'
    '    train_y: np.ndarray\n'
    '    val_x: np.ndarray\n'
    '    val_y: np.ndarray\n'
    '    test_x: np.ndarray\n'
    '    test_y: np.ndarray\n'
    '    target_sequence: np.ndarray\n'
    '    initial_window: np.ndarray\n'
    '    training_values: np.ndarray\n'
    '    training_batteries: tuple\n'
    '\n'
    '\n'
    '@dataclass(frozen=True)\n'
    'class OutlierFilterResult:\n'
    '    """Auditable result of capacity cleaning.\n'
    '\n'
    '    ``mask`` / ``indices`` / ``removed_indices`` 反映**实际**处理结果；\n'
    '    ``marked_indices`` 始终是「被判定为可疑」的原始下标，无论是否真的删除\n'
    '    （A12：默认只标记不删除，因为容量再生是真实物理而不是噪声）。\n'
    '    """\n'
    '\n'
    '    indices: np.ndarray\n'
    '    mask: np.ndarray\n'
    '    removed_indices: np.ndarray\n'
    '    protected_indices: np.ndarray\n'
    '    reasons: dict\n'
    '    marked_indices: np.ndarray = None\n'
    '\n'
    '    @property\n'
    '    def removed_count(self):\n'
    '        return int(len(self.removed_indices))\n'
    '\n'
    '    @property\n'
    '    def marked_count(self):\n'
    '        marked = self.marked_indices\n'
    '        return 0 if marked is None else int(len(marked))\n'
    '\n'
    '    @property\n'
    '    def mode(self):\n'
    '        """``\'delete\'``（真的删了）/ ``\'mark\'``（只标记）/ ``\'off\'``。"""\n'
    '        if self.marked_count and not self.removed_count:\n'
    "            return 'mark'\n"
    "        return 'delete' if self.removed_count else 'off'\n"
    '\n'
    '\n'
    'class CapacityScaler:\n'
    '    """Capacity scaling fitted once on training data and safe to serialize as JSON."""\n'
    '\n'
    "    METHODS = ('rated', 'minmax', 'zscore')\n"
    '\n'
    "    def __init__(self, method='rated', rated_capacity=1.1):\n"
    '        method = str(method).lower()\n'
    '        if method not in self.METHODS:\n'
    "            raise ValueError(f'不支持的归一化方式: {method}')\n"
    '        if not np.isfinite(rated_capacity) or rated_capacity <= 0:\n'
    "            raise ValueError('额定容量必须是有限正数')\n"
    '        self.method = method\n'
    '        self.rated_capacity = float(rated_capacity)\n'
    '        self.minimum = None\n'
    '        self.maximum = None\n'
    '        self.mean = None\n'
    '        self.std = None\n'
    '        self._fitted = False\n'
    '\n'
    '    def fit(self, values):\n'
    '        values = np.asarray(values, dtype=np.float64).reshape(-1)\n'
    '        if len(values) == 0 or not np.all(np.isfinite(values)):\n'
    "            raise ValueError('scaler 训练数据必须包含有限数值')\n"
    '        self.minimum = float(np.min(values))\n'
    '        self.maximum = float(np.max(values))\n'
    '        self.mean = float(np.mean(values))\n'
    '        self.std = float(np.std(values))\n'
    '        self._fitted = True\n'
    '        return self\n'
    '\n'
    '    def _check_fitted(self):\n'
    '        if not self._fitted:\n'
    "            raise RuntimeError('scaler 尚未拟合')\n"
    '\n'
    '    def transform(self, values):\n'
    '        self._check_fitted()\n'
    '        values = np.asarray(values, dtype=np.float32)\n'
    "        if self.method == 'rated':\n"
    '            return values / self.rated_capacity\n'
    "        if self.method == 'minmax':\n"
    '            scale = self.maximum - self.minimum\n'
    '            if scale <= 1e-12:\n'
    '                return np.zeros_like(values, dtype=np.float32)\n'
    '            return (values - self.minimum) / scale\n'
    '        scale = self.std if self.std > 1e-12 else 1.0\n'
    '        return (values - self.mean) / scale\n'
    '\n'
    '    def inverse_transform(self, values):\n'
    '        self._check_fitted()\n'
    '        values = np.asarray(values, dtype=np.float32)\n'
    "        if self.method == 'rated':\n"
    '            return values * self.rated_capacity\n'
    "        if self.method == 'minmax':\n"
    '            return values * (self.maximum - self.minimum) + self.minimum\n'
    '        scale = self.std if self.std > 1e-12 else 1.0\n'
    '        return values * scale + self.mean\n'
    '\n'
    '    def to_dict(self):\n'
    '        self._check_fitted()\n'
    '        return {\n'
    "            'method': self.method,\n"
    "            'rated_capacity': self.rated_capacity,\n"
    "            'minimum': self.minimum,\n"
    "            'maximum': self.maximum,\n"
    "            'mean': self.mean,\n"
    "            'std': self.std,\n"
    '        }\n'
    '\n'
    '    @classmethod\n'
    '    def from_dict(cls, data):\n'
    '        if not isinstance(data, dict):\n'
    "            raise ValueError('scaler 元数据必须是对象')\n"
    '        scaler = cls(\n'
    "            method=data.get('method', 'rated'),\n"
    "            rated_capacity=data.get('rated_capacity', 1.1),\n"
    '        )\n'
    "        required = ('minimum', 'maximum', 'mean', 'std')\n"
    '        if any(key not in data for key in required):\n'
    "            raise ValueError('scaler 元数据缺少拟合参数')\n"
    '        for key in required:\n'
    '            value = data[key]\n'
    '            if value is None or not np.isfinite(value):\n'
    "                raise ValueError(f'scaler 元数据字段无效: {key}')\n"
    '            setattr(scaler, key, float(value))\n'
    '        scaler._fitted = True\n'
    '        return scaler\n'
    '\n'
    '\n'
    '#: 离群点处理模式（A12）\n'
    "#:   ``'mark'``  —— 只标记可疑点，**保留数据**（默认）。窗口均值对快速下降段和\n"
    '#:                 NASA 的容量再生（真实物理，不是噪声）都会滞后，直接删会误伤。\n'
    "#:   ``'delete'``—— 真的丢弃（旧行为，对含趋势序列容易误判）。\n"
    "#:   ``'off'``   —— 完全不检测。\n"
    "OUTLIER_MODES = ('off', 'mark', 'delete')\n"
    '\n'
    '\n'
    'def filter_capacity_outliers(array, bins=40, enabled=True,\n'
    '                             protect_knees=True, mode=None):\n'
    '    """Causally filter local 2-sigma outliers without consulting future cycles.\n'
    '\n'
    '    判定规则（只读历史窗口，不看未来）不变；``mode`` 决定**如何处理**判定结果\n'
    "    （A12）：``'mark'``（默认）只标记并保留数据，``'delete'`` 才真的丢弃，\n"
    "    ``'off'`` 不检测。``enabled=False`` 等价于 ``mode='off'``；\n"
    '    显式给了 ``mode`` 时以 ``mode`` 为准。\n'
    '    """\n'
    '    values = np.asarray(array, dtype=np.float64).reshape(-1)\n'
    '    if bins <= 0:\n'
    "        raise ValueError('异常值窗口大小必须大于 0')\n"
    '    if mode is None:\n'
    "        mode = 'off' if not enabled else 'delete'\n"
    '    if mode not in OUTLIER_MODES:\n'
    '        raise ValueError(\n'
    "            f'不支持的离群点模式: {mode}（可选 {OUTLIER_MODES}）')\n"
    "    detect = mode in ('mark', 'delete')\n"
    "    delete = mode == 'delete'\n"
    '\n'
    '    finite = np.isfinite(values)\n'
    '    mask = finite.copy()\n'
    '    reasons = {\n'
    "        int(index): '非有限容量值'\n"
    '        for index in np.flatnonzero(~finite)\n'
    '    }\n'
    '    protected = set()\n'
    '    marked = set(int(index) for index in np.flatnonzero(~finite))\n'
    '\n'
    '    if detect:\n'
    '        for index, value in enumerate(values):\n'
    '            if not finite[index]:\n'
    '                continue\n'
    '            start = max(0, index - bins)\n'
    '            history_indices = [\n'
    '                item for item in range(start, index)\n'
    '                if finite[item] and (mask[item] or not delete)\n'
    '            ]\n'
    '            if len(history_indices) < 5:\n'
    '                continue\n'
    '            history = values[history_indices]\n'
    '            mean = float(np.mean(history))\n'
    '            sigma = float(np.std(history))\n'
    '            tolerance = max(1e-12, abs(mean) * 1e-12)\n'
    '            scale = max(sigma, abs(mean) * 0.005, tolerance)\n'
    '            lower = mean - 2 * scale\n'
    '            upper = mean + 2 * scale\n'
    '            if lower - tolerance <= value <= upper + tolerance:\n'
    '                continue\n'
    '\n'
    '            previous_index = history_indices[-1]\n'
    '            previous = values[previous_index]\n'
    '            drop_threshold = max(abs(previous) * 0.02, tolerance)\n'
    '            follows_protected_drop = (\n'
    '                previous_index in protected and value <= previous + tolerance)\n'
    '            starts_degradation_knee = previous - value >= drop_threshold\n'
    '            if protect_knees and (\n'
    '                    starts_degradation_knee or follows_protected_drop):\n'
    '                protected.add(index)\n'
    '                continue\n'
    '\n'
    '            marked.add(index)\n'
    '            reasons[index] = (\n'
    "                f'超出仅基于历史局部窗口的均值±2σ范围 '\n"
    "                f'[{lower:.6g}, {upper:.6g}]')\n"
    '            if delete:\n'
    '                mask[index] = False\n'
    '\n'
    '    indices = np.flatnonzero(mask).astype(int)\n'
    '    removed = np.flatnonzero(~mask).astype(int)\n'
    '    return OutlierFilterResult(\n'
    '        indices=indices,\n'
    '        mask=mask,\n'
    '        removed_indices=removed,\n'
    '        protected_indices=np.asarray(sorted(protected), dtype=int),\n'
    '        reasons=reasons,\n'
    '        marked_indices=np.asarray(sorted(marked), dtype=int),\n'
    '    )\n'
    '\n'
    '\n'
    'def drop_outlier(array, count, bins):\n'
    '    """Backward-compatible index-only wrapper."""\n'
    '    values = np.asarray(array).reshape(-1)[:count]\n'
    '    return filter_capacity_outliers(values, bins=bins).indices\n'
    '\n'
    '\n'
    'def build_instances(sequence, window_size):\n'
    '    x, y = [], []\n'
    '    for i in range(len(sequence) - window_size):\n'
    '        features = sequence[i:i + window_size]\n'
    '        target = sequence[i + window_size]\n'
    '        x.append(features)\n'
    '        y.append(target)\n'
    '    return np.array(x).astype(np.float32), np.array(y).astype(np.float32)\n'
    '\n'
    '\n'
    'def build_instances_fast(sequence, window_size):\n'
    '    """与 :func:`build_instances` 等价的向量化实现。\n'
    '\n'
    '    零拷贝滑窗，再各复制一次得到 (X, y)；含「长度不足」的边界处理。\n'
    '    """\n'
    '    seq = np.asarray(sequence, dtype=np.float32).reshape(-1)\n'
    '    if len(seq) <= window_size:\n'
    '        return (np.empty((0, window_size), np.float32),\n'
    '                np.empty((0,), np.float32))\n'
    '    view = sliding_window_view(seq, window_size + 1)          # (N, W+1)\n'
    '    return view[:, :-1].copy(), view[:, -1].copy()\n'
    '\n'
    '\n'
    '#: 多特征输入默认使用的列。\n'
    '#:\n'
    "#: 注意 ``dq_v`` 就是适配器里原来叫 ``'SoH'`` 的那一列（电压窗口内放电的容量\n"
    '#: 差），它是**健康指标 HI**，不是 SOH（SOH = C / C_rated）。改名以避免混淆。\n'
    "FEATURE_COLS = ('capacity', 'dq_v', 'CCCT', 'CVCT', 'resistance')\n"
    '\n'
    '\n'
    'def build_instances_mf(frame, window, cols=FEATURE_COLS, fill_values=None):\n'
    '    """多特征滑窗。返回 ``X:(N, W, F)``、``y:(N,)``（下一个循环的容量，永远是第 0 列）。\n'
    '\n'
    '    缺失值只做**因果前向填充**（只用过去），剩余缺失用训练集统计量\n'
    '    ``fill_values`` 填充，不会把未来信息泄漏回窗口。\n'
    '    """\n'
    '\n'
    '    cols = [c for c in cols if c in frame.columns]\n'
    "    if not cols or 'capacity' not in cols:\n"
    "        raise ValueError('多特征滑窗至少需要 capacity 列')\n"
    '    # 容量永远是第 0 列，y 从它取\n'
    "    if cols[0] != 'capacity':\n"
    "        cols = ['capacity'] + [c for c in cols if c != 'capacity']\n"
    '\n'
    "    selected = frame.loc[:, cols].astype('float32')\n"
    '    # 先用「仅列」的前向填充（不跨列），再按列用训练集统计量兜底\n'
    '    selected = selected.ffill()\n'
    '    if fill_values is not None:\n'
    '        selected = selected.fillna(\n'
    '            {c: fill_values.get(c, 0.0) for c in cols})\n'
    '    selected = selected.fillna(0.0)\n'
    '    array = selected.to_numpy(dtype=np.float32)\n'
    '    features = array.shape[1]\n'
    '    if len(array) <= window:\n'
    '        return (np.empty((0, window, features), np.float32),\n'
    '                np.empty((0,), np.float32))\n'
    '    view = sliding_window_view(array, (window + 1, features))[:, 0]   # (N, W+1, F)\n'
    '    return view[:, :-1, :].copy(), view[:, -1, 0].copy()\n'
    '\n'
    '\n'
    'def feature_fill_values(frame, cols=FEATURE_COLS):\n'
    '    """用训练集统计量（均值）填充剩余缺失；只允许在训练电池上拟合。"""\n'
    '    values = {}\n'
    '    for column in cols:\n'
    '        if column not in frame.columns:\n'
    '            continue\n'
    "        series = frame[column].astype('float64')\n"
    '        mean = series.mean(skipna=True)\n'
    '        values[column] = float(mean) if np.isfinite(mean) else 0.0\n'
    '    return values\n'
    '\n'
    '\n'
    'class FeatureScaler:\n'
    '    """逐特征 z-score；只用训练电池的窗口拟合，可 JSON 序列化后随模型保存。"""\n'
    '\n'
    '    def __init__(self, mean=None, std=None):\n'
    '        self.mean = None if mean is None else np.asarray(mean, dtype=np.float64)\n'
    '        self.std = None if std is None else np.asarray(std, dtype=np.float64)\n'
    '\n'
    '    def fit(self, features):\n'
    '        array = np.asarray(features, dtype=np.float64)\n'
    '        if array.ndim == 2:\n'
    '            array = array.reshape(array.shape[0], 1, -1)\n'
    '        flat = array.reshape(-1, array.shape[-1])\n'
    '        self.mean = np.nanmean(flat, axis=0)\n'
    '        std = np.nanstd(flat, axis=0)\n'
    '        self.mean = np.where(np.isfinite(self.mean), self.mean, 0.0)\n'
    '        self.std = np.where(\n'
    '            np.isfinite(std) & (std > 1e-8), std, 1.0)\n'
    '        return self\n'
    '\n'
    '    def transform(self, features):\n'
    '        if self.mean is None or self.std is None:\n'
    "            raise RuntimeError('FeatureScaler 尚未拟合')\n"
    '        array = np.asarray(features, dtype=np.float32)\n'
    '        return ((array - self.mean) / self.std).astype(np.float32)\n'
    '\n'
    '    def to_dict(self):\n'
    '        if self.mean is None:\n'
    "            raise RuntimeError('FeatureScaler 尚未拟合')\n"
    "        return {'mean': self.mean.tolist(), 'std': self.std.tolist()}\n"
    '\n'
    '    @classmethod\n'
    '    def from_dict(cls, data):\n'
    "        if not isinstance(data, dict) or 'mean' not in data or 'std' not in data:\n"
    "            raise ValueError('FeatureScaler 元数据缺少 mean/std')\n"
    "        return cls(mean=data['mean'], std=data['std'])\n"
    '\n'
    '\n'
    'def fit_persistence_blend(windows, targets, model_prediction):\n'
    '    """Fit validation-only shrinkage toward the last observed capacity."""\n'
    '    windows = np.asarray(windows, dtype=np.float64)\n'
    '    targets = np.asarray(targets, dtype=np.float64).reshape(-1)\n'
    '    prediction = np.asarray(model_prediction, dtype=np.float64).reshape(-1)\n'
    '    if windows.ndim != 2 or windows.shape[1] == 0:\n'
    "        raise ValueError('校准窗口必须是非空二维数组')\n"
    '    if len(windows) != len(targets) or len(targets) != len(prediction):\n'
    "        raise ValueError('校准窗口、标签和预测长度必须一致')\n"
    '    if not (np.all(np.isfinite(windows[:, -1])) and\n'
    '            np.all(np.isfinite(targets)) and\n'
    '            np.all(np.isfinite(prediction))):\n'
    "        raise ValueError('校准数据必须全部为有限数值')\n"
    '\n'
    '    persistence = windows[:, -1]\n'
    '    model_delta = prediction - persistence\n'
    '    target_delta = targets - persistence\n'
    '    denominator = float(np.dot(model_delta, model_delta))\n'
    '    if denominator <= 1e-12:\n'
    '        return 0.0\n'
    '    blend = float(np.dot(model_delta, target_delta) / denominator)\n'
    '    return float(np.clip(blend, 0.0, 1.0))\n'
    '\n'
    '\n'
    'def generate_one_step_predictions(sequence, window_size, predict_batch):\n'
    '    """Predict every next point using the observed history available at that step."""\n'
    '    test_x, test_y = build_instances(sequence, window_size)\n'
    '    if len(test_x) == 0:\n'
    "        raise ValueError('序列长度不足，无法执行一步预测')\n"
    '    prediction = np.asarray(predict_batch(test_x), dtype=np.float64).reshape(-1)\n'
    '    if len(prediction) != len(test_y):\n'
    "        raise ValueError('一步预测结果长度与测试标签不一致')\n"
    '    return test_y.astype(np.float64), prediction\n'
    '\n'
    '\n'
    'def generate_recursive_predictions(sequence, window_size, predict_batch):\n'
    '    """Forecast the future from one observed window, feeding predictions back in."""\n'
    '    sequence = np.asarray(sequence, dtype=np.float64).reshape(-1)\n'
    '    if len(sequence) <= window_size:\n'
    "        raise ValueError('序列长度不足，无法执行递归未来预测')\n"
    '\n'
    '    history = sequence[:window_size].tolist()\n'
    '    prediction = []\n'
    '    for _ in range(len(sequence) - window_size):\n'
    '        window = np.asarray(history[-window_size:], dtype=np.float32).reshape(1, -1)\n'
    '        next_values = np.asarray(\n'
    '            predict_batch(window), dtype=np.float64).reshape(-1)\n'
    '        if len(next_values) != 1 or not np.isfinite(next_values[0]):\n'
    "            raise ValueError('递归预测器必须为单个窗口返回一个有限数值')\n"
    '        next_value = float(next_values[0])\n'
    '        prediction.append(next_value)\n'
    '        history.append(next_value)\n'
    '\n'
    '    truth = sequence[window_size:]\n'
    '    return truth, np.asarray(prediction, dtype=np.float64)\n'
    '\n'
    '\n'
    'def prepare_leave_one_out_split(data_dict, name, window_size=8,\n'
    '                                validation_fraction=0.2):\n'
    '    """Build a zero-shot cross-battery train/validation/test fold.\n'
    '\n'
    '    The held-out battery contributes no label or feature to model fitting,\n'
    '    preprocessing fitting, early stopping, or model selection. Validation is a\n'
    '    deterministic trailing period taken separately from every training battery.\n'
    '    """\n'
    '    if name not in data_dict:\n'
    "        raise KeyError(f'目标电池不存在: {name}')\n"
    '    if window_size < 1:\n'
    "        raise ValueError('窗口大小必须大于 0')\n"
    '    if not 0.0 < validation_fraction < 1.0:\n'
    "        raise ValueError('验证集比例必须在 0 和 1 之间')\n"
    '\n'
    '    train_x_parts, train_y_parts = [], []\n'
    '    val_x_parts, val_y_parts = [], []\n'
    '    training_values = []\n'
    '    training_batteries = []\n'
    '\n'
    '    for battery_name, battery_data in data_dict.items():\n'
    '        if battery_name == name:\n'
    '            continue\n'
    "        sequence = np.asarray(battery_data['capacity'], dtype=np.float32)\n"
    '        data_x, data_y = build_instances(sequence, window_size)\n'
    '        if len(data_x) < 2:\n'
    '            continue\n'
    '\n'
    '        val_count = max(1, int(np.ceil(len(data_x) * validation_fraction)))\n'
    '        train_count = len(data_x) - val_count\n'
    '        if train_count < 1:\n'
    '            continue\n'
    '\n'
    '        train_x_parts.append(data_x[:train_count])\n'
    '        train_y_parts.append(data_y[:train_count])\n'
    '        val_x_parts.append(data_x[train_count:])\n'
    '        val_y_parts.append(data_y[train_count:])\n'
    '        training_values.append(sequence)\n'
    '        training_batteries.append(battery_name)\n'
    '\n'
    '    if not train_x_parts or not val_x_parts:\n'
    "        raise ValueError('训练电池不足，无法建立独立训练集和验证集')\n"
    '\n'
    '    target_sequence = np.asarray(\n'
    "        data_dict[name]['capacity'], dtype=np.float32)\n"
    '    test_x, test_y = build_instances(target_sequence, window_size)\n'
    '    if len(test_x) == 0:\n'
    "        raise ValueError(f'目标电池 {name} 的循环数不足')\n"
    '\n'
    '    return LeaveOneOutSplit(\n'
    '        train_x=np.vstack(train_x_parts).astype(np.float32),\n'
    '        train_y=np.concatenate(train_y_parts).astype(np.float32),\n'
    '        val_x=np.vstack(val_x_parts).astype(np.float32),\n'
    '        val_y=np.concatenate(val_y_parts).astype(np.float32),\n'
    '        test_x=test_x,\n'
    '        test_y=test_y,\n'
    '        target_sequence=target_sequence,\n'
    '        initial_window=target_sequence[:window_size].copy(),\n'
    '        training_values=np.concatenate(training_values).astype(np.float32),\n'
    '        training_batteries=tuple(training_batteries),\n'
    '    )\n'
    '\n'
    '\n'
    'def get_train_test(data_dict, name, window_size=8):\n'
    '    """Backward-compatible strict split without target-battery training labels."""\n'
    '    split = prepare_leave_one_out_split(data_dict, name, window_size)\n'
    '    train_x = np.vstack((split.train_x, split.val_x))\n'
    '    train_y = np.concatenate((split.train_y, split.val_y))\n'
    '    train_data = list(split.initial_window)\n'
    '    test_data = list(split.target_sequence[window_size:])\n'
    '    return train_x, train_y, train_data, test_data\n'
    '\n'
    '\n'
    "def normalize_data(data, method='rated', rated_capacity=1.1):\n"
    '    return CapacityScaler(method, rated_capacity).fit(data).transform(data)\n'
)

# ---- core/prediction.py ----
_MODULE_SOURCES['core.prediction'] = (
    'import numpy as np\n'
    'import torch\n'
    '\n'
    'from core.preprocess import CapacityScaler, FeatureScaler\n'
    '\n'
    '\n'
    "RECURRENT_MODELS = ('RNN', 'GRU', 'LSTM')\n"
    '\n'
    '\n'
    'def resolve_inference_device(device):\n'
    '    """Resolve a supported inference device and fall back safely to CPU."""\n'
    '    try:\n'
    '        requested = torch.device(device)\n'
    '    except (TypeError, RuntimeError) as exc:\n'
    "        raise ValueError(f'无效的预测设备：{device}') from exc\n"
    "    if requested.type == 'cuda':\n"
    '        if not torch.cuda.is_available():\n'
    "            return torch.device('cpu')\n"
    '        if requested.index is not None and requested.index >= torch.cuda.device_count():\n'
    "            return torch.device('cpu')\n"
    '        return requested\n'
    "    if requested.type != 'cpu':\n"
    "        return torch.device('cpu')\n"
    '    return requested\n'
    '\n'
    '\n'
    'def scaler_from_metadata(metadata):\n'
    '    """Restore the fitted scaler, with a rated-capacity fallback for old models."""\n'
    "    scaler_data = metadata.get('scaler')\n"
    '    if scaler_data is not None:\n'
    '        return CapacityScaler.from_dict(scaler_data)\n'
    '    rated_capacity = (\n'
    "        metadata.get('rated_capacity', 1.1)\n"
    "        if metadata.get('mode') in RECURRENT_MODELS else 1.0\n"
    '    )\n'
    '    return CapacityScaler(\n'
    "        method='rated', rated_capacity=rated_capacity).fit([rated_capacity])\n"
    '\n'
    '\n'
    'def feature_names_from_metadata(metadata):\n'
    '    """模型使用的特征名列表；旧模型（无 feature_schema）按单特征容量处理。"""\n'
    "    schema = metadata.get('feature_schema')\n"
    '    if isinstance(schema, dict):\n'
    "        names = schema.get('features')\n"
    '        if isinstance(names, (list, tuple)) and names:\n'
    '            return [str(item) for item in names]\n'
    "        if schema.get('feature') == 'capacity':\n"
    "            return ['capacity']\n"
    "    return ['capacity']\n"
    '\n'
    '\n'
    'def feature_count_from_metadata(metadata):\n'
    '    return len(feature_names_from_metadata(metadata))\n'
    '\n'
    '\n'
    'def feature_scaler_from_metadata(metadata):\n'
    '    """多特征模型随模型保存的 FeatureScaler；单特征模型返回 None。"""\n'
    "    schema = metadata.get('feature_schema')\n"
    "    if isinstance(schema, dict) and isinstance(schema.get('feature_scaler'), dict):\n"
    "        return FeatureScaler.from_dict(schema['feature_scaler'])\n"
    '    return None\n'
    '\n'
    '\n'
    'def prepare_windows(windows, metadata):\n'
    '    """把原始窗口整理成模型输入形状，并返回 (容量窗口, 模型输入)。\n'
    '\n'
    '    单特征：``(N, W)`` -> 输入 ``(N, W)``；\n'
    '    多特征：``(N, W, F)`` 或 ``(N, W)``（此时其余特征用窗口末值占位）-> 输入\n'
    '    ``(N, W, F)``。\n'
    '    """\n'
    '    names = feature_names_from_metadata(metadata)\n'
    "    window_size = int(metadata['window_size'])\n"
    '    array = np.asarray(windows, dtype=np.float32)\n'
    '\n'
    '    if array.ndim == 1:\n'
    '        array = array.reshape(1, -1)\n'
    '    if array.ndim == 3:\n'
    '        if array.shape[1] != window_size:\n'
    '            raise ValueError(\n'
    "                f'预测窗口长度应为 {window_size}，实际为 {array.shape[1]}')\n"
    '        if array.shape[2] != len(names):\n'
    '            raise ValueError(\n'
    "                f'预测特征数应为 {len(names)}，实际为 {array.shape[2]}')\n"
    '        capacity_windows = array[:, :, 0]\n'
    '        return capacity_windows, array\n'
    '\n'
    '    if array.ndim != 2:\n'
    "        raise ValueError('预测输入必须是二维窗口或三维多特征窗口')\n"
    '    if array.shape[1] != window_size:\n'
    '        raise ValueError(\n'
    "            f'预测窗口长度应为 {window_size}，实际为 {array.shape[1]}')\n"
    '\n'
    '    capacity_windows = array\n'
    '    if len(names) == 1:\n'
    '        return capacity_windows, array\n'
    '\n'
    '    # 只给了容量窗口但模型是多特征的：其余特征用窗口末值沿时间轴占位。\n'
    '    # 这是「未来工况未知」时的保守假设，调用方应在结果里标注。\n'
    '    expanded = np.repeat(\n'
    '        capacity_windows[:, :, None], len(names), axis=2).astype(np.float32)\n'
    '    return capacity_windows, expanded\n'
    '\n'
    '\n'
    'def scale_model_input(model_input, metadata):\n'
    '    """按模型保存的 scaler 归一化**模型输入**（训练与预测共用这一处逻辑）。\n'
    '\n'
    '    ``model_input`` 形状 ``(N, W)`` 或 ``(N, W, F)``，值是原始 Ah / 原始特征量纲。\n'
    '    单特征：整块按 ``CapacityScaler`` 归一化；\n'
    '    多特征：容量通道用 ``CapacityScaler``，其余通道用随模型保存的\n'
    '    ``FeatureScaler``（z-score）。这样训练与推理的预处理**完全一致**。\n'
    '    """\n'
    '    array = np.asarray(model_input, dtype=np.float32)\n'
    '    if array.ndim == 2:\n'
    '        array = array[:, :, None]\n'
    '    names = feature_names_from_metadata(metadata)\n'
    '    scaler = scaler_from_metadata(metadata)\n'
    '\n'
    '    if len(names) == 1:\n'
    '        return scaler.transform(array[:, :, 0]).astype(np.float32)\n'
    '\n'
    '    scaled = np.array(array, dtype=np.float32, copy=True)\n'
    '    scaled[:, :, 0] = scaler.transform(array[:, :, 0])\n'
    '    feature_scaler = feature_scaler_from_metadata(metadata)\n'
    '    if feature_scaler is not None:\n'
    '        scaled = feature_scaler.transform(scaled)\n'
    '    return scaled\n'
    '\n'
    '\n'
    "def predict_capacity_batch(model, metadata, windows, device='cpu'):\n"
    '    """Use the model\'s persisted scaler for both batch and real-time prediction."""\n'
    '    capacity_windows, model_input = prepare_windows(windows, metadata)\n'
    "    mode = metadata['mode']\n"
    '    scaled_input = scale_model_input(model_input, metadata)\n'
    '\n'
    '    if mode in RECURRENT_MODELS:\n'
    '        resolved_device = resolve_inference_device(device)\n'
    "        if not hasattr(model, 'to'):\n"
    "            raise ValueError('循环模型不支持设备切换')\n"
    '        model_on_device = model.to(resolved_device)\n'
    '        tensor = torch.from_numpy(\n'
    '            scaled_input.reshape(len(scaled_input), scaled_input.shape[1], -1)\n'
    '        ).to(resolved_device)\n'
    "        if hasattr(model_on_device, 'eval'):\n"
    '            model_on_device.eval()\n'
    '        with torch.no_grad():\n'
    '            scaled_prediction = model_on_device(tensor)\n'
    '        scaled_prediction = np.asarray(\n'
    '            scaled_prediction.detach().cpu().numpy(),\n'
    '            dtype=np.float32).reshape(-1)\n'
    '    else:\n'
    '        flat = scaled_input.reshape(len(scaled_input), -1)\n'
    '        scaled_prediction = np.asarray(\n'
    '            model.predict(flat), dtype=np.float32).reshape(-1)\n'
    '\n'
    '    scaler = scaler_from_metadata(metadata)\n'
    '    prediction = scaler.inverse_transform(scaled_prediction).reshape(-1)\n'
    "    blend = float(metadata.get('persistence_blend', 1.0))\n"
    '    if not np.isfinite(blend) or not 0.0 <= blend <= 1.0:\n'
    "        raise ValueError('持久性基线校准系数必须在 0 和 1 之间')\n"
    '    persistence = capacity_windows[:, -1].astype(np.float32)\n'
    '    return persistence + blend * (prediction - persistence)\n'
)

# ---- core/baselines.py ----
_MODULE_SOURCES['core.baselines'] = (
    '"""经验基线：任何模型都必须先赢过它们。\n'
    '\n'
    '每次评估都并排输出三条基线：\n'
    '\n'
    '- **持久性（平推）**：下一个循环 = 上一个循环；\n'
    '- **线性外推**：用窗口内最小二乘斜率向前推一步；\n'
    '- **双指数**：``C(k) = a·e^{bk} + c·e^{dk}``，电池预测文献里最常用的经验基线。\n'
    '\n'
    '前两条是「逐步」基线（可以放进递归预测器，每步重新拟合）；双指数是**直接多步**\n'
    '基线——它在预测起点上对历史拟合一次，然后整段外推（每步重拟合既慢又没有意义）。\n'
    '"""\n'
    '\n'
    'import warnings\n'
    '\n'
    'import numpy as np\n'
    'from scipy.optimize import OptimizeWarning, curve_fit\n'
    '\n'
    '\n'
    'def persistence_step(windows):\n'
    '    """平推：下一个循环 = 上一个循环。任何模型都必须先赢过它。"""\n'
    '    windows = np.asarray(windows, dtype=np.float64)\n'
    '    return windows[:, -1]\n'
    '\n'
    '\n'
    'def linear_step(windows):\n'
    '    """线性外推：用窗口内最小二乘斜率向前推一步（按行独立拟合）。"""\n'
    '    windows = np.asarray(windows, dtype=np.float64)\n'
    '    if windows.ndim == 1:\n'
    '        windows = windows.reshape(1, -1)\n'
    '    x = np.arange(windows.shape[1], dtype=np.float64)\n'
    '    out = np.empty(len(windows), dtype=np.float64)\n'
    '    for row, values in enumerate(windows):\n'
    '        slope = np.polyfit(x, values, 1)[0]\n'
    '        out[row] = values[-1] + slope\n'
    '    return out\n'
    '\n'
    '\n'
    'def _dexp(k, a, b, c, d):\n'
    '    return a * np.exp(b * k) + c * np.exp(d * k)\n'
    '\n'
    '\n'
    'def double_exp_forecast(history, steps):\n'
    '    """双指数经验退化模型 ``C(k) = a·e^{bk} + c·e^{dk}``。\n'
    '\n'
    '    只用 ``history``（预测起点之前的数据）拟合；拟合失败或外推结果**不可信**时\n'
    '    自动回退为线性外推。返回长度为 ``steps`` 的预测序列。\n'
    '\n'
    '    「不可信」的判据：外推值出现非有限数、跑到负数、或高于历史最大值的 1.5 倍\n'
    '    （电池容量不会越用越高，双指数在长程外推时容易发散）。\n'
    '    """\n'
    '    history = np.asarray(history, dtype=np.float64).reshape(-1)\n'
    '    if steps <= 0:\n'
    '        return np.empty(0, dtype=np.float64)\n'
    '    if len(history) < 4:\n'
    '        return np.full(steps, history[-1] if len(history) else 0.0)\n'
    '\n'
    '    y = history\n'
    '    k = np.arange(len(y), dtype=np.float64)\n'
    '    try:\n'
    '        p0 = (max(y[0], 1e-6) * 0.95, -1e-3, max(y[0], 1e-6) * 0.05, 1e-2)\n'
    '        lo = (0.0, -0.1, -5.0, -0.1)\n'
    '        hi = (5.0, 0.0, 5.0, 0.1)\n'
    '        with warnings.catch_warnings():\n'
    "            warnings.simplefilter('ignore', OptimizeWarning)\n"
    '            popt, _ = curve_fit(_dexp, k, y, p0=p0, bounds=(lo, hi), maxfev=20000)\n'
    '        future = _dexp(np.arange(len(y), len(y) + steps, dtype=np.float64), *popt)\n'
    '        if (np.all(np.isfinite(future))\n'
    '                and np.all(future >= 0.0)\n'
    '                and float(np.max(future)) <= 1.5 * float(np.max(y))):\n'
    '            return future\n'
    '    except (RuntimeError, ValueError, TypeError):\n'
    '        pass\n'
    '\n'
    '    tail = min(len(k), 16)\n'
    '    slope = np.polyfit(k[-tail:], y[-tail:], 1)[0]\n'
    '    return y[-1] + slope * np.arange(1, steps + 1, dtype=np.float64)\n'
    '\n'
    '\n'
    'def double_exp_direct(history, steps):\n'
    '    """直接多步基线：在预测起点上拟合一次，然后整段外推。"""\n'
    '    return double_exp_forecast(history, steps)\n'
    '\n'
    '\n'
    '#: 基线注册表：名称 -> 规格\n'
    "#:   kind='step'   : step_fn(windows) -> 下一步容量（可放进递归预测器）\n"
    "#:   kind='direct' : direct_fn(history, steps) -> 整段预测（只拟合一次）\n"
    'BASELINES = {\n'
    "    '平推基线': {'kind': 'step', 'fn': persistence_step},\n"
    "    '线性外推': {'kind': 'step', 'fn': linear_step},\n"
    "    '双指数': {'kind': 'direct', 'fn': double_exp_direct},\n"
    '}\n'
    '\n'
    '\n'
    'def baseline_step(name):\n'
    '    """取「逐步」基线的 step_fn。"""\n'
    '    spec = BASELINES[name]\n'
    "    if spec['kind'] != 'step':\n"
    "        raise ValueError(f'{name} 是直接多步基线，不能作为 step_fn 使用')\n"
    "    return spec['fn']\n"
    '\n'
    '\n'
    'def baseline_direct(name):\n'
    '    """取「直接多步」基线的 direct_fn。"""\n'
    '    spec = BASELINES[name]\n'
    "    if spec['kind'] != 'direct':\n"
    "        raise ValueError(f'{name} 是逐步基线，不能作为 direct_fn 使用')\n"
    "    return spec['fn']\n"
)

# ---- core/protocol.py ----
_MODULE_SOURCES['core.protocol'] = (
    '"""统一的「选超参 → 重训 → 滚动评估」协议。\n'
    '\n'
    '目标：让**评估路径**和**部署路径**使用同一套流程，并且评估的是真正的未来预测。\n'
    '\n'
    '  外层  留一电池 (LOBO)：目标电池全程不参与任何拟合 / 选择；\n'
    '  内层  在训练电池里再做留一电池交叉验证，用「多步滚动预测误差」选超参\n'
    '        （验证对象是一块没见过的电池，和最终使用场景一致）；\n'
    '  定型  选定超参后，用全部训练电池的全部窗口重训一次，得到最终模型；\n'
    '  评估  在多个预测起点（寿命的 40%~70%）做递归预测，报告 RMSE / RUL 误差。\n'
    '\n'
    '这正是改进方案的 A2 / A3 / A4：旧流程把每块训练电池切成「前 80% 训练 +\n'
    '后 20% 验证」，而寿命末段（膝点）恰好落在后 20%，于是模型从没见过寿命末段，\n'
    '却被要求预测「什么时候越过失效阈值」。\n'
    '\n'
    '本模块对「单特征容量序列」和「多特征 (T, F) 帧」都适用，容量恒为第 0 列。\n'
    '"""\n'
    '\n'
    'import numpy as np\n'
    '\n'
    'from core.preprocess import build_instances, build_instances_mf\n'
    'from core.result_semantics import (\n'
    '    DEFAULT_DEBOUNCE_CYCLES,\n'
    '    first_failure_index,\n'
    ')\n'
    '\n'
    '\n'
    '#: 滚动预测起点（占观测序列长度的比例）\n'
    'DEFAULT_STARTS = (0.4, 0.5, 0.6, 0.7)\n'
    '\n'
    '\n'
    'def capacity_of(data_dict, name):\n'
    '    """从电池条目里取容量序列；兼容 DataFrame 与 ``{\'capacity\': ...}``。"""\n'
    '    entry = data_dict[name]\n'
    "    if hasattr(entry, 'columns'):\n"
    "        if 'capacity' not in entry.columns:\n"
    "            raise KeyError(f'电池 {name} 缺少 capacity 列')\n"
    "        return np.asarray(entry['capacity'], dtype=np.float64).reshape(-1)\n"
    "    return np.asarray(entry['capacity'], dtype=np.float64).reshape(-1)\n"
    '\n'
    '\n'
    'def feature_frame(data_dict, name, columns):\n'
    '    """取某块电池的特征帧 ``(T, F)``，容量为第 0 列。\n'
    '\n'
    '    ``columns`` 里不存在的列会被跳过；容量列始终保留。\n'
    '    """\n'
    '    entry = data_dict[name]\n'
    "    if hasattr(entry, 'columns'):\n"
    '        available = [c for c in columns if c in entry.columns]\n'
    "        if 'capacity' not in available:\n"
    "            available = ['capacity'] + available\n"
    '        return np.asarray(\n'
    "            entry.loc[:, available].astype('float64'), dtype=np.float64)\n"
    "    capacity = np.asarray(entry['capacity'], dtype=np.float64).reshape(-1)\n"
    '    return capacity.reshape(-1, 1)\n'
    '\n'
    '\n'
    'def _to_frame(values):\n'
    '    """把 1-D 容量序列或 2-D 特征帧统一成 ``(T, F)``。"""\n'
    '    array = np.asarray(values, dtype=np.float64)\n'
    '    if array.ndim == 1:\n'
    '        return array.reshape(-1, 1)\n'
    '    if array.ndim == 2:\n'
    '        return array\n'
    "    raise ValueError('序列必须是容量序列或 (T, F) 特征帧')\n"
    '\n'
    '\n'
    'def first_cross(values, threshold, debounce=DEFAULT_DEBOUNCE_CYCLES):\n'
    '    """首次**持续**低于阈值的位置；从未低于则返回 ``None``（右删失）。\n'
    '\n'
    '    委托给 :func:`core.result_semantics.first_failure_index`——全工程只有那一处\n'
    '    失效判定实现。``debounce=1``（默认）是「首次下穿即失效」的旧语义；\n'
    '    ``debounce=3`` 要求连续 3 个循环低于阈值（A12）。\n'
    '    """\n'
    '    return first_failure_index(values, threshold, debounce)\n'
    '\n'
    '\n'
    'def _call_step(step_fn, window_rows):\n'
    '    """调用 step_fn：单特征传 ``(1, W)``，多特征传 ``(1, W, F)``。"""\n'
    '    if window_rows.shape[1] == 1:\n'
    '        payload = window_rows[:, 0].reshape(1, -1).astype(np.float32)\n'
    '    else:\n'
    '        payload = window_rows.reshape(1, *window_rows.shape).astype(np.float32)\n'
    '    values = np.asarray(step_fn(payload), dtype=np.float64).reshape(-1)\n'
    '    if len(values) != 1 or not np.isfinite(values[0]):\n'
    "        raise ValueError('递归预测器必须为单个窗口返回一个有限数值')\n"
    '    return float(values[0])\n'
    '\n'
    '\n'
    'def recursive_forecast(step_fn, window_values, steps):\n'
    '    """递归预测。\n'
    '\n'
    '    ``window_values`` 可以是 ``(W,)`` 容量窗口或 ``(W, F)`` 特征帧。多特征时\n'
    '    **只有容量通道自回归**：其余特征保持为窗口内最后一个观测值（未来工况未知\n'
    '    时的保守假设）。\n'
    '    """\n'
    '    if steps <= 0:\n'
    '        return np.empty(0, dtype=np.float64)\n'
    '    window = _to_frame(window_values)\n'
    '    if len(window) == 0:\n'
    "        raise ValueError('递归预测的初始窗口不能为空')\n"
    '    width, features = window.shape\n'
    '    held = window[-1, 1:].copy()          # 非容量通道的占位值\n'
    '    history = window.copy()\n'
    '    out = []\n'
    '    for _ in range(steps):\n'
    '        value = _call_step(step_fn, history[-width:])\n'
    '        out.append(value)\n'
    '        row = np.empty(features, dtype=np.float64)\n'
    '        row[0] = value\n'
    '        if features > 1:\n'
    '            row[1:] = held\n'
    '        history = np.vstack([history, row])\n'
    '    return np.asarray(out, dtype=np.float64)\n'
    '\n'
    '\n'
    'def rolling_origin_eval(sequence, window, step_fn, threshold,\n'
    '                        starts=DEFAULT_STARTS, battery=None, debounce=None):\n'
    '    """在多个预测起点上做真正的未来预测（递归），而不是「用真实历史的一步预测」。\n'
    '\n'
    '    ``sequence`` 可以是容量序列 ``(T,)`` 或特征帧 ``(T, F)``。\n'
    '    ``debounce`` 是失效判定所需的连续低于阈值循环数（A12，默认 1）。\n'
    '    返回每个起点一行：rmse / mae / true_rul / pred_rul / rul_err /\n'
    '    rul_rel_err / within_20pct / status\n'
    '    （rul 以「预测起点之后的第几个循环」计，None 表示观测期内没有越过阈值）。\n'
    '    """\n'
    '    if debounce is None:\n'
    '        debounce = DEFAULT_DEBOUNCE_CYCLES\n'
    '    frame = _to_frame(sequence)\n'
    '    rows = []\n'
    '    for frac in starts:\n'
    '        start = int(len(frame) * frac)\n'
    '        if start < window or start >= len(frame) - 1:\n'
    '            continue\n'
    '        truth = frame[start:, 0]\n'
    '        prediction = recursive_forecast(\n'
    '            step_fn, frame[start - window:start], len(truth))\n'
    '        true_eol = first_cross(truth, threshold, debounce)\n'
    '        pred_eol = first_cross(prediction, threshold, debounce)\n'
    '        row = {\n'
    "            'start_frac': float(frac),\n"
    "            'start': int(start),\n"
    "            'battery': battery,\n"
    "            'rmse': float(np.sqrt(np.mean((prediction - truth) ** 2))),\n"
    "            'mae': float(np.mean(np.abs(prediction - truth))),\n"
    "            'true_rul': true_eol,\n"
    "            'pred_rul': pred_eol,\n"
    "            'rul_err': None,\n"
    "            'rul_rel_err': None,\n"
    "            'within_20pct': None,\n"
    '        }\n'
    '        if true_eol is None:\n'
    "            row['status'] = 'true_censored'       # 真实电池在观测期内没失效\n"
    '        elif pred_eol is None:\n'
    "            row['status'] = 'pred_censored'       # 模型预测「不会失效」\n"
    '        else:\n'
    "            row['status'] = 'ok'\n"
    "            row['rul_err'] = int(pred_eol - true_eol)\n"
    "            row['rul_rel_err'] = abs(pred_eol - true_eol) / max(true_eol, 1)\n"
    "            row['within_20pct'] = bool(\n"
    '                abs(pred_eol - true_eol) <= 0.2 * max(true_eol, 1))\n'
    '        rows.append(row)\n'
    '    return rows\n'
    '\n'
    '\n'
    'def persistence_rows(sequence, window, threshold, starts=DEFAULT_STARTS,\n'
    '                     battery=None):\n'
    '    """同一组起点上「平推」基线的滚动评估行。"""\n'
    '    return rolling_origin_eval(\n'
    '        sequence, window, lambda w: w[:, -1], threshold, starts, battery)\n'
    '\n'
    '\n'
    'def baseline_rmse_by_start(rows):\n'
    '    """把基线行压成 ``{start_frac: rmse}``（技能分的分母）。"""\n'
    "    return {row['start_frac']: row['rmse'] for row in rows}\n"
    '\n'
    '\n'
    'def skill_vs_persistence(rows, baseline_by_start):\n'
    '    """技能分 = 1 − RMSE模型 / RMSE平推；> 0 表示比平推好。"""\n'
    '    values = []\n'
    '    for row in rows:\n'
    "        baseline = baseline_by_start.get(row['start_frac'])\n"
    '        if baseline is None or baseline <= 1e-12:\n'
    '            continue\n'
    "        values.append(1.0 - row['rmse'] / baseline)\n"
    '    if not values:\n'
    '        return None\n'
    '    return float(np.mean(values))\n'
    '\n'
    '\n'
    '# ── 窗口构造（单特征 / 多特征共用） ────────────────────────────────\n'
    '\n'
    'def _windows_for(data_dict, name, window, columns, fill_values):\n'
    '    entry = data_dict[name]\n'
    '    if columns is None or len(columns) <= 1:\n'
    '        capacity = capacity_of(data_dict, name)\n'
    '        return build_instances(capacity, window)\n'
    "    if hasattr(entry, 'columns'):\n"
    '        return build_instances_mf(\n'
    '            entry, window, cols=columns, fill_values=fill_values)\n'
    '    # 字典条目没有额外特征列，退化为单特征\n'
    '    capacity = capacity_of(data_dict, name)\n'
    '    return build_instances(capacity, window)\n'
    '\n'
    '\n'
    'def make_windows(data_dict, names, window, columns=None, fill_values=None):\n'
    '    """把若干块电池的窗口拼成 ``(X, y)``；多特征时 X 为 ``(N, W, F)``。\n'
    '\n'
    '    返回的是**原始量纲**（Ah / 原始特征），归一化由 ``fit_fn`` / step_fn 内部负责。\n'
    '    """\n'
    '    xs, ys = [], []\n'
    '    for name in names:\n'
    '        try:\n'
    '            x, y = _windows_for(data_dict, name, window, columns, fill_values)\n'
    '        except (KeyError, ValueError):\n'
    '            continue\n'
    '        if len(x):\n'
    '            xs.append(x)\n'
    '            ys.append(y)\n'
    '    if not xs:\n'
    "        raise ValueError('没有可用的训练窗口')\n"
    '    return np.vstack(xs), np.concatenate(ys)\n'
    '\n'
    '\n'
    'def training_fill_values(data_dict, names, columns):\n'
    '    """用**训练电池**统计量计算缺失填充值（不得使用目标电池）。"""\n'
    '    if columns is None or len(columns) <= 1:\n'
    '        return None\n'
    '    from core.preprocess import feature_fill_values\n'
    '\n'
    '    frames = []\n'
    '    for name in names:\n'
    '        entry = data_dict[name]\n'
    "        if hasattr(entry, 'columns'):\n"
    '            frames.append(entry)\n'
    '    if not frames:\n'
    '        return None\n'
    '    import pandas as pd\n'
    '\n'
    '    return feature_fill_values(pd.concat(frames, ignore_index=True), columns)\n'
    '\n'
    '\n'
    'def batched_rollout_rmse(step_fn, frame, window, start_frac):\n'
    '    """一次前向跑完整条递归轨迹（每步只调用一次 ``step_fn``，传单行窗口）。\n'
    '\n'
    '    sklearn 的单次 ``predict`` 开销基本固定，所以「逐步调用」与「批量调用」在\n'
    '    单位成本上差别不大，但这里避免了 Python 层的重复构造。\n'
    '    """\n'
    '    start = int(len(frame) * start_frac)\n'
    '    if start < window or start >= len(frame) - 1:\n'
    '        return None\n'
    '    steps = len(frame) - start\n'
    '    truth = frame[start:, 0]\n'
    '    history = frame[start - window:start].copy()\n'
    '    features = history.shape[1]\n'
    '    errors = np.empty(steps, dtype=np.float64)\n'
    '    for step in range(steps):\n'
    '        value = _call_step(step_fn, history[-window:])\n'
    '        errors[step] = (value - truth[step]) ** 2\n'
    '        row = np.empty(features, dtype=np.float64)\n'
    '        row[0] = value\n'
    '        if features > 1:\n'
    '            row[1:] = history[-1, 1:]\n'
    '        history = np.vstack([history, row])\n'
    '    return float(np.sqrt(np.mean(errors)))\n'
    '\n'
    '\n'
    'def _rolling_rmse(step_fn, frame, window, start_frac):\n'
    '    return batched_rollout_rmse(step_fn, frame, window, start_frac)\n'
    '\n'
    '\n'
    'def is_recurrent(model):\n'
    '    """判断是否为 PyTorch 循环模型（而不是 sklearn 树模型）。"""\n'
    "    return hasattr(model, 'forward') and not hasattr(model, 'predict')\n"
    '\n'
    '\n'
    "def model_step_for(model, rated, device='cpu', feature_scaler=None):\n"
    '    """给「原始量纲进出」的模型造递归预测 step_fn。\n'
    '\n'
    '    ``fit_fn``（见 :func:`core.model_factory.make_fit_fn`）内部已经把输入按\n'
    '    ``/rated`` 归一化，多特征时再叠加 ``FeatureScaler``。因此 step_fn 必须还原\n'
    '    **同一套映射**：先把原始窗口归一化，再把输出乘回 ``rated``。\n'
    '\n'
    '    单特征与多特征共用这一处实现，避免两条路径量纲不一致（多特征路径曾经就是\n'
    '    这样：训练除以 rated，推理却用 z-score，导致误差大到不可用）。\n'
    '    """\n'
    '    def step(windows):\n'
    '        array = np.asarray(windows, dtype=np.float32)\n'
    '        if array.ndim == 2:\n'
    '            array = array[:, :, None]\n'
    '        scaled = np.array(array, dtype=np.float32, copy=True)\n'
    '        scaled[:, :, 0] = array[:, :, 0] / rated\n'
    '        if scaled.shape[2] > 1 and feature_scaler is not None:\n'
    '            scaled = feature_scaler.transform(scaled)\n'
    '\n'
    '        if is_recurrent(model):\n'
    '            import torch\n'
    '\n'
    '            tensor = torch.from_numpy(scaled).to(device)\n'
    "            if hasattr(model, 'eval'):\n"
    '                model.eval()\n'
    '            with torch.no_grad():\n'
    '                output = model(tensor)\n'
    '            raw = np.asarray(output.detach().cpu().numpy(),\n'
    '                             dtype=np.float64).reshape(-1)\n'
    '        else:\n'
    '            raw = np.asarray(\n'
    '                model.predict(scaled.reshape(len(scaled), -1)),\n'
    '                dtype=np.float64).reshape(-1)\n'
    '        return raw * rated\n'
    '\n'
    '    return step\n'
    '\n'
    '\n'
    'def select_hparams(data_dict, train_names, window, fit_fn, grid, rated,\n'
    '                   start_frac=0.5, stop_flag=None, columns=None,\n'
    "                   return_folds=False, device='cpu', feature_scaler=None):\n"
    '    """内层留一电池交叉验证：用滚动预测 RMSE（单位 Ah）选超参。\n'
    '\n'
    '    ``fit_fn(X, y, hp) -> model``，其中 X、y 是**原始量纲**（``fit_fn`` 内部\n'
    '    负责归一化）。至少需要 2 块训练电池，否则退化为直接取 ``grid[0]``。\n'
    '\n'
    '    ``return_folds=True`` 时额外返回选定超参下的折模型\n'
    '    ``{held_out_name: model}``——这些模型**没见过**对应的留出电池，正好用来\n'
    '    无偏地标定 α（A3），无需再拟合一遍。\n'
    '    """\n'
    '    if len(train_names) < 2:\n'
    "        return (grid[0], float('nan'), {}) if return_folds else (\n"
    "            grid[0], float('nan'))\n"
    '    best_hp, best_score = None, np.inf\n'
    '    best_folds = {}\n'
    '    for hp in grid:\n'
    '        if stop_flag is not None and stop_flag():\n'
    '            break\n'
    '        scores = []\n'
    '        folds = {}\n'
    '        for val_name in train_names:\n'
    '            train_subset = [n for n in train_names if n != val_name]\n'
    '            try:\n'
    '                fill = training_fill_values(data_dict, train_subset, columns)\n'
    '                x, y = make_windows(\n'
    '                    data_dict, train_subset, window, columns, fill)\n'
    '                model = fit_fn(x, y, hp)\n'
    '            except (ValueError, KeyError):\n'
    '                continue\n'
    '            folds[val_name] = model\n'
    '            step = model_step_for(\n'
    '                model, rated, device=device, feature_scaler=feature_scaler)\n'
    '            score = _rolling_rmse(\n'
    "                step, feature_frame(data_dict, val_name, columns or ['capacity']),\n"
    '                window, start_frac)\n'
    '            if score is not None:\n'
    '                scores.append(score)\n'
    '        if not scores:\n'
    '            continue\n'
    '        score = float(np.mean(scores))\n'
    '        if score < best_score:\n'
    '            best_hp, best_score, best_folds = hp, score, folds\n'
    '    if best_hp is None:\n'
    "        return (grid[0], float('nan'), {}) if return_folds else (\n"
    "            grid[0], float('nan'))\n"
    '    if return_folds:\n'
    '        return best_hp, best_score, best_folds\n'
    '    return best_hp, best_score\n'
    '\n'
    '\n'
    'def fit_final(data_dict, train_names, window, fit_fn, hp, rated, columns=None):\n'
    '    """用全部训练电池的全部窗口定型（评估与部署共用这一个函数）。\n'
    '\n'
    '    X、y 传**原始量纲**；归一化由 ``fit_fn`` 内部完成（见\n'
    '    :func:`core.model_factory.make_fit_fn`）。这里**不能**再除一次 ``rated``，\n'
    '    否则训练输入被归一化两遍，模型连训练集都拟合不上。\n'
    '    """\n'
    '    fill = training_fill_values(data_dict, train_names, columns)\n'
    '    x, y = make_windows(data_dict, train_names, window, columns, fill)\n'
    '    return fit_fn(x, y, hp)\n'
    '\n'
    '\n'
    'def inner_fold_models(data_dict, train_names, window, fit_fn, hp, rated,\n'
    '                      columns=None):\n'
    '    """内层留一电池的折模型：``{held_out_name: model}``。\n'
    '\n'
    '    这些模型**没见过**对应的留出电池，因此可以用来无偏地标定 α（A3）。\n'
    '    X、y 传**原始量纲**，归一化由 ``fit_fn`` 内部负责。\n'
    '    """\n'
    '    models = {}\n'
    '    for val_name in train_names:\n'
    '        train_subset = [n for n in train_names if n != val_name]\n'
    '        if not train_subset:\n'
    '            continue\n'
    '        try:\n'
    '            fill = training_fill_values(data_dict, train_subset, columns)\n'
    '            x, y = make_windows(data_dict, train_subset, window, columns, fill)\n'
    '            models[val_name] = fit_fn(x, y, hp)\n'
    '        except (ValueError, KeyError):\n'
    '            continue\n'
    '    return models\n'
    '\n'
    '\n'
    'def choose_blend_by_rollout(step_raw, data_dict, val_names, window,\n'
    '                            starts=(0.5, 0.6), grid=None, columns=None):\n'
    '    """用多步滚动误差（而不是一步误差）选持久性混合系数 α。\n'
    '\n'
    '    ``step_raw`` 必须来自「没见过 val_names 里电池」的模型（例如内层交叉验证\n'
    '    得到的模型），否则 α 会偏向 1。若返回的 α < 0.05，应在界面上提示\n'
    '    「模型没有超越持久性基线」。\n'
    '\n'
    '    实现上把**所有候选 α 的递归轨迹并行推进**：每一步只调用一次 ``step_raw``\n'
    '    处理一个 ``(len(grid), W)`` 批次。sklearn 的单次 ``predict`` 开销基本固定，\n'
    '    因此这比「逐 α 逐个窗口调用」快一个数量级。\n'
    '    """\n'
    '    grid = (np.linspace(0.0, 1.0, 21) if grid is None\n'
    '            else np.asarray(grid, dtype=np.float64))\n'
    '    if len(grid) == 0:\n'
    "        return 1.0, float('nan')\n"
    '\n'
    '    errors = [[] for _ in grid]\n'
    '    for name in val_names:\n'
    "        frame = feature_frame(data_dict, name, columns or ['capacity'])\n"
    '        for frac in starts:\n'
    '            start = int(len(frame) * frac)\n'
    '            if start < window or start >= len(frame) - 1:\n'
    '                continue\n'
    '            steps = len(frame) - start\n'
    '            truth = frame[start:, 0]\n'
    '            window_rows = frame[start - window:start]\n'
    '            _rollout_blend_errors(\n'
    '                step_raw, window_rows, truth, steps, grid, errors)\n'
    '\n'
    '    scores = [float(np.mean(values)) if values else np.inf for values in errors]\n'
    '    best = int(np.argmin(scores))\n'
    '    best_score = scores[best]\n'
    '    return float(grid[best]), (\n'
    "        float(np.sqrt(best_score)) if np.isfinite(best_score) else float('nan'))\n"
    '\n'
    '\n'
    'def _rollout_blend_errors(step_raw, window_rows, truth, steps, grid, errors):\n'
    '    """并行推进所有 α 的递归轨迹，把每步平方误差累加到 ``errors``。"""\n'
    '    n_alpha = len(grid)\n'
    '    features = window_rows.shape[1]\n'
    '    width = len(window_rows)\n'
    '    # 每个 α 一份历史副本\n'
    '    histories = [window_rows.copy() for _ in range(n_alpha)]\n'
    '    for step in range(steps):\n'
    '        # 每次把「全部 α 的当前窗口」拼成一个批次，一次 predict 处理完\n'
    '        batch = np.stack(\n'
    '            [history[-width:] for history in histories]).astype(np.float32)\n'
    '        raw = np.asarray(step_raw(batch), dtype=np.float64).reshape(-1)\n'
    '        if len(raw) != n_alpha:\n'
    "            raise ValueError('step_raw 必须为每个窗口返回一个数值')\n"
    '        target = float(truth[step])\n'
    '        for index, alpha in enumerate(grid):\n'
    '            last = float(histories[index][-1, 0])\n'
    '            value = last + float(alpha) * (raw[index] - last)\n'
    '            errors[index].append((value - target) ** 2)\n'
    '            row = np.empty(features, dtype=np.float64)\n'
    '            row[0] = value\n'
    '            if features > 1:\n'
    '                row[1:] = histories[index][-1, 1:]\n'
    '            histories[index] = np.vstack([histories[index], row])\n'
    '\n'
    '\n'
    'def summarize_rolling_rows(rows, baseline_by_start=None):\n'
    '    """把多折 / 多起点的滚动评估行汇总成表格与跨电池统计。\n'
    '\n'
    "    返回 ``{'per_start': {...}, 'overall': {...}}``；``n`` 是**电池数**，\n"
    '    这才是泛化不确定性的来源（不是随机种子）。\n'
    '    """\n'
    '    per_start = {}\n'
    "    for frac in sorted({row['start_frac'] for row in rows}):\n"
    "        subset = [row for row in rows if row['start_frac'] == frac]\n"
    "        detected = [row for row in subset if row['status'] == 'ok']\n"
    '        needs_detection = [row for row in subset\n'
    "                           if row['status'] in ('ok', 'pred_censored')]\n"
    '        entry = {\n'
    "            'n': len(subset),\n"
    "            'rmse': float(np.mean([row['rmse'] for row in subset])),\n"
    "            'mae': float(np.mean([row['mae'] for row in subset])),\n"
    "            'detected': len(detected),\n"
    "            'needs_detection': len(needs_detection),\n"
    "            'mean_abs_rul_err': (\n"
    "                float(np.mean([abs(row['rul_err']) for row in detected]))\n"
    '                if detected else None),\n'
    '        }\n'
    '        if baseline_by_start:\n'
    "            entry['skill'] = skill_vs_persistence(subset, baseline_by_start)\n"
    '        per_start[frac] = entry\n'
    '\n'
    "    all_detected = [row for row in rows if row['status'] == 'ok']\n"
    "    batteries = {row.get('battery') for row in rows if row.get('battery')}\n"
    '    overall = {\n'
    "        'n': len(batteries),\n"
    "        'rmse': float(np.mean([row['rmse'] for row in rows])) if rows else None,\n"
    "        'mae': float(np.mean([row['mae'] for row in rows])) if rows else None,\n"
    "        'detected': len(all_detected),\n"
    "        'needs_detection': len(\n"
    "            [row for row in rows if row['status'] in ('ok', 'pred_censored')]),\n"
    "        'mean_abs_rul_err': (\n"
    "            float(np.mean([abs(row['rul_err']) for row in all_detected]))\n"
    '            if all_detected else None),\n'
    '    }\n'
    '    if baseline_by_start:\n'
    "        overall['skill'] = skill_vs_persistence(rows, baseline_by_start)\n"
    "    return {'per_start': per_start, 'overall': overall}\n"
)

# ---- core/stream_protocol.py ----
_MODULE_SOURCES['core.stream_protocol'] = (
    '"""TCP 实时预测的纯 Python 部分（不依赖 Qt，可直接单元测试）。\n'
    '\n'
    '``ui/tcp_server.py`` 只负责收发字节和发信号；解析、预测、限流都在这里，\n'
    '因此这些逻辑可以在没有 PyQt6 的环境里被完整测试。\n'
    '"""\n'
    '\n'
    'import json\n'
    'import math\n'
    'import time\n'
    'from collections import deque\n'
    '\n'
    'import numpy as np\n'
    '\n'
    '\n'
    '#: 单条消息上限（字节）\n'
    'MAX_LINE = 4096\n'
    '#: 缓冲区上限（循环数）；deque(maxlen=...) 满了自动丢弃最旧的点\n'
    'MAX_BUFFER = 5000\n'
    '#: 单次递归预测的最大步数（防止「永远越不过阈值」时跑满）\n'
    'MAX_FORECAST_STEPS = 1500\n'
    '\n'
    '\n'
    'def _reject_constant(name):\n'
    '    # 拒绝 NaN / Infinity / -Infinity：它们不是合法 JSON，且会污染预测\n'
    "    raise ValueError(f'非法 JSON 常量: {name}')\n"
    '\n'
    '\n'
    'def parse_message(raw, rated_capacity):\n'
    '    """解析一行 TCP 消息，**永不抛异常**。\n'
    '\n'
    "    返回 ``('reset', None)`` / ``('sample', 容量Ah)`` / ``('error', 原因)``。\n"
    '    """\n'
    '    if not isinstance(raw, (bytes, bytearray)):\n'
    "        return 'error', '消息必须是字节串'\n"
    '    if len(raw) > MAX_LINE:\n'
    "        return 'error', '消息过长'\n"
    '    try:\n'
    "        text = raw.decode('utf-8')\n"
    '    except UnicodeDecodeError:\n'
    "        return 'error', '消息不是合法 UTF-8'\n"
    '    try:\n'
    '        msg = json.loads(text, parse_constant=_reject_constant)\n'
    '    except (ValueError, RecursionError) as exc:\n'
    "        return 'error', f'不是合法 JSON: {type(exc).__name__}'\n"
    '    if not isinstance(msg, dict):\n'
    "        return 'error', '消息必须是 JSON 对象'\n"
    "    if msg.get('reset') is True:\n"
    "        return 'reset', None\n"
    "    if 'capacity' not in msg:\n"
    "        return 'error', '缺少 capacity 字段'\n"
    "    capacity = msg['capacity']\n"
    '    # bool 是 int 的子类，必须显式排除，否则 True 会被当成 1.0 Ah\n'
    '    if isinstance(capacity, bool) or not isinstance(capacity, (int, float)):\n'
    "        return 'error', 'capacity 必须是数值'\n"
    '    try:\n'
    '        capacity = float(capacity)\n'
    '    except (OverflowError, ValueError):\n'
    "        return 'error', 'capacity 数值过大'\n"
    '    if not math.isfinite(capacity):\n'
    "        return 'error', 'capacity 必须是有限数值'\n"
    '    try:\n'
    '        rated = float(rated_capacity)\n'
    '    except (TypeError, ValueError):\n'
    "        return 'error', '额定容量无效'\n"
    '    if not math.isfinite(rated) or rated <= 0:\n'
    "        return 'error', '额定容量无效'\n"
    '    if not 0.0 < capacity <= 2.0 * rated:\n'
    "        return 'error', f'capacity 超出合理范围 (0, {2 * rated:g}] Ah'\n"
    "    return 'sample', capacity\n"
    '\n'
    '\n'
    'def forecast_eol(history, window, step_fn, threshold, max_steps=MAX_FORECAST_STEPS):\n'
    '    """递归预测直到容量首次低于阈值。\n'
    '\n'
    '    返回 ``(rul, forecast)``：\n'
    '\n'
    '    - ``rul``      = 「从最新一个**已观测**循环算起，还要再过几个循环越过阈值」\n'
    '                     （真正的 RUL）；当前已低于阈值返回 0；``max_steps`` 内\n'
    '                     不会越过返回 ``None``；\n'
    '    - ``forecast`` = 预测的容量序列（用于画图）。\n'
    '\n'
    '    旧实现的「RUL」是 ``cycle_80 − cycle_stage``，即「SOH 从 pct% 掉到 80%\n'
    '    需要多少个循环」，不是从现在起的剩余寿命。\n'
    '    """\n'
    '    hist = [float(value) for value in np.asarray(\n'
    '        history, dtype=np.float64).reshape(-1)]\n'
    '    if len(hist) < window:\n'
    "        raise ValueError('历史长度小于窗口')\n"
    '    if hist[-1] < threshold:\n'
    '        return 0, []\n'
    '    win, out = hist[-window:], []\n'
    '    for step in range(1, max_steps + 1):\n'
    '        next_values = np.asarray(\n'
    '            step_fn(np.asarray(win, dtype=np.float32).reshape(1, -1)),\n'
    '            dtype=np.float64).reshape(-1)\n'
    '        if len(next_values) != 1 or not np.isfinite(next_values[0]):\n'
    "            raise ValueError('递归预测器必须为单个窗口返回一个有限数值')\n"
    '        nxt = float(next_values[0])\n'
    '        out.append(nxt)\n'
    '        win = win[1:] + [nxt]\n'
    '        if nxt < threshold:\n'
    '            return step, out\n'
    '    return None, out\n'
    '\n'
    '\n'
    'def soh_stage_table(history, window, step_fn, rated_capacity,\n'
    '                    max_steps=MAX_FORECAST_STEPS):\n'
    '    """给出 SOH 阶段表：每个百分比首次到达的循环序号（相对最新观测点）。\n'
    '\n'
    '    与 :func:`forecast_eol` 同一口径：SOH 一律定义为 ``C / C_rated``。\n'
    '    """\n'
    '    if rated_capacity <= 0:\n'
    "        raise ValueError('额定容量必须为正数')\n"
    '    hist = [float(value) for value in np.asarray(\n'
    '        history, dtype=np.float64).reshape(-1)]\n'
    '    table = {}\n'
    '    for pct in (100, 95, 90, 85, 80):\n'
    '        target = rated_capacity * pct / 100.0\n'
    '        offset = None\n'
    '        for index, value in enumerate(hist):\n'
    '            if value <= target:\n'
    '                offset = index - (len(hist) - 1)\n'
    '                break\n'
    '        if offset is None and len(hist) >= window:\n'
    '            win = hist[-window:]\n'
    '            for step in range(1, max_steps + 1):\n'
    '                next_values = np.asarray(\n'
    '                    step_fn(np.asarray(win, dtype=np.float32).reshape(1, -1)),\n'
    '                    dtype=np.float64).reshape(-1)\n'
    '                nxt = float(next_values[0])\n'
    '                win = win[1:] + [nxt]\n'
    '                if nxt <= target:\n'
    '                    offset = step\n'
    '                    break\n'
    '        table[pct] = {\n'
    "            'cycle_offset': offset,\n"
    "            'reached': offset is not None and offset <= 0,\n"
    '        }\n'
    '    return table\n'
    '\n'
    '\n'
    'class Throttle:\n'
    '    """限流：两次预测之间至少间隔 ``min_interval`` 秒。\n'
    '\n'
    '    其余样本只入缓冲、不触发预测，避免「每条消息同步做上千步递归」把接收\n'
    '    线程堵死。\n'
    '    """\n'
    '\n'
    '    def __init__(self, min_interval=1.0):\n'
    '        self.min_interval = float(min_interval)\n'
    '        self._last = 0.0\n'
    '\n'
    '    def ready(self):\n'
    '        now = time.monotonic()\n'
    '        if now - self._last >= self.min_interval:\n'
    '            self._last = now\n'
    '            return True\n'
    '        return False\n'
    '\n'
    '\n'
    'def new_buffer():\n'
    '    """有上限的容量历史缓冲。"""\n'
    '    return deque(maxlen=MAX_BUFFER)\n'
    '\n'
    '\n'
    'class PredictionJob:\n'
    '    """把「解析 → 缓冲 → 预测」串起来的纯逻辑对象（不依赖 Qt）。\n'
    '\n'
    '    UI 层只负责把信号接出去，因此这里可以直接单测。\n'
    '    """\n'
    '\n'
    '    def __init__(self, window, step_fn, threshold, rated_capacity,\n'
    '                 min_interval=1.0):\n'
    '        self.window = int(window)\n'
    '        self.step_fn = step_fn\n'
    '        self.threshold = float(threshold)\n'
    '        self.rated_capacity = float(rated_capacity)\n'
    '        self.buffer = new_buffer()\n'
    '        self.throttle = Throttle(min_interval)\n'
    '\n'
    '    def reset(self):\n'
    '        self.buffer.clear()\n'
    '\n'
    '    def history(self):\n'
    '        return list(self.buffer)\n'
    '\n'
    '    def feed(self, capacity):\n'
    '        """接收一个容量样本，返回 ``(should_predict, history)``。"""\n'
    '        self.buffer.append(float(capacity))\n'
    '        history = list(self.buffer)\n'
    '        should_predict = (\n'
    '            len(history) >= self.window and self.throttle.ready())\n'
    '        return should_predict, history\n'
    '\n'
    '    def predict(self, history=None):\n'
    '        """在（给定的）历史快照上做一次真正的 RUL 预测。\n'
    '\n'
    '        ``history`` 为 ``None`` 时用当前缓冲。传入快照可以让预测在**独立线程**\n'
    '        里跑，而接收线程继续追加新样本——否则一次最长 1500 步的递归预测会把\n'
    '        接收阻塞住（实测：单步 2.6 ms 时最坏阻塞约 4 s，sklearn 的 9.7 ms\n'
    '        则接近 15 s）。\n'
    '        """\n'
    '        if history is None:\n'
    '            history = list(self.buffer)\n'
    '        history = [float(value) for value in history]\n'
    '        if len(history) < self.window:\n'
    "            raise ValueError('历史长度小于窗口')\n"
    '        rul, forecast = forecast_eol(\n'
    '            history, self.window, self.step_fn, self.threshold)\n'
    '        return {\n'
    "            'rul': rul,\n"
    "            'forecast': forecast,\n"
    "            'history': history,\n"
    "            'soh_stages': soh_stage_table(\n"
    '                history, self.window, self.step_fn, self.rated_capacity),\n'
    '        }\n'
    '\n'
    '\n'
    'class LatestOnlyQueue:\n'
    '    """只保留**最新**一项的容量 1 队列（供实时预测使用）。\n'
    '\n'
    '    预测比数据慢时，中间那些过时的请求没有价值：界面只关心「当前缓冲对应的\n'
    '    那一次预测」。因此放新项时直接丢弃尚未处理的旧项，队列永不积压。\n'
    '    """\n'
    '\n'
    '    def __init__(self):\n'
    '        import queue\n'
    '\n'
    '        self._queue = queue.Queue(maxsize=1)\n'
    '\n'
    '    def put_latest(self, item):\n'
    '        """放入最新项，返回是否替换掉了尚未处理的旧项。"""\n'
    '        import queue\n'
    '\n'
    '        replaced = False\n'
    '        while True:\n'
    '            try:\n'
    '                self._queue.put_nowait(item)\n'
    '                return replaced\n'
    '            except queue.Full:\n'
    '                try:\n'
    '                    self._queue.get_nowait()\n'
    '                    replaced = True\n'
    '                except queue.Empty:\n'
    '                    pass\n'
    '\n'
    '    def get(self, timeout=None):\n'
    '        import queue\n'
    '\n'
    '        try:\n'
    '            return self._queue.get(timeout=timeout)\n'
    '        except queue.Empty:\n'
    '            return None\n'
)

# ---- core/validation.py ----
_MODULE_SOURCES['core.validation'] = (
    'import glob\n'
    'import logging\n'
    'import os\n'
    '\n'
    'import numpy as np\n'
    'import pandas as pd\n'
    '\n'
    '\n'
    "logger = logging.getLogger('battery_soh')\n"
    '\n'
    '\n'
    'DEFAULT_MAX_FILE_BYTES = 100 * 1024 * 1024\n'
    'DEFAULT_MAX_ROWS = 2_000_000\n'
    'DEFAULT_MAX_COLUMNS = 256\n'
    'DEFAULT_MAX_SHEETS = 32\n'
    'DEFAULT_MAX_STRUCTURE_DEPTH = 12\n'
    '\n'
    '# 列名映射：标准英文名 → 可接受的中英文别名列表\n'
    'COLUMN_NAME_MAP = {\n'
    "    'Date_Time': [\n"
    "        'Date_Time', '日期时间', '日期', '时间', '测试时间',\n"
    "        'datetime', 'date_time'],\n"
    "    'Cycle_Index': [\n"
    "        'Cycle_Index', '循环序号', '循环索引', '循环次数', '循环',\n"
    "        'cycle', 'cycle_index'],\n"
    "    'Step_Index': [\n"
    "        'Step_Index', '工步序号', '工步索引', '步序号', '工步',\n"
    "        'step', 'step_index'],\n"
    "    'Voltage(V)': ['Voltage(V)', '电压(V)', '电压', 'voltage', 'Voltage'],\n"
    "    'Current(A)': ['Current(A)', '电流(A)', '电流', 'current', 'Current'],\n"
    "    'Test_Time(s)': [\n"
    "        'Test_Time(s)', '测试时间(s)', '测试时间', 'Test_Time',\n"
    "        'test_time', 'test_time(s)'],\n"
    "    'Internal_Resistance(Ohm)': [\n"
    "        'Internal_Resistance(Ohm)', '内阻(Ohm)', '内阻', 'resistance',\n"
    "        'internal_resistance'],\n"
    '}\n'
    '\n'
    'REQUIRED_COLUMNS = [\n'
    "    'Date_Time', 'Cycle_Index', 'Step_Index', 'Voltage(V)',\n"
    "    'Current(A)', 'Test_Time(s)']\n"
    '\n'
    '\n'
    'def _build_reverse_map():\n'
    '    reverse = {}\n'
    '    for canonical, aliases in COLUMN_NAME_MAP.items():\n'
    '        for alias in aliases:\n'
    '            reverse[alias.lower()] = canonical\n'
    '    return reverse\n'
    '\n'
    '\n'
    '_REVERSE_COLUMN_MAP = _build_reverse_map()\n'
    '\n'
    '\n'
    'def normalize_column_names(df):\n'
    '    """将 DataFrame 中的中文或变体列名统一为标准英文列名。"""\n'
    '    rename_dict = {}\n'
    '    for column in df.columns:\n'
    '        key = str(column).strip().lower()\n'
    '        if key in _REVERSE_COLUMN_MAP:\n'
    '            canonical = _REVERSE_COLUMN_MAP[key]\n'
    '            if column != canonical:\n'
    '                rename_dict[column] = canonical\n'
    '    if rename_dict:\n'
    '        df.rename(columns=rename_dict, inplace=True)\n'
    '    return df\n'
    '\n'
    '\n'
    'def validate_training_config(config):\n'
    '    """Validate parameters that affect data interpretation and model inputs."""\n'
    '    errors = []\n'
    "    upper = getattr(config, 'voltage_upper', None)\n"
    "    lower = getattr(config, 'voltage_lower', None)\n"
    '    if (not _is_finite_number(upper) or not _is_finite_number(lower) or\n'
    '            upper <= lower):\n'
    "        errors.append('SOH 上电压必须是有限数值并且大于下电压')\n"
    '\n'
    "    rated = getattr(config, 'rated_capacity', None)\n"
    '    if not _is_finite_number(rated) or not 0.01 <= rated <= 1000:\n'
    "        errors.append('额定容量必须是 0.01～1000 Ah 范围内的有限数值')\n"
    '\n'
    "    threshold = getattr(config, 'threshold_ratio', None)\n"
    '    if not _is_finite_number(threshold) or not 0.1 <= threshold <= 1.0:\n'
    "        errors.append('失效阈值比例必须位于 0.1～1.0')\n"
    '\n'
    "    window = getattr(config, 'window_size', None)\n"
    '    if (isinstance(window, bool) or not isinstance(window, (int, np.integer)) or\n'
    '            not 1 <= int(window) <= 10000):\n'
    "        errors.append('窗口大小必须是 1～10000 的整数')\n"
    '\n'
    "    if str(getattr(config, 'adapter_type', 'CALCE')).upper() == 'CALCE':\n"
    '        steps = [\n'
    "            getattr(config, 'cc_step', None),\n"
    "            getattr(config, 'cv_step', None),\n"
    "            getattr(config, 'discharge_step', None),\n"
    '        ]\n'
    '        if any(value is None for value in steps):\n'
    '            errors.append(\n'
    "                '请在“设置工步”中输入恒流充电、恒压充电和放电工步')\n"
    '        elif (any(isinstance(value, bool) or not isinstance(\n'
    '                value, (int, np.integer)) or int(value) < 0\n'
    '                  for value in steps) or\n'
    '                len(set(steps)) != 3):\n'
    "            errors.append('恒流、恒压和放电工步必须是三个不同的非负整数')\n"
    '    return errors\n'
    '\n'
    '\n'
    'def _is_finite_number(value):\n'
    '    return (not isinstance(value, (bool, np.bool_)) and\n'
    '            isinstance(value, (int, float, np.integer, np.floating)) and\n'
    '            np.isfinite(value))\n'
    '\n'
    '\n'
    'def validate_file_resource_limits(\n'
    '        filepath, max_file_bytes=DEFAULT_MAX_FILE_BYTES,\n'
    '        max_sheets=DEFAULT_MAX_SHEETS):\n'
    '    """Reject oversized files and workbooks before loading their data."""\n'
    '    errors = []\n'
    '    try:\n'
    '        size = os.path.getsize(filepath)\n'
    '    except OSError as exc:\n'
    "        return [f'无法读取文件大小：{exc}']\n"
    '    if size <= 0:\n'
    "        errors.append('文件大小为 0，无法读取')\n"
    '    elif size > max_file_bytes:\n'
    '        errors.append(\n'
    "            f'文件大小超过限制（{size} 字节 > {max_file_bytes} 字节）')\n"
    '    if errors:\n'
    '        return errors\n'
    '\n'
    '    extension = os.path.splitext(filepath)[1].lower()\n'
    "    if extension in ('.xlsx', '.xls'):\n"
    '        try:\n'
    '            with pd.ExcelFile(filepath) as workbook:\n'
    '                if len(workbook.sheet_names) > max_sheets:\n'
    '                    errors.append(\n'
    "                        f'工作表数量超过限制（{len(workbook.sheet_names)} > '\n"
    "                        f'{max_sheets}）')\n"
    '        except Exception as exc:\n'
    "            errors.append(f'无法读取工作表结构：{exc}')\n"
    '    return errors\n'
    '\n'
    '\n'
    'def _read_data_file(filepath, max_rows=DEFAULT_MAX_ROWS,\n'
    '                    max_sheets=DEFAULT_MAX_SHEETS):\n'
    '    """读取受支持的表格文件，限制一次读取的最大行数。"""\n'
    '    extension = os.path.splitext(filepath)[1].lower()\n'
    '    row_limit = max_rows + 1 if max_rows is not None else None\n'
    '\n'
    "    if extension == '.csv':\n"
    "        for encoding in ('utf-8', 'utf-8-sig', 'gbk', 'gb2312', 'latin-1'):\n"
    '            try:\n'
    '                return pd.read_csv(\n'
    '                    filepath, encoding=encoding, nrows=row_limit)\n'
    '            except (UnicodeDecodeError, UnicodeError):\n'
    '                continue\n'
    "        raise ValueError('无法读取 CSV 文件（编码不支持）')\n"
    '\n'
    "    if extension in ('.xlsx', '.xls'):\n"
    '        with pd.ExcelFile(filepath) as workbook:\n'
    '            if len(workbook.sheet_names) > max_sheets:\n'
    '                raise ValueError(\n'
    "                    f'工作表数量超过限制（{len(workbook.sheet_names)} > '\n"
    "                    f'{max_sheets}）')\n"
    '            sheet = 1 if len(workbook.sheet_names) > 1 else 0\n'
    '            return pd.read_excel(\n'
    '                workbook, sheet_name=sheet, nrows=row_limit)\n'
    '\n'
    "    if extension == '.json':\n"
    '        return pd.read_json(filepath)\n'
    '\n'
    "    if extension in ('.h5', '.hdf5'):\n"
    '        try:\n'
    '            return pd.read_hdf(filepath)\n'
    '        except Exception:\n'
    "            with pd.HDFStore(filepath, mode='r') as store:\n"
    '                keys = store.keys()\n'
    '                if keys:\n'
    '                    return pd.read_hdf(filepath, key=keys[0])\n'
    "            raise ValueError('HDF5 文件中未找到有效数据集')\n"
    '\n'
    "    if extension == '.mat':\n"
    '        from scipy.io import loadmat\n'
    '        mat = loadmat(filepath)\n'
    '        for key, value in mat.items():\n'
    "            if not key.startswith('__'):\n"
    '                try:\n'
    '                    return pd.DataFrame(value)\n'
    '                except Exception as error:\n'
    '                    logger.debug(\n'
    "                        'MAT 变量 %s 无法转换为表格：%s', key, error)\n"
    "        raise ValueError('MAT 文件中未找到可转换为表格的数据')\n"
    '\n'
    '    raise ValueError(\n'
    "        f'不支持的文件格式: {extension}'\n"
    "        '（支持 .csv / .xlsx / .json / .h5 / .mat）')\n"
    '\n'
    '\n'
    'def validate_calce_dataframe(\n'
    '        dataframe, discharge_step=7, window_size=64, rated_capacity=1.1,\n'
    '        max_rows=DEFAULT_MAX_ROWS, max_columns=DEFAULT_MAX_COLUMNS):\n'
    '    """Validate one normalized CALCE table without mutating the caller."""\n'
    '    errors = []\n'
    '    if not isinstance(dataframe, pd.DataFrame):\n'
    "        return ['CALCE 数据必须是表格结构']\n"
    '    df = dataframe.copy()\n'
    '    normalize_column_names(df)\n'
    '\n'
    '    if len(df) > max_rows:\n'
    "        errors.append(f'数据行数超过限制（{len(df)} > {max_rows}）')\n"
    '    if len(df.columns) > max_columns:\n'
    "        errors.append(f'数据列数超过限制（{len(df.columns)} > {max_columns}）')\n"
    '    duplicated = [\n'
    '        str(name) for name in df.columns[df.columns.duplicated()].unique()]\n'
    '    if duplicated:\n'
    '        errors.append(f\'存在重复列：{", ".join(duplicated)}\')\n'
    '        return errors\n'
    '\n'
    '    actual_columns = [str(column).strip() for column in df.columns]\n'
    '    missing = [\n'
    '        column for column in REQUIRED_COLUMNS if column not in actual_columns]\n'
    '    if missing:\n'
    '        errors.append(f\'缺少必要列：{", ".join(missing)}\')\n'
    '        return errors\n'
    '\n'
    "    parsed_time = pd.to_datetime(df['Date_Time'], errors='coerce')\n"
    '    if parsed_time.isna().any():\n'
    "        errors.append('日期时间列包含无法解析的值')\n"
    '    elif not parsed_time.is_monotonic_increasing:\n'
    "        errors.append('日期时间必须按时间单调递增')\n"
    '\n'
    '    numeric = {}\n'
    '    for column in (\n'
    "            'Cycle_Index', 'Step_Index', 'Voltage(V)', 'Current(A)',\n"
    "            'Test_Time(s)'):\n"
    "        values = pd.to_numeric(df[column], errors='coerce')\n"
    '        numeric[column] = values\n'
    '        array = values.to_numpy(dtype=np.float64, na_value=np.nan)\n'
    '        if not np.all(np.isfinite(array)):\n'
    "            errors.append(f'{column} 必须全部是有限数值')\n"
    "    if any('有限数值' in error for error in errors):\n"
    '        return errors\n'
    '\n'
    "    cycle_values = numeric['Cycle_Index'].to_numpy(dtype=np.float64)\n"
    '    if np.any(np.diff(cycle_values) < 0):\n'
    "        errors.append('循环顺序必须单调递增，不能回退')\n"
    '\n'
    "    step_values = numeric['Step_Index']\n"
    '    discharge_mask = step_values == discharge_step\n'
    '    if not discharge_mask.any():\n'
    "        errors.append(f'未找到放电工步（Step_Index={discharge_step}）')\n"
    '        return errors\n'
    "    discharge_cycles = numeric['Cycle_Index'][discharge_mask].nunique()\n"
    '    if discharge_cycles <= window_size:\n'
    '        errors.append(\n'
    "            f'有效放电循环数 {discharge_cycles} 必须大于窗口大小 '\n"
    "            f'{window_size}')\n"
    '\n'
    "    test_times = numeric['Test_Time(s)']\n"
    '    group_frame = pd.DataFrame({\n'
    "        'cycle': numeric['Cycle_Index'],\n"
    "        'step': step_values,\n"
    "        'time': test_times,\n"
    '    })\n'
    "    if any(not group['time'].is_monotonic_increasing\n"
    "           for _, group in group_frame.groupby(['cycle', 'step'], sort=False)):\n"
    "        errors.append('同一循环和工步内的测试时间必须单调递增')\n"
    '\n'
    "    discharge_current = numeric['Current(A)'][discharge_mask]\n"
    '    if len(discharge_current) == 0 or float(discharge_current.median()) >= 0:\n'
    "        errors.append('放电工步电流方向异常，应以负电流为主')\n"
    '\n'
    "    for cycle in numeric['Cycle_Index'][discharge_mask].drop_duplicates():\n"
    "        mask = discharge_mask & (numeric['Cycle_Index'] == cycle)\n"
    '        times = test_times[mask].to_numpy(dtype=np.float64)\n'
    "        currents = numeric['Current(A)'][mask].to_numpy(dtype=np.float64)\n"
    '        if len(times) < 2:\n'
    '            continue\n'
    '        capacity = -float(np.sum(np.diff(times) * currents[1:]) / 3600)\n'
    '        if (not np.isfinite(capacity) or capacity <= 0 or\n'
    '                capacity > rated_capacity * 5):\n'
    '            errors.append(\n'
    "                f'循环 {cycle:g} 的放电容量 {capacity:.6g} Ah 超出合理范围')\n"
    '            break\n'
    '    return errors\n'
    '\n'
    '\n'
    'def _structure_depth(value, depth=1, seen=None):\n'
    '    if seen is None:\n'
    '        seen = set()\n'
    '    if isinstance(value, (dict, list, tuple, np.ndarray, np.void)):\n'
    '        identity = id(value)\n'
    '        if identity in seen:\n'
    '            return depth\n'
    '        seen.add(identity)\n'
    '    if isinstance(value, dict):\n'
    '        children = value.values()\n'
    '    elif isinstance(value, (list, tuple)):\n'
    '        children = value\n'
    '    elif isinstance(value, np.ndarray) and value.dtype == object:\n'
    '        children = value.flat\n'
    '    elif isinstance(value, np.void) and value.dtype.names:\n'
    '        children = (value[name] for name in value.dtype.names)\n'
    '    else:\n'
    '        return depth\n'
    '    child_depths = [\n'
    '        _structure_depth(child, depth + 1, seen) for child in children]\n'
    '    return max([depth, *child_depths])\n'
    '\n'
    '\n'
    'def _find_named_value(value, target, depth=0, max_depth=12):\n'
    '    if depth > max_depth:\n'
    '        return None\n'
    '    if isinstance(value, dict):\n'
    '        if target in value:\n'
    '            return value[target]\n'
    '        for child in value.values():\n'
    '            found = _find_named_value(child, target, depth + 1, max_depth)\n'
    '            if found is not None:\n'
    '                return found\n'
    '    elif isinstance(value, (list, tuple)):\n'
    '        for child in value:\n'
    '            found = _find_named_value(child, target, depth + 1, max_depth)\n'
    '            if found is not None:\n'
    '                return found\n'
    '    elif isinstance(value, np.ndarray) and value.dtype == object:\n'
    '        for child in value.flat:\n'
    '            found = _find_named_value(child, target, depth + 1, max_depth)\n'
    '            if found is not None:\n'
    '                return found\n'
    '    return None\n'
    '\n'
    '\n'
    'def _as_scalar(value):\n'
    '    array = np.asarray(value).reshape(-1)\n'
    '    return array[0] if len(array) else None\n'
    '\n'
    '\n'
    'def validate_nasa_structure(\n'
    '        structure, window_size=64, rated_capacity=1.1,\n'
    '        max_structure_depth=DEFAULT_MAX_STRUCTURE_DEPTH):\n'
    '    """Validate NASA MAT semantics without applying CALCE column rules."""\n'
    '    errors = []\n'
    '    depth = _structure_depth(structure)\n'
    '    if depth > max_structure_depth:\n'
    '        errors.append(\n'
    "            f'NASA MAT 结构深度超过限制（{depth} > {max_structure_depth}）')\n"
    '        return errors\n'
    '\n'
    '    cycles = _find_named_value(\n'
    "        structure, 'cycle', max_depth=max_structure_depth)\n"
    '    if cycles is None:\n'
    "        return ['NASA MAT 中未找到 cycle 结构']\n"
    '    if isinstance(cycles, dict):\n'
    '        cycle_items = [cycles]\n'
    '    elif isinstance(cycles, np.ndarray):\n'
    '        cycle_items = list(cycles.reshape(-1))\n'
    '    else:\n'
    '        cycle_items = list(cycles) if isinstance(\n'
    '            cycles, (list, tuple)) else [cycles]\n'
    '\n'
    '    capacities = []\n'
    '    invalid_capacity = False\n'
    '    for cycle in cycle_items:\n'
    '        if not isinstance(cycle, dict):\n'
    '            continue\n'
    "        cycle_type = str(_as_scalar(cycle.get('type', ''))).lower()\n"
    "        if cycle_type != 'discharge':\n"
    '            continue\n'
    "        data = cycle.get('data', {})\n"
    '        if not isinstance(data, dict):\n'
    '            continue\n'
    "        capacity = _as_scalar(data.get('Capacity'))\n"
    "        if capacity is None and {'Current_measured', 'Time'}.issubset(data):\n"
    "            current = np.asarray(data['Current_measured'], dtype=float).reshape(-1)\n"
    "            times = np.asarray(data['Time'], dtype=float).reshape(-1)\n"
    '            if len(times) > 1 and len(current) == len(times):\n'
    '                capacity = -np.sum(np.diff(times) * current[1:]) / 3600\n'
    '        if not _is_finite_number(capacity):\n'
    '            invalid_capacity = True\n'
    '            continue\n'
    '        capacity = float(capacity)\n'
    '        if capacity <= 0 or capacity > rated_capacity * 5:\n'
    "            errors.append(f'NASA 放电容量 {capacity:.6g} Ah 超出合理范围')\n"
    '        else:\n'
    '            capacities.append(capacity)\n'
    '    if invalid_capacity:\n'
    "        errors.append('NASA 放电容量必须全部是有限数值')\n"
    '    if len(capacities) <= window_size:\n'
    '        errors.append(\n'
    "            f'NASA 有效放电循环数 {len(capacities)} 必须大于窗口大小 '\n"
    "            f'{window_size}')\n"
    '    return errors\n'
    '\n'
    '\n'
    'def _validate_calce_file(\n'
    '        filepath, discharge_step, window_size, rated_capacity,\n'
    '        max_file_bytes, max_rows, max_columns, max_sheets):\n'
    '    errors = validate_file_resource_limits(\n'
    '        filepath, max_file_bytes=max_file_bytes, max_sheets=max_sheets)\n'
    '    if errors:\n'
    '        return errors\n'
    '    try:\n'
    '        dataframe = _read_data_file(\n'
    '            filepath, max_rows=max_rows, max_sheets=max_sheets)\n'
    '    except Exception as exc:\n'
    "        return [f'文件无法读取：{exc}']\n"
    '    return validate_calce_dataframe(\n'
    '        dataframe, discharge_step=discharge_step,\n'
    '        window_size=window_size, rated_capacity=rated_capacity,\n'
    '        max_rows=max_rows, max_columns=max_columns)\n'
    '\n'
    '\n'
    'def _load_nasa_structure(filepath):\n'
    '    from scipy.io import loadmat\n'
    '    raw = loadmat(filepath, simplify_cells=True)\n'
    '    return {\n'
    "        key: value for key, value in raw.items() if not key.startswith('__')}\n"
    '\n'
    '\n'
    'def _validate_nasa_file(\n'
    '        filepath, window_size, rated_capacity, max_file_bytes,\n'
    '        max_sheets, max_structure_depth):\n'
    '    errors = validate_file_resource_limits(\n'
    '        filepath, max_file_bytes=max_file_bytes, max_sheets=max_sheets)\n'
    '    if errors:\n'
    '        return errors\n'
    '    try:\n'
    '        structure = _load_nasa_structure(filepath)\n'
    '    except Exception as exc:\n'
    "        return [f'NASA MAT 文件无法读取：{exc}']\n"
    '    return validate_nasa_structure(\n'
    '        structure, window_size=window_size, rated_capacity=rated_capacity,\n'
    '        max_structure_depth=max_structure_depth)\n'
    '\n'
    '\n'
    'def validate_imported_item(\n'
    '        path, log_callback=None, discharge_step=7, extensions=None,\n'
    "        adapter_type='CALCE', window_size=64, rated_capacity=1.1,\n"
    '        max_file_bytes=DEFAULT_MAX_FILE_BYTES, max_rows=DEFAULT_MAX_ROWS,\n'
    '        max_columns=DEFAULT_MAX_COLUMNS, max_sheets=DEFAULT_MAX_SHEETS,\n'
    '        max_structure_depth=DEFAULT_MAX_STRUCTURE_DEPTH):\n'
    '    """Validate one imported battery path with adapter-specific rules."""\n'
    '    adapter_type = str(adapter_type).upper()\n'
    "    if adapter_type not in ('CALCE', 'NASA'):\n"
    "        return [f'不支持的数据适配器：{adapter_type}']\n"
    '    if extensions is None:\n'
    "        extensions = ('.mat',) if adapter_type == 'NASA' else ('.xlsx', '.csv')\n"
    '\n'
    '    if os.path.isfile(path):\n'
    '        file_list = [path]\n'
    '        enforce_window_per_file = True\n'
    '    elif os.path.isdir(path):\n'
    '        file_list = []\n'
    '        for extension in extensions:\n'
    "            file_list.extend(glob.glob(os.path.join(path, f'*{extension}')))\n"
    '        enforce_window_per_file = False\n'
    '    else:\n'
    "        return [f'路径不存在或不是有效的文件/文件夹：{path}']\n"
    '    if not file_list:\n'
    '        return [f\'未找到支持的文件（{", ".join(extensions)}）\']\n'
    '\n'
    '    errors = []\n'
    '    successful_cycle_count = 0\n'
    '    for filepath in sorted(file_list):\n'
    '        extension = os.path.splitext(filepath)[1].lower()\n'
    '        if extension not in extensions:\n'
    "            errors.append(f'不支持的文件类型：{os.path.basename(filepath)}')\n"
    '            continue\n'
    '        per_file_window = window_size if enforce_window_per_file else 0\n'
    "        if adapter_type == 'NASA':\n"
    '            file_errors = _validate_nasa_file(\n'
    '                filepath, per_file_window, rated_capacity, max_file_bytes,\n'
    '                max_sheets, max_structure_depth)\n'
    '            if not file_errors and not enforce_window_per_file:\n'
    '                structure = _load_nasa_structure(filepath)\n'
    '                cycles = _find_named_value(\n'
    "                    structure, 'cycle', max_depth=max_structure_depth)\n"
    '                successful_cycle_count += len(cycles) if hasattr(\n'
    "                    cycles, '__len__') else 1\n"
    '        else:\n'
    '            file_errors = _validate_calce_file(\n'
    '                filepath, discharge_step, per_file_window, rated_capacity,\n'
    '                max_file_bytes, max_rows, max_columns, max_sheets)\n'
    '            if not file_errors and not enforce_window_per_file:\n'
    '                frame = _read_data_file(\n'
    '                    filepath, max_rows=max_rows, max_sheets=max_sheets)\n'
    '                normalize_column_names(frame)\n'
    "                step = pd.to_numeric(frame['Step_Index'], errors='coerce')\n"
    "                cycle = pd.to_numeric(frame['Cycle_Index'], errors='coerce')\n"
    '                successful_cycle_count += int(\n'
    '                    cycle[step == discharge_step].nunique())\n'
    '        if file_errors:\n'
    '            filename = os.path.basename(filepath)\n'
    '            if log_callback:\n'
    "                log_callback(f'验证失败：{filename}')\n"
    "            errors.extend(f'[{filename}] {error}' for error in file_errors)\n"
    '\n'
    '    if (not enforce_window_per_file and not errors and\n'
    '            successful_cycle_count <= window_size):\n'
    '        errors.append(\n'
    "            f'整块电池有效循环数 {successful_cycle_count} 必须大于窗口大小 '\n"
    "            f'{window_size}')\n"
    '    return errors\n'
    '\n'
    '\n'
    'def validate_evaluation_request(config, imported_paths, log_callback=None):\n'
    '    """Unified gate used immediately before starting a worker."""\n'
    '    errors = validate_training_config(config)\n'
    '    if errors:\n'
    '        return errors\n'
    '    if not imported_paths:\n'
    "        return ['请先导入文件或文件夹']\n"
    '    for path in imported_paths:\n'
    '        errors.extend(validate_imported_item(\n'
    '            path,\n'
    '            log_callback=log_callback,\n'
    '            adapter_type=config.adapter_type,\n'
    '            window_size=config.window_size,\n'
    '            rated_capacity=config.rated_capacity,\n'
    '            discharge_step=config.discharge_step,\n'
    '        ))\n'
    '    return errors\n'
)

# ---- core/adapters.py ----
_MODULE_SOURCES['core.adapters'] = (
    '"""\n'
    '电池数据适配器模块\n'
    '\n'
    '通过适配器模式将不同来源、不同格式的电池循环数据统一为标准输出：\n'
    '  DataFrame(cycle, capacity, dq_v, resistance, CCCT, CVCT)\n'
    '\n'
    '其中 dq_v 是电压窗口 [voltage_lower, voltage_upper] 内的放电容量差，属于\n'
    "健康指标 HI，不是 SOH（SOH = C / C_rated）；旧列名 'SoH' 仍作为别名保留。\n"
    '\n'
    '内置两种适配器：\n'
    '  1. CALCEAdapter  — CALCE 数据集格式（xlsx/csv），工步可配置（默认 2/4/7）\n'
    '  2. NASAAdapter   — NASA 数据集格式（.mat），容量直接从结构体提取\n'
    '\n'
    '所有适配器返回相同的 (battery_dict, battery_list) 结构，\n'
    '下游 preprocess / train / evaluate 无需感知数据来源。\n'
    '"""\n'
    'import os\n'
    'import glob\n'
    'import numpy as np\n'
    'import pandas as pd\n'
    'from abc import ABC, abstractmethod\n'
    '\n'
    'from .preprocess import OUTLIER_MODES, filter_capacity_outliers\n'
    'from .validation import normalize_column_names, _read_data_file\n'
    '\n'
    '\n'
    'def _read_data_sort_date(path):\n'
    '    """Read only the first row needed to sort a CALCE source file."""\n'
    '    extension = os.path.splitext(path)[1].lower()\n'
    "    if extension == '.csv':\n"
    '        header = pd.read_csv(path, nrows=1)\n'
    "    elif extension == '.xlsx':\n"
    '        with pd.ExcelFile(path) as workbook:\n'
    '            sheet = 1 if len(workbook.sheet_names) > 1 else 0\n'
    '            header = pd.read_excel(workbook, sheet_name=sheet, nrows=1)\n'
    '    else:\n'
    "        raise ValueError(f'不支持的数据文件格式: {extension}')\n"
    '    normalize_column_names(header)\n'
    "    if len(header) == 0 or 'Date_Time' not in header.columns:\n"
    "        raise ValueError('缺少可用于排序的 Date_Time 首行')\n"
    "    return header['Date_Time'].iloc[0]\n"
    '\n'
    '\n'
    'def split_cc_cv(t, v, v_cv=4.2, tol=0.02):\n'
    '    """从一次充电记录里分出恒流(CC)与恒压(CV)的时长（秒）。\n'
    '\n'
    '    判据：电压第一次到达 v_cv - tol 就认为 CC 结束、进入 CV。\n'
    '    NASA 电池充电协议是 1.5 A 恒流充到 4.2 V 再恒压（v_cv 做成参数，换电池体系时可调）。\n'
    '    返回 (ccct, cvct)；数据太短返回 (nan, nan)；从未进入恒压则 cvct = 0。\n'
    '    """\n'
    '    t = np.asarray(t, dtype=float).reshape(-1)\n'
    '    v = np.asarray(v, dtype=float).reshape(-1)\n'
    '    if len(t) < 2 or len(t) != len(v):\n'
    '        return (np.nan, np.nan)\n'
    '    hit = np.flatnonzero(v >= v_cv - tol)\n'
    '    if len(hit) == 0:\n'
    '        return (float(t[-1] - t[0]), 0.0)\n'
    '    k = int(hit[0])\n'
    '    return (float(t[k] - t[0]), float(t[-1] - t[k]))\n'
    '\n'
    '\n'
    'class BatteryDataAdapter(ABC):\n'
    '    """电池数据适配器基类"""\n'
    '\n'
    '    @classmethod\n'
    '    @abstractmethod\n'
    '    def name(cls) -> str:\n'
    '        """适配器唯一标识（用于配置序列化）"""\n'
    '\n'
    '    @classmethod\n'
    '    @abstractmethod\n'
    '    def display_name(cls) -> str:\n'
    '        """UI 显示名称"""\n'
    '\n'
    '    @classmethod\n'
    '    @abstractmethod\n'
    '    def extensions(cls) -> tuple:\n'
    '        """支持的文件扩展名，如 (\'.xlsx\', \'.csv\')"""\n'
    '\n'
    '    @classmethod\n'
    '    @abstractmethod\n'
    '    def needs_step_config(cls) -> bool:\n'
    '        """是否需要用户配置工步序号"""\n'
    '\n'
    '    @classmethod\n'
    '    @abstractmethod\n'
    '    def needs_voltage_config(cls) -> bool:\n'
    '        """是否需要用户配置 SOH 上下电压"""\n'
    '\n'
    '    @abstractmethod\n'
    '    def load_battery_data(self, paths, voltage_upper, voltage_lower,\n'
    '                          cc_step, cv_step, discharge_step,\n'
    '                          log_callback, stop_flag) -> tuple:\n'
    '        """\n'
    '        加载电池数据，返回 (battery_dict, battery_list)\n'
    '\n'
    '        参数:\n'
    '            paths           : 导入路径列表（文件或文件夹）\n'
    '            voltage_upper   : SOH 上电压 (V)\n'
    '            voltage_lower   : SOH 下电压 (V)\n'
    '            cc_step         : 恒流充电工步序号\n'
    '            cv_step         : 恒压充电工步序号\n'
    '            discharge_step  : 放电工步序号\n'
    '            log_callback    : 日志回调函数\n'
    '            stop_flag       : 停止标志函数（返回 True 时中止）\n'
    '\n'
    '        返回:\n'
    '            battery_dict[name] = pd.DataFrame(cycle, capacity, dq_v, resistance, CCCT, CVCT)\n'
    '            battery_list = [name1, name2, ...]\n'
    '\n'
    '        说明:\n'
    "            dq_v 是电压窗口内的放电容量差（健康指标 HI），'SoH' 仅作为它的\n"
    '            兼容别名列保留，含义与 dq_v 完全相同。\n'
    '        """\n'
    '\n'
    '\n'
    '# ─── 通用容量提取逻辑（CALCE 适配器使用） ────────────────────────\n'
    '\n'
    'def _extract_capacity_from_tabular(df, voltage_upper, voltage_lower,\n'
    '                                   cc_step, cv_step, discharge_step,\n'
    '                                   log_callback, name):\n'
    '    """\n'
    '    从标准化 DataFrame 中提取每循环的容量、SOH、内阻、充放电时间。\n'
    '\n'
    '    这是 CALCE 适配器使用的核心逻辑，\n'
    '    工步序号由参数传入而非硬编码。\n'
    '    """\n'
    "    cycles = sorted(list(set(df['Cycle_Index'])))\n"
    '    discharge_cycles = []\n'
    '    discharge_capacities = []\n'
    '    health_indicator = []\n'
    '    internal_resistance = []\n'
    '    CCCT = []\n'
    '    CVCT = []\n'
    '\n'
    '    for c in cycles:\n'
    "        df_lim = df[df['Cycle_Index'] == c]\n"
    '\n'
    '        # 充电阶段：恒流 + 恒压\n'
    "        df_cc = df_lim[df_lim['Step_Index'] == cc_step]\n"
    "        df_cv = df_lim[df_lim['Step_Index'] == cv_step]\n"
    '\n'
    '        if len(df_cc) != 0:\n'
    "            ccct = np.max(df_cc['Test_Time(s)']) - np.min(df_cc['Test_Time(s)'])\n"
    '        else:\n'
    '            ccct = 0\n'
    '\n'
    '        if len(df_cv) != 0:\n'
    "            cvct = np.max(df_cv['Test_Time(s)']) - np.min(df_cv['Test_Time(s)'])\n"
    '        else:\n'
    '            cvct = 0\n'
    '\n'
    '        # 放电阶段\n'
    "        df_d = df_lim[df_lim['Step_Index'] == discharge_step]\n"
    "        d_v = df_d['Voltage(V)']\n"
    "        d_c = df_d['Current(A)']\n"
    "        d_t = df_d['Test_Time(s)']\n"
    "        d_im = df_d['Internal_Resistance(Ohm)'] if 'Internal_Resistance(Ohm)' in df_d.columns else pd.Series(dtype=float)\n"
    '\n'
    '        if (len(list(d_c)) != 0) and (len(list(d_t)) > 1):\n'
    '            time_diff = np.diff(list(d_t))\n'
    '            d_c_arr = np.array(list(d_c))[1:]\n'
    '            instant_cap = time_diff * d_c_arr / 3600\n'
    '            if len(instant_cap) == 0:\n'
    '                continue\n'
    '            discharge_cycles.append(c)\n'
    '            discharge_capacities.append(-1 * np.sum(instant_cap))\n'
    '            CCCT.append(ccct)\n'
    '            CVCT.append(cvct)\n'
    '\n'
    '            cum_cap = np.cumsum(instant_cap)\n'
    '            dec = np.abs(np.array(d_v) - voltage_upper)[1:]\n'
    '            if len(dec) == 0:\n'
    '                health_indicator.append(np.nan)\n'
    '            else:\n'
    '                start = cum_cap[np.argmin(dec)]\n'
    '                dec = np.abs(np.array(d_v) - voltage_lower)[1:]\n'
    '                end = cum_cap[np.argmin(dec)] if len(dec) != 0 else start\n'
    '                health_indicator.append(-1 * (end - start))\n'
    '\n'
    '            if len(d_im) != 0:\n'
    '                internal_resistance.append(np.mean(np.array(d_im)))\n'
    '            else:\n'
    '                internal_resistance.append(np.nan)\n'
    '\n'
    '    return (discharge_cycles, discharge_capacities, health_indicator,\n'
    '            internal_resistance, CCCT, CVCT)\n'
    '\n'
    '\n'
    'def _extract_capacity_lists_fast(df, voltage_upper, voltage_lower,\n'
    '                                 cc_step, cv_step, discharge_step):\n'
    '    """与 :func:`_extract_capacity_from_tabular` 数值等价的单遍扫描实现。\n'
    '\n'
    '    只对整表做一次 ``groupby``，不再逐循环布尔筛选；组内保持原始行顺序\n'
    '    （groupby 不会重排组内行），所以积分、极值、均值结果与原实现逐位一致。\n'
    '    返回同样的 6 个列表：\n'
    '    ``(cycles, capacities, health_indicator, resistance, CCCT, CVCT)``。\n'
    '    """\n'
    "    has_ir = 'Internal_Resistance(Ohm)' in df.columns\n"
    '    cycles, capacities, health_indicator = [], [], []\n'
    '    internal_resistance, CCCT, CVCT = [], [], []\n'
    '\n'
    "    for cyc, g in df.groupby('Cycle_Index', sort=True):\n"
    "        step = g['Step_Index'].to_numpy()\n"
    "        t = g['Test_Time(s)'].to_numpy(dtype=float)\n"
    "        v = g['Voltage(V)'].to_numpy(dtype=float)\n"
    "        i = g['Current(A)'].to_numpy(dtype=float)\n"
    '        is_cc, is_cv, is_d = step == cc_step, step == cv_step, step == discharge_step\n'
    '        ccct = float(t[is_cc].max() - t[is_cc].min()) if is_cc.any() else 0.0\n'
    '        cvct = float(t[is_cv].max() - t[is_cv].min()) if is_cv.any() else 0.0\n'
    '        td, vd, idd = t[is_d], v[is_d], i[is_d]\n'
    '        if len(idd) == 0 or len(td) <= 1:\n'
    '            continue\n'
    '        inst = np.diff(td) * idd[1:] / 3600.0\n'
    '        cum = np.cumsum(inst)\n'
    '        start = cum[np.argmin(np.abs(vd - voltage_upper)[1:])]\n'
    '        end = cum[np.argmin(np.abs(vd - voltage_lower)[1:])]\n'
    "        ir = (float(np.mean(g['Internal_Resistance(Ohm)'].to_numpy()[is_d]))\n"
    '              if has_ir else np.nan)\n'
    '        cycles.append(cyc)\n'
    '        capacities.append(float(-inst.sum()))\n'
    '        health_indicator.append(float(-(end - start)))\n'
    '        internal_resistance.append(ir)\n'
    '        CCCT.append(ccct)\n'
    '        CVCT.append(cvct)\n'
    '\n'
    '    return (cycles, capacities, health_indicator,\n'
    '            internal_resistance, CCCT, CVCT)\n'
    '\n'
    '\n'
    'def extract_cycles_fast(df, voltage_upper, voltage_lower, cc_step, cv_step, discharge_step):\n'
    '    """与 _extract_capacity_from_tabular 数值等价，但只扫描一遍整表。\n'
    '\n'
    '    组内保持原始行顺序（groupby 不会重排组内行），所以积分结果与原实现逐位一致。\n'
    '    返回 DataFrame：cycle, capacity, dq_v(原 SoH), resistance, CCCT, CVCT\n'
    '    """\n'
    '    (cycles, capacities, health_indicator,\n'
    '     internal_resistance, CCCT, CVCT) = _extract_capacity_lists_fast(\n'
    '        df, voltage_upper, voltage_lower, cc_step, cv_step, discharge_step)\n'
    '    return pd.DataFrame({\n'
    "        'cycle': cycles,\n"
    "        'capacity': capacities,\n"
    "        'dq_v': health_indicator,\n"
    "        'resistance': internal_resistance,\n"
    "        'CCCT': CCCT,\n"
    "        'CVCT': CVCT,\n"
    "    }, columns=['cycle', 'capacity', 'dq_v', 'resistance', 'CCCT', 'CVCT'])\n"
    '\n'
    '\n'
    'def _build_battery_dataframe(cycle_indices, discharge_capacities, health_indicator,\n'
    '                             internal_resistance, CCCT, CVCT,\n'
    '                             name, log_callback, clean_outliers=None,\n'
    '                             protect_knees=True, raw_index=None,\n'
    "                             outlier_mode='mark'):\n"
    '    """将提取数组组装为 DataFrame；默认保留有限原始容量以避免评估泄漏。\n'
    '\n'
    '    参数:\n'
    '        raw_index : 可选，与 capacities 等长的原始循环索引（如 NASA 原始工步序号）。\n'
    "                    提供时输出额外的 'raw_index' 列，便于回溯到源文件中的位置。\n"
    "        outlier_mode : ``'mark'``（默认，A12）/ ``'delete'`` / ``'off'``。\n"
    '                    默认只**标记**可疑点并保留数据：局部窗口均值对快速下降段和\n'
    '                    NASA 的容量再生（真实物理）都会滞后，直接删会误伤。\n'
    '        clean_outliers : 旧参数，保持向后兼容。显式传 ``True``/``False`` 时分别\n'
    "                    等价于 ``outlier_mode='delete'`` / ``'off'``；传 ``None``\n"
    '                    （默认）则使用 ``outlier_mode``。\n'
    '    """\n'
    '    count = len(discharge_capacities)\n'
    '    if count == 0:\n'
    '        return None\n'
    '\n'
    '    if clean_outliers is not None:\n'
    "        outlier_mode = 'delete' if clean_outliers else 'off'\n"
    '    if outlier_mode not in OUTLIER_MODES:\n'
    '        raise ValueError(\n'
    "            f'不支持的离群点模式: {outlier_mode}（可选 {OUTLIER_MODES}）')\n"
    '\n'
    '    discharge_capacities = np.array(discharge_capacities)\n'
    '    cycle_indices = np.asarray(cycle_indices)\n'
    '\n'
    '    def aligned(values):\n'
    '        result = np.full(count, np.nan, dtype=float)\n'
    '        values = np.asarray(values).reshape(-1)\n'
    '        available = min(count, len(values))\n'
    '        if available:\n'
    '            result[:available] = values[:available]\n'
    '        return result\n'
    '\n'
    '    if len(cycle_indices) != count:\n'
    "        raise ValueError('原始循环编号与有效放电容量数量不一致')\n"
    '    health_indicator = aligned(health_indicator)\n'
    '    internal_resistance = aligned(internal_resistance)\n'
    '    CCCT = aligned(CCCT)\n'
    '    CVCT = aligned(CVCT)\n'
    '    if raw_index is not None:\n'
    '        raw_index = aligned(raw_index)\n'
    '\n'
    '    filter_result = filter_capacity_outliers(\n'
    '        discharge_capacities, bins=40, protect_knees=protect_knees,\n'
    '        mode=outlier_mode)\n'
    '    idx = filter_result.indices\n'
    '\n'
    '    if log_callback:\n'
    "        if outlier_mode == 'delete':\n"
    '            log_callback(\n'
    "                '数据筛选原则：每个容量点只参考此前最多 40 个有效循环，'\n"
    "                '按历史均值 μ 与标准差 σ 剔除异常点。'\n"
    "                '不读取未来循环，初始稳定段和退化膝点受到保护。'\n"
    '            )\n'
    "        elif outlier_mode == 'mark':\n"
    '            log_callback(\n'
    "                '数据筛选原则：只**标记**可疑点、不删除（容量再生是真实物理；'\n"
    "                '局部窗口均值对快速下降段会滞后）。'\n"
    "                '判定只用此前最多 40 个有效循环，不读取未来循环。'\n"
    '            )\n'
    '        else:\n'
    '            log_callback(\n'
    "                '数据筛选原则：为避免使用完整测试轨迹造成评估泄漏，'\n"
    "                '默认保留所有有限容量点；仅剔除 NaN/Inf。')\n"
    '        log_callback(\n'
    "            f'{name} 异常值审计：输入 {count}，保留 {len(idx)}，'\n"
    "            f'剔除 {filter_result.removed_count}，'\n"
    "            f'标记 {filter_result.marked_count}，'\n"
    "            f'保护膝点 {len(filter_result.protected_indices)}。')\n"
    "        log_callback('─' * 40)\n"
    '\n'
    '    filtered_cycles = cycle_indices[idx]\n'
    '    has_cycle_reset = (\n'
    '        len(filtered_cycles) > 1 and\n'
    '        np.any(np.diff(filtered_cycles.astype(np.float64)) <= 0)\n'
    '    )\n'
    '    display_cycles = (\n'
    '        np.arange(1, len(filtered_cycles) + 1)\n'
    '        if has_cycle_reset else filtered_cycles\n'
    '    )\n'
    '    result_data = {\n'
    "        'cycle': display_cycles,\n"
    "        'capacity': discharge_capacities[idx],\n"
    "        'dq_v': health_indicator[idx],\n"
    "        'resistance': internal_resistance[idx],\n"
    "        'CCCT': CCCT[idx],\n"
    "        'CVCT': CVCT[idx],\n"
    '    }\n'
    '    # 兼容别名：dq_v 即电压窗口内的放电容量差（健康指标 HI），不是 SOH。\n'
    "    # 保留 'SoH' 键名，避免旧代码 / 旧 notebook 读取 df['SoH'] 时 KeyError。\n"
    "    result_data['SoH'] = result_data['dq_v']\n"
    '    if raw_index is not None:\n'
    "        result_data['raw_index'] = raw_index[idx]\n"
    '    if has_cycle_reset:\n'
    '        if log_callback:\n'
    '            log_callback(\n'
    "                f'{name} 检测到分文件循环号重复或回退；结果已按有效放电记录'\n"
    "                '连续编号。')\n"
    '    df_result = pd.DataFrame(result_data)\n'
    '    # raw_index 是原始序号，能完整取整时转成整数列（更贴近源文件里的编号）\n'
    '    if raw_index is not None and len(df_result) and \\\n'
    "            np.all(np.isfinite(df_result['raw_index'])) and \\\n"
    "            np.all(df_result['raw_index'] == np.floor(df_result['raw_index'])):\n"
    "        df_result['raw_index'] = df_result['raw_index'].astype(np.int64)\n"
    "    df_result.attrs['outlier_audit'] = {\n"
    "        'mode': outlier_mode,\n"
    "        'enabled': outlier_mode != 'off',\n"
    "        'protect_knees': bool(protect_knees),\n"
    "        'input_count': count,\n"
    "        'kept_count': int(len(idx)),\n"
    "        'removed_count': filter_result.removed_count,\n"
    "        'marked_count': filter_result.marked_count,\n"
    "        'mask': filter_result.mask.tolist(),\n"
    "        'marked_indices': filter_result.marked_indices.tolist(),\n"
    "        'removed_indices': filter_result.removed_indices.tolist(),\n"
    "        'protected_indices': filter_result.protected_indices.tolist(),\n"
    "        'reasons': dict(filter_result.reasons),\n"
    '    }\n'
    '\n'
    '    return df_result\n'
    '\n'
    '\n'
    '# ─── 1. CALCE 适配器 ──────────────────────────────────────────────\n'
    '\n'
    'class CALCEAdapter(BatteryDataAdapter):\n'
    '    """CALCE 数据集适配器 — xlsx/csv 格式，工步由用户配置"""\n'
    '\n'
    '    @classmethod\n'
    '    def name(cls):\n'
    "        return 'CALCE'\n"
    '\n'
    '    @classmethod\n'
    '    def display_name(cls):\n'
    "        return '.xlsx/.csv'\n"
    '\n'
    '    @classmethod\n'
    '    def extensions(cls):\n'
    "        return ('.xlsx', '.csv')\n"
    '\n'
    '    @classmethod\n'
    '    def needs_step_config(cls):\n'
    '        return True\n'
    '\n'
    '    @classmethod\n'
    '    def needs_voltage_config(cls):\n'
    '        return True\n'
    '\n'
    '    def load_battery_data(self, paths, voltage_upper, voltage_lower,\n'
    '                          cc_step, cv_step, discharge_step,\n'
    '                          log_callback, stop_flag):\n'
    '        battery_dict = {}\n'
    '        battery_list = []\n'
    '\n'
    '        for path in paths:\n'
    '            if stop_flag is not None and stop_flag():\n'
    '                break\n'
    '\n'
    '            if os.path.isfile(path):\n'
    '                name = os.path.splitext(os.path.basename(path))[0]\n'
    '                file_list = [path]\n'
    '            elif os.path.isdir(path):\n'
    "                name = os.path.basename(path.rstrip('/\\\\'))\n"
    '                file_list = []\n'
    '                for ext in self.extensions():\n'
    "                    file_list.extend(glob.glob(os.path.join(path, f'*{ext}')))\n"
    '                # 文件系统返回顺序不保证稳定；先排序，再按日期排序，\n'
    '                # 保证同一目录在不同机器上得到一致的读取顺序。\n'
    '                file_list = sorted(file_list)\n'
    '            else:\n'
    '                continue\n'
    '\n'
    '            if not file_list:\n'
    '                continue\n'
    '\n'
    '            if log_callback:\n'
    "                log_callback(f'加载数据集 {name} ...')\n"
    '\n'
    '            # 按日期排序\n'
    '            dates = []\n'
    '            valid_path = []\n'
    '            for p in file_list:\n'
    '                try:\n'
    '                    sort_date = _read_data_sort_date(p)\n'
    '                    if log_callback:\n'
    "                        log_callback(f'读取 {p} 的排序信息 ...')\n"
    '                    dates.append(sort_date)\n'
    '                    valid_path.append(p)\n'
    '                except Exception as e:\n'
    '                    if log_callback:\n'
    "                        log_callback(f'跳过 {p}，原因：{e}')\n"
    '\n'
    '            if len(valid_path) == 0:\n'
    '                if log_callback:\n'
    "                    log_callback(f'跳过数据集 {name}：没有可读取的有效文件')\n"
    '                continue\n'
    '\n'
    '            idx = np.argsort(dates)\n'
    '            path_sorted = np.array(valid_path)[idx]\n'
    '\n'
    '            all_cap = []\n'
    '            all_cycles = []\n'
    '            all_soh = []\n'
    '            all_ir = []\n'
    '            all_ccct = []\n'
    '            all_cvct = []\n'
    '\n'
    '            for p in path_sorted:\n'
    '                if stop_flag is not None and stop_flag():\n'
    '                    break\n'
    '                df = _read_data_file(p)\n'
    '                normalize_column_names(df)\n'
    '                if log_callback:\n'
    "                    log_callback(f'加载 {p} ...')\n"
    '\n'
    '                cycles, cap, soh, ir, ccct, cvct = _extract_capacity_lists_fast(\n'
    '                    df, voltage_upper, voltage_lower,\n'
    '                    cc_step, cv_step, discharge_step\n'
    '                )\n'
    '                all_cycles.extend(cycles)\n'
    '                all_cap.extend(cap)\n'
    '                all_soh.extend(soh)\n'
    '                all_ir.extend(ir)\n'
    '                all_ccct.extend(ccct)\n'
    '                all_cvct.extend(cvct)\n'
    '\n'
    '            df_result = _build_battery_dataframe(\n'
    '                all_cycles, all_cap, all_soh, all_ir, all_ccct, all_cvct,\n'
    '                name, log_callback\n'
    '            )\n'
    '            if df_result is not None:\n'
    '                if name in battery_dict:\n'
    '                    if log_callback:\n'
    "                        log_callback(f'跳过数据集 {name}：电池名称重复')\n"
    '                    continue\n'
    '                battery_dict[name] = df_result\n'
    '                battery_list.append(name)\n'
    '            elif log_callback:\n'
    "                log_callback(f'跳过数据集 {name}：没有可用的放电循环')\n"
    '\n'
    '        return battery_dict, battery_list\n'
    '\n'
    '\n'
    '# ─── 2. NASA 适配器 ───────────────────────────────────────────────\n'
    '\n'
    'class NASAAdapter(BatteryDataAdapter):\n'
    '    """NASA 数据集适配器 — .mat 格式，容量直接从结构体提取"""\n'
    '\n'
    '    @classmethod\n'
    '    def name(cls):\n'
    "        return 'NASA'\n"
    '\n'
    '    @classmethod\n'
    '    def display_name(cls):\n'
    "        return '.mat'\n"
    '\n'
    '    @classmethod\n'
    '    def extensions(cls):\n'
    "        return ('.mat',)\n"
    '\n'
    '    @classmethod\n'
    '    def needs_step_config(cls):\n'
    '        return False\n'
    '\n'
    '    @classmethod\n'
    '    def needs_voltage_config(cls):\n'
    '        return True\n'
    '\n'
    '    def load_battery_data(self, paths, voltage_upper, voltage_lower,\n'
    '                          cc_step, cv_step, discharge_step,\n'
    '                          log_callback, stop_flag, v_cv=None):\n'
    '        try:\n'
    '            from scipy.io import loadmat\n'
    '        except ImportError:\n'
    '            raise ImportError(\n'
    "                'NASA 数据集适配器需要 scipy 库。请在环境中安装：pip install scipy'\n"
    '            )\n'
    '\n'
    '        # CC/CV 分界电压：优先使用调用方显式传入的 v_cv；否则若 voltage_upper\n'
    '        # 看起来是合理的充电截止电压（>= 3.0 V，例如 NASA 用户填 4.2），就用它；\n'
    '        # 否则（例如沿用 CALCE 默认的 3.8 以下窗口电压）退回 4.2 V 默认值。\n'
    '        if v_cv is None:\n'
    '            if voltage_upper is not None and np.isfinite(voltage_upper) \\\n'
    '                    and voltage_upper >= 3.0:\n'
    '                v_cv = float(voltage_upper)\n'
    '            else:\n'
    '                v_cv = 4.2\n'
    '        else:\n'
    '            v_cv = float(v_cv)\n'
    '\n'
    '        battery_dict = {}\n'
    '        battery_list = []\n'
    '\n'
    '        for path in paths:\n'
    '            if stop_flag is not None and stop_flag():\n'
    '                break\n'
    '\n'
    "            if os.path.isfile(path) and path.lower().endswith('.mat'):\n"
    '                name = os.path.splitext(os.path.basename(path))[0]\n'
    '                file_list = [path]\n'
    '            elif os.path.isdir(path):\n'
    "                name = os.path.basename(path.rstrip('/\\\\'))\n"
    '                # 排序：glob 的返回顺序依赖文件系统，排序后读取顺序才可复现\n'
    "                file_list = sorted(glob.glob(os.path.join(path, '*.mat')))\n"
    '            else:\n'
    '                continue\n'
    '\n'
    '            if not file_list:\n'
    '                continue\n'
    '\n'
    '            if log_callback:\n'
    "                log_callback(f'加载数据集 {name}...')\n"
    '\n'
    '            discharge_capacities = []\n'
    '            discharge_cycles = []\n'
    '            discharge_raw_index = []\n'
    '            health_indicator = []\n'
    '            internal_resistance = []\n'
    '            CCCT = []\n'
    '            CVCT = []\n'
    '            pending_ccct = np.nan\n'
    '            pending_cvct = np.nan\n'
    '\n'
    '            for p in file_list:\n'
    '                if stop_flag is not None and stop_flag():\n'
    '                    break\n'
    '                try:\n'
    '                    mat = loadmat(p, simplify_cells=True)\n'
    '                except Exception as e:\n'
    '                    if log_callback:\n'
    "                        log_callback(f'跳过 {p}，原因：{e}')\n"
    '                    continue\n'
    '\n'
    '                # 找到电池结构体键（跳过 __header__ 等元数据键）\n'
    '                battery_key = None\n'
    '                for k in mat.keys():\n'
    "                    if not k.startswith('__'):\n"
    '                        battery_key = k\n'
    '                        break\n'
    '                if battery_key is None:\n'
    '                    if log_callback:\n'
    "                        log_callback(f'跳过 {p}，原因：未找到有效数据键')\n"
    '                    continue\n'
    '\n'
    '                battery_struct = mat[battery_key]\n'
    '                try:\n'
    '                    if not isinstance(battery_struct, dict):\n'
    "                        raise ValueError('电池根节点必须是结构体')\n"
    "                    cycles = battery_struct['cycle']\n"
    '                    if isinstance(cycles, dict):\n'
    '                        cycles = [cycles]\n'
    '                    else:\n'
    '                        cycles = np.asarray(\n'
    '                            cycles, dtype=object).reshape(-1).tolist()\n'
    '                except (KeyError, TypeError, ValueError) as e:\n'
    '                    if log_callback:\n'
    "                        log_callback(f'跳过 {p}，原因：数据结构异常 {e}')\n"
    '                    continue\n'
    '\n'
    '                for i in range(len(cycles)):\n'
    '                    if stop_flag is not None and stop_flag():\n'
    '                        break\n'
    '                    try:\n'
    '                        cycle = cycles[i]\n'
    '                        if not isinstance(cycle, dict):\n'
    '                            continue\n'
    "                        cycle_type = str(cycle.get('type', ''))\n"
    "                        data = cycle.get('data')\n"
    '                        if not isinstance(data, dict):\n'
    '                            continue\n'
    '\n'
    "                        if cycle_type.lower() == 'discharge':\n"
    '                            # NASA 数据集直接提供放电容量\n'
    "                            if 'Capacity' in data:\n"
    '                                cap = float(np.asarray(\n'
    "                                    data['Capacity']).reshape(-1)[0])\n"
    '                            else:\n'
    '                                # 回退：从电流和时间积分\n'
    '                                v = np.asarray(\n'
    "                                    data['Voltage_measured']).reshape(-1)\n"
    '                                c = np.asarray(\n'
    "                                    data['Current_measured']).reshape(-1)\n"
    "                                t = np.asarray(data['Time']).reshape(-1)\n"
    '                                if len(t) > 1:\n'
    '                                    dt = np.diff(t)\n'
    '                                    c_arr = c[1:]\n'
    '                                    cap = -np.sum(dt * c_arr / 3600)\n'
    '                                else:\n'
    '                                    continue\n'
    '\n'
    '                            if cap > 0 and not np.isnan(cap):\n'
    '                                # cycle 用「有效放电次数」编号（1,2,3,...），与文献里\n'
    '                                # 的放电循环数一致；原始工步序号保留在 raw_index 列。\n'
    '                                discharge_cycles.append(len(discharge_cycles) + 1)\n'
    '                                discharge_raw_index.append(i + 1)\n'
    '                                discharge_capacities.append(cap)\n'
    '\n'
    '                                # SOH：从电压-容量曲线提取\n'
    '                                v = np.asarray(\n'
    "                                    data.get('Voltage_measured', [])).reshape(-1)\n"
    '                                c_arr = np.asarray(\n'
    "                                    data.get('Current_measured', [])).reshape(-1)\n"
    "                                t = np.asarray(data.get('Time', [])).reshape(-1)\n"
    '                                if len(t) > 1:\n'
    '                                    dt = np.diff(t)\n'
    '                                    instant_cap = dt * c_arr[1:] / 3600\n'
    '                                    cum_cap = np.cumsum(instant_cap)\n'
    '                                    dec_upper = np.abs(v[1:] - voltage_upper)\n'
    '                                    if len(dec_upper) > 0:\n'
    '                                        start = cum_cap[np.argmin(dec_upper)]\n'
    '                                        dec_lower = np.abs(v[1:] - voltage_lower)\n'
    '                                        end = cum_cap[np.argmin(dec_lower)] if len(dec_lower) > 0 else start\n'
    '                                        health_indicator.append(-1 * (end - start))\n'
    '                                    else:\n'
    '                                        health_indicator.append(np.nan)\n'
    '                                else:\n'
    '                                    health_indicator.append(np.nan)\n'
    '\n'
    '                                internal_resistance.append(np.nan)\n'
    '                                CCCT.append(pending_ccct)\n'
    '                                CVCT.append(pending_cvct)\n'
    '                                pending_ccct = np.nan\n'
    '                                pending_cvct = np.nan\n'
    '\n'
    "                        elif cycle_type.lower() == 'charge':\n"
    '                            # 从充电阶段提取 CCCT / CVCT：按电压是否到达充电截止\n'
    '                            # 电压（v_cv）真实切分恒流段与恒压段，不再用固定比例估计。\n'
    "                            t = np.asarray(data.get('Time', [])).reshape(-1)\n"
    '                            v = np.asarray(\n'
    "                                data.get('Voltage_measured', [])).reshape(-1)\n"
    '                            pending_ccct, pending_cvct = split_cc_cv(\n'
    '                                t, v, v_cv=v_cv)\n'
    '                    except (IndexError, KeyError, ValueError):\n'
    '                        continue\n'
    '\n'
    '            df_result = _build_battery_dataframe(\n'
    '                discharge_cycles, discharge_capacities, health_indicator,\n'
    '                internal_resistance, CCCT, CVCT,\n'
    '                name, log_callback, raw_index=discharge_raw_index\n'
    '            )\n'
    '            if df_result is not None:\n'
    '                if name in battery_dict:\n'
    '                    if log_callback:\n'
    "                        log_callback(f'跳过数据集 {name}：电池名称重复')\n"
    '                    continue\n'
    '                battery_dict[name] = df_result\n'
    '                battery_list.append(name)\n'
    '            elif log_callback:\n'
    "                log_callback(f'跳过数据集 {name}：没有可用的放电循环')\n"
    '\n'
    '        return battery_dict, battery_list\n'
    '\n'
    '\n'
    '# ─── 适配器注册表 ─────────────────────────────────────────────────\n'
    '\n'
    'def detect_step_indices(df):\n'
    '    """从标准化后的 CALCE DataFrame 推断 (cc_step, cv_step, discharge_step)。\n'
    '\n'
    '    判据（尽量保守，识别不出就返回 None）：\n'
    '      * 放电：电流 < 0；\n'
    '      * 恒流充电 CC：电流 > 0 且电压在上升；\n'
    '      * 恒压充电 CV：电流 > 0 但在衰减，且电压接近本循环最大值。\n'
    '\n'
    "    返回 {'cc_step', 'cv_step', 'discharge_step', 'confidence', 'summary'}，\n"
    '    供 UI「自动识别工步」按钮使用；空表或缺少必需列时各项为 None。\n'
    '    """\n'
    "    result = {'cc_step': None, 'cv_step': None, 'discharge_step': None,\n"
    "              'confidence': 0.0, 'summary': '无法识别'}\n"
    "    required = ('Step_Index', 'Current(A)', 'Voltage(V)', 'Cycle_Index')\n"
    '    if df is None or len(df) == 0:\n'
    "        result['summary'] = '数据为空'\n"
    '        return result\n'
    '    if any(column not in df.columns for column in required):\n'
    "        result['summary'] = '缺少必要列：' + ', '.join(\n"
    '            column for column in required if column not in df.columns)\n'
    '        return result\n'
    '\n'
    '    try:\n'
    '        frame = df.loc[:, list(required)].dropna()\n'
    '        if len(frame) == 0:\n'
    "            result['summary'] = '数据为空'\n"
    '            return result\n'
    "        step = frame['Step_Index'].to_numpy()\n"
    "        current = frame['Current(A)'].to_numpy(dtype=float)\n"
    "        voltage = frame['Voltage(V)'].to_numpy(dtype=float)\n"
    "        cycle = frame['Cycle_Index'].to_numpy()\n"
    '\n'
    '        discharge_votes = {}\n'
    '        cc_votes = {}\n'
    '        cv_votes = {}\n'
    '        for cyc in pd.unique(cycle):\n'
    '            mask = cycle == cyc\n'
    '            group_step, group_current = step[mask], current[mask]\n'
    '            group_voltage = voltage[mask]\n'
    '            if len(group_step) == 0:\n'
    '                continue\n'
    '            max_voltage = float(np.nanmax(group_voltage))\n'
    '            for value in pd.unique(group_step):\n'
    '                cell = group_step == value\n'
    '                cell_current, cell_voltage = group_current[cell], group_voltage[cell]\n'
    '                if len(cell_current) == 0:\n'
    '                    continue\n'
    '                if np.all(cell_current < 0):\n'
    '                    discharge_votes[value] = discharge_votes.get(value, 0) + 1\n'
    '                    continue\n'
    '                if not np.all(cell_current > 0):\n'
    '                    continue\n'
    '                # 恒压段：电压基本不变且贴住本循环最高电压；恒流段：电压仍在上升\n'
    '                span = (float(np.nanmax(cell_voltage)) -\n'
    '                        float(np.nanmin(cell_voltage))) if len(cell_voltage) else 0.0\n'
    '                near_max = float(np.nanmax(cell_voltage)) >= max_voltage - 0.02\n'
    '                if near_max and span <= 0.05:\n'
    '                    cv_votes[value] = cv_votes.get(value, 0) + 1\n'
    '                elif span > 0.05:\n'
    '                    cc_votes[value] = cc_votes.get(value, 0) + 1\n'
    '\n'
    '        def best(votes):\n'
    '            if not votes:\n'
    '                return None\n'
    '            return int(max(votes.items(), key=lambda item: (item[1], -item[0]))[0])\n'
    '\n'
    '        cc_step, cv_step = best(cc_votes), best(cv_votes)\n'
    '        discharge_step = best(discharge_votes)\n'
    '        if cc_step is None and cv_step is None and discharge_step is None:\n'
    "            result['summary'] = '无法识别'\n"
    '            return result\n'
    '\n'
    '        cycle_count = max(len(pd.unique(cycle)), 1)\n'
    '        hits = (cc_votes.get(cc_step, 0) + cv_votes.get(cv_step, 0) +\n'
    '                discharge_votes.get(discharge_step, 0))\n'
    '        detected = sum(1 for value in (cc_step, cv_step, discharge_step)\n'
    '                       if value is not None)\n'
    '        coverage = min(hits / (3.0 * cycle_count), 1.0)\n'
    '        confidence = float(min(1.0, 0.5 * detected / 3.0 + 0.5 * coverage))\n'
    '        result.update({\n'
    "            'cc_step': cc_step,\n"
    "            'cv_step': cv_step,\n"
    "            'discharge_step': discharge_step,\n"
    "            'confidence': confidence,\n"
    "            'summary': (\n"
    "                f'恒流 {cc_step}，恒压 {cv_step}，放电 {discharge_step}'\n"
    "                f'（置信度 {confidence:.2f}）'),\n"
    '        })\n'
    '        return result\n'
    '    except Exception as e:  # 防御：自动识别失败不应影响主流程\n'
    "        result['summary'] = f'识别失败：{e}'\n"
    '        return result\n'
    '\n'
    '\n'
    'ADAPTERS = {\n'
    "    'CALCE': CALCEAdapter,\n"
    "    'NASA': NASAAdapter,\n"
    '}\n'
    '\n'
    '\n'
    "def get_adapter(adapter_type='CALCE'):\n"
    '    """根据名称获取适配器实例。\n'
    '\n'
    '    未知名称直接抛 ValueError 并列出支持的名字，避免静默回退到 CALCE\n'
    '    导致后续出现难以定位的结构性错误。\n'
    '    """\n'
    "    key = adapter_type if adapter_type is not None else 'CALCE'\n"
    '    if not isinstance(key, str):\n'
    '        raise ValueError(\n'
    "            f'数据适配器类型必须是字符串，收到 {type(adapter_type).__name__}；'\n"
    '            f\'支持的类型：{", ".join(ADAPTERS)}\')\n'
    '    normalized = key.strip().upper()\n'
    '    if normalized not in ADAPTERS:\n'
    '        raise ValueError(\n'
    "            f'不支持的数据适配器：{adapter_type}；'\n"
    '            f\'支持的类型：{", ".join(ADAPTERS)}\')\n'
    '    return ADAPTERS[normalized]()\n'
    '\n'
    '\n'
    'def get_adapter_list():\n'
    '    """返回所有适配器的 (name, display_name) 列表，用于 UI 下拉框"""\n'
    '    return [(cls.name(), cls.display_name()) for cls in ADAPTERS.values()]\n'
)

# ---- core/dataload.py ----
_MODULE_SOURCES['core.dataload'] = (
    'import os\n'
    'import glob\n'
    'import numpy as np\n'
    'import pandas as pd\n'
    'from .preprocess import drop_outlier\n'
    'from .validation import normalize_column_names, _read_data_file\n'
    'from .adapters import get_adapter\n'
    '\n'
    '\n'
    'def load_battery_from_paths(imported_paths, log_callback=None, stop_flag=None,\n'
    '                           voltage_upper=3.8, voltage_lower=3.4,\n'
    "                           adapter_type='CALCE',\n"
    '                           cc_step=2, cv_step=4, discharge_step=7):\n'
    '    """加载电池数据，自动选择适配器处理不同格式。\n'
    '\n'
    '    参数:\n'
    '        imported_paths : 导入路径列表（文件或文件夹）\n'
    '        log_callback   : 日志回调函数\n'
    '        stop_flag      : 停止标志函数\n'
    '        voltage_upper  : SOH 上电压 (V)\n'
    '        voltage_lower  : SOH 下电压 (V)\n'
    "        adapter_type   : 适配器类型（'CALCE' / 'NASA'）\n"
    '        cc_step        : 恒流充电工步序号\n'
    '        cv_step        : 恒压充电工步序号\n'
    '        discharge_step : 放电工步序号\n'
    '\n'
    '    返回:\n'
    '        (battery_dict, battery_list)\n'
    '    """\n'
    '    adapter = get_adapter(adapter_type)\n'
    '    return adapter.load_battery_data(\n'
    '        imported_paths, voltage_upper, voltage_lower,\n'
    '        cc_step, cv_step, discharge_step,\n'
    '        log_callback, stop_flag\n'
    '    )\n'
)

# ---- core/result_semantics.py ----
_MODULE_SOURCES['core.result_semantics'] = (
    '"""Interpret failure-cycle results without losing original cycle identifiers."""\n'
    '\n'
    'import numpy as np\n'
    '\n'
    '#: 判定「真正失效」所需的连续低于阈值循环数（A12）。\n'
    '#: 默认 1 = 旧行为（首次下穿即失效），保持向后兼容；设为 3 可避免单点噪声\n'
    '#: 下穿阈值就被当成失效。\n'
    'DEFAULT_DEBOUNCE_CYCLES = 1\n'
    '\n'
    '\n'
    'def first_failure_index(values, threshold, debounce=DEFAULT_DEBOUNCE_CYCLES):\n'
    '    """首次**持续**下穿的位置；从未下穿返回 None（右删失）。\n'
    '\n'
    '    这是全工程**唯一**的失效判定实现：``core.protocol.first_cross``、\n'
    '    ``core.evaluate`` 与 ``core.train`` 都委托到这里，避免多份逻辑各自漂移。\n'
    '\n'
    '    ``debounce`` 是需要连续低于阈值的循环数：\n'
    '    ``1``（默认）＝「首次下穿即失效」；``3`` 则要求连续 3 个循环低于阈值。\n'
    '    返回值仍是**连续区间的第一个位置**，因此开启去抖也不会让报告的失效循环\n'
    '    比真实下穿更晚。\n'
    '    """\n'
    '    array = np.asarray(values, dtype=np.float64).reshape(-1)\n'
    '    below = array < threshold\n'
    '    run = int(max(1, debounce))\n'
    '    if run == 1:\n'
    '        positions = np.flatnonzero(below)\n'
    '        return int(positions[0]) if len(positions) else None\n'
    '\n'
    '    if len(below) < run:\n'
    '        return None\n'
    '    # 长度为 run 的滑窗内是否全为 True。\n'
    "    # 注意：``mode='valid'`` 的输出下标 i 正好对应该窗口的**起点** i，\n"
    '    # 所以命中的第一个下标就是「首次下穿处」，不需要再偏移。\n'
    '    window_ok = np.convolve(\n'
    "        below.astype(np.int64), np.ones(run, dtype=np.int64), mode='valid')\n"
    '    hits = np.flatnonzero(window_ok == run)\n'
    '    return int(hits[0]) if len(hits) else None\n'
    '\n'
    '\n'
    'def _cycle_value(cycle_ids, position):\n'
    '    if position is None:\n'
    '        return None\n'
    '    value = np.asarray(cycle_ids).reshape(-1)[position]\n'
    '    return value.item() if isinstance(value, np.generic) else value\n'
    '\n'
    '\n'
    'def analyze_failure_cycles(cycle_ids, measured, predicted, threshold,\n'
    '                           prediction_start=0):\n'
    '    """Return measured/predicted failure states using the supplied cycle IDs."""\n'
    '    cycle_ids = np.asarray(cycle_ids).reshape(-1)\n'
    '    measured = np.asarray(measured, dtype=np.float64).reshape(-1)\n'
    '    predicted = np.asarray(predicted, dtype=np.float64).reshape(-1)\n'
    '    if (isinstance(prediction_start, bool) or\n'
    '            not isinstance(prediction_start, (int, np.integer)) or\n'
    '            not 0 <= int(prediction_start) <= len(measured)):\n'
    "        raise ValueError('预测起始位置必须位于实测序列范围内')\n"
    '    prediction_start = int(prediction_start)\n'
    '    if (len(cycle_ids) != len(measured) or\n'
    '            len(predicted) != len(measured) - prediction_start):\n'
    "        raise ValueError('循环编号、实测容量和预测区间长度不匹配')\n"
    '\n'
    '    measured_position = first_failure_index(measured, threshold)\n'
    '    predicted_local_position = first_failure_index(predicted, threshold)\n'
    '    predicted_position = (\n'
    '        None if predicted_local_position is None\n'
    '        else prediction_start + predicted_local_position)\n'
    '\n'
    '    def status(position):\n'
    '        if position is None:\n'
    "            return 'not_observed'\n"
    '        if position == 0:\n'
    "            return 'initial_failure'\n"
    "        return 'failed'\n"
    '\n'
    '    return {\n'
    "        'measured_failure_cycle': _cycle_value(\n"
    '            cycle_ids, measured_position),\n'
    "        'predicted_failure_cycle': _cycle_value(\n"
    '            cycle_ids, predicted_position),\n'
    "        'measured_failure_position': measured_position,\n"
    "        'predicted_failure_position': predicted_position,\n"
    "        'measured_failure_status': status(measured_position),\n"
    "        'predicted_failure_status': status(predicted_position),\n"
    '    }\n'
)

# ---- core/run_snapshot.py ----
_MODULE_SOURCES['core.run_snapshot'] = (
    '"""Immutable snapshots for one evaluation or prediction run."""\n'
    '\n'
    'from copy import deepcopy\n'
    'from dataclasses import dataclass, replace\n'
    'from datetime import datetime, timezone\n'
    'from types import MappingProxyType\n'
    'from typing import Any, Mapping\n'
    'from uuid import uuid4\n'
    '\n'
    '\n'
    'def _freeze(value):\n'
    '    if isinstance(value, Mapping):\n'
    '        return MappingProxyType({key: _freeze(item)\n'
    '                                 for key, item in value.items()})\n'
    '    if isinstance(value, (list, tuple)):\n'
    '        return tuple(_freeze(item) for item in value)\n'
    '    if isinstance(value, set):\n'
    '        return frozenset(_freeze(item) for item in value)\n'
    '    return value\n'
    '\n'
    '\n'
    'def _thaw(value):\n'
    '    if isinstance(value, Mapping):\n'
    '        return {key: _thaw(item) for key, item in value.items()}\n'
    '    if isinstance(value, tuple):\n'
    '        return [_thaw(item) for item in value]\n'
    '    if isinstance(value, frozenset):\n'
    '        return [_thaw(item) for item in value]\n'
    '    return deepcopy(value)\n'
    '\n'
    '\n'
    '@dataclass(frozen=True)\n'
    'class RunSnapshot:\n'
    '    """A deeply frozen record of inputs and outputs for exactly one run."""\n'
    '\n'
    '    run_id: str\n'
    '    started_at: str\n'
    '    imported_paths: tuple[str, ...]\n'
    '    config: Mapping[str, Any]\n'
    '    results: Mapping[str, Any]\n'
    '    elapsed_seconds: float | None = None\n'
    '\n'
    '    @classmethod\n'
    '    def capture(cls, config, imported_paths, *, now=None, run_id=None):\n'
    '        captured_at = now or datetime.now(timezone.utc)\n'
    '        if captured_at.tzinfo is None:\n'
    '            captured_at = captured_at.replace(tzinfo=timezone.utc)\n'
    '        captured_at = captured_at.astimezone(timezone.utc)\n'
    '        if run_id is None:\n'
    "            stamp = captured_at.strftime('%Y%m%dT%H%M%SZ')\n"
    "            run_id = f'{stamp}-{uuid4().hex[:8]}'\n"
    '\n'
    '        config_data = (\n'
    "            config.to_dict() if hasattr(config, 'to_dict') else dict(config)\n"
    '        )\n'
    '        copied_paths = tuple(str(path) for path in deepcopy(imported_paths))\n'
    '        return cls(\n'
    '            run_id=str(run_id),\n'
    '            started_at=captured_at.isoformat(),\n'
    '            imported_paths=copied_paths,\n'
    '            config=_freeze(deepcopy(config_data)),\n'
    '            results=_freeze({}),\n'
    '        )\n'
    '\n'
    '    def with_results(self, results, *, elapsed_seconds):\n'
    '        return replace(\n'
    '            self,\n'
    '            results=_freeze(deepcopy(results)),\n'
    '            elapsed_seconds=float(elapsed_seconds),\n'
    '        )\n'
    '\n'
    '    def config_dict(self):\n'
    '        return _thaw(self.config)\n'
    '\n'
    '    def results_dict(self):\n'
    '        return _thaw(self.results)\n'
)

# ---- core/report_export.py ----
_MODULE_SOURCES['core.report_export'] = (
    '"""Snapshot-based, atomic report export."""\n'
    '\n'
    'import errno\n'
    'import json\n'
    'import os\n'
    'from pathlib import Path\n'
    'from uuid import uuid4\n'
    '\n'
    'import numpy as np\n'
    'import pandas as pd\n'
    '\n'
    'from core.run_snapshot import RunSnapshot\n'
    'from utils.paths import REPORT_DIR\n'
    '\n'
    '\n'
    'class ExportCancelled(RuntimeError):\n'
    '    """The user declined to overwrite existing report artifacts."""\n'
    '\n'
    '\n'
    'class ReportExportError(RuntimeError):\n'
    '    """A report could not be written, with a user-actionable message."""\n'
    '\n'
    '\n'
    'def friendly_export_error(error):\n'
    "    error_number = getattr(error, 'errno', None)\n"
    "    windows_error = getattr(error, 'winerror', None)\n"
    '    if error_number == errno.ENOSPC:\n'
    "        return '磁盘空间不足。请释放空间或选择其他磁盘后重试。'\n"
    '    if (isinstance(error, PermissionError)\n'
    '            or error_number in (errno.EACCES, errno.EPERM)\n'
    '            or windows_error in (5, 32, 33)):\n'
    '        return (\n'
    "            '文件可能被占用或目录无写入权限。请关闭正在占用报告的 '\n"
    "            'Excel/图片查看器，或选择有写入权限的目录后重试。'\n"
    '        )\n'
    "    return f'导出失败：{error}。请检查目标目录后重试。'\n"
    '\n'
    '\n'
    'def _json_value(value):\n'
    '    if isinstance(value, dict):\n'
    '        return {str(key): _json_value(item) for key, item in value.items()}\n'
    '    if isinstance(value, (list, tuple)):\n'
    '        return [_json_value(item) for item in value]\n'
    '    if isinstance(value, np.ndarray):\n'
    '        return [_json_value(item) for item in value.tolist()]\n'
    '    if isinstance(value, np.generic):\n'
    '        return value.item()\n'
    '    if isinstance(value, Path):\n'
    '        return str(value)\n'
    '    return value\n'
    '\n'
    '\n'
    'def _report_payload(snapshot):\n'
    '    return {\n'
    "        'run': {\n"
    "            'run_id': snapshot.run_id,\n"
    "            'started_at': snapshot.started_at,\n"
    "            'elapsed_seconds': snapshot.elapsed_seconds,\n"
    '        },\n'
    "        'imported_paths': list(snapshot.imported_paths),\n"
    "        'config': snapshot.config_dict(),\n"
    "        'results': snapshot.results_dict(),\n"
    '    }\n'
    '\n'
    '\n'
    'def _metrics_rows(snapshot):\n'
    '    rows = []\n'
    '    for name, result in snapshot.results_dict().items():\n'
    "        item = result.get('detail', {})\n"
    '        row = {\n'
    "            'battery': item.get('battery', name),\n"
    "            'cycles': item.get('cycles'),\n"
    "            'model': item.get('model'),\n"
    "            'rmse': item.get('rmse'),\n"
    "            'mae': item.get('mae'),\n"
    "            'r2': item.get('r2'),\n"
    "            'pearson': item.get('pearson'),\n"
    "            're': item.get('re'),\n"
    "            'n_seeds': item.get('n_seeds', 1),\n"
    "            'failure_cycle': item.get('failure_cycle'),\n"
    "            'threshold': item.get('threshold'),\n"
    '        }\n'
    "        ci = item.get('ci', {})\n"
    "        for key in ('rmse', 'mae', 'r2', 'pearson', 're'):\n"
    '            if key in ci:\n'
    '                values = ci[key]\n'
    "                row[f'{key}_mean'] = values.get('mean')\n"
    "                row[f'{key}_std'] = values.get('std')\n"
    "                row[f'{key}_ci_lower'] = values.get('lower')\n"
    "                row[f'{key}_ci_upper'] = values.get('upper')\n"
    '        rows.append(row)\n'
    '    return rows\n'
    '\n'
    '\n'
    'def _temporary_path(target, token):\n'
    '    return target.with_name(\n'
    "        f'.{target.stem}.{token}.tmp{target.suffix}')\n"
    '\n'
    '\n'
    'def _cleanup(paths):\n'
    '    for path in paths:\n'
    '        try:\n'
    '            path.unlink(missing_ok=True)\n'
    '        except OSError:\n'
    '            pass\n'
    '\n'
    '\n'
    'def export_run_report(snapshot, canvas, *, base_directory=None,\n'
    '                      confirm_overwrite=None):\n'
    '    if not isinstance(snapshot, RunSnapshot):\n'
    "        raise TypeError('报告导出必须使用 RunSnapshot')\n"
    '    if not snapshot.results:\n'
    "        raise ReportExportError('运行快照中没有可导出的评估结果。')\n"
    '\n'
    '    base_directory = REPORT_DIR if base_directory is None else base_directory\n'
    '    run_directory = Path(base_directory) / snapshot.run_id\n'
    '    targets = {\n'
    "        'report_json': run_directory / 'report.json',\n"
    "        'metrics_excel': run_directory / '评估结果.xlsx',\n"
    "        'chart_image': run_directory / '评估结果.png',\n"
    '    }\n'
    '    existing = tuple(path for path in targets.values() if path.exists())\n'
    '    if existing:\n'
    '        if confirm_overwrite is None or not confirm_overwrite(existing):\n'
    "            raise ExportCancelled('已取消覆盖现有报告。')\n"
    '\n'
    '    temporary_paths = []\n'
    '    try:\n'
    '        run_directory.mkdir(parents=True, exist_ok=True)\n'
    '        token = uuid4().hex\n'
    '        temporary = {\n'
    '            key: _temporary_path(path, token)\n'
    '            for key, path in targets.items()\n'
    '        }\n'
    '        temporary_paths = list(temporary.values())\n'
    '\n'
    "        with temporary['report_json'].open('w', encoding='utf-8') as handle:\n"
    '            json.dump(\n'
    '                _json_value(_report_payload(snapshot)), handle,\n'
    '                ensure_ascii=False, indent=2)\n'
    '            handle.flush()\n'
    '            os.fsync(handle.fileno())\n'
    '\n'
    '        pd.DataFrame(_metrics_rows(snapshot)).to_excel(\n'
    "            temporary['metrics_excel'], index=False)\n"
    "        canvas.save_figure(str(temporary['chart_image']))\n"
    "        if not temporary['chart_image'].is_file():\n"
    "            raise OSError('图表临时文件未生成')\n"
    '\n'
    '        for key, target in targets.items():\n'
    '            os.replace(temporary[key], target)\n'
    '    except ExportCancelled:\n'
    '        raise\n'
    '    except Exception as error:\n'
    '        _cleanup(temporary_paths)\n'
    '        raise ReportExportError(friendly_export_error(error)) from error\n'
    '    finally:\n'
    '        _cleanup(temporary_paths)\n'
    '\n'
    '    return {\n'
    "        'run_directory': str(run_directory),\n"
    '        **{key: str(path) for key, path in targets.items()},\n'
    '    }\n'
    '\n'
    '\n'
    'def atomic_save_figure(canvas, target_path):\n'
    '    target = Path(target_path)\n'
    '    temporary = _temporary_path(target, uuid4().hex)\n'
    '    try:\n'
    '        target.parent.mkdir(parents=True, exist_ok=True)\n'
    '        canvas.save_figure(str(temporary))\n'
    '        if not temporary.is_file():\n'
    "            raise OSError('图表临时文件未生成')\n"
    '        os.replace(temporary, target)\n'
    '    except Exception as error:\n'
    '        _cleanup([temporary])\n'
    '        raise ReportExportError(friendly_export_error(error)) from error\n'
    '    finally:\n'
    '        _cleanup([temporary])\n'
    '    return str(target)\n'
)

# ---- models/rnn_model.py ----
_MODULE_SOURCES['models.rnn_model'] = (
    'import torch.nn as nn\n'
    'from utils.config import normalize_model_name\n'
    '\n'
    '\n'
    'class Net(nn.Module):\n'
    '    """单层 RNN / GRU / LSTM，末端线性层输出下一个容量。\n'
    '\n'
    '    ``input_size`` 是特征数：单变量容量序列为 1，多特征（capacity / dq_v /\n'
    '    CCCT / CVCT / resistance）时为 F。\n'
    '    """\n'
    '\n'
    "    CELLS = {'RNN': nn.RNN, 'GRU': nn.GRU, 'LSTM': nn.LSTM}\n"
    '\n'
    "    def __init__(self, hidden_dim=8, num_layers=1, mode='LSTM',\n"
    '                 input_size=1, dropout=0.0):\n'
    '        super(Net, self).__init__()\n'
    '        mode = normalize_model_name(mode)\n'
    '        if mode not in self.CELLS:\n'
    "            raise ValueError(f'{mode} 不是循环神经网络模型')\n"
    '        if isinstance(input_size, bool) or not isinstance(input_size, int) or input_size < 1:\n'
    "            raise ValueError('输入特征数必须是正整数')\n"
    '        self.hidden_dim = hidden_dim\n'
    '        self.input_size = input_size\n'
    '        self.num_layers = num_layers\n'
    '        self.mode = mode\n'
    '        # 直接建目标单元，不再「先建 LSTM 再替换」造成浪费\n'
    '        self.cell = self.CELLS[mode](\n'
    '            input_size=input_size,\n'
    '            hidden_size=hidden_dim,\n'
    '            num_layers=num_layers,\n'
    '            batch_first=True,\n'
    '            dropout=dropout if num_layers > 1 else 0.0,\n'
    '        )\n'
    '        self.drop = nn.Dropout(dropout)\n'
    '        self.linear = nn.Linear(hidden_dim, 1)\n'
    '\n'
    '    def forward(self, x):\n'
    '        out, _ = self.cell(x)\n'
    '        return self.linear(self.drop(out[:, -1, :]))\n'
)

# ---- models/XGBoost.py ----
_MODULE_SOURCES['models.XGBoost'] = (
    'import numpy as np\n'
    'import time\n'
    '\n'
    'from xgboost import XGBRegressor\n'
    'from core.cancellation import check_cancelled, xgboost_stop_callbacks\n'
    '\n'
    '\n'
    'def _flatten(features):\n'
    '    array = np.asarray(features)\n'
    '    if array.ndim == 3:\n'
    '        return array.reshape(len(array), -1)\n'
    '    return array\n'
    '\n'
    '\n'
    'def train_xgboost(train_x, train_y, val_x, val_y, n_estimators=100,\n'
    '                  learning_rate=0.1, max_depth=6, subsample=1.0,\n'
    '                  colsample_bytree=1.0, patience=20, seed=2,\n'
    "                  log_callback=None, name='', stop_flag=None,\n"
    '                  progress_callback=None):\n'
    '    """在**训练电池**的验证集上做 early stopping。\n'
    '\n'
    '    ``val_x`` / ``val_y`` 绝不能来自目标电池。改进方案 A2 修好后，这里的验证集\n'
    '    由 ``core.protocol`` 的内层留一电池交叉验证提供，因此它是一块**没见过的\n'
    '    电池**，和最终使用场景一致。\n'
    '    """\n'
    '    check_cancelled(stop_flag)\n'
    '    progress_started_at = time.monotonic()\n'
    '    train_x = _flatten(train_x)\n'
    '    val_x = _flatten(val_x)\n'
    '    train_y = np.asarray(train_y, dtype=np.float32).reshape(-1)\n'
    '    val_y = np.asarray(val_y, dtype=np.float32).reshape(-1)\n'
    '    options = dict(\n'
    '        n_estimators=n_estimators,\n'
    '        learning_rate=learning_rate,\n'
    '        max_depth=max_depth,\n'
    '        subsample=subsample,\n'
    '        colsample_bytree=colsample_bytree,\n'
    '        early_stopping_rounds=patience,\n'
    '        random_state=seed,\n'
    '        verbosity=0,\n'
    '    )\n'
    '    callbacks = xgboost_stop_callbacks(\n'
    '        stop_flag,\n'
    '        progress_callback,\n'
    '        battery=name,\n'
    '        seed=seed,\n'
    '        total=n_estimators,\n'
    '        started_at=progress_started_at,\n'
    '    )\n'
    '    if callbacks is not None:\n'
    "        options['callbacks'] = callbacks\n"
    '    model = XGBRegressor(**options)\n'
    '    if log_callback:\n'
    "        log_callback(f'[{name}] 训练中...')\n"
    '    model.fit(train_x, train_y, eval_set=[(val_x, val_y)], verbose=False)\n'
    '    check_cancelled(stop_flag)\n'
    '\n'
    '    best_iteration = model.get_booster().best_iteration\n'
    '    actual_trees = best_iteration if best_iteration is not None else n_estimators\n'
    '\n'
    '    if log_callback:\n'
    "        log_callback(f'[{name}] 训练完成，树数={n_estimators}（验证选择{actual_trees}）')\n"
    '\n'
    '    return model\n'
)

# ---- models/RF.py ----
_MODULE_SOURCES['models.RF'] = (
    '"""随机森林训练。\n'
    '\n'
    '改进方案 A7：旧实现用「分批加树 + 验证 RMSE 早停」来选树数，但这在统计上\n'
    '没有意义——随机森林的方差随树数增加而单调下降，不会过拟合；而且旧代码里\n'
    '``batch_size = max(1, min(10, n_estimators // 10))`` 只有 10 个批次，``patience=20``\n'
    '的早停永远不会触发（计数器最大只能到 9），选出来的其实是噪声，之后还要**从头\n'
    '重训**一遍。\n'
    '\n'
    '现在：固定树数、一次训练。用于选超参的验证集交给 ``core.protocol`` 的\n'
    '内层留一电池交叉验证。\n'
    '"""\n'
    '\n'
    'import numpy as np\n'
    'from sklearn.ensemble import RandomForestRegressor\n'
    '\n'
    'from core.cancellation import check_cancelled\n'
    'from core.progress import make_progress_event\n'
    '\n'
    '\n'
    'def train_rf(train_x, train_y, val_x=None, val_y=None, *, n_estimators=100,\n'
    '             max_depth=6, min_samples_leaf=1, max_features=1.0, seed=2,\n'
    "             n_jobs=1, log_callback=None, name='', stop_flag=None,\n"
    '             progress_callback=None, patience=None, **_ignored):\n'
    '    """训练一个随机森林。\n'
    '\n'
    '    ``val_x`` / ``val_y`` / ``patience`` 保留在签名里以兼容旧调用方，但不再用于\n'
    '    早停（随机森林不需要早停）。``train_x`` 可以是 ``(N, W)`` 或 ``(N, W, F)``。\n'
    '\n'
    '    ``n_jobs`` 默认 1：递归预测每步只喂一个窗口，而 joblib 的并行调度开销远大于\n'
    '    单棵树的预测成本（实测 1 行 predict：``n_jobs=-1`` 27 ms vs ``n_jobs=1`` 2.6 ms）。\n'
    '    """\n'
    '    check_cancelled(stop_flag)\n'
    '    train_x = np.asarray(train_x)\n'
    '    if train_x.ndim == 3:\n'
    '        train_x = train_x.reshape(len(train_x), -1)\n'
    '    train_y = np.asarray(train_y, dtype=np.float32).reshape(-1)\n'
    '    if len(train_x) == 0:\n'
    "        raise ValueError('随机森林训练集不能为空')\n"
    '\n'
    '    if progress_callback:\n'
    '        progress_callback(make_progress_event(\n'
    "            'rf_trees', started_at=0.0, battery=name, seed=seed,\n"
    '            epoch=None, current=1, total=1))\n'
    '\n'
    '    model = RandomForestRegressor(\n'
    '        n_estimators=int(n_estimators),\n'
    '        max_depth=int(max_depth),\n'
    '        min_samples_leaf=int(min_samples_leaf),\n'
    '        max_features=max_features,\n'
    '        random_state=seed,\n'
    '        n_jobs=n_jobs,\n'
    '    )\n'
    '    if log_callback:\n'
    "        log_callback(f'[{name}] 随机森林训练中（树数={int(n_estimators)}）...')\n"
    '    model.fit(train_x, train_y)\n'
    '    check_cancelled(stop_flag)\n'
    '\n'
    '    if log_callback:\n'
    "        log_callback(f'[{name}] 随机森林训练完成，树数={int(n_estimators)}')\n"
    '    return model\n'
)

# ---- core/model_factory.py ----
_MODULE_SOURCES['core.model_factory'] = (
    '"""模型构造与训练的**唯一入口**（评估与部署共用）。\n'
    '\n'
    '改进方案 A2 的核心：旧流程里评估走 ``prepare_leave_one_out_split``（每块训练\n'
    '电池只用前 80% 训练），部署走 ``_prepare_final_training_data``（全量重训），\n'
    '于是「报告的评估指标评估的并不是最终部署的那个模型」。\n'
    '\n'
    '这里把两者的拟合逻辑收敛到一处：\n'
    '\n'
    '- :func:`make_fit_fn` 返回 ``fit_fn(X, y, hp) -> model``，供\n'
    '  :func:`core.protocol.select_hparams` / :func:`core.protocol.fit_final` 使用；\n'
    '- :func:`hparam_grid` 给出可搜索的超参网格；\n'
    '- :func:`make_step_fn` 把已拟合模型包装成「一个窗口 → 下一个容量」的递归预测器。\n'
    '\n'
    '输入约定：``X`` 形状为 ``(N, W, F)``（单特征时 ``(N, W)`` 亦可）。树模型内部\n'
    '展平成 ``(N, W*F)``，循环模型直接使用 ``(N, W, F)``。\n'
    '"""\n'
    '\n'
    'import numpy as np\n'
    '# 显式再导出：``fit_rf`` 在调用时通过 globals() 取这个名字，\n'
    '# 测试与调用方也以 ``core.model_factory.RandomForestRegressor`` 为替换点。\n'
    'from sklearn.ensemble import RandomForestRegressor as RandomForestRegressor\n'
    '\n'
    'from core.batching import make_tensor_loader, train_recurrent_epoch\n'
    'from core.cancellation import check_cancelled\n'
    '\n'
    "RECURRENT_MODES = ('RNN', 'GRU', 'LSTM')\n"
    "TREE_MODES = ('XGBoost', 'RF')\n"
    '\n'
    '\n'
    'def as_3d(features):\n'
    '    """把 ``(N, W)`` 或 ``(N, W, F)`` 统一成 ``(N, W, F)`` float32。"""\n'
    '    array = np.asarray(features, dtype=np.float32)\n'
    '    if array.ndim == 2:\n'
    '        return array.reshape(array.shape[0], array.shape[1], 1)\n'
    '    if array.ndim != 3:\n'
    "        raise ValueError('特征必须是二维窗口或三维多特征窗口')\n"
    '    return array\n'
    '\n'
    '\n'
    'def n_features(features):\n'
    '    """特征数 F；单特征窗口返回 1。"""\n'
    '    array = np.asarray(features)\n'
    '    if array.ndim == 2:\n'
    '        return 1\n'
    '    if array.ndim == 3:\n'
    '        return int(array.shape[2])\n'
    "    raise ValueError('特征必须是二维窗口或三维多特征窗口')\n"
    '\n'
    '\n'
    'def flatten(features):\n'
    '    """树模型用：``(N, W, F)`` -> ``(N, W*F)``。"""\n'
    '    array = as_3d(features)\n'
    '    return array.reshape(len(array), -1)\n'
    '\n'
    '\n'
    'def hparam_grid(config, mode=None):\n'
    '    """可搜索的超参网格（内层留一电池交叉验证的候选集）。\n'
    '\n'
    '    树模型搜「树数 / 深度」，循环模型搜「训练轮数」。网格保持很小：内层 CV 的\n'
    '    计算量是 ``训练电池数 × 网格大小``。\n'
    '    """\n'
    '    mode = mode or config.mode\n'
    "    if mode == 'RF':\n"
    "        depths = sorted({int(getattr(config, 'max_depth', 6)), 8})\n"
    "        return [{'n_estimators': int(getattr(config, 'n_estimators', 100)),\n"
    "                 'max_depth': depth} for depth in depths]\n"
    "    if mode == 'XGBoost':\n"
    "        depths = sorted({int(getattr(config, 'max_depth', 6)), 4})\n"
    "        return [{'n_estimators': int(getattr(config, 'n_estimators', 100)),\n"
    "                 'max_depth': depth} for depth in depths]\n"
    '    if mode in RECURRENT_MODES:\n'
    "        epochs = int(getattr(config, 'epochs', 100))\n"
    '        # 循环模型较贵：先用「固定轮数」的少量候选做快速模式\n'
    '        candidates = sorted({max(1, epochs // 2), max(1, epochs)})\n'
    "        return [{'epochs': value} for value in candidates]\n"
    "    raise ValueError(f'不支持的模型类型: {mode}')\n"
    '\n'
    '\n'
    'def scale_training_input(x, y, rated, feature_scaler=None):\n'
    '    """按与推理**完全一致**的规则归一化训练输入。\n'
    '\n'
    '    单特征：``x / rated``、``y / rated``；\n'
    '    多特征：容量通道 ``/ rated``，其余通道用 ``FeatureScaler``（z-score）。\n'
    '    推理端由 :func:`core.prediction.scale_model_input` 做同一件事，两边必须同步，\n'
    '    否则模型在训练时看到的量纲和预测时不同（多特征路径曾经就是这样）。\n'
    '    """\n'
    '    features = as_3d(x)\n'
    '    targets = np.asarray(y, dtype=np.float32).reshape(-1)\n'
    '    scaled = np.array(features, dtype=np.float32, copy=True)\n'
    '    scaled[:, :, 0] = features[:, :, 0] / rated\n'
    '    if features.shape[2] > 1 and feature_scaler is not None:\n'
    '        scaled = feature_scaler.transform(scaled)\n'
    '    return scaled, targets / rated\n'
    '\n'
    '\n'
    "def make_fit_fn(config, *, stop_flag=None, log_callback=None, name='',\n"
    '                net_class=None, progress_callback=None, feature_scaler=None):\n'
    '    """返回 ``fit_fn(X, y, hp) -> model``；X、y 是**原始** Ah / 原始特征。\n'
    '\n'
    '    内部会用 :func:`scale_training_input` 归一化，因此调用方传原始窗口即可，\n'
    '    不必自己先除额定容量。\n'
    '\n'
    "    对循环模型，``hp['epochs']`` 就是「内层 CV 选出的最佳轮数」——最终重训时\n"
    '    固定该轮数，不再做早停（早停的验证集来自训练电池的寿命末段，正是 A2 的\n'
    '    病根）。\n'
    '\n'
    '    ``net_class`` 允许注入 ``Net``（便于测试与打包环境定位），默认取\n'
    '    ``models.rnn_model.Net``。\n'
    '    """\n'
    '    mode = config.mode\n'
    "    seed = int(getattr(config, 'seed', 2))\n"
    "    device = getattr(config, 'device', 'cpu')\n"
    "    rated = float(getattr(config, 'rated_capacity', 1.0))\n"
    '\n'
    '    def _scale(x, y):\n'
    '        return scale_training_input(x, y, rated, feature_scaler)\n'
    '\n'
    "    if mode == 'RF':\n"
    '        def fit_rf(x, y, hp):\n'
    '            # 在**调用时**取 RandomForestRegressor（而不是在 make_fit_fn 里），\n'
    '            # 这样测试与调用方 patch ``core.model_factory.RandomForestRegressor``\n'
    '            # 才能生效。\n'
    "            model_class = globals()['RandomForestRegressor']\n"
    '            scaled_x, scaled_y = _scale(x, y)\n'
    '            model = model_class(\n'
    "                n_estimators=int(hp.get('n_estimators', 100)),\n"
    "                max_depth=int(hp.get('max_depth', 6)),\n"
    "                min_samples_leaf=int(getattr(config, 'min_samples_leaf', 1)),\n"
    "                max_features=getattr(config, 'max_features', 1.0),\n"
    '                random_state=seed,\n'
    '                # n_jobs=1：递归预测每步只喂一个窗口，而 joblib 的并行调度开销\n'
    '                # 远大于单棵树的预测成本（实测 1 行 predict：27 ms vs 2.6 ms）。\n'
    '                n_jobs=1,\n'
    '            )\n'
    '            model.fit(flatten(scaled_x), scaled_y)\n'
    '            return model\n'
    '\n'
    '        return fit_rf\n'
    '\n'
    "    if mode == 'XGBoost':\n"
    '        from xgboost import XGBRegressor\n'
    '\n'
    '        def fit_xgb(x, y, hp):\n'
    '            scaled_x, scaled_y = _scale(x, y)\n'
    '            model = XGBRegressor(\n'
    "                n_estimators=int(hp.get('n_estimators', 100)),\n"
    "                learning_rate=float(getattr(config, 'learning_rate', 0.1)),\n"
    "                max_depth=int(hp.get('max_depth', 6)),\n"
    "                subsample=float(getattr(config, 'subsample', 1.0)),\n"
    "                colsample_bytree=float(getattr(config, 'colsample_bytree', 1.0)),\n"
    '                random_state=seed,\n'
    '                verbosity=0,\n'
    '            )\n'
    '            model.fit(flatten(scaled_x), scaled_y)\n'
    '            return model\n'
    '\n'
    '        return fit_xgb\n'
    '\n'
    '    if mode in RECURRENT_MODES:\n'
    '        import time\n'
    '\n'
    '        import torch\n'
    '        import torch.nn as nn\n'
    '\n'
    '        from core.prediction import resolve_inference_device\n'
    '        from core.progress import make_progress_event\n'
    '        from utils.config import setup_seed\n'
    '\n'
    '        if net_class is None:\n'
    '            from models.rnn_model import Net as net_class  # noqa: N813\n'
    '\n'
    '        def fit_rnn(x, y, hp):\n'
    '            resolved = resolve_inference_device(device)\n'
    '            setup_seed(seed)\n'
    '            scaled_x, scaled_y = _scale(x, y)\n'
    '            features = scaled_x.shape[2]\n'
    "            hidden_dim = int(getattr(config, 'hidden_dim', 64))\n"
    '            # 只在多特征时才传 input_size，保持旧调用签名可用\n'
    '            if features == 1:\n'
    '                model = net_class(hidden_dim=hidden_dim, num_layers=1, mode=mode)\n'
    '            else:\n'
    '                model = net_class(\n'
    '                    hidden_dim=hidden_dim, num_layers=1, mode=mode,\n'
    '                    input_size=features)\n'
    '            model = model.to(resolved)\n'
    '            criterion = nn.MSELoss()\n'
    '            optimizer = torch.optim.AdamW(\n'
    '                model.parameters(),\n'
    "                lr=float(getattr(config, 'rnn_lr', 0.001)),\n"
    '                weight_decay=1e-4,\n'
    '            )\n'
    '            scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(\n'
    '                optimizer, factor=0.5,\n'
    "                patience=max(3, int(getattr(config, 'patience', 20)) // 3))\n"
    '            loader = make_tensor_loader(\n'
    '                scaled_x, scaled_y.reshape(-1, 1),\n'
    '                shuffle=True,          # 训练窗口互相独立，必须打乱\n'
    '                seed=seed,\n'
    '            )\n'
    "            epochs = max(1, int(hp.get('epochs', 1)))\n"
    '            started_at = time.monotonic()\n'
    '            for epoch in range(epochs):\n'
    '                check_cancelled(stop_flag)\n'
    '                loss = train_recurrent_epoch(\n'
    '                    model, loader, optimizer, criterion, resolved,\n'
    '                    stop_flag=stop_flag)\n'
    '                scheduler.step(loss)\n'
    '                if progress_callback:\n'
    '                    progress_callback(make_progress_event(\n'
    "                        'rnn_epoch', started_at=started_at, battery=name,\n"
    '                        seed=seed, epoch=epoch + 1, current=epoch + 1,\n'
    '                        total=epochs))\n'
    '                if log_callback and (epoch + 1) % 10 == 0:\n'
    '                    log_callback(\n'
    "                        f'[{name}] 内层定型 第{epoch + 1}/{epochs}轮 '\n"
    "                        f'损失={loss:.4f}')\n"
    '            model.eval()\n'
    '            return model\n'
    '\n'
    '        return fit_rnn\n'
    '\n'
    "    raise ValueError(f'不支持的模型类型: {mode}')\n"
    '\n'
    '\n'
    "def make_step_fn(model, metadata, device='cpu'):\n"
    '    """把已拟合模型包装成递归预测器：``(1, W) 或 (1, W, F) -> (1,)`` 容量。\n'
    '\n'
    '    对多特征模型，递归时**只有容量通道是自回归的**；其余特征按「持久性」保持\n'
    '    为窗口内最后一个观测值（未来工况未知时的保守假设，已在结果里标注）。\n'
    '    """\n'
    '    from core.prediction import predict_capacity_batch\n'
    '\n'
    '    def step(windows):\n'
    '        return predict_capacity_batch(model, metadata, windows, device=device)\n'
    '\n'
    '    return step\n'
    '\n'
    '\n'
    'def state_dict_of(model):\n'
    '    """循环模型的 CPU state_dict（用于最终模型保存）。"""\n'
    '    return {\n'
    '        key: value.detach().cpu().clone()\n'
    '        for key, value in model.state_dict().items()\n'
    '    }\n'
)

# ---- core/train.py ----
_MODULE_SOURCES['core.train'] = (
    '"""留一电池评估：统一的「选超参 → 重训 → 滚动起点评估」协议。\n'
    '\n'
    '改进方案 A2 / A3 / A4 的落地：\n'
    '\n'
    '- **A2**：评估用的模型与部署用的模型走同一个 ``fit_final``——用**全部训练电池的\n'
    '  全部窗口**训练。旧流程把每块训练电池切成「前 80% 训练 + 后 20% 验证」，\n'
    '  而寿命末段（膝点）恰好落在后 20%，模型从没见过寿命末段却被要求预测失效点。\n'
    '- **A3**：持久性混合系数 α 用**多步滚动误差**标定，且只用「没见过该验证电池」的\n'
    '  内层折模型，避免一步误差标定、递归多步使用造成的坍缩。\n'
    '- **A4**：头条指标改为**滚动预测起点**（40%–70%）上的递归预测误差，一步指标\n'
    '  降级为诊断信息；同时并排给出「平推 / 线性外推 / 双指数」三条基线。\n'
    '"""\n'
    '\n'
    'import numpy as np\n'
    'import time\n'
    '\n'
    'from core.preprocess import (\n'
    '    CapacityScaler,\n'
    '    FeatureScaler,\n'
    '    build_instances,\n'
    '    build_instances_mf,\n'
    '    feature_fill_values,\n'
    '    generate_one_step_predictions,\n'
    '    generate_recursive_predictions,\n'
    ')\n'
    'from core.prediction import predict_capacity_batch\n'
    'from core.evaluate import calc_all_metrics, confidence_interval\n'
    'from core.cancellation import check_cancelled\n'
    'from core.progress import make_progress_event\n'
    'from core.model_factory import (\n'
    '    hparam_grid,\n'
    '    make_fit_fn,\n'
    '    make_step_fn,\n'
    ')\n'
    'from core.protocol import model_step_for\n'
    'from core import protocol as protocol_module\n'
    'from core.protocol import (\n'
    '    DEFAULT_STARTS,\n'
    '    choose_blend_by_rollout,\n'
    '    fit_final,\n'
    '    inner_fold_models,\n'
    '    baseline_rmse_by_start,\n'
    '    rolling_origin_eval,\n'
    '    select_hparams,\n'
    '    skill_vs_persistence,\n'
    '    summarize_rolling_rows,\n'
    ')\n'
    'from core.baselines import BASELINES\n'
    '#: 模块级 ``Net``：保持既有测试/扩展点可用（可被 mock 替换）\n'
    'from models.rnn_model import Net  # noqa: F401\n'
    '\n'
    '\n'
    '#: 头条指标使用的预测起点（寿命的 50%）\n'
    'PRIMARY_START = 0.5\n'
    '\n'
    '\n'
    'def _feature_columns(config):\n'
    "    columns = getattr(config, 'feature_columns', None)\n"
    '    if columns is None:\n'
    "        return ('capacity',)\n"
    '    return tuple(columns)\n'
    '\n'
    '\n'
    'def _uses_multifeature(config):\n'
    '    return len(_feature_columns(config)) > 1\n'
    '\n'
    '\n'
    'def _frames_for(config, battery_dict, name):\n'
    '    """取某块电池的输入帧（单特征时为容量序列）。"""\n'
    '    entry = battery_dict[name]\n'
    '    columns = _feature_columns(config)\n'
    "    if not _uses_multifeature(config) or not hasattr(entry, 'columns'):\n"
    '        return protocol_module.capacity_of(battery_dict, name)\n'
    '    available = [c for c in columns if c in entry.columns]\n'
    "    if 'capacity' not in available:\n"
    "        available = ['capacity'] + available\n"
    '    return entry.loc[:, available]\n'
    '\n'
    '\n'
    'def _build_windows(config, values, window):\n'
    '    """把帧 / 序列切成 (X, y)。"""\n'
    '    columns = _feature_columns(config)\n'
    "    if _uses_multifeature(config) and getattr(values, 'columns', None) is not None:\n"
    '        return build_instances_mf(values, window, cols=list(columns))\n'
    '    return build_instances(np.asarray(values, dtype=np.float32).reshape(-1), window)\n'
    '\n'
    '\n'
    'def evaluate_prediction_protocols(sequence, window_size, predict_batch,\n'
    '                                  rated_capacity, threshold_ratio):\n'
    '    """评估「用真实历史的一步预测」与「从初始窗口起的完全递归预测」。\n'
    '\n'
    '    这两个协议**分开报告**：一步预测每一步都用真实历史，误差不累积，天然接近\n'
    '    「平推」的好成绩，区分不出模型好坏；递归预测才是真实使用场景。\n'
    '\n'
    '    头条指标请看 :func:`rolling_origin_eval` 的滚动起点结果。\n'
    '    """\n'
    '    one_truth, one_prediction = generate_one_step_predictions(\n'
    '        sequence, window_size, predict_batch)\n'
    '    recursive_truth, recursive_prediction = generate_recursive_predictions(\n'
    '        sequence, window_size, predict_batch)\n'
    '    one_metrics = calc_all_metrics(\n'
    '        one_truth, one_prediction, rated_capacity, threshold_ratio)\n'
    '    recursive_metrics = calc_all_metrics(\n'
    '        recursive_truth, recursive_prediction, rated_capacity, threshold_ratio)\n'
    '    return {\n'
    "        'one_step': {\n"
    "            'truth': one_truth,\n"
    "            'prediction': one_prediction,\n"
    "            'metrics': one_metrics,\n"
    '        },\n'
    "        'recursive': {\n"
    "            'truth': recursive_truth,\n"
    "            'prediction': recursive_prediction,\n"
    "            'metrics': recursive_metrics,\n"
    '        },\n'
    "        'rul_re': recursive_metrics['re'],\n"
    '    }\n'
    '\n'
    '\n'
    'def _baseline_one_step_metrics(one_step, target_frames, window, multifeature,\n'
    '                               rated_capacity, threshold_ratio):\n'
    '    """「平推」基线的一步预测指标（供结果表并排展示，A3/A9）。\n'
    '\n'
    "    平推的一步预测就是窗口末值，因此与 ``one_step['truth']`` 逐位对齐。\n"
    '    """\n'
    "    truth = np.asarray(one_step.get('truth', []), dtype=np.float64).reshape(-1)\n"
    '    if len(truth) == 0:\n'
    '        return {}\n'
    '    frames = np.asarray(target_frames, dtype=np.float64)\n'
    '    if multifeature:\n'
    '        frames = frames[:, 0]\n'
    '    windows = frames[:-1] if len(frames) == len(truth) + 1 else frames[:len(truth)]\n'
    '    persistence = windows if len(windows) == len(truth) else np.full(\n'
    '        len(truth), frames[0] if len(frames) else 0.0)\n'
    '    try:\n'
    '        return calc_all_metrics(\n'
    '            truth, persistence, rated_capacity, threshold_ratio)\n'
    '    except ValueError:\n'
    '        return {}\n'
    '\n'
    '\n'
    'def _capacity_only_step(step_fn):\n'
    '    """把「逐步」基线包装成只吃容量通道的 step_fn。\n'
    '\n'
    '    基线（平推 / 线性外推）只关心容量序列，但多特征帧的窗口是 ``(1, W, F)``；\n'
    '    这里统一截出容量列，让基线在多特征配置下也能评估。\n'
    '    """\n'
    '    def wrapped(windows):\n'
    '        array = np.asarray(windows)\n'
    '        if array.ndim == 3:\n'
    '            array = array[:, :, 0]\n'
    '        return step_fn(array)\n'
    '\n'
    '    return wrapped\n'
    '\n'
    '\n'
    'def _baseline_table(config, frames, window, threshold, rated_capacity,\n'
    "                    starts=DEFAULT_STARTS, name='', debounce=1):\n"
    '    """在同一组滚动起点上评估三条经验基线（平推 / 线性外推 / 双指数）。"""\n'
    '    table = {}\n'
    '    for baseline_name, spec in BASELINES.items():\n'
    '        try:\n'
    "            if spec['kind'] == 'step':\n"
    '                rows = rolling_origin_eval(\n'
    "                    frames, window, _capacity_only_step(spec['fn']), threshold,\n"
    '                    starts, battery=name, debounce=debounce)\n'
    '            else:\n'
    '                rows = _direct_baseline_rows(\n'
    "                    spec['fn'], frames, window, threshold, starts, name,\n"
    '                    debounce)\n'
    '        except (ValueError, FloatingPointError):\n'
    '            continue\n'
    '        if rows:\n'
    '            table[baseline_name] = {\n'
    "                'kind': spec['kind'],\n"
    "                'rows': rows,\n"
    "                'rmse': float(np.mean([row['rmse'] for row in rows])),\n"
    "                'mean_abs_rul_err': _mean_rul_error(rows),\n"
    "                'detected': len([row for row in rows if row['status'] == 'ok']),\n"
    '            }\n'
    '    return table\n'
    '\n'
    '\n'
    'def _direct_baseline_rows(direct_fn, frames, window, threshold, starts, name,\n'
    '                          debounce=1):\n'
    '    """直接多步基线：在起点拟合一次，整段外推（不逐步重拟合）。"""\n'
    '    array = np.asarray(frames, dtype=np.float64)\n'
    '    if array.ndim == 1:\n'
    '        array = array.reshape(-1, 1)\n'
    '    rows = []\n'
    '    for frac in starts:\n'
    '        start = int(len(array) * frac)\n'
    '        if start < window or start >= len(array) - 1:\n'
    '            continue\n'
    '        truth = array[start:, 0]\n'
    '        prediction = np.asarray(\n'
    '            direct_fn(array[start - window:start, 0], len(truth)),\n'
    '            dtype=np.float64).reshape(-1)\n'
    '        rows.append(_score_row(\n'
    '            frac, start, name, truth, prediction, threshold, debounce))\n'
    '    return rows\n'
    '\n'
    '\n'
    'def _score_row(frac, start, name, truth, prediction, threshold, debounce=1):\n'
    '    """把一段真实 / 预测序列打分（与 ``rolling_origin_eval`` 同一口径）。"""\n'
    '    true_eol = protocol_module.first_cross(truth, threshold, debounce)\n'
    '    pred_eol = protocol_module.first_cross(prediction, threshold, debounce)\n'
    '    row = {\n'
    "        'start_frac': float(frac),\n"
    "        'start': int(start),\n"
    "        'battery': name,\n"
    "        'rmse': float(np.sqrt(np.mean((prediction - truth) ** 2))),\n"
    "        'mae': float(np.mean(np.abs(prediction - truth))),\n"
    "        'true_rul': true_eol,\n"
    "        'pred_rul': pred_eol,\n"
    "        'rul_err': None,\n"
    "        'rul_rel_err': None,\n"
    "        'within_20pct': None,\n"
    '    }\n'
    '    if true_eol is None:\n'
    "        row['status'] = 'true_censored'\n"
    '    elif pred_eol is None:\n'
    "        row['status'] = 'pred_censored'\n"
    '    else:\n'
    "        row['status'] = 'ok'\n"
    "        row['rul_err'] = int(pred_eol - true_eol)\n"
    "        row['rul_rel_err'] = abs(pred_eol - true_eol) / max(true_eol, 1)\n"
    "        row['within_20pct'] = bool(\n"
    '            abs(pred_eol - true_eol) <= 0.2 * max(true_eol, 1))\n'
    '    return row\n'
    '\n'
    '\n'
    'def _mean_rul_error(rows):\n'
    "    detected = [abs(row['rul_err']) for row in rows if row['status'] == 'ok']\n"
    '    return float(np.mean(detected)) if detected else None\n'
    '\n'
    '\n'
    'def _train_one_battery(config, battery_dict, name, stop_flag=None,\n'
    '                       log_callback=None, seed=None, progress_callback=None):\n'
    '    """训练单个电池（留一法），返回 ``(pred_list, metrics_dict, detail_dict)``。\n'
    '\n'
    '    评估与部署共用 :func:`core.protocol.fit_final`：用全部训练电池的全部窗口\n'
    '    定型，因此模型**见过寿命末段**，也才可能预测出失效。\n'
    '    """\n'
    '    check_cancelled(stop_flag)\n'
    '    window = int(config.window_size)\n'
    '    mode = config.mode\n'
    "    device = getattr(config, 'device', 'cpu')\n"
    '    rated_capacity = float(config.rated_capacity)\n'
    '    threshold_ratio = float(config.threshold_ratio)\n'
    '    threshold = rated_capacity * threshold_ratio\n'
    '    columns = _feature_columns(config)\n'
    '    multifeature = _uses_multifeature(config)\n'
    '\n'
    '    if seed is not None:\n'
    '        from utils.config import setup_seed\n'
    '        setup_seed(seed)\n'
    "    fit_seed = int(seed if seed is not None else getattr(config, 'seed', 2))\n"
    '\n'
    '    train_names = [\n'
    '        item for item in battery_dict\n'
    "        if item != name and len(battery_dict[item].get('capacity', ())) > window + 1\n"
    '    ]\n'
    '    if not train_names:\n'
    '        if log_callback:\n'
    "            log_callback(f'跳过 {name}，原因：没有可用的训练电池')\n"
    '        return None, None, None\n'
    '\n'
    '    target_frames = _frames_for(config, battery_dict, name)\n'
    '    if len(target_frames) <= window + 1:\n'
    '        if log_callback:\n'
    "            log_callback(f'跳过 {name}，原因：循环数不足（需>{window}）')\n"
    '        return None, None, None\n'
    '\n'
    '    # ── scaler 只用训练电池拟合（目标电池不得参与） ──\n'
    '    # 必须在构造 fit_fn 之前算好：多特征时 fit_fn 与 step_fn 共用同一个\n'
    '    # FeatureScaler，否则训练与推理的量纲会不一致。\n'
    '    scaler, feature_scaler, fill_values = _fit_scalers(\n'
    '        config, battery_dict, train_names, window, columns, multifeature,\n'
    '        rated_capacity)\n'
    '\n'
    '    # ── 内层留一电池交叉验证：选超参（验证对象是一块没见过的电池） ──\n'
    '    fit_config = _config_with_seed(config, fit_seed)\n'
    '    fit_fn = make_fit_fn(\n'
    '        fit_config, stop_flag=stop_flag, log_callback=log_callback, name=name,\n'
    '        net_class=Net, progress_callback=progress_callback,\n'
    '        feature_scaler=feature_scaler)\n'
    '    grid = hparam_grid(config, mode)\n'
    "    use_cv = bool(getattr(config, 'inner_cv', True)) and len(train_names) >= 2\n"
    '    if use_cv:\n'
    '        hp, cv_score, fold_models = select_hparams(\n'
    '            battery_dict, train_names, window, fit_fn, grid, rated_capacity,\n'
    '            start_frac=PRIMARY_START, stop_flag=stop_flag,\n'
    '            columns=columns if multifeature else None, return_folds=True,\n'
    '            device=device, feature_scaler=feature_scaler)\n'
    '        if log_callback:\n'
    '            score_text = (\n'
    "                'N/A' if cv_score is None or not np.isfinite(cv_score)\n"
    "                else f'{cv_score:.4f} Ah')\n"
    '            log_callback(\n'
    "                f'[{name}] 内层留一电池交叉验证（{len(train_names)} 折）：'\n"
    "                f'选定超参 {hp}，滚动 RMSE@50%={score_text}')\n"
    '    else:\n'
    '        hp = grid[0]\n'
    "        cv_score = float('nan')\n"
    '        # None（而不是空 dict）=「尚未计算」，让 _calibrate_blend 自己去建内层折\n'
    '        fold_models = None\n'
    '        if log_callback:\n'
    "            log_callback(f'[{name}] 快速模式：跳过内层交叉验证，使用 {hp}')\n"
    '\n'
    '    check_cancelled(stop_flag)\n'
    '\n'
    '    # ── 定型：用全部训练电池的全部窗口重训（评估与部署共用同一函数） ──\n'
    '    model = fit_final(\n'
    '        battery_dict, train_names, window, fit_fn, hp, rated_capacity,\n'
    '        columns=columns if multifeature else None)\n'
    '    check_cancelled(stop_flag)\n'
    '\n'
    '    metadata = _model_metadata(\n'
    '        config, window, rated_capacity, scaler, feature_scaler, columns,\n'
    '        multifeature, hp)\n'
    '    step_fn = make_step_fn(model, metadata, device=device)\n'
    '\n'
    '    # ── A3：α 用多步滚动误差标定，且只用「没见过验证电池」的内层折模型 ──\n'
    '    blend, blend_rmse = _calibrate_blend(\n'
    '        config, battery_dict, train_names, window, fit_fn, hp, rated_capacity,\n'
    '        columns, multifeature, scaler=scaler, feature_scaler=feature_scaler,\n'
    '        fold_models=fold_models, stop_flag=stop_flag, log_callback=log_callback,\n'
    '        name=name)\n'
    "    metadata['persistence_blend'] = blend\n"
    '\n'
    '    # ── A4：头条指标 = 滚动起点上的递归预测（A12：失效判定可去抖） ──\n'
    "    starts = tuple(getattr(config, 'rolling_starts', DEFAULT_STARTS))\n"
    "    debounce = int(getattr(config, 'eol_debounce', 1) or 1)\n"
    '    rows = rolling_origin_eval(\n'
    '        target_frames, window, step_fn, threshold, starts, battery=name,\n'
    '        debounce=debounce)\n'
    '    baseline_table = _baseline_table(\n'
    '        config, target_frames, window, threshold, rated_capacity, starts, name,\n'
    '        debounce)\n'
    "    persistence = baseline_table.get('平推基线', {})\n"
    '    baseline_by_start = (\n'
    "        baseline_rmse_by_start(persistence['rows'])\n"
    "        if persistence.get('rows') else {})\n"
    '    rolling_summary = summarize_rolling_rows(rows, baseline_by_start)\n'
    '    skill = skill_vs_persistence(rows, baseline_by_start)\n'
    '\n'
    '    # ── 诊断信息：一步预测与从初始窗口起的完全递归预测 ──\n'
    '    protocols = evaluate_prediction_protocols(\n'
    '        np.asarray(target_frames)[:, 0] if multifeature else target_frames,\n'
    '        window,\n'
    '        lambda windows: predict_capacity_batch(\n'
    '            model, metadata, windows, device=device),\n'
    '        rated_capacity, threshold_ratio)\n'
    "    one_step = protocols['one_step']\n"
    "    recursive = protocols['recursive']\n"
    '\n'
    '    primary = _primary_row(rows, PRIMARY_START) or (rows[0] if rows else None)\n'
    '    metrics = _metrics_from_row(primary)\n'
    "    metrics['r2'] = one_step['metrics'].get('r2')\n"
    "    metrics['pearson'] = one_step['metrics'].get('pearson')\n"
    "    metrics['re'] = protocols['rul_re']\n"
    "    metrics['re_status'] = recursive['metrics'].get('re_status')\n"
    '\n'
    '    forecast = _forecast_for_plot(step_fn, target_frames, window, primary)\n'
    '    baseline_metrics = _baseline_one_step_metrics(\n'
    '        one_step, target_frames, window, multifeature, rated_capacity,\n'
    '        threshold_ratio)\n'
    '\n'
    '    train_data = list(np.asarray(target_frames)[:window, 0]) if multifeature \\\n'
    '        else list(np.asarray(target_frames)[:window])\n'
    "    pred_list = train_data + list(one_step['prediction'])\n"
    '\n'
    '    detail = {\n'
    "        'battery': name,\n"
    "        'cycles': int(len(target_frames)),\n"
    "        'model': mode,\n"
    "        'training_batteries': tuple(train_names),\n"
    "        'protocol': 'strict_zero_shot',\n"
    "        'rul_protocol': 'rolling_origin',\n"
    "        'selected_hparams': dict(hp),\n"
    "        'inner_cv_rmse': (None if not np.isfinite(cv_score) else float(cv_score)),\n"
    "        'scaler': scaler.to_dict(),\n"
    "        'feature_columns': list(columns),\n"
    "        'feature_scaler': (\n"
    '            feature_scaler.to_dict() if feature_scaler is not None else None),\n'
    "        'one_step_prediction': one_step['prediction'].tolist(),\n"
    "        'recursive_prediction': recursive['prediction'].tolist(),\n"
    "        'one_step_metrics': one_step['metrics'],\n"
    "        'recursive_metrics': recursive['metrics'],\n"
    "        'persistence_blend': float(blend),\n"
    "        'persistence_blend_rmse': (\n"
    '            None if blend_rmse is None or not np.isfinite(blend_rmse)\n'
    '            else float(blend_rmse)),\n'
    "        'persistence_baseline_metrics': baseline_metrics,\n"
    "        'rmse_skill_vs_persistence': skill,\n"
    "        'rolling': rolling_summary,\n"
    "        'rolling_rows': rows,\n"
    "        'baselines': {\n"
    "            key: {k: v for k, v in value.items() if k != 'rows'}\n"
    '            for key, value in baseline_table.items()\n'
    '        },\n'
    "        'baseline_rows': {\n"
    "            key: value['rows'] for key, value in baseline_table.items()\n"
    '        },\n'
    "        'primary_start_frac': PRIMARY_START,\n"
    "        'forecast_start': (primary['start'] if primary else None),\n"
    "        'forecast': forecast,\n"
    "        'threshold': float(threshold),\n"
    '    }\n'
    '    return pred_list, metrics, detail\n'
    '\n'
    '\n'
    'def _config_with_seed(config, seed):\n'
    '    """返回一个 seed 被覆盖的配置副本（不改动调用方对象）。"""\n'
    '    try:\n'
    '        from dataclasses import replace\n'
    '        return replace(config, seed=seed)\n'
    '    except (TypeError, ValueError):\n'
    '        return config\n'
    '\n'
    '\n'
    'def _primary_row(rows, start_frac):\n'
    '    for row in rows:\n'
    "        if abs(row['start_frac'] - start_frac) < 1e-9:\n"
    '            return row\n'
    '    return None\n'
    '\n'
    '\n'
    'def _metrics_from_row(row):\n'
    '    """把滚动起点的一行转成指标字典。"""\n'
    '    if row is None:\n'
    "        return {'rmse': None, 'mae': None, 'r2': None, 'pearson': None,\n"
    "                're': None, 're_status': 'unavailable'}\n"
    '    return {\n'
    "        'rmse': float(row['rmse']),\n"
    "        'mae': float(row['mae']),\n"
    "        'r2': None,\n"
    "        'pearson': None,\n"
    "        're': (\n"
    "            abs(row['rul_err']) / max(row['true_rul'], 1)\n"
    "            if row['status'] == 'ok' and row['true_rul'] else None),\n"
    "        're_status': {\n"
    "            'ok': 'observed',\n"
    "            'true_censored': 'observed_censored',\n"
    "            'pred_censored': 'prediction_censored',\n"
    "        }.get(row['status'], 'unavailable'),\n"
    '    }\n'
    '\n'
    '\n'
    'def _fit_scalers(config, battery_dict, train_names, window, columns,\n'
    '                 multifeature, rated_capacity):\n'
    '    """scaler 只用训练电池拟合（目标电池不得参与）。"""\n'
    '    import pandas as pd\n'
    '\n'
    '    capacity_parts = []\n'
    '    frames = []\n'
    '    for item in train_names:\n'
    '        entry = battery_dict[item]\n'
    "        if multifeature and hasattr(entry, 'columns'):\n"
    '            frame = entry\n'
    '            available = [c for c in columns if c in frame.columns]\n'
    "            if 'capacity' not in available:\n"
    "                available = ['capacity'] + available\n"
    '            frames.append(frame.loc[:, available])\n'
    "        capacity = np.asarray(entry['capacity'], dtype=np.float32).reshape(-1)\n"
    '        capacity_parts.append(capacity)\n'
    '\n'
    '    scaler = CapacityScaler(\n'
    '        method=config.norm_method,\n'
    '        rated_capacity=rated_capacity,\n'
    '    ).fit(np.concatenate(capacity_parts) if capacity_parts else np.array([1.0]))\n'
    '\n'
    '    feature_scaler = None\n'
    '    fill_values = None\n'
    '    if multifeature and frames:\n'
    '        combined = pd.concat(frames, ignore_index=True)\n'
    '        fill_values = feature_fill_values(combined, list(columns))\n'
    '        filled = combined.ffill().fillna(fill_values).fillna(0.0)\n'
    '        feature_scaler = FeatureScaler().fit(filled.to_numpy(dtype=np.float32))\n'
    '    return scaler, feature_scaler, fill_values\n'
    '\n'
    '\n'
    'def _model_metadata(config, window, rated_capacity, scaler, feature_scaler,\n'
    '                    columns, multifeature, hp):\n'
    '    """构造用于**评估内部**递归预测的元数据（与最终模型保存的 schema 一致）。"""\n'
    '    schema = {\n'
    "        'features': list(columns),\n"
    "        'feature': 'capacity' if not multifeature else 'multifeature',\n"
    "        'dtype': 'float32',\n"
    "        'shape': (['batch', 'window_size', 'features'] if multifeature\n"
    "                  else ['batch', 'window_size']),\n"
    "        'feature_scaler': (\n"
    '            feature_scaler.to_dict() if feature_scaler is not None else None),\n'
    "        'selected_hparams': dict(hp),\n"
    "        'multifeature_recursive_policy': (\n"
    "            '非容量通道在递归预测时保持窗口末值（未来工况未知）'\n"
    '            if multifeature else None),\n'
    '    }\n'
    '    metadata = {\n'
    "        'mode': config.mode,\n"
    "        'window_size': int(window),\n"
    "        'rated_capacity': float(rated_capacity),\n"
    "        'threshold_ratio': float(config.threshold_ratio),\n"
    "        'scaler': scaler.to_dict(),\n"
    "        'feature_schema': schema,\n"
    "        'persistence_blend': 1.0,\n"
    '    }\n'
    "    if config.mode in ('RNN', 'GRU', 'LSTM'):\n"
    "        metadata['hidden_dim'] = int(getattr(config, 'hidden_dim', 64))\n"
    "        metadata['input_size'] = int(len(columns))\n"
    '    return metadata\n'
    '\n'
    '\n'
    'def _calibrate_blend(config, battery_dict, train_names, window, fit_fn, hp,\n'
    '                     rated_capacity, columns, multifeature, scaler=None,\n'
    '                     feature_scaler=None, fold_models=None, stop_flag=None,\n'
    "                     log_callback=None, name=''):\n"
    '    """A3：用多步滚动误差 + 内层折模型标定持久性混合系数 α。\n'
    '\n'
    '    ``fold_models`` 由 :func:`core.protocol.select_hparams` 的\n'
    '    ``return_folds=True`` 提供（每个折模型没见过对应留出电池），因此 α 不会被\n'
    '    「模型见过验证电池」这件事偏向 1。\n'
    '    """\n'
    '    if fold_models is None:\n'
    '        try:\n'
    '            fold_models = inner_fold_models(\n'
    '                battery_dict, train_names, window, fit_fn, hp, rated_capacity,\n'
    '                columns=columns if multifeature else None)\n'
    '        except (ValueError, KeyError):\n'
    '            fold_models = {}\n'
    '\n'
    '    if not fold_models:\n'
    '        if log_callback:\n'
    "            log_callback(f'[{name}] 无法建立内层折模型，α 取 1.0（不做收缩）')\n"
    '        return 1.0, None\n'
    '\n'
    '    if scaler is None:\n'
    '        scaler = _fit_scalers(\n'
    '            config, battery_dict, train_names, window, columns, multifeature,\n'
    '            rated_capacity)[0]\n'
    "    device = getattr(config, 'device', 'cpu')\n"
    '\n'
    '    # 每个验证电池用自己的内层折模型（该模型没见过它）。\n'
    '    # 折模型是用「原始量纲 + 内部归一化」训练的，所以 step 必须走同一套\n'
    '    # 映射（model_step_for），与 select_hparams 内部保持一致。\n'
    '    blend_by_name = {}\n'
    '    for val_name, fold_model in fold_models.items():\n'
    '        step_raw = model_step_for(\n'
    '            fold_model, rated_capacity, device=device,\n'
    '            feature_scaler=feature_scaler)\n'
    '        alpha, _ = choose_blend_by_rollout(\n'
    '            step_raw, battery_dict, [val_name], window,\n'
    '            starts=(0.5, 0.6), columns=columns if multifeature else None)\n'
    '        blend_by_name[val_name] = alpha\n'
    '\n'
    '    blend = float(np.mean(list(blend_by_name.values()))) if blend_by_name else 1.0\n'
    '    if log_callback:\n'
    "        detail = '，'.join(\n"
    "            f'{key}={value:.2f}' for key, value in blend_by_name.items())\n"
    '        log_callback(\n'
    "            f'[{name}] 防过拟合校准系数 α={blend:.3f}'\n"
    "            f'（多步滚动标定；{detail}；0=平推，1=原模型）')\n"
    '        if blend < 0.05:\n'
    '            log_callback(\n'
    "                f'[{name}] ⚠ 模型未超越持久性基线（α≈0）：'\n"
    "                '递归预测退化为平推，请以滚动起点指标为准。')\n"
    '    return blend, None\n'
    '\n'
    '\n'
    'def _forecast_for_plot(step_fn, frames, window, primary):\n'
    '    """为图表准备递归预测序列（从主预测起点起，直到观测末端）。"""\n'
    '    if primary is None:\n'
    '        return []\n'
    "    start = primary['start']\n"
    '    steps = len(frames) - start\n'
    '    if steps <= 0:\n'
    '        return []\n'
    '    window_values = frames[start - window:start]\n'
    '    try:\n'
    '        forecast = protocol_module.recursive_forecast(\n'
    '            step_fn, window_values, steps)\n'
    '    except (ValueError, FloatingPointError):\n'
    '        return []\n'
    '    return forecast.tolist()\n'
    '\n'
    '\n'
    'def train(config, battery_dict, battery_list, stop_flag=None, log_callback=None,\n'
    '          progress_callback=None):\n'
    '    """留一电池评估主循环；主结果是所有有效种子的**均值**（不挑最好种子）。"""\n'
    '    feature_size = config.window_size\n'
    '    mode = config.mode\n'
    '    base_seed = config.seed\n'
    "    n_seeds = max(1, getattr(config, 'n_seeds', 1))\n"
    '\n'
    '    results = {}\n'
    '    progress_started_at = time.monotonic()\n'
    '    seeds = [base_seed + i for i in range(n_seeds)]\n'
    '\n'
    '    if n_seeds > 1 and log_callback:\n'
    '        log_callback(\n'
    "            f'多种子评估：共 {n_seeds} 个种子 {seeds}，'\n"
    "            f'计算 95% 置信区间（仅同一留一折内的种子波动）')\n"
    '\n'
    '    for i in range(len(battery_list)):\n'
    '        check_cancelled(stop_flag)\n'
    '        name = battery_list[i]\n'
    '        if name not in battery_dict:\n'
    '            continue\n'
    "        capacity = battery_dict[name].get('capacity', ())\n"
    '        if len(capacity) <= feature_size + 2:\n'
    '            if log_callback:\n'
    "                log_callback(f'跳过 {name}：循环数不足（需>{feature_size}）')\n"
    '            continue\n'
    '\n'
    '        if progress_callback:\n'
    '            progress_callback(make_progress_event(\n'
    "                'battery', started_at=progress_started_at, battery=name,\n"
    '                current=i + 1, total=len(battery_list)))\n'
    '\n'
    '        all_metrics = []\n'
    '        all_predictions = []\n'
    '        run_details = []\n'
    '\n'
    '        for s_idx, sd in enumerate(seeds):\n'
    '            check_cancelled(stop_flag)\n'
    '            if progress_callback:\n'
    '                progress_callback(make_progress_event(\n'
    "                    'seed', started_at=progress_started_at, battery=name,\n"
    '                    seed=sd, current=s_idx + 1, total=len(seeds)))\n'
    '            if n_seeds > 1 and log_callback:\n'
    "                log_callback(f'[{name}] 种子 {s_idx + 1}/{n_seeds} (seed={sd})')\n"
    '\n'
    '            pred_list, metrics, run_detail = _train_one_battery(\n'
    '                config, battery_dict, name, stop_flag=stop_flag,\n'
    '                log_callback=log_callback, seed=sd,\n'
    '                progress_callback=progress_callback)\n'
    '            if metrics is None:\n'
    '                continue\n'
    '            all_metrics.append(metrics)\n'
    '            all_predictions.append(np.asarray(pred_list, dtype=np.float64))\n'
    '            run_details.append(run_detail or {})\n'
    '\n'
    '        if not all_metrics or not all_predictions:\n'
    '            continue\n'
    '\n'
    '        ci_info = {}\n'
    "        for key in ('rmse', 'mae', 'r2', 'pearson', 're'):\n"
    '            values = [\n'
    '                float(item[key]) for item in all_metrics\n'
    '                if item.get(key) is not None and np.isfinite(item[key])\n'
    '            ]\n'
    '            if not values:\n'
    '                continue\n'
    '            mean, lo, hi, std = confidence_interval(values, confidence=0.95)\n'
    '            ci_info[key] = {\n'
    "                'mean': mean, 'lower': lo, 'upper': hi, 'std': std,\n"
    "                'values': values,\n"
    '            }\n'
    '\n'
    "        mean_metrics = {key: ci_info[key]['mean'] for key in ci_info}\n"
    '        mean_prediction = np.mean(np.vstack(all_predictions), axis=0)\n'
    '        detail = _aggregate_detail(\n'
    '            name, mode, battery_dict, ci_info, mean_metrics, run_details)\n'
    '\n'
    "        selected_metric = getattr(config, 'metric', 'rmse')\n"
    '        selected_score = mean_metrics.get(\n'
    "            selected_metric, mean_metrics.get('rmse'))\n"
    '        results[name] = {\n'
    "            'score': (float(selected_score)\n"
    '                      if selected_score is not None else None),\n'
    "            'prediction': mean_prediction.tolist(),\n"
    "            'detail': detail,\n"
    '        }\n'
    '\n'
    "        if n_seeds > 1 and log_callback and 'rmse' in ci_info:\n"
    '            log_callback(\n'
    "                f'[{name}] 多种子汇总：'\n"
    '                f\'RMSE={ci_info["rmse"]["mean"]:.4f}±{ci_info["rmse"]["std"]:.4f} \'\n'
    '                f\'95%CI=[{ci_info["rmse"]["lower"]:.4f}, \'\n'
    '                f\'{ci_info["rmse"]["upper"]:.4f}]\')\n'
    '    return results\n'
    '\n'
    '\n'
    'def _aggregate_detail(name, mode, battery_dict, ci_info, mean_metrics,\n'
    '                      run_details):\n'
    '    """把每个种子的 detail 汇总成电池级 detail。"""\n'
    '    def mean_protocol_metrics(field):\n'
    '        protocol_metrics = [item[field] for item in run_details if field in item]\n'
    '        if not protocol_metrics:\n'
    '            return {}\n'
    '        result = {}\n'
    "        for key in ('rmse', 'mae', 'r2', 'pearson', 're'):\n"
    '            values = [\n'
    '                float(item[key]) for item in protocol_metrics\n'
    '                if item.get(key) is not None and np.isfinite(item[key])\n'
    '            ]\n'
    '            if values:\n'
    '                result[key] = float(np.mean(values))\n'
    "        statuses = [item.get('re_status') for item in protocol_metrics\n"
    "                    if item.get('re_status')]\n"
    '        if statuses:\n'
    "            result['re_status'] = (\n"
    "                statuses[0] if len(set(statuses)) == 1 else 'mixed')\n"
    '        return result\n'
    '\n'
    '    def mean_protocol_prediction(field):\n'
    '        values = [item[field] for item in run_details if field in item]\n'
    '        if not values:\n'
    '            return []\n'
    '        return np.mean(\n'
    '            np.vstack([np.asarray(value, dtype=np.float64)\n'
    '                       for value in values]), axis=0).tolist()\n'
    '\n'
    '    def mean_scalar(field):\n'
    '        values = [\n'
    '            float(item[field]) for item in run_details\n'
    '            if item.get(field) is not None\n'
    '            and np.isfinite(item[field])\n'
    '        ]\n'
    '        return float(np.mean(values)) if values else None\n'
    '\n'
    '    def mean_dict_of_floats(field):\n'
    '        collected = {}\n'
    '        for item in run_details:\n'
    '            for key, value in (item.get(field) or {}).items():\n'
    '                if isinstance(value, (int, float)) and np.isfinite(value):\n'
    '                    collected.setdefault(key, []).append(float(value))\n'
    '        return {key: float(np.mean(values)) for key, values in collected.items()}\n'
    '\n'
    '    # 滚动起点汇总：把各种子的行按起点取均值\n'
    '    rows_by_start = {}\n'
    '    for item in run_details:\n'
    "        for row in item.get('rolling_rows', []) or []:\n"
    "            rows_by_start.setdefault(row['start_frac'], []).append(row)\n"
    '\n'
    '    aggregated_rows = []\n'
    '    for frac, rows in sorted(rows_by_start.items()):\n'
    '        merged = {\n'
    "            'start_frac': frac,\n"
    "            'start': rows[0]['start'],\n"
    "            'battery': name,\n"
    "            'rmse': float(np.mean([r['rmse'] for r in rows])),\n"
    "            'mae': float(np.mean([r['mae'] for r in rows])),\n"
    "            'true_rul': rows[0]['true_rul'],\n"
    "            'pred_rul': (\n"
    "                float(np.mean([r['pred_rul'] for r in rows\n"
    "                               if r['pred_rul'] is not None]))\n"
    "                if any(r['pred_rul'] is not None for r in rows) else None),\n"
    "            'status': rows[0]['status'],\n"
    "            'rul_err': (\n"
    "                float(np.mean([r['rul_err'] for r in rows\n"
    "                               if r['rul_err'] is not None]))\n"
    "                if any(r['rul_err'] is not None for r in rows) else None),\n"
    '        }\n'
    '        aggregated_rows.append(merged)\n'
    '\n'
    '    baseline_by_start = {}\n'
    '    for item in run_details:\n'
    "        for key, value in (item.get('baselines') or {}).items():\n"
    "            baseline_by_start.setdefault(key, []).append(value.get('rmse'))\n"
    '\n'
    '    baselines = {}\n'
    '    for key, values in baseline_by_start.items():\n'
    '        finite = [v for v in values if v is not None and np.isfinite(v)]\n'
    '        if finite:\n'
    "            baselines[key] = {'rmse': float(np.mean(finite))}\n"
    '\n'
    '    blends = [\n'
    "        float(item['persistence_blend']) for item in run_details\n"
    "        if item.get('persistence_blend') is not None\n"
    '    ]\n'
    '    first = run_details[0] if run_details else {}\n'
    '\n'
    '    detail = {\n'
    "        'battery': name,\n"
    "        'cycles': int(len(battery_dict[name]['capacity'])),\n"
    "        'model': mode,\n"
    "        'rmse': mean_metrics.get('rmse'),\n"
    "        'mae': mean_metrics.get('mae'),\n"
    "        'r2': mean_metrics.get('r2'),\n"
    "        'pearson': mean_metrics.get('pearson'),\n"
    "        're': mean_metrics.get('re'),\n"
    "        're_status': mean_protocol_metrics('recursive_metrics').get(\n"
    "            're_status', 'unavailable'),\n"
    "        'n_seeds': len(run_details),\n"
    "        'ci': ci_info,\n"
    "        'ci_statistical_object': '同一留一折内的随机种子波动',\n"
    "        'seed_policy': 'all_seed_mean',\n"
    "        'protocol': 'strict_zero_shot',\n"
    "        'rul_protocol': 'rolling_origin',\n"
    "        'one_step_prediction': mean_protocol_prediction('one_step_prediction'),\n"
    "        'recursive_prediction': mean_protocol_prediction('recursive_prediction'),\n"
    "        'one_step_metrics': mean_protocol_metrics('one_step_metrics'),\n"
    "        'recursive_metrics': mean_protocol_metrics('recursive_metrics'),\n"
    "        'persistence_blend': float(np.mean(blends)) if blends else 1.0,\n"
    "        'rmse_skill_vs_persistence': mean_scalar('rmse_skill_vs_persistence'),\n"
    "        'inner_cv_rmse': mean_scalar('inner_cv_rmse'),\n"
    "        'selected_hparams': first.get('selected_hparams', {}),\n"
    "        'feature_columns': first.get('feature_columns', ['capacity']),\n"
    "        'rolling_rows': aggregated_rows,\n"
    "        'rolling': summarize_rolling_rows(aggregated_rows),\n"
    "        'baselines': baselines,\n"
    "        'primary_start_frac': first.get('primary_start_frac', PRIMARY_START),\n"
    "        'forecast_start': first.get('forecast_start'),\n"
    "        'forecast': mean_protocol_prediction('forecast'),\n"
    "        'threshold': first.get('threshold'),\n"
    "        'training_batteries': first.get('training_batteries', ()),\n"
    "        'run_details': run_details,\n"
    '    }\n'
    '    # 平推基线的一步指标（供结果表并排展示）\n'
    "    baseline_metrics = first.get('persistence_baseline_metrics')\n"
    '    if isinstance(baseline_metrics, dict):\n'
    "        detail['persistence_baseline_metrics'] = baseline_metrics\n"
    '    return detail\n'
)

# ---- core/model_persistence.py ----
_MODULE_SOURCES['core.model_persistence'] = (
    'import os\n'
    'import json\n'
    'import hashlib\n'
    'import platform\n'
    'from datetime import datetime, timezone\n'
    'from pathlib import Path\n'
    '\n'
    'import numpy as np\n'
    'import torch\n'
    'from models.rnn_model import Net\n'
    'from core.preprocess import (\n'
    '    build_instances,\n'
    '    build_instances_mf,\n'
    '    CapacityScaler,\n'
    '    FeatureScaler,\n'
    ')\n'
    'from core.model_factory import (\n'
    '    hparam_grid,\n'
    '    make_fit_fn,\n'
    ')\n'
    'from core.protocol import (\n'
    '    choose_blend_by_rollout,\n'
    '    fit_final,\n'
    '    model_step_for,\n'
    '    select_hparams,\n'
    ')\n'
    'from core.cancellation import check_cancelled\n'
    'from utils.config import normalize_model_name\n'
    '\n'
    '\n'
    'MODEL_FORMAT_VERSION = 2\n'
    'MAX_MODEL_FILE_BYTES = 512 * 1024 * 1024\n'
    'MAX_METADATA_FILE_BYTES = 1024 * 1024\n'
    "RECURRENT_MODES = ('RNN', 'GRU', 'LSTM')\n"
    "TREE_MODES = ('XGBoost', 'RF')\n"
    '\n'
    '\n'
    'def _sha256_file(filepath):\n'
    '    digest = hashlib.sha256()\n'
    "    with open(filepath, 'rb') as stream:\n"
    "        for chunk in iter(lambda: stream.read(1024 * 1024), b''):\n"
    '            digest.update(chunk)\n'
    '    return digest.hexdigest()\n'
    '\n'
    '\n'
    'def _infer_input_size(state_dict):\n'
    '    """从权重形状推断输入特征数（兼容没有 ``input_size`` 字段的旧模型）。\n'
    '\n'
    '    循环单元的 ``weight_ih_l0`` 形状是 ``(gate_count * hidden, input_size)``。\n'
    '    """\n'
    "    for key in ('cell.weight_ih_l0', 'cell.weight_ih_l0_reverse'):\n"
    '        tensor = state_dict.get(key)\n'
    "        if tensor is not None and getattr(tensor, 'dim', lambda: 0)() == 2:\n"
    '            return int(tensor.shape[1])\n'
    '    return 1\n'
    '\n'
    '\n'
    'def _library_versions():\n'
    '    versions = {\n'
    "        'python': platform.python_version(),\n"
    "        'numpy': np.__version__,\n"
    "        'torch': torch.__version__,\n"
    '    }\n'
    '    try:\n'
    '        import sklearn\n'
    "        versions['scikit_learn'] = sklearn.__version__\n"
    '    except ImportError:\n'
    '        pass\n'
    '    try:\n'
    '        import xgboost\n'
    "        versions['xgboost'] = xgboost.__version__\n"
    '    except ImportError:\n'
    '        pass\n'
    '    return versions\n'
    '\n'
    '\n'
    'def _complete_metadata(metadata):\n'
    '    if not isinstance(metadata, dict):\n'
    "        raise ValueError('模型元数据必须是对象')\n"
    '    completed = dict(metadata)\n'
    "    mode = normalize_model_name(completed.get('mode', ''))\n"
    "    model_type = normalize_model_name(completed.get('model_type', mode))\n"
    '    if model_type != mode:\n'
    "        raise ValueError('模型类型与运行模式不匹配')\n"
    '\n'
    "    completed['format_version'] = MODEL_FORMAT_VERSION\n"
    "    completed['mode'] = mode\n"
    "    completed['model_type'] = model_type\n"
    "    completed.setdefault('threshold_ratio', 0.8)\n"
    "    completed.setdefault('feature_schema', {\n"
    "        'feature': 'capacity',\n"
    "        'dtype': 'float32',\n"
    "        'shape': ['batch', 'window_size'],\n"
    '    })\n'
    "    completed.setdefault('training_params', {})\n"
    "    completed.setdefault('library_versions', _library_versions())\n"
    "    completed.setdefault('data_hash', hashlib.sha256(b'').hexdigest())\n"
    '    completed.setdefault(\n'
    "        'created_at', datetime.now(timezone.utc).isoformat())\n"
    '    return completed\n'
    '\n'
    '\n'
    'def _validate_metadata(metadata, extension, require_file_hash=True):\n'
    '    if not isinstance(metadata, dict):\n'
    "        raise ValueError('模型元数据必须是 JSON 对象')\n"
    '    required = {\n'
    "        'format_version', 'mode', 'model_type', 'window_size',\n"
    "        'rated_capacity', 'threshold_ratio', 'scaler', 'feature_schema',\n"
    "        'training_params', 'library_versions', 'data_hash', 'created_at',\n"
    '    }\n'
    '    if require_file_hash:\n'
    "        required.add('file_sha256')\n"
    '    missing = sorted(required.difference(metadata))\n'
    '    if missing:\n'
    '        raise ValueError(f\'模型元数据缺少字段：{", ".join(missing)}\')\n'
    "    if metadata['format_version'] != MODEL_FORMAT_VERSION:\n"
    '        raise ValueError(\n'
    '            f\'不支持的模型格式版本：{metadata["format_version"]}\')\n'
    '\n'
    "    mode = normalize_model_name(metadata['mode'])\n"
    "    model_type = normalize_model_name(metadata['model_type'])\n"
    '    if mode != model_type:\n'
    "        raise ValueError('模型类型与运行模式不匹配')\n"
    "    if extension in ('.pt', '.pth') and mode not in RECURRENT_MODES:\n"
    "        raise ValueError('模型类型与文件扩展名不匹配')\n"
    "    if extension == '.joblib' and mode not in TREE_MODES:\n"
    "        raise ValueError('模型类型与文件扩展名不匹配')\n"
    '\n'
    "    window_size = metadata['window_size']\n"
    '    if isinstance(window_size, bool) or not isinstance(window_size, int) or window_size <= 0:\n'
    "        raise ValueError('模型元数据中的窗口大小无效')\n"
    "    rated_capacity = metadata['rated_capacity']\n"
    '    if (isinstance(rated_capacity, bool) or\n'
    '            not isinstance(rated_capacity, (int, float)) or\n'
    '            not np.isfinite(rated_capacity) or rated_capacity <= 0):\n'
    "        raise ValueError('模型元数据中的额定容量无效')\n"
    "    threshold = metadata['threshold_ratio']\n"
    '    if (isinstance(threshold, bool) or\n'
    '            not isinstance(threshold, (int, float)) or\n'
    '            not np.isfinite(threshold) or not 0 < threshold <= 1):\n'
    "        raise ValueError('模型元数据中的失效阈值无效')\n"
    "    if not isinstance(metadata['feature_schema'], dict):\n"
    "        raise ValueError('模型特征结构元数据无效')\n"
    "    if not isinstance(metadata['training_params'], dict):\n"
    "        raise ValueError('模型训练参数元数据无效')\n"
    "    if not isinstance(metadata['library_versions'], dict):\n"
    "        raise ValueError('模型依赖版本元数据无效')\n"
    '    try:\n'
    "        CapacityScaler.from_dict(metadata['scaler'])\n"
    '    except (KeyError, TypeError, ValueError) as exc:\n'
    "        raise ValueError(f'模型归一化元数据无效：{exc}') from exc\n"
    '    if mode in RECURRENT_MODES:\n'
    "        hidden_dim = metadata.get('hidden_dim')\n"
    '        if (isinstance(hidden_dim, bool) or\n'
    '                not isinstance(hidden_dim, int) or hidden_dim <= 0):\n'
    "            raise ValueError('循环模型隐藏层大小元数据无效')\n"
    '\n'
    "    hashes = [metadata['data_hash']]\n"
    '    if require_file_hash:\n'
    "        hashes.append(metadata['file_sha256'])\n"
    '    if any(not isinstance(value, str) or len(value) != 64 or\n'
    "           any(char not in '0123456789abcdef' for char in value)\n"
    '           for value in hashes):\n'
    "        raise ValueError('模型哈希元数据无效')\n"
    "    if not isinstance(metadata['created_at'], str) or not metadata['created_at']:\n"
    "        raise ValueError('模型创建时间元数据无效')\n"
    '    return mode\n'
    '\n'
    '\n'
    'def _write_metadata_sidecar(filepath, metadata):\n'
    "    sidecar = filepath + '.meta.json'\n"
    "    with open(sidecar, 'w', encoding='utf-8') as stream:\n"
    '        json.dump(metadata, stream, ensure_ascii=False, indent=2)\n'
    '\n'
    '\n'
    'def _read_validated_metadata(filepath, extension):\n'
    '    if not os.path.isfile(filepath):\n'
    "        raise ValueError('模型文件不存在')\n"
    '    size = os.path.getsize(filepath)\n'
    '    if size <= 0:\n'
    "        raise ValueError('模型文件为空')\n"
    '    if size > MAX_MODEL_FILE_BYTES:\n'
    "        raise ValueError('模型文件过大，已拒绝加载')\n"
    '\n'
    "    sidecar = filepath + '.meta.json'\n"
    '    if not os.path.isfile(sidecar):\n'
    "        raise ValueError('缺少模型元数据文件，旧格式需先安全迁移')\n"
    '    metadata_size = os.path.getsize(sidecar)\n'
    '    if metadata_size <= 0 or metadata_size > MAX_METADATA_FILE_BYTES:\n'
    "        raise ValueError('模型元数据文件大小无效')\n"
    '    try:\n'
    "        with open(sidecar, 'r', encoding='utf-8') as stream:\n"
    '            metadata = json.load(stream)\n'
    '    except (OSError, UnicodeError, json.JSONDecodeError) as exc:\n'
    "        raise ValueError(f'模型元数据无法解析：{exc}') from exc\n"
    '\n'
    '    _validate_metadata(metadata, extension)\n'
    '    actual_hash = _sha256_file(filepath)\n'
    "    if actual_hash != metadata['file_sha256']:\n"
    "        raise ValueError('模型文件哈希校验失败，文件可能已损坏或被篡改')\n"
    '    return metadata\n'
    '\n'
    '\n'
    'def save_model(model, metadata, filepath):\n'
    '    """保存模型；权重与经过校验的元数据分离存放。"""\n'
    '    filepath = os.fspath(filepath)\n'
    '    extension = Path(filepath).suffix.lower()\n'
    '    completed = _complete_metadata(metadata)\n'
    '    mode = _validate_metadata(\n'
    '        completed, extension, require_file_hash=False)\n'
    '    if mode in RECURRENT_MODES:\n'
    "        if extension not in ('.pt', '.pth'):\n"
    "            raise ValueError('循环模型必须保存为 .pt 或 .pth 文件')\n"
    '        state_dict = model.state_dict()\n'
    '        if not state_dict or not all(\n'
    '                isinstance(key, str) and torch.is_tensor(value)\n'
    '                for key, value in state_dict.items()):\n'
    "            raise ValueError('PyTorch 模型权重无效')\n"
    '        torch.save(state_dict, filepath)\n'
    '    elif mode in TREE_MODES:\n'
    "        if extension != '.joblib':\n"
    "            raise ValueError('树模型必须保存为 .joblib 文件')\n"
    '        import joblib\n'
    '        joblib.dump(model, filepath)\n'
    '    else:\n'
    "        raise ValueError(f'不支持的模型类型：{mode}')\n"
    '\n'
    "    completed['file_sha256'] = _sha256_file(filepath)\n"
    '    _write_metadata_sidecar(filepath, completed)\n'
    '\n'
    '\n'
    'def load_model(filepath, allow_unsafe_joblib=False):\n'
    '    """加载模型；joblib 仅能在用户明确知情同意后启用。"""\n'
    '    filepath = os.fspath(filepath)\n'
    '    ext = os.path.splitext(filepath)[1].lower()\n'
    "    if ext in ('.pt', '.pth'):\n"
    '        metadata = _read_validated_metadata(filepath, ext)\n'
    '        try:\n'
    '            state_dict = torch.load(\n'
    "                filepath, map_location='cpu', weights_only=True)\n"
    '        except Exception as exc:\n'
    "            raise ValueError(f'模型权重文件无法安全读取：{exc}') from exc\n"
    '        if not isinstance(state_dict, dict) or not state_dict or not all(\n'
    '                isinstance(key, str) and torch.is_tensor(value)\n'
    '                for key, value in state_dict.items()):\n'
    "            raise ValueError('模型权重必须是仅包含张量的 state_dict')\n"
    "        mode = metadata['mode']\n"
    '        # 多特征模型需要重建正确的 input_size；旧模型（无该字段）回退为 1\n'
    "        input_size = metadata.get('input_size')\n"
    '        if isinstance(input_size, bool) or not isinstance(input_size, int) \\\n'
    '                or input_size < 1:\n'
    '            input_size = _infer_input_size(state_dict)\n'
    '        if input_size == 1:\n'
    "            model = Net(hidden_dim=metadata['hidden_dim'], num_layers=1, mode=mode)\n"
    '        else:\n'
    "            model = Net(hidden_dim=metadata['hidden_dim'], num_layers=1,\n"
    '                        mode=mode, input_size=input_size)\n'
    '        try:\n'
    '            model.load_state_dict(state_dict, strict=True)\n'
    '        except (KeyError, RuntimeError, TypeError) as exc:\n'
    "            raise ValueError(f'模型权重键与元数据不匹配：{exc}') from exc\n"
    '        model.eval()\n'
    '        return model, metadata\n'
    "    elif ext == '.pkl':\n"
    "        raise ValueError('禁止加载 .pkl 模型；请使用受控格式重新导出')\n"
    "    elif ext == '.joblib':\n"
    '        if not allow_unsafe_joblib:\n'
    '            raise PermissionError(\n'
    "                'joblib 反序列化可能执行代码，必须经用户明确确认后加载')\n"
    '        metadata = _read_validated_metadata(filepath, ext)\n'
    '        import joblib\n'
    '        try:\n'
    '            model = joblib.load(filepath)\n'
    '        except Exception as exc:\n'
    "            raise ValueError(f'joblib 模型加载失败：{exc}') from exc\n"
    '        expected_name = {\n'
    "            'RF': 'RandomForestRegressor',\n"
    "            'XGBoost': 'XGBRegressor',\n"
    "        }[metadata['mode']]\n"
    '        if type(model).__name__ != expected_name:\n'
    "            raise ValueError('反序列化后的模型类型与元数据不匹配')\n"
    '        return model, metadata\n'
    '    else:\n'
    '        raise ValueError(\n'
    "            f'不支持的模型文件格式：{ext}，请选择 .pt/.pth 或 .joblib 文件')\n"
    '\n'
    '\n'
    'def _config_snapshot(config):\n'
    "    if hasattr(config, 'to_dict'):\n"
    '        return config.to_dict()\n'
    '    names = (\n'
    "        'mode', 'window_size', 'hidden_dim', 'epochs', 'rated_capacity',\n"
    "        'threshold_ratio', 'norm_method', 'device', 'seed', 'patience',\n"
    "        'n_estimators', 'learning_rate', 'max_depth', 'subsample',\n"
    "        'colsample_bytree', 'min_samples_leaf', 'max_features',\n"
    '    )\n'
    '    return {name: getattr(config, name) for name in names if hasattr(config, name)}\n'
    '\n'
    '\n'
    'def _battery_capacity_hash(values):\n'
    '    capacity = np.ascontiguousarray(values, dtype=np.float64)\n'
    '    return hashlib.sha256(capacity.tobytes()).hexdigest()\n'
    '\n'
    '\n'
    'def _final_training_metadata(config, scaler, valid_names, battery_dict,\n'
    '                             sample_count, selected_parameters,\n'
    '                             feature_scaler=None, columns=None):\n'
    '    battery_hashes = {\n'
    "        name: _battery_capacity_hash(battery_dict[name]['capacity'])\n"
    '        for name in valid_names\n'
    '    }\n'
    '    data_digest = hashlib.sha256()\n'
    '    for name in sorted(battery_hashes):\n'
    "        data_digest.update(name.encode('utf-8'))\n"
    "        data_digest.update(battery_hashes[name].encode('ascii'))\n"
    '    training_params = _config_snapshot(config)\n'
    '    training_params.update(selected_parameters)\n'
    "    columns = tuple(columns or ('capacity',))\n"
    '    multifeature = len(columns) > 1\n'
    '    metadata = {\n'
    "        'mode': config.mode,\n"
    "        'model_type': config.mode,\n"
    "        'window_size': config.window_size,\n"
    "        'rated_capacity': config.rated_capacity,\n"
    "        'threshold_ratio': getattr(config, 'threshold_ratio', 0.8),\n"
    "        'norm_method': scaler.method,\n"
    "        'scaler': scaler.to_dict(),\n"
    "        'feature_schema': {\n"
    "            'features': list(columns),\n"
    "            'feature': 'capacity' if not multifeature else 'multifeature',\n"
    "            'dtype': 'float32',\n"
    "            'shape': (['batch', config.window_size, len(columns)]\n"
    '                      if multifeature\n'
    "                      else ['batch', config.window_size]),\n"
    "            'feature_scaler': (\n"
    '                feature_scaler.to_dict() if feature_scaler is not None\n'
    '                else None),\n'
    "            'multifeature_recursive_policy': (\n"
    "                '非容量通道在递归预测时保持窗口末值（未来工况未知）'\n"
    '                if multifeature else None),\n'
    '        },\n'
    "        'training_params': training_params,\n"
    "        'data_hash': data_digest.hexdigest(),\n"
    "        'training_batteries': list(valid_names),\n"
    "        'battery_hashes': battery_hashes,\n"
    "        'final_training_sample_count': int(sample_count),\n"
    "        'final_training_scope': 'all_valid_batteries',\n"
    '    }\n'
    '    if config.mode in RECURRENT_MODES:\n'
    "        metadata['hidden_dim'] = config.hidden_dim\n"
    "        metadata['input_size'] = int(len(columns))\n"
    '    return _complete_metadata(metadata)\n'
    '\n'
    '\n'
    'def _prepare_final_training_data(config, battery_dict, battery_list):\n'
    '    """收集全部有效电池的全部窗口（不再切出「训练电池的后 20%」作验证）。\n'
    '\n'
    '    改进方案 A2：验证集必须是**一块没见过的电池**（由 ``core.protocol`` 的内层\n'
    '    留一电池交叉验证提供），而不是「训练电池的最后一段」——后者恰好是寿命末段，\n'
    '    会让模型永远见不到膝点。\n'
    '    """\n'
    '    battery_x, battery_y = {}, {}\n'
    '    valid_names = []\n'
    '    columns = _feature_columns(config)\n'
    '    multifeature = len(columns) > 1\n'
    '    for name in battery_list:\n'
    '        if name in battery_x or name not in battery_dict:\n'
    '            continue\n'
    '        entry = battery_dict[name]\n'
    '        capacity = np.asarray(\n'
    "            entry['capacity'], dtype=np.float32).reshape(-1)\n"
    '        if len(capacity) <= config.window_size:\n'
    '            continue\n'
    "        if multifeature and hasattr(entry, 'columns'):\n"
    '            available = [c for c in columns if c in entry.columns]\n'
    "            if 'capacity' not in available:\n"
    "                available = ['capacity'] + available\n"
    '            x, y = build_instances_mf(\n'
    '                entry.loc[:, available], config.window_size,\n'
    '                cols=available)\n'
    '        else:\n'
    '            x, y = build_instances(capacity, config.window_size)\n'
    '        if len(x) == 0:\n'
    '            continue\n'
    '        battery_x[name] = x\n'
    '        battery_y[name] = y\n'
    '        valid_names.append(name)\n'
    '    if not valid_names:\n'
    "        raise ValueError('没有足够的数据训练最终模型')\n"
    '\n'
    '    all_x = np.vstack([battery_x[name] for name in valid_names])\n'
    '    all_y = np.concatenate([battery_y[name] for name in valid_names])\n'
    '    if len(all_x) < 2:\n'
    "        raise ValueError('最终模型至少需要两个训练样本')\n"
    '\n'
    '    return {\n'
    "        'valid_names': valid_names,\n"
    "        'battery_x': battery_x,\n"
    "        'battery_y': battery_y,\n"
    "        'all_x': all_x,\n"
    "        'all_y': all_y,\n"
    '    }\n'
    '\n'
    '\n'
    'def train_model_on_all_data(config, battery_dict, battery_list, stop_flag=None,\n'
    '                            log_callback=None):\n'
    '    """选超参 → 用**全部**有效电池的全部窗口定型（与评估路径共用 ``fit_final``）。\n'
    '\n'
    '    改进方案 A2：旧实现自己在 ``model_persistence`` 里重复了一遍 RNN 训练循环、\n'
    '    RF 分批加树和 XGBoost early stopping，而且「调参用的验证集」是训练电池的\n'
    '    最后一块 / 后 10%——与评估路径不同，导致「报告的评估指标评估的并不是最终\n'
    '    部署的那个模型」。\n'
    '\n'
    '    现在两条路径共用 :func:`core.protocol.fit_final`，超参由内层留一电池交叉验证\n'
    '    选出（验证对象是一块没见过的电池，和最终使用场景一致）。\n'
    '    """\n'
    '    check_cancelled(stop_flag)\n'
    '    mode = normalize_model_name(config.mode)\n'
    '    data = _prepare_final_training_data(config, battery_dict, battery_list)\n'
    "    valid_names = data['valid_names']\n"
    "    all_x = data['all_x']\n"
    '    columns = _feature_columns(config)\n'
    '    multifeature = len(columns) > 1\n'
    '    rated = float(config.rated_capacity)\n'
    '\n'
    '    # ── 选超参：内层留一电池交叉验证 ──\n'
    '    # scaler 只用全部有效电池拟合；fit_fn 内部会用它归一化，因此这里传原始量纲。\n'
    '    final_scaler, feature_scaler = _fit_final_scalers(\n'
    '        config, data, columns, multifeature, rated)\n'
    '    fit_fn = make_fit_fn(\n'
    '        config, stop_flag=stop_flag, log_callback=log_callback,\n'
    "        name='最终模型', net_class=Net, feature_scaler=feature_scaler)\n"
    '    grid = hparam_grid(config, mode)\n'
    "    device = getattr(config, 'device', 'cpu')\n"
    '    if len(valid_names) >= 2:\n'
    '        hp, cv_score, fold_models = select_hparams(\n'
    '            battery_dict, valid_names, config.window_size, fit_fn, grid, rated,\n'
    '            start_frac=0.5, stop_flag=stop_flag,\n'
    '            columns=columns if multifeature else None, return_folds=True,\n'
    '            device=device, feature_scaler=feature_scaler)\n'
    '        if log_callback:\n'
    '            score_text = (\n'
    "                'N/A' if cv_score is None or not np.isfinite(cv_score)\n"
    "                else f'{cv_score:.4f} Ah')\n"
    '            log_callback(\n'
    "                f'[最终模型] 内层留一电池交叉验证（{len(valid_names)} 折）：'\n"
    "                f'选定超参 {hp}，滚动 RMSE@50%={score_text}')\n"
    '    else:\n'
    '        hp = grid[0]\n'
    '        fold_models = {}\n'
    '        if log_callback:\n'
    "            log_callback(f'[最终模型] 只有一块电池，跳过内层交叉验证，使用 {hp}')\n"
    '\n'
    '    check_cancelled(stop_flag)\n'
    '\n'
    '    # ── 定型：用全部有效电池的全部窗口重训 ──\n'
    '    # 走的是与评估路径**同一个** core.protocol.fit_final（而不是各写一遍），\n'
    '    # 因此「报告的评估指标」与「最终部署的模型」是同一套流程的产物。\n'
    '    final_model = fit_final(\n'
    '        battery_dict, valid_names, config.window_size, fit_fn, hp, rated,\n'
    '        columns=columns if multifeature else None)\n'
    '    check_cancelled(stop_flag)\n'
    '\n'
    '    # ── 持久性混合系数：用「没见过验证电池」的内层折模型 + 多步滚动标定 ──\n'
    '    blend = _final_blend(\n'
    '        config, battery_dict, valid_names, rated, columns,\n'
    '        multifeature, feature_scaler, fold_models, log_callback)\n'
    '\n'
    '    if mode in RECURRENT_MODES:\n'
    "        final_model = final_model.to('cpu')\n"
    '\n'
    '    metadata = _final_training_metadata(\n'
    '        config, final_scaler, valid_names, battery_dict, len(all_x), hp,\n'
    '        feature_scaler=feature_scaler, columns=columns)\n'
    "    metadata['persistence_blend'] = blend\n"
    '    if log_callback:\n'
    '        log_callback(\n'
    "            f'[最终模型] 已用全部 {len(valid_names)} 块电池、'\n"
    "            f'{len(all_x)} 个样本重训，超参={hp}，α={blend:.3f}')\n"
    '    return final_model, metadata\n'
    '\n'
    '\n'
    'def _fit_final_scalers(config, data, columns, multifeature, rated):\n'
    '    """最终 scaler：只用全部有效电池的窗口拟合。"""\n'
    '\n'
    '    scaler = CapacityScaler(\n'
    '        method=config.norm_method,\n'
    '        rated_capacity=rated,\n'
    '    ).fit(np.concatenate(\n'
    "        [data['all_x'][:, :, 0].reshape(-1) if multifeature\n"
    "         else data['all_x'].reshape(-1),\n"
    "         data['all_y'].reshape(-1)]))\n"
    '\n'
    '    feature_scaler = None\n'
    '    if multifeature:\n'
    '        frames = []\n'
    "        for name in data['valid_names']:\n"
    "            x = data['battery_x'][name]\n"
    '            frames.append(x.reshape(-1, x.shape[-1]))\n'
    '        combined = np.vstack(frames)\n'
    '        feature_scaler = FeatureScaler().fit(combined)\n'
    '    return scaler, feature_scaler\n'
    '\n'
    '\n'
    'def _final_blend(config, battery_dict, valid_names, rated, columns,\n'
    '                 multifeature, feature_scaler, fold_models, log_callback):\n'
    '    """最终模型的 α：与评估路径同一口径（多步滚动 + 内层折模型）。"""\n'
    '    if not fold_models:\n'
    '        return 1.0\n'
    "    device = getattr(config, 'device', 'cpu')\n"
    '    alphas = {}\n'
    '    for val_name, fold_model in fold_models.items():\n'
    '        step_raw = model_step_for(\n'
    '            fold_model, rated, device=device, feature_scaler=feature_scaler)\n'
    '        alpha, _ = choose_blend_by_rollout(\n'
    '            step_raw, battery_dict, [val_name], config.window_size,\n'
    '            starts=(0.5, 0.6),\n'
    '            columns=columns if multifeature else None)\n'
    '        alphas[val_name] = alpha\n'
    '    blend = float(np.mean(list(alphas.values()))) if alphas else 1.0\n'
    '    if log_callback:\n'
    "        detail = '，'.join(f'{k}={v:.2f}' for k, v in alphas.items())\n"
    "        log_callback(f'[最终模型] 防过拟合校准系数 α={blend:.3f}（{detail}）')\n"
    '        if blend < 0.05:\n'
    '            log_callback(\n'
    "                '[最终模型] ⚠ 模型未超越持久性基线（α≈0）：'\n"
    "                '预测将退化为平推。')\n"
    '    return blend\n'
    '\n'
    '\n'
    'def _feature_columns(config):\n'
    "    columns = getattr(config, 'feature_columns', None)\n"
    '    if columns is None:\n'
    "        return ('capacity',)\n"
    '    return tuple(columns)\n'
)

# ---- ui/fonts.py ----
_MODULE_SOURCES['ui.fonts'] = (
    '"""Qt 字体引导：保证中文在任何平台插件下都能正确渲染。\n'
    '\n'
    '## 为什么需要这个模块\n'
    '\n'
    'PyQt6 的 **offscreen / minimal 平台插件不使用 Windows 字体引擎**，只认\n'
    '``PyQt6/Qt6/lib/fonts`` 目录。该目录在多数 pip / conda 安装里是缺失的，于是：\n'
    '\n'
    '* ``QFontDatabase.families()`` 返回**空列表**；\n'
    '* QSS 里的 ``font-family`` 一个都解析不到；\n'
    '* 所有 Qt 文字渲染成方框（豆腐块），而 matplotlib 图表不受影响——它自己\n'
    '  解析 ``theme_tokens.CJK_FONTS``。\n'
    '\n'
    '实测（本仓库目标环境）：\n'
    '\n'
    '* ``platform = windows`` → 570 个字体族，中文正常；\n'
    '* ``platform = offscreen`` → **0 个字体族**，中文全部变成方框。\n'
    '\n'
    '因此本模块显式把系统中文字体注册进 Qt 并设为应用字体，做到：\n'
    '\n'
    '1. 真实窗口环境（``windows`` / ``cocoa`` / ``xcb``）本来就能枚举字体，\n'
    '   这里只是幂等地挑出最合适的字体族；\n'
    '2. offscreen 环境（README 截图、CI 冒烟）下补齐字体，截图不再出现方框；\n'
    '3. 用户机器上 Qt 字体库损坏时也能自愈。\n'
    '"""\n'
    '\n'
    'from __future__ import annotations\n'
    '\n'
    'import os\n'
    'import sys\n'
    '\n'
    '_FONT_DIRS = (\n'
    "    os.path.join(os.environ.get('WINDIR', r'C:\\Windows'), 'Fonts'),\n"
    "    os.path.expanduser('~/.fonts'),\n"
    "    '/usr/share/fonts',\n"
    "    '/usr/local/share/fonts',\n"
    "    '/System/Library/Fonts',\n"
    "    '/Library/Fonts',\n"
    ')\n'
    '\n'
    '#: 需要注册的字体文件，按「中文 UI → Latin UI → 等宽 → 标题 → 兜底」排列。\n'
    '#: ``.ttc`` 是字体集合，一个文件里可能注册出多个家族（如 msyh.ttc →\n'
    '#: ``Microsoft YaHei`` 与 ``Microsoft YaHei UI``）。\n'
    '_FONT_FILES = (\n'
    "    'msyh.ttc', 'msyhbd.ttc', 'msyhl.ttc',       # 微软雅黑（中文 UI 首选）\n"
    "    'msjh.ttc',                                   # 微软正黑（繁体环境兜底）\n"
    "    'segoeui.ttf', 'segoeuib.ttf', 'segoeuil.ttf',  # Latin UI\n"
    "    'consola.ttf', 'consolab.ttf',                # 等宽（数值 / 日志）\n"
    "    'stzhongs.ttf', 'stkaiti.ttf', 'stxihei.ttf', 'stsong.ttf',  # 中文字体\n"
    "    'simhei.ttf', 'simsun.ttc', 'deng.ttf',       # 兜底中文\n"
    "    'NotoSansCJK-Regular.ttc', 'NotoSansCJKsc-Regular.otf',\n"
    "    'wqy-microhei.ttc', 'DejaVuSans.ttf',         # Linux 兜底\n"
    ')\n'
    '\n'
    '#: UI 字体回退链。第一项是目标族，其余是不同平台 / 不同字体包的写法。\n'
    'UI_FONT_FAMILIES = (\n'
    "    'Microsoft YaHei UI', 'Microsoft YaHei', 'PingFang SC',\n"
    "    'Noto Sans CJK SC', 'Noto Sans CJK JP', 'Source Han Sans SC',\n"
    "    'WenQuanYi Micro Hei', 'Segoe UI', 'SimHei', 'DengXian', 'SimSun',\n"
    ')\n'
    '\n'
    '#: 标题 / 展示用字体回退链（中文衬线优先，更有「宣纸」气质）。\n'
    'DISPLAY_FONT_FAMILIES = (\n'
    "    'STZhongsong', 'STKaiti', 'STXihei', 'FangSong', 'KaiTi',\n"
    "    'Microsoft YaHei', 'SimSun',\n"
    ')\n'
    '\n'
    '#: 等宽字体回退链（数值、日志、坐标读数）。\n'
    'MONO_FONT_FAMILIES = (\n'
    "    'Consolas', 'JetBrains Mono', 'Cascadia Mono', 'Cascadia Code',\n"
    "    'DejaVu Sans Mono', 'Courier New',\n"
    ')\n'
    '\n'
    '_INSTALLED = False\n'
    '_REGISTERED = False\n'
    "_RESOLVED = {'ui': None, 'display': None, 'mono': None, 'registered': ()}\n"
    '#: 已经配置过的 QApplication（按 id 记录）与当时设置的字体族。\n'
    '#: ``setFont`` 会触发**所有现存控件**的样式重算，因此在长生命周期进程里\n'
    '#: 反复调用既浪费又危险（实测在连续创建/销毁大量窗口的测试进程中会段错误）。\n'
    '_CONFIGURED_APPS = {}\n'
    '\n'
    '\n'
    'def _font_path(name):\n'
    '    """在候选目录里找字体文件，返回第一个存在的绝对路径。"""\n'
    '    for directory in _FONT_DIRS:\n'
    '        candidate = os.path.join(directory, name)\n'
    '        if os.path.isfile(candidate):\n'
    '            return candidate\n'
    '    return None\n'
    '\n'
    '\n'
    'def register_system_fonts(force=False):\n'
    '    """把系统字体文件注册进 Qt；返回本次新注册的家族名元组。\n'
    '\n'
    '    **每个进程只做一次**。``QFontDatabase.addApplicationFont`` 每次调用都会往\n'
    '    Qt 内部的字体表里追加记录（即使文件相同），因此在「创建大量窗口」的进程里\n'
    '    反复调用会不断膨胀内部状态，实测会让长时间运行的测试进程崩溃。\n'
    '    字体是进程级资源，没有理由随窗口重复注册。\n'
    '\n'
    '    ``force=True`` 可强制重新扫描（例如用户在运行中装了新字体）。\n'
    '    """\n'
    '    global _REGISTERED\n'
    '    if _REGISTERED and not force:\n'
    "        return _RESOLVED.get('registered') or ()\n"
    '\n'
    '    try:\n'
    '        from PyQt6.QtGui import QFontDatabase\n'
    '    except ImportError:          # pragma: no cover - 无 PyQt6 时静默跳过\n'
    '        return ()\n'
    '\n'
    '    registered = []\n'
    '    for name in _FONT_FILES:\n'
    '        path = _font_path(name)\n'
    '        if path is None:\n'
    '            continue\n'
    '        font_id = QFontDatabase.addApplicationFont(path)\n'
    '        if font_id == -1:\n'
    '            continue\n'
    '        registered.extend(QFontDatabase.applicationFontFamilies(font_id))\n'
    '    _REGISTERED = True\n'
    '    return tuple(dict.fromkeys(registered))\n'
    '\n'
    '\n'
    'def _pick_family(families, candidates):\n'
    '    """在 ``families`` 里按 ``candidates`` 的顺序挑第一个可用的族名。"""\n'
    '    available = set(families)\n'
    '    for candidate in candidates:\n'
    '        if candidate in available:\n'
    '            return candidate\n'
    '    return None\n'
    '\n'
    '\n'
    'def resolve_families():\n'
    '    """返回 ``{\'ui\':…, \'display\':…, \'mono\':…}`` 与实际注册到的家族列表。"""\n'
    '    from PyQt6.QtGui import QFontDatabase\n'
    '\n'
    '    registered = register_system_fonts()\n'
    '    families = list(QFontDatabase.families())\n'
    '\n'
    '    resolved = {\n'
    "        'ui': _pick_family(families, UI_FONT_FAMILIES),\n"
    "        'display': _pick_family(families, DISPLAY_FONT_FAMILIES),\n"
    "        'mono': _pick_family(families, MONO_FONT_FAMILIES),\n"
    '    }\n'
    '    _RESOLVED.update(resolved)\n'
    "    _RESOLVED['registered'] = registered\n"
    '    return dict(_RESOLVED)\n'
    '\n'
    '\n'
    'def install_fonts(app=None, point_size=10):\n'
    '    """注册系统字体并把解析出的 UI 字体设为应用默认字体。\n'
    '\n'
    '    应在创建 **任何控件之前** 调用（``battery_soh_app.py`` 在 QApplication\n'
    '    构造后立刻调用；``MainWindow`` 也会兜底调用一次）。返回解析出的 UI 族名。\n'
    '\n'
    '    幂等：字体注册总要跑（Qt 自己会去重），但 ``QApplication.setFont`` 对同一个\n'
    '    QApplication 只做一次——它会让**所有现存控件**重算样式，重复调用没有收益，\n'
    '    在窗口频繁创建销毁的长时间进程里还会踩到已析构的控件。\n'
    '\n'
    '    返回值可能为 ``None``——表示这台机器上一个候选字体都没有，此时 Qt 自己\n'
    '    的回退仍然生效，但我们不会假装已经修好。\n'
    '    """\n'
    '    global _INSTALLED\n'
    '\n'
    '    from PyQt6.QtGui import QFont\n'
    '\n'
    '    if app is None:\n'
    '        from PyQt6.QtWidgets import QApplication\n'
    '\n'
    '        app = QApplication.instance()\n'
    '\n'
    '    families = resolve_families()\n'
    "    ui_family = families.get('ui')\n"
    '    key = id(app)\n'
    '\n'
    '    if ui_family and _CONFIGURED_APPS.get(key) == ui_family:\n'
    '        _INSTALLED = True\n'
    '        return ui_family\n'
    '\n'
    '    if ui_family:\n'
    '        font = QFont(ui_family, point_size)\n'
    '        font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)\n'
    '        if app is not None:\n'
    '            app.setFont(font)\n'
    '            _CONFIGURED_APPS[key] = ui_family\n'
    '        else:                                # pragma: no cover - 无 QApplication\n'
    '            QFont.insertSubstitutions(ui_family, [ui_family])\n'
    '    _INSTALLED = True\n'
    '    return ui_family\n'
    '\n'
    '\n'
    'def installed():\n'
    '    """是否已调用过 :func:`install_fonts`。"""\n'
    '    return _INSTALLED\n'
    '\n'
    '\n'
    'def ui_font(point_size=10, weight=None, family=None):\n'
    '    """构造 UI 字体（未安装时给出安全的族名回退）。"""\n'
    '    from PyQt6.QtGui import QFont\n'
    '\n'
    "    name = family or _RESOLVED.get('ui') or UI_FONT_FAMILIES[0]\n"
    '    font = QFont(name, point_size)\n'
    '    if weight is not None:\n'
    '        font.setWeight(weight)\n'
    '    return font\n'
    '\n'
    '\n'
    'def font_fallbacks_css(candidates=UI_FONT_FAMILIES):\n'
    '    """QSS 用的回退链字符串，例如 ``"Microsoft YaHei", "Segoe UI", sans-serif``。"""\n'
    '    quoted = \', \'.join(f\'"{name}"\' for name in candidates)\n'
    "    return f'{quoted}, sans-serif'\n"
    '\n'
    '\n'
    'def diagnostics():\n'
    '    """诊断信息：字体目录、已注册家族、解析结果。供启动日志与排查使用。"""\n'
    '    try:\n'
    '        from PyQt6.QtGui import QFontDatabase\n'
    '    except ImportError:          # pragma: no cover\n'
    "        return {'error': 'PyQt6 不可用'}\n"
    '\n'
    '    available = list(QFontDatabase.families())\n'
    '    return {\n'
    "        'platform': (os.environ.get('QT_QPA_PLATFORM') or 'default'),\n"
    "        'family_count': len(available),\n"
    "        'registered': list(_RESOLVED.get('registered') or ()),\n"
    "        'resolved': {key: _RESOLVED.get(key)\n"
    "                     for key in ('ui', 'display', 'mono')},\n"
    "        'font_dirs': [d for d in _FONT_DIRS if os.path.isdir(d)],\n"
    "        'cjk_ok': bool(available) and _pick_family(\n"
    '            available, UI_FONT_FAMILIES) is not None,\n'
    "        'python': sys.version.split()[0],\n"
    '    }\n'
)

# ---- ui/style.py ----
_MODULE_SOURCES['ui.style'] = (
    '"""\n'
    '统一主题样式 - Battery SOH Assessment System\n'
    '设计语言：宣纸水墨（专业评估仪器）\n'
    '- 暖宣纸基底 + 墨色层级 + 单一黛青主强调\n'
    '- 朱砂仅用于危险/失效，竹青与赭石用于语义状态\n'
    '- 统一细描边、清晰焦点、克制墨晕反馈\n'
    '\n'
    '颜色不再写在本文件里：唯一真相来源是工程根目录的 ``theme_tokens.py``\n'
    '（纯字典 + 纯函数，不 import 第三方库，因此启动闪屏可以在重库加载前就用它）。\n'
    '本模块只负责把这些 token 渲染成 QSS。\n'
    '"""\n'
    '\n'
    'from pathlib import Path\n'
    '\n'
    'from theme_tokens import (\n'
    '    DEFAULT_THEME,\n'
    '    THEMES,\n'
    '    get_theme,\n'
    '    rgba,\n'
    ')\n'
    'from ui.fonts import (\n'
    '    DISPLAY_FONT_FAMILIES,\n'
    '    MONO_FONT_FAMILIES,\n'
    '    UI_FONT_FAMILIES,\n'
    '    font_fallbacks_css,\n'
    ')\n'
    '\n'
    '\n'
    "DESIGN_LANGUAGE = '宣纸水墨'\n"
    '\n'
    '#: 兼容旧引用：``COLORS`` 是当前浅色主题的 token 别名。\n'
    '#: 新代码请直接用 ``build_qss(tokens)`` / ``get_theme(mode)``。\n'
    'COLORS = THEMES[DEFAULT_THEME]\n'
    '\n'
    '#: 当前生效的主题模式（由 :func:`apply_theme` 更新）\n'
    '_current_mode = DEFAULT_THEME\n'
    '\n'
    'COMBO_DOWN_ARROW_URL = (\n'
    "    Path(__file__).resolve().parents[1] / 'assets' / 'icons' /\n"
    "    'combo-down-arrow.svg'\n"
    ').as_posix()\n'
    '\n'
    '\n'
    '# ── 字体族 ──────────────────────────────────────────────────\n'
    '# 候选链写在 ui/fonts.py 里；这里把它渲染成 QSS 的 font-family 列表。\n'
    '# 之所以不再硬写死一个族名：PyQt6 的 offscreen 平台插件下 QFontDatabase\n'
    '# 可能是空的（见 ui/fonts.py 的模块说明），必须由 install_fonts() 显式\n'
    '# 注册系统字体后，这些族名才解析得到。\n'
    'FONT_FAMILY = font_fallbacks_css(UI_FONT_FAMILIES)\n'
    'FONT_DISPLAY = font_fallbacks_css(DISPLAY_FONT_FAMILIES)\n'
    'FONT_MONO = font_fallbacks_css(MONO_FONT_FAMILIES)\n'
    '\n'
    '\n'
    "def _font(size=10, weight='normal', mono=False):\n"
    '    family = FONT_MONO if mono else FONT_FAMILY\n'
    "    return f'font-family: {family}; font-size: {size}pt; font-weight: {weight};'\n"
    '\n'
    '\n'
    "def _display_font(size=10, weight='normal'):\n"
    "    return f'font-family: {FONT_DISPLAY}; font-size: {size}pt; font-weight: {weight};'\n"
    '\n'
    '\n'
    'def build_qss(COLORS):\n'
    '    """把一套主题 token 渲染成全局 QSS。\n'
    '\n'
    "    形参刻意命名为 ``COLORS``，这样函数体里原有的 ``COLORS['…']`` 引用\n"
    '    一个字都不用改；手写的半透明色统一走 :func:`theme_tokens.rgba`。\n'
    '    """\n'
    '    return f"""\n'
    '/* ── 全局 ───────────────────────────────────── */\n'
    '* {{\n'
    '    {_font(10)}\n'
    "    color: {COLORS['text']};\n"
    '}}\n'
    '\n'
    'QMainWindow, QDialog, QWidget#central {{\n'
    "    background: {COLORS['bg_deep']};\n"
    '}}\n'
    '\n'
    '/* ── 文本 ─────────────────────────────────────── */\n'
    'QLabel {{\n'
    "    color: {COLORS['text']};\n"
    '    background: transparent;\n'
    '    {_font(10)}\n'
    '}}\n'
    'QLabel[role="title"] {{\n'
    "    {_font(14, 'bold')}\n"
    "    color: {COLORS['text']};\n"
    '    letter-spacing: 1px;\n'
    '}}\n'
    'QLabel[role="subtitle"] {{\n'
    '    {_font(9)}\n'
    "    color: {COLORS['text_muted']};\n"
    '    letter-spacing: 0.5px;\n'
    '}}\n'
    '\n'
    '/* ── 顶部条（右上顶角主题切换） ────────────────── */\n'
    'QFrame[role="topBar"] {{\n'
    "    background: {COLORS['bg_elevated']};\n"
    "    border: 1px solid {COLORS['border_soft']};\n"
    '    border-radius: 6px;\n'
    '}}\n'
    'QLabel[role="topBarTitle"] {{\n'
    "    {_font(11, 'bold')}\n"
    "    color: {COLORS['text']};\n"
    '    letter-spacing: 0.6px;\n'
    '}}\n'
    'QLabel[role="topBarSubtitle"] {{\n'
    '    {_font(9)}\n'
    "    color: {COLORS['text_dim']};\n"
    '    letter-spacing: 0.4px;\n'
    '}}\n'
    'QPushButton#themeToggle {{\n'
    "    {_font(9, 'bold')}\n"
    "    color: {COLORS['text']};\n"
    "    background: {COLORS['bg_surface']};\n"
    "    border: 1px solid {COLORS['border']};\n"
    '    border-radius: 14px;\n'
    '    padding: 5px 14px;\n'
    '}}\n'
    'QPushButton#themeToggle:hover {{\n'
    "    background: {COLORS['bg_hover']};\n"
    "    border-color: {COLORS['primary']};\n"
    '}}\n'
    'QPushButton#themeToggle:pressed {{\n'
    "    background: {COLORS['primary']};\n"
    "    color: {COLORS['on_accent']};\n"
    '}}\n'
    'QPushButton#themeToggle:focus {{\n'
    "    border: 2px solid {COLORS['primary']};\n"
    '}}\n'
    'QLabel[role="metric"] {{\n'
    "    {_font(20, 'bold')}\n"
    "    color: {COLORS['primary']};\n"
    '}}\n'
    'QLabel[role="badge"] {{\n'
    "    color: {COLORS['primary']};\n"
    "    {_font(8, 'bold')}\n"
    '    padding: 2px 8px;\n'
    "    border: 1px solid {COLORS['primary_d']};\n"
    '    border-radius: 8px;\n'
    "    background: {rgba(COLORS['primary'], 0.10)};\n"
    '}}\n'
    'QLabel[role="sectionTitle"] {{\n'
    "    {_font(11, 'bold')}\n"
    "    color: {COLORS['text']};\n"
    '    padding: 2px 0;\n'
    '}}\n'
    'QLabel[role="runStatus"] {{\n'
    "    {_font(9, '600')}\n"
    "    color: {COLORS['text_muted']};\n"
    "    background: {COLORS['bg_surface']};\n"
    "    border: 1px solid {COLORS['border_soft']};\n"
    '    border-radius: 6px;\n'
    '    padding: 7px 10px;\n'
    '}}\n'
    'QLabel[role="runStatus"][state="running"] {{\n'
    "    color: {COLORS['primary']};\n"
    "    border-color: {COLORS['primary_d']};\n"
    '}}\n'
    'QLabel[role="emptyState"] {{\n'
    '    {_font(10)}\n'
    "    color: {COLORS['text_muted']};\n"
    "    background: {COLORS['bg_base']};\n"
    "    border: 1px dashed {COLORS['border']};\n"
    '    border-radius: 10px;\n'
    '    padding: 24px 18px;\n'
    '}}\n'
    '\n'
    'QFrame[role="dataSummary"] {{\n'
    "    background: {rgba(COLORS['primary'], 0.06)};\n"
    "    border: 1px solid {COLORS['border_soft']};\n"
    '    border-radius: 6px;\n'
    '}}\n'
    'QLabel[role="dataSummaryText"] {{\n'
    '    {_font(8)}\n'
    "    color: {COLORS['text_muted']};\n"
    '}}\n'
    'QLabel[role="dataSummaryText"][state="ready"] {{\n'
    "    color: {COLORS['primary_d']};\n"
    '}}\n'
    'QLabel[role="dataSummaryCount"] {{\n'
    "    {_font(11, 'bold', mono=True)}\n"
    "    color: {COLORS['on_accent']};\n"
    "    background: {COLORS['primary']};\n"
    "    border: 1px solid {COLORS['primary_d']};\n"
    '    border-radius: 11px;\n'
    '    min-width: 22px;\n'
    '    min-height: 22px;\n'
    '}}\n'
    '\n'
    'QFrame[role="modelShelf"] {{\n'
    "    background: {COLORS['bg_base']};\n"
    "    border: 1px solid {COLORS['border_soft']};\n"
    '    border-radius: 7px;\n'
    '}}\n'
    'QLabel[role="modelHint"] {{\n'
    '    {_font(8)}\n'
    "    color: {COLORS['text_muted']};\n"
    '}}\n'
    '\n'
    'QFrame[role="runStatusStrip"] {{\n'
    "    background: {COLORS['bg_surface']};\n"
    "    border: 1px solid {COLORS['border_soft']};\n"
    '    border-radius: 6px;\n'
    '}}\n'
    'QFrame[role="runStatusDot"] {{\n'
    "    background: {COLORS['bg_elevated']};\n"
    "    border: 1px solid {COLORS['border']};\n"
    '    border-radius: 5px;\n'
    '}}\n'
    'QFrame[role="runStatusDot"][state="running"] {{\n'
    "    background: {COLORS['primary']};\n"
    "    border-color: {COLORS['primary_d']};\n"
    '}}\n'
    'QFrame[role="runStatusStrip"] QLabel[role="runStatus"] {{\n'
    '    background: transparent;\n'
    '    border: none;\n'
    '    padding: 2px 0;\n'
    '}}\n'
    'QLabel[role="runContext"] {{\n'
    '    {_font(9)}\n'
    "    color: {COLORS['text_muted']};\n"
    '}}\n'
    '\n'
    'QFrame[role="resultBatchBar"] {{\n'
    "    background: {COLORS['bg_elevated']};\n"
    "    border: 1px solid {COLORS['border_soft']};\n"
    '    border-radius: 4px;\n'
    '}}\n'
    'QLabel[role="resultBatchLabel"] {{\n'
    "    {_font(9, '600')}\n"
    "    color: {COLORS['text_muted']};\n"
    '}}\n'
    '\n'
    'QFrame[role="resultSummary"] {{\n'
    "    background: {rgba(COLORS['primary'], 0.06)};\n"
    "    border: 1px solid {COLORS['border_soft']};\n"
    "    border-left: 3px solid {COLORS['primary']};\n"
    '    border-radius: 5px;\n'
    '}}\n'
    'QLabel[role="resultSummaryTitle"] {{\n'
    "    {_display_font(11, 'bold')}\n"
    "    color: {COLORS['primary_d']};\n"
    '}}\n'
    'QLabel[role="resultSummaryMetric"] {{\n'
    "    {_font(10, 'bold', mono=True)}\n"
    "    color: {COLORS['primary_d']};\n"
    '}}\n'
    'QLabel[role="resultSummaryMeta"] {{\n'
    '    {_font(9)}\n'
    "    color: {COLORS['text_muted']};\n"
    '}}\n'
    '\n'
    'QFrame[role="resultState"] {{\n'
    "    background: {COLORS['bg_base']};\n"
    "    border: 1px dashed {COLORS['border']};\n"
    '    border-radius: 10px;\n'
    '}}\n'
    'QFrame[role="resultStateBattery"] {{\n'
    '    background: transparent;\n'
    "    border: 1px solid {COLORS['primary']};\n"
    '    border-radius: 5px;\n'
    '}}\n'
    'QFrame[role="resultStateBatteryFill"] {{\n'
    "    background: {rgba(COLORS['primary'], 0.18)};\n"
    "    border: 1px solid {COLORS['primary_l']};\n"
    '    border-radius: 2px;\n'
    '}}\n'
    'QFrame[role="resultStateBatteryTerminal"] {{\n'
    "    background: {COLORS['primary']};\n"
    '    border: none;\n'
    '    border-radius: 2px;\n'
    '}}\n'
    'QLabel[role="resultStateTitle"] {{\n'
    "    {_display_font(12, 'bold')}\n"
    "    color: {COLORS['primary_d']};\n"
    '    letter-spacing: 0.5px;\n'
    '}}\n'
    'QLabel[role="resultStateDetail"] {{\n'
    '    {_font(9)}\n'
    "    color: {COLORS['text_muted']};\n"
    '}}\n'
    'QLabel[role="resultStateGuide"] {{\n'
    "    {_font(9, '600')}\n"
    "    color: {COLORS['warning']};\n"
    '    background: rgba(122, 78, 34, 0.07);\n'
    "    border: 1px solid {COLORS['border_soft']};\n"
    '    border-radius: 8px;\n'
    '    padding: 4px 9px;\n'
    '}}\n'
    '\n'
    '/* ── 分组框 ───────────────────────────────────── */\n'
    'QGroupBox {{\n'
    "    {_font(10, 'bold')}\n"
    "    color: {COLORS['text']};\n"
    "    border: 1px solid {COLORS['border_soft']};\n"
    '    border-radius: 8px;\n'
    '    margin-top: 14px;\n'
    '    padding: 14px 10px 10px 10px;\n'
    "    background: {COLORS['bg_surface']};\n"
    '}}\n'
    'QGroupBox::title {{\n'
    '    subcontrol-origin: margin;\n'
    '    subcontrol-position: top left;\n'
    '    padding: 2px 12px;\n'
    '    left: 12px;\n'
    "    color: {COLORS['text']};\n"
    '    background: transparent;\n'
    '}}\n'
    'QGroupBox[role="resultCard"] {{\n'
    '    background: transparent;\n'
    '    border: none;\n'
    "    border-top: 1px solid {COLORS['border_soft']};\n"
    '    border-radius: 0;\n'
    '}}\n'
    'QLabel[role="resultStatus"] {{\n'
    "    {_font(10, 'bold')}\n"
    '}}\n'
    'QLabel[role="resultStatus"][state="success"] {{ color: {COLORS[\'success_l\']}; }}\n'
    'QLabel[role="resultStatus"][state="warning"] {{ color: {COLORS[\'warning\']}; }}\n'
    'QLabel[role="resultStatus"][state="danger"] {{ color: {COLORS[\'danger\']}; }}\n'
    '\n'
    '/* ── 按钮基础 (由 AnimatedButton 接管点击效果) ── */\n'
    'QPushButton {{\n'
    "    {_font(10, '500')}\n"
    "    color: {COLORS['text']};\n"
    "    background: {COLORS['bg_elevated']};\n"
    "    border: 1px solid {COLORS['border']};\n"
    '    border-radius: 4px;\n'
    '    padding: 7px 14px;\n'
    '    min-height: 18px;\n'
    '    text-align: center;\n'
    '}}\n'
    'QPushButton:hover {{\n'
    "    background: {COLORS['bg_hover']};\n"
    "    border-color: {COLORS['primary']};\n"
    "    color: {COLORS['primary_d']};\n"
    '}}\n'
    'QPushButton:pressed {{\n'
    "    background: {COLORS['bg_surface']};\n"
    '    padding-top: 8px;\n'
    '    padding-bottom: 6px;\n'
    '}}\n'
    'QPushButton:focus {{\n'
    "    border: 2px solid {COLORS['primary']};\n"
    '}}\n'
    'QPushButton:disabled {{\n'
    "    color: {COLORS['text_dim']};\n"
    "    background: {COLORS['bg_elevated']};\n"
    "    border-color: {COLORS['border_soft']};\n"
    '}}\n'
    '\n'
    '/* ── 角色按钮（主色） ─────────────────────────── */\n'
    'QPushButton[role="primary"] {{\n'
    "    color: {COLORS['on_accent']};\n"
    "    background: {COLORS['primary']};\n"
    "    border: 1px solid {COLORS['primary']};\n"
    "    {_font(10, 'bold')}\n"
    '    letter-spacing: 1px;\n'
    '}}\n'
    'QPushButton[role="primary"]:hover {{\n'
    "    background: {COLORS['primary_l']};\n"
    "    color: {COLORS['on_accent']};\n"
    '}}\n'
    'QPushButton[role="primary"]:pressed {{\n'
    "    background: {COLORS['primary_d']};\n"
    '}}\n'
    '\n'
    'QPushButton[role="success"] {{\n'
    "    color: {COLORS['on_accent']};\n"
    "    background: {COLORS['success']};\n"
    "    border: 1px solid {COLORS['success']};\n"
    "    {_font(10, 'bold')}\n"
    '}}\n'
    'QPushButton[role="success"]:hover {{\n'
    "    background: {COLORS['success_d']};\n"
    '}}\n'
    '\n'
    'QPushButton[role="danger"] {{\n'
    "    color: {COLORS['on_danger']};\n"
    "    background: {COLORS['danger']};\n"
    "    border: 1px solid {COLORS['danger']};\n"
    "    {_font(10, 'bold')}\n"
    '}}\n'
    'QPushButton[role="danger"]:hover {{\n'
    "    background: {COLORS['danger_d']};\n"
    '}}\n'
    '\n'
    'QPushButton[role="ghost"] {{\n'
    '    background: transparent;\n'
    "    border: 1px solid {COLORS['border']};\n"
    "    color: {COLORS['text_muted']};\n"
    '}}\n'
    'QPushButton[role="ghost"]:hover {{\n'
    "    background: {rgba(COLORS['primary'], 0.08)};\n"
    "    border-color: {COLORS['primary']};\n"
    "    color: {COLORS['primary_d']};\n"
    '}}\n'
    '\n'
    '/* ── 模型选择按钮（激活态） ───────────────────── */\n'
    'QPushButton[role="model"] {{\n'
    "    {_font(10, '600')}\n"
    "    color: {COLORS['text_muted']};\n"
    "    background: {COLORS['bg_surface']};\n"
    "    border: 1px solid {COLORS['border']};\n"
    '    border-radius: 4px;\n'
    '    padding: 8px 4px;\n'
    '    min-width: 64px;\n'
    '    letter-spacing: 1px;\n'
    '}}\n'
    'QPushButton[role="model"]:hover {{\n'
    "    color: {COLORS['text']};\n"
    "    border-color: {COLORS['primary']};\n"
    "    background: {rgba(COLORS['primary'], 0.08)};\n"
    '}}\n'
    'QPushButton[role="model"][active="true"] {{\n'
    "    color: {COLORS['on_accent']};\n"
    "    background: {COLORS['primary']};\n"
    "    border: 1px solid {COLORS['primary_l']};\n"
    "    {_font(10, 'bold')}\n"
    '}}\n'
    '\n'
    '/* ── 输入控件 ─────────────────────────────────── */\n'
    'QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{\n'
    '    {_font(10)}\n'
    "    color: {COLORS['text']};\n"
    "    background: {COLORS['bg_surface']};\n"
    "    border: 1px solid {COLORS['border']};\n"
    '    border-radius: 3px;\n'
    '    padding: 5px 8px;\n'
    "    selection-background-color: {COLORS['primary_d']};\n"
    '}}\n'
    'QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{\n'
    "    border-color: {COLORS['primary']};\n"
    "    background: {COLORS['bg_focus']};\n"
    '}}\n'
    'QSpinBox, QDoubleSpinBox {{\n'
    "    selection-background-color: {COLORS['spin_selection']};\n"
    "    selection-color: {COLORS['on_selection']};\n"
    '}}\n'
    'QSpinBox::up-button, QSpinBox::down-button,\n'
    'QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{\n'
    '    width: 0; height: 0; border: 0;\n'
    '}}\n'
    'QComboBox::drop-down {{\n'
    '    border: none;\n'
    '    width: 22px;\n'
    '}}\n'
    'QComboBox QAbstractItemView {{\n'
    '    {_font(10)}\n'
    "    color: {COLORS['text']};\n"
    "    background: {COLORS['bg_surface']};\n"
    "    border: 1px solid {COLORS['border']};\n"
    "    selection-background-color: {COLORS['primary_d']};\n"
    "    selection-color: {COLORS['on_accent']};\n"
    '    padding: 4px;\n'
    '}}\n'
    'QComboBox::down-arrow {{\n'
    '    image: url("{COMBO_DOWN_ARROW_URL}");\n'
    '    width: 12px;\n'
    '    height: 8px;\n'
    '    margin-right: 6px;\n'
    '}}\n'
    '\n'
    'QMenu {{\n'
    '    {_font(10)}\n'
    "    color: {COLORS['text']};\n"
    "    background: {COLORS['bg_surface']};\n"
    "    border: 1px solid {COLORS['border']};\n"
    '    padding: 4px;\n'
    '}}\n'
    'QMenu::item {{\n'
    '    padding: 6px 24px 6px 10px;\n'
    '    border-radius: 3px;\n'
    '}}\n'
    'QMenu::item:selected {{\n'
    "    color: {COLORS['on_accent']};\n"
    "    background: {COLORS['primary_d']};\n"
    '}}\n'
    'QMenu::item:disabled {{\n'
    "    color: {COLORS['text_dim']};\n"
    '    background: transparent;\n'
    '}}\n'
    '\n'
    '/* ── 文件夹选择对话框 ─────────────────────────── */\n'
    'QFileDialog {{\n'
    "    background: {COLORS['bg_deep']};\n"
    '}}\n'
    'QFileDialog QLabel {{\n'
    "    color: {COLORS['text']};\n"
    '    background: transparent;\n'
    '}}\n'
    'QFileDialog QSplitter {{\n'
    "    background: {COLORS['bg_deep']};\n"
    '}}\n'
    'QFileDialog QLineEdit, QFileDialog QComboBox {{\n'
    "    color: {COLORS['text']};\n"
    "    background: {COLORS['bg_surface']};\n"
    "    border: 1px solid {COLORS['border']};\n"
    "    selection-background-color: {COLORS['primary']};\n"
    "    selection-color: {COLORS['on_accent']};\n"
    '}}\n'
    'QFileDialog QToolButton {{\n'
    "    color: {COLORS['text_muted']};\n"
    "    background: {COLORS['bg_base']};\n"
    '    border: 1px solid transparent;\n'
    '    border-radius: 4px;\n'
    '}}\n'
    'QFileDialog QToolButton:hover {{\n'
    "    color: {COLORS['primary_d']};\n"
    "    background: {COLORS['bg_elevated']};\n"
    "    border-color: {COLORS['border']};\n"
    '}}\n'
    'QFileDialog QToolButton:checked,\n'
    'QFileDialog QToolButton:pressed {{\n'
    "    color: {COLORS['on_accent']};\n"
    "    background: {COLORS['primary']};\n"
    "    border-color: {COLORS['primary_d']};\n"
    '}}\n'
    'QFileDialog QPushButton {{\n'
    "    color: {COLORS['text']};\n"
    "    background: {COLORS['bg_elevated']};\n"
    "    border: 1px solid {COLORS['border']};\n"
    '}}\n'
    'QFileDialog QPushButton:hover {{\n'
    "    color: {COLORS['primary_d']};\n"
    "    background: {COLORS['bg_hover']};\n"
    "    border-color: {COLORS['primary']};\n"
    '}}\n'
    'QFileDialog QTreeView, QFileDialog QListView {{\n'
    "    color: {COLORS['text']};\n"
    "    background: {COLORS['bg_surface']};\n"
    "    alternate-background-color: {COLORS['bg_base']};\n"
    "    border: 1px solid {COLORS['border']};\n"
    '    border-radius: 4px;\n'
    "    selection-background-color: {COLORS['primary']};\n"
    "    selection-color: {COLORS['on_accent']};\n"
    '}}\n'
    'QFileDialog QTreeView::item, QFileDialog QListView::item {{\n'
    "    color: {COLORS['text']};\n"
    '    background: transparent;\n'
    '    padding: 4px 6px;\n'
    '}}\n'
    'QFileDialog QTreeView::item:hover, QFileDialog QListView::item:hover {{\n'
    "    color: {COLORS['primary_d']};\n"
    "    background: {COLORS['bg_elevated']};\n"
    '}}\n'
    'QFileDialog QTreeView::item:selected, QFileDialog QListView::item:selected {{\n'
    "    color: {COLORS['on_accent']};\n"
    "    background: {COLORS['primary']};\n"
    '}}\n'
    'QFileDialog QHeaderView::section {{\n'
    "    color: {COLORS['text']};\n"
    "    background: {COLORS['bg_elevated']};\n"
    '    border: none;\n'
    "    border-right: 1px solid {COLORS['border_soft']};\n"
    "    border-bottom: 1px solid {COLORS['border']};\n"
    '    padding: 5px 8px;\n'
    '}}\n'
    '\n'
    '/* ── 列表 ─────────────────────────────────────── */\n'
    'QListWidget {{\n'
    '    {_font(10)}\n'
    "    color: {COLORS['text']};\n"
    "    background: {COLORS['bg_base']};\n"
    "    border: 1px solid {COLORS['border']};\n"
    '    border-radius: 6px;\n'
    '    padding: 4px;\n'
    '}}\n'
    'QListWidget:focus {{\n'
    "    border: 2px solid {COLORS['primary']};\n"
    '}}\n'
    'QListWidget::item {{\n'
    '    padding: 6px 8px;\n'
    '    border-radius: 4px;\n'
    '    margin: 1px 0;\n'
    '}}\n'
    'QListWidget::item:hover {{\n'
    "    background: {rgba(COLORS['primary'], 0.08)};\n"
    "    color: {COLORS['primary_d']};\n"
    '}}\n'
    'QListWidget::item:selected {{\n'
    "    background: {COLORS['primary_d']};\n"
    "    color: {COLORS['on_accent']};\n"
    '}}\n'
    '\n'
    '/* ── 文本编辑 ─────────────────────────────────── */\n'
    'QTextEdit, QPlainTextEdit {{\n'
    "    {_font(9, 'normal', mono=True)}\n"
    "    color: {COLORS['text']};\n"
    "    background: {COLORS['bg_base']};\n"
    "    border: 1px solid {COLORS['border']};\n"
    '    border-radius: 6px;\n'
    '    padding: 6px;\n'
    "    selection-background-color: {COLORS['primary_d']};\n"
    '}}\n'
    'QTextEdit:focus, QPlainTextEdit:focus {{\n'
    "    border: 2px solid {COLORS['primary']};\n"
    '}}\n'
    '\n'
    '/* ── 工作区页签 ───────────────────────────────── */\n'
    '/* QTabWidget / QTabBar 都要显式给背景：只写 ::tab 的话，最后一个页签**右侧\n'
    '   的空白区**由 QTabBar 自己绘制，会露出默认调色板（深色主题下看不出来，\n'
    '   浅色主题下就是一块突兀的黑条）。 */\n'
    'QTabWidget {{\n'
    '    background: transparent;\n'
    '}}\n'
    'QTabWidget::pane {{\n'
    "    background: {COLORS['bg_base']};\n"
    "    border: 1px solid {COLORS['border_soft']};\n"
    '    border-top: none;\n'
    '}}\n'
    'QTabWidget::tab-bar {{\n'
    '    alignment: left;\n'
    '    background: transparent;\n'
    '}}\n'
    'QTabBar {{\n'
    '    background: transparent;\n'
    '    /* 关掉 QTabBar 自己画的基线，否则会在页签下方留一条深色横线 */\n'
    '    qproperty-drawBase: 0;\n'
    '}}\n'
    'QTabBar::tab {{\n'
    "    {_font(9, '600')}\n"
    "    color: {COLORS['text_muted']};\n"
    "    background: {COLORS['bg_elevated']};\n"
    "    border: 1px solid {COLORS['border_soft']};\n"
    "    border-bottom: 1px solid {COLORS['border']};\n"
    '    padding: 7px 14px;\n'
    '    min-width: 78px;\n'
    '}}\n'
    'QTabBar::tab:selected {{\n'
    "    color: {COLORS['primary_d']};\n"
    "    background: {COLORS['bg_base']};\n"
    "    border-bottom-color: {COLORS['bg_base']};\n"
    '}}\n'
    'QTabBar::tab:hover:!selected {{\n'
    "    color: {COLORS['primary_d']};\n"
    "    background: {COLORS['bg_hover']};\n"
    '}}\n'
    'QTabBar:focus {{\n'
    "    border: 2px solid {COLORS['primary']};\n"
    '}}\n'
    '/* 页签过多时出现的滚动按钮，同样不能露出默认配色 */\n'
    'QTabBar QToolButton {{\n'
    "    background: {COLORS['bg_elevated']};\n"
    "    border: 1px solid {COLORS['border_soft']};\n"
    "    color: {COLORS['text']};\n"
    '}}\n'
    'QTabBar QToolButton:hover {{\n'
    "    background: {COLORS['bg_hover']};\n"
    '}}\n'
    '\n'
    '/* ── 进度条 ───────────────────────────────────── */\n'
    'QProgressBar {{\n'
    "    border: 1px solid {COLORS['border']};\n"
    '    border-radius: 6px;\n'
    "    background: {COLORS['bg_base']};\n"
    '    text-align: center;\n'
    "    color: {COLORS['text']};\n"
    '    height: 14px;\n'
    '}}\n'
    'QProgressBar::chunk {{\n'
    "    background: {COLORS['primary']};\n"
    '    border-radius: 5px;\n'
    '}}\n'
    '\n'
    '/* ── 状态栏 ───────────────────────────────────── */\n'
    'QStatusBar {{\n'
    "    background: {COLORS['bg_base']};\n"
    "    color: {COLORS['text_muted']};\n"
    "    border-top: 1px solid {COLORS['border']};\n"
    '    {_font(9)}\n'
    '    padding: 2px 8px;\n'
    '}}\n'
    'QStatusBar::item {{\n'
    '    border: none;\n'
    '}}\n'
    '\n'
    '/* ── 分割器 ───────────────────────────────────── */\n'
    'QSplitter::handle {{\n'
    "    background: {COLORS['border']};\n"
    '}}\n'
    'QSplitter::handle:horizontal {{ width: 2px; }}\n'
    'QSplitter::handle:vertical   {{ height: 2px; }}\n'
    'QSplitter::handle:hover {{\n'
    "    background: {COLORS['primary']};\n"
    '}}\n'
    'QSplitter#leftPanelSplitter::handle:vertical {{\n'
    '    background: qlineargradient(\n'
    '        x1: 0, y1: 0, x2: 0, y2: 1,\n'
    '        stop: 0 transparent,\n'
    '        stop: 0.39 transparent,\n'
    "        stop: 0.40 {COLORS['border']},\n"
    "        stop: 0.60 {COLORS['border']},\n"
    '        stop: 0.61 transparent,\n'
    '        stop: 1 transparent\n'
    '    );\n'
    '}}\n'
    'QSplitter#leftPanelSplitter::handle:vertical:hover {{\n'
    '    background: qlineargradient(\n'
    '        x1: 0, y1: 0, x2: 0, y2: 1,\n'
    '        stop: 0 transparent,\n'
    '        stop: 0.39 transparent,\n'
    "        stop: 0.40 {COLORS['primary']},\n"
    "        stop: 0.60 {COLORS['primary']},\n"
    '        stop: 0.61 transparent,\n'
    '        stop: 1 transparent\n'
    '    );\n'
    '}}\n'
    '\n'
    '/* ── 滚动区 ───────────────────────────────────── */\n'
    'QScrollArea {{\n'
    '    background: transparent;\n'
    '    border: none;\n'
    '}}\n'
    'QWidget[role="resultContainer"] {{\n'
    "    background: {COLORS['bg_base']};\n"
    '}}\n'
    'QScrollBar:vertical {{\n'
    '    background: transparent;\n'
    '    width: 8px;\n'
    '    margin: 0;\n'
    '}}\n'
    'QScrollBar::handle:vertical {{\n'
    "    background: {COLORS['border']};\n"
    '    border-radius: 4px;\n'
    '    min-height: 24px;\n'
    '}}\n'
    'QScrollBar::handle:vertical:hover {{\n'
    "    background: {COLORS['primary']};\n"
    '}}\n'
    'QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{\n'
    '    height: 0;\n'
    '}}\n'
    'QScrollBar:horizontal {{\n'
    '    background: transparent;\n'
    '    height: 8px;\n'
    '    margin: 0;\n'
    '}}\n'
    'QScrollBar::handle:horizontal {{\n'
    "    background: {COLORS['border']};\n"
    '    border-radius: 4px;\n'
    '    min-width: 24px;\n'
    '}}\n'
    'QScrollBar::handle:horizontal:hover {{\n'
    "    background: {COLORS['primary']};\n"
    '}}\n'
    'QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{\n'
    '    width: 0;\n'
    '}}\n'
    '\n'
    '/* ── 工具栏 ───────────────────────────────────── */\n'
    'QToolBar {{\n'
    "    background: {COLORS['bg_base']};\n"
    "    border: 1px solid {COLORS['border_soft']};\n"
    '    border-radius: 4px;\n'
    '    padding: 3px;\n'
    '    spacing: 2px;\n'
    '}}\n'
    'QToolButton {{\n'
    '    {_font(9)}\n'
    "    color: {COLORS['text_muted']};\n"
    '    background: transparent;\n'
    '    border: 1px solid transparent;\n'
    '    border-radius: 4px;\n'
    '    padding: 5px 8px;\n'
    '    margin: 1px;\n'
    '}}\n'
    'QToolButton:hover {{\n'
    "    background: {rgba(COLORS['primary'], 0.10)};\n"
    "    border-color: {COLORS['primary']};\n"
    "    color: {COLORS['primary_d']};\n"
    '}}\n'
    'QToolButton:pressed {{\n'
    "    background: {COLORS['primary_d']};\n"
    "    color: {COLORS['on_accent']};\n"
    '}}\n'
    'QToolButton:focus {{\n'
    "    border: 2px solid {COLORS['primary']};\n"
    '}}\n'
    '\n'
    '/* ── 参数分区 ─────────────────────────────────── */\n'
    'QFrame[role="parameterSection"] {{\n'
    "    background: {COLORS['bg_base']};\n"
    "    border: 1px solid {COLORS['border_soft']};\n"
    '    border-radius: 8px;\n'
    '}}\n'
    'QToolButton[role="sectionToggle"] {{\n'
    "    {_font(10, 'bold')}\n"
    "    color: {COLORS['text']};\n"
    '    background: transparent;\n'
    '    border: none;\n'
    '    border-radius: 6px;\n'
    '    padding: 8px 10px;\n'
    '    text-align: left;\n'
    '}}\n'
    'QToolButton[role="sectionToggle"]:hover {{\n'
    "    color: {COLORS['primary_d']};\n"
    "    background: {COLORS['bg_elevated']};\n"
    '    border: none;\n'
    '}}\n'
    'QToolButton[role="sectionToggle"]:focus {{\n'
    "    border: 2px solid {COLORS['primary']};\n"
    '}}\n'
    '\n'
    '/* ── 表单标签 ─────────────────────────────────── */\n'
    'QFormLayout {{\n'
    '    {_font(10)}\n'
    '}}\n'
    '\n'
    '/* ── 消息框 ───────────────────────────────────── */\n'
    'QMessageBox {{\n'
    "    background: {COLORS['bg_surface']};\n"
    '    {_font(10)}\n'
    '}}\n'
    'QMessageBox QLabel {{\n'
    "    color: {COLORS['text']};\n"
    '    {_font(10)}\n'
    '}}\n'
    'QMessageBox QPushButton {{\n'
    '    min-width: 70px;\n'
    '}}\n'
    '\n'
    '/* ── 滚动条覆盖 ───────────────────────────────── */\n'
    'QToolTip {{\n'
    '    {_font(9)}\n'
    "    color: {COLORS['text']};\n"
    "    background: {COLORS['bg_surface']};\n"
    "    border: 1px solid {COLORS['primary']};\n"
    '    border-radius: 4px;\n'
    '    padding: 4px 8px;\n'
    '}}\n'
    '\n'
    '/* ── 启动大按钮 (主行动点) ────────────────────── */\n'
    'QPushButton[role="hero"] {{\n'
    "    color: {COLORS['on_accent']};\n"
    "    background: {COLORS['primary']};\n"
    "    border: 1px solid {COLORS['primary_d']};\n"
    '    border-radius: 4px;\n'
    "    {_font(12, 'bold')}\n"
    '    letter-spacing: 2px;\n'
    '    padding: 10px 24px;\n'
    '}}\n'
    'QPushButton[role="hero"]:hover {{\n'
    "    color: {COLORS['on_accent']};\n"
    "    background: {COLORS['primary_d']};\n"
    "    border: 1px solid {COLORS['primary_d']};\n"
    '}}\n'
    'QPushButton[role="hero"]:pressed {{\n'
    "    color: {COLORS['on_accent']};\n"
    "    background: {COLORS['primary_d']};\n"
    '    padding-top: 11px;\n'
    '    padding-bottom: 9px;\n'
    '}}\n'
    'QPushButton[role="hero"]:disabled {{\n'
    "    color: {COLORS['text_dim']};\n"
    "    background: {COLORS['bg_surface']};\n"
    "    border: 1px solid {COLORS['border_soft']};\n"
    '    letter-spacing: 2px;\n'
    '}}\n'
    '\n'
    '/* 角色色不得覆盖禁用态，避免停止、保存等按钮看起来仍可操作。 */\n'
    'QPushButton[role="primary"]:disabled,\n'
    'QPushButton[role="success"]:disabled,\n'
    'QPushButton[role="danger"]:disabled,\n'
    'QPushButton[role="ghost"]:disabled,\n'
    'QPushButton[role="model"]:disabled,\n'
    'QPushButton[role="model"][active="true"]:disabled {{\n'
    "    color: {COLORS['text_muted']};\n"
    "    background: {COLORS['bg_surface']};\n"
    "    border: 1px solid {COLORS['border_soft']};\n"
    '}}\n'
    '\n'
    '/* ── 动态属性样式（取代内联 setStyleSheet，见 C1） ── */\n'
    'QLabel[role="muted"] {{\n'
    '    {_font(9)}\n'
    "    color: {COLORS['text_muted']};\n"
    '    background: transparent;\n'
    '}}\n'
    'QLabel[role="mono"] {{\n'
    "    {_font(10, 'bold', mono=True)}\n"
    "    color: {COLORS['primary_d']};\n"
    '    background: transparent;\n'
    '}}\n'
    'QLabel[role="warning"] {{\n'
    "    {_font(9, '600')}\n"
    "    color: {COLORS['warning']};\n"
    '    background: transparent;\n'
    '}}\n'
    'QLabel[role="dangerText"] {{\n'
    "    {_font(9, '600')}\n"
    "    color: {COLORS['danger']};\n"
    '    background: transparent;\n'
    '}}\n'
    'QLabel[role="successText"] {{\n'
    "    {_font(9, '600')}\n"
    "    color: {COLORS['success_d']};\n"
    '    background: transparent;\n'
    '}}\n'
    '/* 状态色必须带非颜色冗余（图标 / 文字前缀），见 U6 */\n'
    'QTableView {{\n'
    '    {_font(9)}\n'
    "    color: {COLORS['text']};\n"
    "    background: {COLORS['bg_surface']};\n"
    "    alternate-background-color: {COLORS['bg_base']};\n"
    "    border: 1px solid {COLORS['border']};\n"
    '    border-radius: 4px;\n'
    "    gridline-color: {COLORS['border_soft']};\n"
    "    selection-background-color: {COLORS['primary']};\n"
    "    selection-color: {COLORS['on_accent']};\n"
    '}}\n'
    'QTableView::item {{\n'
    '    /* U1：结果面板较窄，内边距压到最小以便更多列可见 */\n'
    '    padding: 2px 5px;\n'
    '}}\n'
    'QTableView QHeaderView::section {{\n'
    "    {_font(9, 'bold')}\n"
    "    color: {COLORS['text']};\n"
    "    background: {COLORS['bg_elevated']};\n"
    '    border: none;\n'
    "    border-right: 1px solid {COLORS['border_soft']};\n"
    "    border-bottom: 1px solid {COLORS['border']};\n"
    '    padding: 5px 6px;\n'
    '}}\n'
    'QTableView QTableCornerButton::section {{\n'
    "    background: {COLORS['bg_elevated']};\n"
    '    border: none;\n'
    '}}\n'
    '"""\n'
    '\n'
    '\n'
    'def theme_tokens(mode=None):\n'
    '    """取某套主题 token（默认当前生效的主题）。"""\n'
    '    return get_theme(mode or _current_mode)\n'
    '\n'
    '\n'
    'def apply_theme(app, mode=None):\n'
    '    """应用全局主题样式到 QApplication；``mode`` 为 ``\'light\'`` 或 ``\'dark\'``。"""\n'
    '    global _current_mode, COLORS\n'
    '    if mode is not None:\n'
    '        _current_mode = str(mode).strip().lower()\n'
    '    tokens = get_theme(_current_mode)\n'
    '    COLORS = tokens\n'
    '    app.setStyleSheet(build_qss(tokens))\n'
    '    # 让 Qt 原生控件（对话框、菜单、滚动条）也跟随明暗\n'
    '    try:\n'
    '        from PyQt6.QtCore import Qt\n'
    '        from PyQt6.QtWidgets import QApplication\n'
    '        style_hints = QApplication.styleHints()\n'
    "        scheme = (Qt.ColorScheme.Dark if _current_mode == 'dark'\n"
    '                  else Qt.ColorScheme.Light)\n'
    '        style_hints.setColorScheme(scheme)\n'
    '    except (ImportError, AttributeError):\n'
    '        pass\n'
    '    return tokens\n'
    '\n'
    '\n'
    'def current_theme_mode():\n'
    '    return _current_mode\n'
    '\n'
    '\n'
    '#: 兼容旧引用：模块级 ``GLOBAL_QSS`` 现在是默认主题渲染出的静态样式表。\n'
    'GLOBAL_QSS = build_qss(COLORS)\n'
)

# ---- ui/animated_button.py ----
_MODULE_SOURCES['ui.animated_button'] = (
    '"""\n'
    'AnimatedButton - 带水墨按压反馈的自定义 QPushButton\n'
    '效果：\n'
    '1. 墨晕（ink bloom）：从落点自然扩散，短促且不发光\n'
    '2. 压印（wash）：按下瞬间产生低透明度墨色覆盖\n'
    '3. 激活态：模型按钮的激活高亮\n'
    '"""\n'
    'import sys\n'
    'import time\n'
    'from PyQt6.QtCore import (\n'
    '    Qt, QPropertyAnimation, QEasingCurve, QPoint, QPointF, QSize,\n'
    '    QTimer, pyqtProperty\n'
    ')\n'
    'from PyQt6.QtGui import (\n'
    '    QPainter, QColor, QBrush, QPen, QRadialGradient\n'
    ')\n'
    'from PyQt6.QtWidgets import QPushButton\n'
    '\n'
    'from theme_tokens import get_theme\n'
    '\n'
    '\n'
    '# 角色对应颜色（墨色、浅色、深色）——取值全部来自 theme_tokens。\n'
    '# 键仍是角色名，这样构造函数里的 `role in _ROLE_COLORS` 判断保持原样；\n'
    '# 值为 ``(token, token, token)`` 三元组：主墨色 / 压印色 / 深色。\n'
    '_ROLE_COLORS = {\n'
    "    'default':  ('primary', 'primary_l', 'primary_d'),\n"
    "    'primary':  ('primary', 'primary_l', 'primary_d'),\n"
    "    'success':  ('success', 'success_l', 'success_d'),\n"
    "    'danger':   ('danger', 'danger_d', 'danger_d'),\n"
    "    'warning':  ('warning', 'warning', 'warning'),\n"
    "    'ghost':    ('text_dim', 'text_muted', 'text'),\n"
    "    'model':    ('primary', 'primary_l', 'primary_d'),\n"
    "    'hero':     ('primary', 'primary_l', 'primary_d'),\n"
    '}\n'
    '\n'
    '#: 当前主题模式，仅在拿不到 ``ui.style`` 时兜底。\n'
    "_current_theme_mode = 'light'\n"
    '\n'
    '\n'
    'def set_button_theme(mode):\n'
    '    """设置按钮动画跟随的主题（``\'light\'`` / ``\'dark\'``）。"""\n'
    '    global _current_theme_mode\n'
    '    _current_theme_mode = str(mode).strip().lower()\n'
    '\n'
    '\n'
    'def _tokens():\n'
    '    """当前主题 token：优先问**已加载**的 ``ui.style``。\n'
    '\n'
    '    用 ``sys.modules`` 而不是 ``import ui.style``：``ui/__init__.py`` 会连带\n'
    '    导入 main_window / torch，而按钮可能在重库加载完成前就被创建；本模块\n'
    '    也因此绝不反向被 ``ui.style`` 导入，不存在循环导入。\n'
    '    """\n'
    "    style = sys.modules.get('ui.style')\n"
    '    if style is not None:\n'
    '        try:\n'
    '            return style.theme_tokens()\n'
    '        except (AttributeError, KeyError, ImportError):\n'
    '            # ui.style 已加载但没有 theme_tokens（例如版本不匹配）时回退\n'
    '            return get_theme(_current_theme_mode)\n'
    '    return get_theme(_current_theme_mode)\n'
    '\n'
    '\n'
    'def _role_color(role, index):\n'
    '    """取某角色的第 ``index`` 个 token 对应的 ``\'#RRGGBB\'``。"""\n'
    '    return _tokens()[_ROLE_COLORS[role][index]]\n'
    '\n'
    '\n'
    '# 墨晕与压印保持短促，避免持续动效干扰专业操作。\n'
    '_INK_BLOOM_DURATION = 360\n'
    '_WASH_DURATION = 180\n'
    '_MAX_INK_BLOOMS = 2\n'
    '\n'
    '\n'
    'class AnimatedButton(QPushButton):\n'
    '    """带墨晕、压印和激活态的 QPushButton。"""\n'
    '\n'
    "    def __init__(self, text='', role='default', parent=None):\n"
    '        super().__init__(text, parent)\n'
    "        self._role = role if role in _ROLE_COLORS else 'default'\n"
    '        self._ink_blooms = []  # 每项: [x, y, start_ms, max_r]\n'
    '        self._pressed_inside = False\n'
    '        self._flash_value = 0.0  # 0~1\n'
    '        self._active = False  # 模型选择激活态\n'
    '\n'
    "        self.setProperty('role', self._role)\n"
    '        self.setCursor(Qt.CursorShape.PointingHandCursor)\n'
    '\n'
    '        # 约 60fps 重绘定时器（仅在点击反馈期间运行）\n'
    '        self._tick_timer = QTimer(self)\n'
    '        self._tick_timer.setInterval(16)\n'
    '        self._tick_timer.timeout.connect(self._on_tick)\n'
    '\n'
    '        # 压印属性动画\n'
    "        self._flash_anim = QPropertyAnimation(self, b'flashValue', self)\n"
    '        self._flash_anim.setDuration(_WASH_DURATION)\n'
    '        self._flash_anim.setEasingCurve(QEasingCurve.Type.OutCubic)\n'
    '        self._flash_anim.finished.connect(lambda: self._tick_timer.stop())\n'
    '\n'
    '    # ── Qt 属性（供动画使用） ───────────────────────\n'
    '    def getFlashValue(self):\n'
    '        return self._flash_value\n'
    '\n'
    '    def setFlashValue(self, v):\n'
    '        self._flash_value = v\n'
    '        self.update()\n'
    '\n'
    '    flashValue = pyqtProperty(float, getFlashValue, setFlashValue)\n'
    '\n'
    '    # ── 模型激活态切换 ──────────────────────────────\n'
    '    def set_active(self, active: bool):\n'
    '        self._active = active\n'
    "        self.setProperty('active', 'true' if active else 'false')\n"
    '        self.style().unpolish(self)\n'
    '        self.style().polish(self)\n'
    '        self.update()\n'
    '\n'
    '    # ── 鼠标事件 ─────────────────────────────────────\n'
    '    def mousePressEvent(self, e):\n'
    '        if e.button() == Qt.MouseButton.LeftButton and self.isEnabled():\n'
    '            self._pressed_inside = True\n'
    '            self._start_ink_bloom(e.position().toPoint())\n'
    '            self._trigger_flash()\n'
    '        super().mousePressEvent(e)\n'
    '\n'
    '    def mouseReleaseEvent(self, e):\n'
    '        self._pressed_inside = False\n'
    '        super().mouseReleaseEvent(e)\n'
    '\n'
    '    # ── 闪光 ─────────────────────────────────────────\n'
    '    def _trigger_flash(self):\n'
    '        self._flash_anim.stop()\n'
    '        self._flash_anim.setStartValue(0.0)\n'
    '        self._flash_anim.setKeyValueAt(0.25, 1.0)\n'
    '        self._flash_anim.setEndValue(0.0)\n'
    '        self._flash_anim.start()\n'
    '        # 启动重绘定时器驱动波纹\n'
    '        if not self._tick_timer.isActive():\n'
    '            self._tick_timer.start()\n'
    '\n'
    '    # ── 墨晕 ─────────────────────────────────────────\n'
    '    def _start_ink_bloom(self, pos: QPoint):\n'
    '        max_r = float(max(self.width(), self.height()) * 0.72)\n'
    '        self._ink_blooms.append([float(pos.x()), float(pos.y()),\n'
    '                                 time.time() * 1000.0, max_r])\n'
    '        while len(self._ink_blooms) > _MAX_INK_BLOOMS:\n'
    '            self._ink_blooms.pop(0)\n'
    '        if not self._tick_timer.isActive():\n'
    '            self._tick_timer.start()\n'
    '        self.update()\n'
    '\n'
    '    def _on_tick(self):\n'
    '        if not self._ink_blooms and self._flash_value <= 0.001:\n'
    '            self._tick_timer.stop()\n'
    '            self.update()\n'
    '            return\n'
    '        # 清理过期的墨晕\n'
    '        now = time.time() * 1000.0\n'
    '        self._ink_blooms = [r for r in self._ink_blooms\n'
    '                            if (now - r[2]) < _INK_BLOOM_DURATION]\n'
    '        self.update()\n'
    '\n'
    '    # ── 自定义绘制：叠加墨晕与压印 ───────────────────\n'
    '    def paintEvent(self, e):\n'
    '        super().paintEvent(e)\n'
    '        if not self._ink_blooms and self._flash_value <= 0.001:\n'
    '            return\n'
    '\n'
    '        p = QPainter(self)\n'
    '        p.setRenderHint(QPainter.RenderHint.Antialiasing)\n'
    '        p.setClipRect(self.rect())\n'
    '\n'
    '        # 低透明度压印，模拟墨色落在宣纸上的轻微洇染。\n'
    '        if self._flash_value > 0.001:\n'
    '            c = QColor(_role_color(self._role, 1))\n'
    '            c.setAlpha(int(48 * self._flash_value))\n'
    '            grad = QRadialGradient(\n'
    '                QPointF(self.rect().center()),\n'
    '                max(self.width(), self.height()) * 0.6\n'
    '            )\n'
    '            grad.setColorAt(0.0, c)\n'
    '            grad.setColorAt(1.0, QColor(c.red(), c.green(), c.blue(), 0))\n'
    '            p.fillRect(self.rect(), QBrush(grad))\n'
    '\n'
    '        # 墨晕没有霓虹描边，只保留柔和的中心与细薄外缘。\n'
    '        now = time.time() * 1000.0\n'
    '        for rx, ry, start_ms, max_r in self._ink_blooms:\n'
    '            progress = (now - start_ms) / _INK_BLOOM_DURATION\n'
    '            if progress >= 1.0 or progress < 0:\n'
    '                continue\n'
    '            # 缓动：OutCubic\n'
    '            eased = 1.0 - (1.0 - progress) ** 3\n'
    '            radius = eased * max_r\n'
    '            opacity = 1.0 - progress\n'
    '\n'
    '            main_hex = _role_color(self._role, 0)\n'
    '\n'
    '            # 填充\n'
    '            c_fill = QColor(main_hex)\n'
    '            c_fill.setAlpha(int(34 * opacity))\n'
    '            p.setBrush(QBrush(c_fill))\n'
    '            p.setPen(Qt.PenStyle.NoPen)\n'
    '            p.drawEllipse(QPointF(rx, ry), radius, radius)\n'
    '\n'
    '            # 描边\n'
    '            c_edge = QColor(main_hex)\n'
    '            c_edge.setAlpha(int(80 * opacity))\n'
    '            pen = QPen(c_edge)\n'
    '            pen.setWidthF(1.0)\n'
    '            p.setPen(pen)\n'
    '            p.setBrush(Qt.BrushStyle.NoBrush)\n'
    '            p.drawEllipse(QPointF(rx, ry), radius, radius)\n'
    '\n'
    '        p.end()\n'
    '\n'
    '\n'
    "def make_button(text, role='default', parent=None):\n"
    '    """工厂函数：创建带动画效果的按钮"""\n'
    '    return AnimatedButton(text, role, parent)\n'
)

# ---- ui/result_model.py ----
_MODULE_SOURCES['ui.result_model'] = (
    '"""结果表的数据模型（U1）。\n'
    '\n'
    '旧实现的「结果表」其实是 N 张卡片竖排：不能排序、不好对比、5 段指标代码\n'
    '复制粘贴、数值用 ``.6f`` 打印、颜色内联写死。这里换成\n'
    '``QTableView + QAbstractTableModel + QSortFilterProxyModel``：\n'
    '\n'
    '- 点列头排序（用 ``UserRole`` 里的**原始值**排序，而不是格式化后的字符串）；\n'
    '- 列包含滚动起点的 RMSE / MAE / 技能分 / 预测 RUL / 真实 RUL / RUL 误差；\n'
    '- 末尾一行**汇总**：跨电池 mean ± std（n = 电池数）+ bootstrap 区间；\n'
    '- 技能分 < 0.05 的单元格用 warning 色并加 ⚠（A3）；\n'
    '- 数值保留 4 位小数并带单位。\n'
    '"""\n'
    '\n'
    'import numpy as np\n'
    'from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt\n'
    'from PyQt6.QtGui import QBrush, QColor, QFont\n'
    '\n'
    '\n'
    '#: (表头, 键, 数值格式)；``key`` 为 None 表示该列由 getter 计算\n'
    '#:\n'
    '#: 表头刻意用短名：结果面板只有约 300–400 px 宽，长表头会把数值挤出可视区。\n'
    '#: 完整含义写在列的工具提示里（见 :meth:`ResultTableModel.headerData`）。\n'
    'COLUMNS = (\n'
    "    ('电池', 'name', '{}'),\n"
    "    ('RMSE', 'rmse', '{:.4f}'),\n"
    "    ('MAE', 'mae', '{:.4f}'),\n"
    "    ('技能分', 'skill', '{:+.3f}'),\n"
    "    ('预测RUL', 'pred_rul', '{}'),\n"
    "    ('真实RUL', 'true_rul', '{}'),\n"
    "    ('RUL误差', 'rul_err', '{:+d}'),\n"
    "    ('状态', 'status', '{}'),\n"
    ')\n'
    '\n'
    '#: 每列的完整说明（工具提示）\n'
    'COLUMN_HELP = {\n'
    "    'name': '电池名称',\n"
    "    'rmse': '滚动预测起点上的递归预测 RMSE（Ah）',\n"
    "    'mae': '滚动预测起点上的递归预测 MAE（Ah）',\n"
    "    'skill': '技能分 = 1 − RMSE模型 / RMSE平推；< 0.05 表示未超越平推基线',\n"
    "    'pred_rul': '模型预测的剩余寿命（循环数）',\n"
    "    'true_rul': '真实剩余寿命（循环数）',\n"
    "    'rul_err': 'RUL 误差 = 预测 − 真实；正值表示预测偏保守',\n"
    "    'status': '失效检出状态：EOL 是否落在预测期内',\n"
    '}\n'
    '\n'
    '#: 各列宽度（px）。结果面板默认约 480–560 px，用 `ResizeToContents` 会被\n'
    '#: 汇总行的长文本撑到 1200 px 以上，因此这里显式给宽度，超出部分省略号 + 提示。\n'
    'COLUMN_WIDTHS = {\n'
    "    'name': 86, 'rmse': 62, 'mae': 62, 'skill': 66,\n"
    "    'pred_rul': 62, 'true_rul': 62, 'rul_err': 66, 'status': 74,\n"
    '}\n'
    '\n'
    '#: 技能分低于此值时提示「模型未超越持久性基线」（A3）\n'
    'SKILL_WARNING_THRESHOLD = 0.05\n'
    '\n'
    '#: 状态列的短标签（含图标，满足「状态不能只靠颜色」的要求）；\n'
    '#: 完整含义见 :data:`STATUS_HELP`，通过单元格工具提示给出。\n'
    'STATUS_LABELS = {\n'
    "    'ok': '✓ 检出',\n"
    "    'pred_censored': '⚠ 未检出',\n"
    "    'true_censored': '✓ 未失效',\n"
    "    'unavailable': '— 不可用',\n"
    "    'mixed': '— 种子不一致',\n"
    '}\n'
    '\n'
    '#: 状态列的完整解释（工具提示 / 无障碍文本）\n'
    'STATUS_HELP = {\n'
    "    'ok': '预测期内已检出失效，RUL 误差可计算',\n"
    "    'pred_censored': '模型预测观测期内不会失效，但真实电池已失效',\n"
    "    'true_censored': '真实电池在观测期内未失效（右删失）',\n"
    "    'unavailable': '该指标当前不可用',\n"
    "    'mixed': '多种子之间状态不一致',\n"
    '}\n'
    '\n'
    '\n'
    'def format_optional(value, fmt):\n'
    '    """按格式渲染；None / 非有限值显示为 ``—``。"""\n'
    '    if value is None:\n'
    "        return '—'\n"
    '    if isinstance(value, float) and not np.isfinite(value):\n'
    "        return '—'\n"
    '    try:\n'
    '        return fmt.format(value)\n'
    '    except (ValueError, TypeError):\n'
    '        return str(value)\n'
    '\n'
    '\n'
    'def rows_from_details(detail_list, start_frac=None, baselines=None):\n'
    '    """把 ``detail`` 列表转成结果表行。\n'
    '\n'
    '    ``start_frac`` 指定看哪个滚动起点（默认用每块电池的主起点）。\n'
    "    ``baselines`` 是 ``{基线名: {'rmse': ...}}``，会作为额外的行插在后面。\n"
    '    """\n'
    '    rows = []\n'
    '    for detail in detail_list or []:\n'
    '        row = _row_from_detail(detail, start_frac)\n'
    '        if row is not None:\n'
    '            rows.append(row)\n'
    '    for name, entry in (baselines or {}).items():\n'
    '        rows.append({\n'
    "            'name': name,\n"
    "            'is_baseline': True,\n"
    "            'rmse': entry.get('rmse'),\n"
    "            'mae': entry.get('mae'),\n"
    "            'skill': None,\n"
    "            'pred_rul': None,\n"
    "            'true_rul': None,\n"
    "            'rul_err': None,\n"
    "            'status': 'baseline',\n"
    "            'status_label': f'基线 · {name}',\n"
    '        })\n'
    '    return rows\n'
    '\n'
    '\n'
    'def _row_from_detail(detail, start_frac):\n'
    '    if not isinstance(detail, dict):\n'
    '        return None\n'
    "    battery = detail.get('battery', '?')\n"
    '    row = {\n'
    "        'name': battery,\n"
    "        'rmse': detail.get('rmse'),\n"
    "        'mae': detail.get('mae'),\n"
    "        'skill': detail.get('rmse_skill_vs_persistence'),\n"
    "        'pred_rul': None,\n"
    "        'true_rul': None,\n"
    "        'rul_err': None,\n"
    "        'status': detail.get('re_status', 'unavailable'),\n"
    '    }\n'
    '\n'
    '    # 优先用滚动起点里对应那一行\n'
    '    target = start_frac if start_frac is not None else detail.get(\n'
    "        'primary_start_frac', 0.5)\n"
    "    rolling = detail.get('rolling') or {}\n"
    "    per_start = rolling.get('per_start') or {}\n"
    '    entry = None\n'
    '    if per_start:\n'
    '        if target is not None:\n'
    '            for frac, value in per_start.items():\n'
    '                if abs(float(frac) - float(target)) < 1e-9:\n'
    '                    entry = value\n'
    '                    break\n'
    '        if entry is None:\n'
    '            entry = next(iter(per_start.values()))\n'
    '    if entry:\n'
    "        row['rmse'] = entry.get('rmse', row['rmse'])\n"
    "        row['mae'] = entry.get('mae', row['mae'])\n"
    "        if entry.get('skill') is not None:\n"
    "            row['skill'] = entry['skill']\n"
    "        row['mean_abs_rul_err'] = entry.get('mean_abs_rul_err')\n"
    "        row['detected'] = entry.get('detected')\n"
    "        row['needs_detection'] = entry.get('needs_detection')\n"
    "        if entry.get('detected'):\n"
    "            row['status'] = 'ok'\n"
    "        elif entry.get('needs_detection'):\n"
    "            row['status'] = 'pred_censored'\n"
    '        else:\n'
    "            row['status'] = 'true_censored'\n"
    '\n'
    '    # RUL 明细：优先取该起点的原始行\n'
    "    rows = detail.get('rolling_rows') or []\n"
    '    picked = None\n'
    '    for item in rows:\n'
    '        if target is not None and abs(\n'
    "                float(item.get('start_frac', -1)) - float(target)) < 1e-9:\n"
    '            picked = item\n'
    '            break\n'
    '    if picked is None and rows:\n'
    '        picked = rows[0]\n'
    '    if picked:\n'
    "        row['true_rul'] = picked.get('true_rul')\n"
    "        row['pred_rul'] = (\n"
    "            None if picked.get('pred_rul') is None\n"
    "            else int(round(picked['pred_rul'])))\n"
    "        row['rul_err'] = (\n"
    "            None if picked.get('rul_err') is None\n"
    "            else int(round(picked['rul_err'])))\n"
    "        if picked.get('status'):\n"
    "            row['status'] = picked['status']\n"
    "    if row.get('rul_err') is None:\n"
    "        row['rul_err'] = detail.get('rul_err')\n"
    '\n'
    "    row['status_label'] = STATUS_LABELS.get(\n"
    "        row['status'], row.get('status') or '—')\n"
    "    row['alpha'] = detail.get('persistence_blend')\n"
    "    row['n_seeds'] = detail.get('n_seeds')\n"
    "    row['cycles'] = detail.get('cycles')\n"
    '    return row\n'
    '\n'
    '\n'
    'def summary_row(rows):\n'
    '    """跨电池汇总：mean ± std（n = 电池数）。基线行不参与。"""\n'
    "    values = [row for row in rows if not row.get('is_baseline')]\n"
    '    if not values:\n'
    '        return None\n'
    '\n'
    '    def stats(key):\n'
    '        items = [\n'
    '            float(row[key]) for row in values\n'
    '            if row.get(key) is not None\n'
    '            and isinstance(row[key], (int, float))\n'
    '            and np.isfinite(row[key])\n'
    '        ]\n'
    '        if not items:\n'
    '            return None, None\n'
    '        return float(np.mean(items)), (\n'
    '            float(np.std(items, ddof=1)) if len(items) > 1 else 0.0)\n'
    '\n'
    "    rmse_mean, rmse_std = stats('rmse')\n"
    "    mae_mean, mae_std = stats('mae')\n"
    "    skill_mean, skill_std = stats('skill')\n"
    "    rul_mean, rul_std = stats('rul_err')\n"
    "    detected = sum(1 for row in values if row.get('status') == 'ok')\n"
    '    needs = sum(1 for row in values\n'
    "                if row.get('status') in ('ok', 'pred_censored'))\n"
    '    return {\n'
    '        # 「电池」列只有 86px，长标签会被省略号截断；完整说明放在工具提示里\n'
    "        'name': f'汇总 n={len(values)}',\n"
    "        'n_batteries': len(values),\n"
    "        'is_summary': True,\n"
    "        'rmse': rmse_mean,\n"
    "        'rmse_std': rmse_std,\n"
    "        'mae': mae_mean,\n"
    "        'mae_std': mae_std,\n"
    "        'skill': skill_mean,\n"
    "        'skill_std': skill_std,\n"
    "        'pred_rul': None,\n"
    "        'true_rul': None,\n"
    "        'rul_err': rul_mean,\n"
    "        'rul_err_std': rul_std,\n"
    "        'status': 'summary',\n"
    "        'status_label': f'检出 {detected}/{needs}' if needs else '—',\n"
    '    }\n'
    '\n'
    '\n'
    "def bootstrap_summary(rows, key='rmse', n_boot=2000, level=0.95, seed=0):\n"
    '    """对「每块电池一个数」的指标做 bootstrap（A9）。"""\n'
    '    from core.evaluate import bootstrap_ci\n'
    '\n'
    '    values = [\n'
    '        row.get(key) for row in rows\n'
    "        if not row.get('is_baseline') and not row.get('is_summary')\n"
    '    ]\n'
    '    return bootstrap_ci(values, n_boot=n_boot, level=level, seed=seed)\n'
    '\n'
    '\n'
    'class ResultTableModel(QAbstractTableModel):\n'
    '    """结果表模型；数值排序走 ``UserRole`` 里的原始值。"""\n'
    '\n'
    '    def __init__(self, rows=None, tokens=None, parent=None):\n'
    '        super().__init__(parent)\n'
    '        self._rows = list(rows or [])\n'
    '        self._tokens = tokens or {}\n'
    '        self._show_summary = True\n'
    '\n'
    '    # ── Qt 接口 ──────────────────────────────────────────────\n'
    '    def rowCount(self, parent=QModelIndex()):\n'
    '        if parent.isValid():\n'
    '            return 0\n'
    '        return len(self._display_rows())\n'
    '\n'
    '    def columnCount(self, parent=QModelIndex()):\n'
    '        if parent.isValid():\n'
    '            return 0\n'
    '        return len(COLUMNS)\n'
    '\n'
    '    def headerData(self, section, orientation,\n'
    '                   role=Qt.ItemDataRole.DisplayRole):\n'
    '        if not (0 <= section < len(COLUMNS)):\n'
    '            return None\n'
    '        header, key, _ = COLUMNS[section]\n'
    '        if orientation == Qt.Orientation.Horizontal:\n'
    '            if role == Qt.ItemDataRole.DisplayRole:\n'
    '                return header\n'
    '            if role == Qt.ItemDataRole.ToolTipRole:\n'
    '                return COLUMN_HELP.get(key, header)\n'
    '        return None\n'
    '\n'
    '    def data(self, index, role=Qt.ItemDataRole.DisplayRole):\n'
    '        if not index.isValid():\n'
    '            return None\n'
    '        rows = self._display_rows()\n'
    '        if not (0 <= index.row() < len(rows)):\n'
    '            return None\n'
    '        row = rows[index.row()]\n'
    '        _, key, fmt = COLUMNS[index.column()]\n'
    '        value = self._cell_value(row, key)\n'
    '\n'
    '        if role == Qt.ItemDataRole.DisplayRole:\n'
    '            return self._display_text(row, key, value, fmt)\n'
    '        if role == Qt.ItemDataRole.UserRole:\n'
    '            # 排序用的原始值；缺失值排到最后\n'
    '            if value is None or (isinstance(value, float)\n'
    '                                 and not np.isfinite(value)):\n'
    "                return float('-inf')\n"
    '            return value\n'
    '        if role == Qt.ItemDataRole.TextAlignmentRole:\n'
    '            if index.column() == 0:\n'
    '                return int(Qt.AlignmentFlag.AlignLeft\n'
    '                           | Qt.AlignmentFlag.AlignVCenter)\n'
    '            return int(Qt.AlignmentFlag.AlignRight\n'
    '                       | Qt.AlignmentFlag.AlignVCenter)\n'
    '        if role == Qt.ItemDataRole.ForegroundRole:\n'
    '            return self._foreground(row, key, value)\n'
    '        if role == Qt.ItemDataRole.FontRole:\n'
    "            if row.get('is_summary') or row.get('is_baseline'):\n"
    '                font = QFont()\n'
    '                font.setBold(True)\n'
    '                return font\n'
    '            return None\n'
    '        if role == Qt.ItemDataRole.ToolTipRole:\n'
    '            return self._tooltip(row)\n'
    '        return None\n'
    '\n'
    '    # ── 数据管理 ────────────────────────────────────────────\n'
    '    def set_rows(self, rows):\n'
    '        self.beginResetModel()\n'
    '        self._rows = list(rows or [])\n'
    '        self.endResetModel()\n'
    '\n'
    '    def set_tokens(self, tokens):\n'
    '        self._tokens = tokens or {}\n'
    '        if self._rows:\n'
    '            top = self.index(0, 0)\n'
    '            bottom = self.index(len(self._display_rows()) - 1,\n'
    '                                len(COLUMNS) - 1)\n'
    '            self.dataChanged.emit(top, bottom)\n'
    '\n'
    '    def set_show_summary(self, show):\n'
    '        self.beginResetModel()\n'
    '        self._show_summary = bool(show)\n'
    '        self.endResetModel()\n'
    '\n'
    '    def rows(self):\n'
    '        return list(self._rows)\n'
    '\n'
    '    def display_rows(self):\n'
    '        return self._display_rows()\n'
    '\n'
    '    # ── 内部 ────────────────────────────────────────────────\n'
    '    def _display_rows(self):\n'
    '        rows = list(self._rows)\n'
    '        if self._show_summary and rows:\n'
    '            summary = summary_row(rows)\n'
    '            if summary is not None:\n'
    '                rows.append(summary)\n'
    '        return rows\n'
    '\n'
    '    @staticmethod\n'
    '    def _cell_value(row, key):\n'
    "        if row.get('is_summary'):\n"
    "            if key == 'name':\n"
    "                return row.get('name')\n"
    "            if key in ('rmse', 'mae', 'skill'):\n"
    '                # 均值用作排序键；±std 由 _display_text 单独渲染\n'
    '                return row.get(key)\n'
    "            if key == 'rul_err':\n"
    "                return row.get('rul_err')\n"
    "            if key == 'status':\n"
    "                return row.get('status_label')\n"
    '            return None\n'
    "        if key == 'status':\n"
    "            return row.get('status_label')\n"
    '        return row.get(key)\n'
    '\n'
    '    def _display_text(self, row, key, value, fmt):\n'
    "        if row.get('is_summary'):\n"
    "            if key in ('rmse', 'mae', 'skill'):\n"
    '                # 单元格只放均值，保证在窄面板里不被省略号截断；\n'
    '                # 「mean ± std」写在工具提示与结果区下方的说明行里。\n'
    "                return '—' if row.get(key) is None else fmt.format(row[key])\n"
    "            if key == 'rul_err':\n"
    "                mean = row.get('rul_err')\n"
    "                return '—' if mean is None else f'{mean:+.1f}'\n"
    "        if key == 'skill' and isinstance(value, (int, float)) \\\n"
    '                and np.isfinite(value) and value < SKILL_WARNING_THRESHOLD:\n'
    "            return f'⚠ {value:+.3f}'\n"
    '        return format_optional(value, fmt)\n'
    '\n'
    '    def _foreground(self, row, key, value):\n'
    '        tokens = self._tokens\n'
    "        if row.get('is_summary'):\n"
    "            color = tokens.get('primary_d') or tokens.get('primary')\n"
    '            return QBrush(QColor(color)) if color else None\n'
    "        if row.get('is_baseline'):\n"
    "            color = tokens.get('text_muted')\n"
    '            return QBrush(QColor(color)) if color else None\n'
    "        if key == 'skill' and isinstance(value, (int, float)) \\\n"
    '                and np.isfinite(value) and value < SKILL_WARNING_THRESHOLD:\n'
    "            color = tokens.get('warning')\n"
    '            return QBrush(QColor(color)) if color else None\n'
    "        if key == 'status':\n"
    "            state = row.get('status')\n"
    '            color = {\n'
    "                'ok': tokens.get('success_d'),\n"
    "                'true_censored': tokens.get('success_d'),\n"
    "                'pred_censored': tokens.get('warning'),\n"
    "                'unavailable': tokens.get('text_muted'),\n"
    '            }.get(state)\n'
    '            return QBrush(QColor(color)) if color else None\n'
    '        return None\n'
    '\n'
    '    @staticmethod\n'
    '    def _tooltip(row):\n'
    '        parts = []\n'
    "        if row.get('is_summary'):\n"
    '            parts.append(\n'
    '                f\'跨电池汇总，n={row.get("n_batteries")} 块电池。\'\n'
    "                'n = 电池数才是泛化不确定性的来源。')\n"
    "            for key, label in (('rmse', 'RMSE'), ('mae', 'MAE'),\n"
    "                               ('skill', '技能分')):\n"
    "                mean, std = row.get(key), row.get(f'{key}_std')\n"
    '                if mean is None:\n'
    '                    continue\n'
    '                if std is None:\n'
    "                    parts.append(f'{label} 均值 = {mean:.4f}')\n"
    '                else:\n'
    "                    parts.append(f'{label} = {mean:.4f} ± {std:.4f}')\n"
    "            if row.get('rul_err') is not None:\n"
    "                std = row.get('rul_err_std')\n"
    '                parts.append(\n'
    '                    f\'RUL 误差均值 = {row["rul_err"]:+.1f}\'\n'
    "                    + (f' ± {std:.1f}' if std is not None else ''))\n"
    "        elif row.get('is_baseline'):\n"
    "            parts.append('经验基线：任何模型都必须先赢过它。')\n"
    '        else:\n'
    "            alpha = row.get('alpha')\n"
    '            if alpha is not None:\n'
    "                parts.append(f'持久性混合系数 α={alpha:.3f}')\n"
    '                if alpha < SKILL_WARNING_THRESHOLD:\n'
    "                    parts.append('⚠ 模型未超越持久性基线（α≈0）')\n"
    "            if row.get('detected') is not None:\n"
    '                parts.append(\n'
    '                    f\'EOL 检出 {row.get("detected")}/\'\n'
    '                    f\'{row.get("needs_detection")}\')\n'
    "            if row.get('n_seeds'):\n"
    '                parts.append(f\'{row["n_seeds"]} 个种子\')\n'
    "            help_text = STATUS_HELP.get(row.get('status'))\n"
    '            if help_text:\n'
    '                parts.append(help_text)\n'
    "        return '\\n'.join(parts) if parts else None\n"
    '\n'
    '\n'
    'def to_csv(rows):\n'
    '    """把结果行导出成 CSV 文本（Excel 可直接打开）。"""\n'
    '    import csv\n'
    '    import io\n'
    '\n'
    '    buffer = io.StringIO()\n'
    '    writer = csv.writer(buffer)\n'
    '    writer.writerow([header for header, _, _ in COLUMNS])\n'
    '    for row in rows:\n'
    '        line = []\n'
    '        for _, key, fmt in COLUMNS:\n'
    '            value = ResultTableModel._cell_value(row, key)\n'
    '            line.append(format_optional(value, fmt))\n'
    '        writer.writerow(line)\n'
    '    return buffer.getvalue()\n'
)

# ---- ui/chart_show.py ----
_MODULE_SOURCES['ui.chart_show'] = (
    'import numpy as np\n'
    'import matplotlib\n'
    "matplotlib.use('QtAgg')\n"
    'import matplotlib as mpl\n'
    'import matplotlib.pyplot as plt\n'
    '# C6：中文字体回退链来自唯一真相来源，不再在本文件里另写一份字体名单。\n'
    'from theme_tokens import (\n'
    '    CJK_FONTS, DARK, LIGHT, get_theme, series_style, usable_colors,\n'
    ')\n'
    "plt.rcParams['font.sans-serif'] = list(CJK_FONTS)\n"
    "plt.rcParams['axes.unicode_minus'] = False\n"
    '# 不再需要 mathtext.fontset，改用 Unicode 原生上下标字符\n'
    '\n'
    'from matplotlib.backends.backend_qtagg import (\n'
    '    FigureCanvasQTAgg as FigureCanvas,\n'
    '    NavigationToolbar2QT,\n'
    ')\n'
    '# U9：刻度密度 —— 刻度用显式数组下发，标签按步长格式化。\n'
    '# 刻意不使用 MultipleLocator / AutoMinorLocator：它们是有状态的 locator，\n'
    '# 会在每次绘制时重新查询轴对象，与本环境的 PyQt6 + offscreen matplotlib\n'
    '# 组合一起会触发原生访问违例（详见 _apply_ticks）。\n'
    'from matplotlib.ticker import FuncFormatter\n'
    '\n'
    'from PyQt6.QtCore import Qt, QSize, QPoint, QTimer, QEvent, QObject\n'
    'from PyQt6.QtGui import (\n'
    '    QIcon, QPixmap, QPainter, QColor, QPen, QBrush, QAction, QFont,\n'
    '    QShortcut, QKeySequence,\n'
    ')\n'
    'from PyQt6.QtWidgets import (\n'
    '    QPushButton, QToolTip, QApplication, QToolButton,\n'
    '    QGroupBox, QLabel, QDialog, QDialogButtonBox, QTabWidget,\n'
    '    QComboBox, QLineEdit, QCheckBox, QSpinBox, QMessageBox,\n'
    '    QInputDialog, QColorDialog, QVBoxLayout, QHBoxLayout, QFormLayout,\n'
    '    QListWidget, QListWidgetItem, QAbstractItemView, QSplitter,\n'
    '    QGridLayout, QScrollArea, QWidget, QFrame, QMenu,\n'
    ')\n'
    'from utils.icon_generator import get_dialog_icon, show_message, input_get_item\n'
    '\n'
    '# ── 图标绘制 ──────────────────────────────────────────────\n'
    '# 淡墨工具图标，与宣纸背景保持稳定对比。\n'
    '# C1：写成 RGB 整数而不是颜色字面量——图标是固定装饰，不随主题切换，\n'
    '# 但色值同样不该以 #RRGGBB 的形式散落在源码里。\n'
    '_ICON_COLOR = QColor(70, 80, 74)  # 淡墨：接近中性墨色\n'
    '_ICON_STROKE = 1.6\n'
    '_ICON_SIZE = QSize(24, 24)\n'
    '\n'
    '\n'
    'def _paint_icon(draw_func):\n'
    '    pix = QPixmap(_ICON_SIZE)\n'
    '    pix.fill(Qt.GlobalColor.transparent)\n'
    '    p = QPainter(pix)\n'
    '    p.setRenderHint(QPainter.RenderHint.Antialiasing)\n'
    '    p.setPen(QPen(_ICON_COLOR, _ICON_STROKE))\n'
    '    p.setBrush(Qt.BrushStyle.NoBrush)\n'
    '    draw_func(p, _ICON_SIZE)\n'
    '    p.end()\n'
    '    return QIcon(pix)\n'
    '\n'
    '\n'
    'def _home_draw(p, sz):\n'
    '    """主页图标：现代感房屋"""\n'
    '    w, h = sz.width(), sz.height()\n'
    '    # 屋顶\n'
    '    p.drawPolyline([QPoint(4, 11), QPoint(12, 4), QPoint(20, 11)])\n'
    '    # 房屋主体\n'
    '    p.drawRect(6, 11, 12, 9)\n'
    '    # 门\n'
    '    p.drawRect(10, 15, 4, 5)\n'
    '\n'
    '\n'
    'def _arrow_left(p, sz):\n'
    '    """返回上一个视图：向左箭头"""\n'
    '    w, h = sz.width(), sz.height()\n'
    '    # 主线\n'
    '    p.drawLine(18, 12, 6, 12)\n'
    '    # 箭头\n'
    '    p.drawPolyline([QPoint(11, 7), QPoint(6, 12), QPoint(11, 17)])\n'
    '\n'
    '\n'
    'def _arrow_right(p, sz):\n'
    '    """前进到下一个视图：向右箭头"""\n'
    '    w, h = sz.width(), sz.height()\n'
    '    # 主线\n'
    '    p.drawLine(6, 12, 18, 12)\n'
    '    # 箭头\n'
    '    p.drawPolyline([QPoint(13, 7), QPoint(18, 12), QPoint(13, 17)])\n'
    '\n'
    '\n'
    'def _pan_draw(p, sz):\n'
    '    """平移画布：十字方向箭头"""\n'
    '    w, h = sz.width(), sz.height()\n'
    '    c = 12\n'
    '    # 垂直线与上下箭头\n'
    '    p.drawLine(c, 4, c, 20)\n'
    '    p.drawPolyline([QPoint(9, 7), QPoint(c, 4), QPoint(15, 7)])\n'
    '    p.drawPolyline([QPoint(9, 17), QPoint(c, 20), QPoint(15, 17)])\n'
    '    # 水平线与左右箭头\n'
    '    p.drawLine(4, c, 20, c)\n'
    '    p.drawPolyline([QPoint(7, 9), QPoint(4, c), QPoint(7, 15)])\n'
    '    p.drawPolyline([QPoint(17, 9), QPoint(20, c), QPoint(17, 15)])\n'
    '\n'
    '\n'
    'def _zoom_draw(p, sz):\n'
    '    """矩形缩放：放大镜与虚线选框"""\n'
    '    w, h = sz.width(), sz.height()\n'
    '    # 放大镜圆圈与手柄\n'
    '    p.drawEllipse(QPoint(10, 10), 5, 5)\n'
    '    p.drawLine(14, 14, 19, 19)\n'
    '\n'
    '    # 外层虚线框 (提示矩形框选)\n'
    '    p.save()\n'
    '    pen = p.pen()\n'
    '    pen.setStyle(Qt.PenStyle.DashLine)\n'
    '    pen.setWidthF(1.2)\n'
    '    p.setPen(pen)\n'
    '    p.drawRect(3, 3, 18, 18)\n'
    '    p.restore()\n'
    '\n'
    '\n'
    'def _subplots_draw(p, sz):\n'
    '    """配置子图参数：网格布局（田字格）"""\n'
    '    w, h = sz.width(), sz.height()\n'
    '    # 整体大边框\n'
    '    p.drawRect(4, 4, 16, 16)\n'
    '    # 内部十字分隔线\n'
    '    p.drawLine(4, 12, 20, 12)\n'
    '    p.drawLine(12, 4, 12, 20)\n'
    '\n'
    '\n'
    'def _customize_draw(p, sz):\n'
    '    """编辑参数：调节滑块"""\n'
    '    w, h = sz.width(), sz.height()\n'
    '    # 上轨道和滑块\n'
    '    p.drawLine(4, 8, 20, 8)\n'
    '    p.drawEllipse(QPoint(16, 8), 2, 2)\n'
    '    # 下轨道和滑块\n'
    '    p.drawLine(4, 16, 20, 16)\n'
    '    p.drawEllipse(QPoint(8, 16), 2, 2)\n'
    '\n'
    '\n'
    'def _save_draw(p, sz):\n'
    '    """保存当前图表：经典软盘"""\n'
    '    w, h = sz.width(), sz.height()\n'
    '    # 软盘轮廓带右上角折角\n'
    '    p.drawPolyline([\n'
    '        QPoint(4, 4), QPoint(16, 4), QPoint(20, 8),\n'
    '        QPoint(20, 20), QPoint(4, 20), QPoint(4, 4)\n'
    '    ])\n'
    '    # 顶部标签槽\n'
    '    p.drawRect(8, 4, 8, 5)\n'
    '    # 底部读写金属片\n'
    '    p.drawRect(6, 14, 12, 6)\n'
    '\n'
    '\n'
    'def _subplots_draw(p, sz):\n'
    '    """子图图标：2x2 网格"""\n'
    '    w, h = sz.width(), sz.height()\n'
    '    m = 4\n'
    '    gap = 4\n'
    '    # 四个矩形\n'
    '    for i in range(2):\n'
    '        for j in range(2):\n'
    '            x = m + i * (w // 2 - m)\n'
    '            y = m + j * (h // 2 - m)\n'
    '            p.drawLine(x, y, x + w // 2 - gap, y)\n'
    '            p.drawLine(x + w // 2 - gap, y, x + w // 2 - gap, y + h // 2 - gap)\n'
    '            p.drawLine(x + w // 2 - gap, y + h // 2 - gap, x, y + h // 2 - gap)\n'
    '            p.drawLine(x, y + h // 2 - gap, x, y)\n'
    '\n'
    'def _customize_draw(p, sz):\n'
    '    """自定义图标：滑块"""\n'
    '    w, h = sz.width(), sz.height()\n'
    '    m = 5\n'
    '    # 滑轨竖线\n'
    '    p.drawLine(w // 2, m, w // 2, h - m)\n'
    '    # 底部横条\n'
    '    p.drawLine(m, h - m, w - m, h - m)\n'
    '    # 滑块圆形\n'
    '    cy = h // 2 - 2\n'
    '    p.drawEllipse(QPoint(w // 2, cy), 4, 4)\n'
    '\n'
    '\n'
    'def _save_draw(p, sz):\n'
    '    """保存图标：磁盘"""\n'
    '    w, h = sz.width(), sz.height()\n'
    '    m = 4\n'
    '    # 外框\n'
    '    p.drawLine(m, m, m, h - m)\n'
    '    p.drawLine(m, h - m, w - m, h - m)\n'
    '    p.drawLine(w - m, m, w - m, h - m)\n'
    '    p.drawLine(m, m, w - m, m)\n'
    '    # 标签缺口\n'
    '    p.drawLine(w - m - 6, m, w - m - 6, m + 5)\n'
    '    p.drawLine(w - m - 6, m + 5, w - m, m + 5)\n'
    '    # 内部向下箭头\n'
    '    c = w // 2\n'
    '    p.drawLine(c, m + 6, c, h - m - 3)\n'
    '    p.drawLine(c - 4, h - m - 7, c, h - m - 3)\n'
    '    p.drawLine(c + 4, h - m - 7, c, h - m - 3)\n'
    '\n'
    '\n'
    'def _line_style_draw(p, sz):\n'
    '    """线条样式图标：三条水平线（修复浮点坐标）"""\n'
    '    w, h = sz.width(), sz.height()\n'
    '    p.setPen(QPen(_ICON_COLOR, _ICON_STROKE))\n'
    '    margin = 4\n'
    '    y1 = int(h * 0.25)\n'
    '    y2 = int(h * 0.5)\n'
    '    y3 = int(h * 0.75)\n'
    '    p.drawLine(margin, y1, w - margin, y1)\n'
    '    p.drawLine(margin, y2, w - margin, y2)\n'
    '    p.drawLine(margin, y3, w - margin, y3)\n'
    '\n'
    '\n'
    '_ICON_DRAW_FUNCS = {\n'
    "    'Home':      _home_draw,\n"
    "    'Back':      _arrow_left,\n"
    "    'Forward':   _arrow_right,\n"
    "    'Pan':       _pan_draw,\n"
    "    'Zoom':      _zoom_draw,\n"
    "    'Subplots':  _subplots_draw,\n"
    "    'Customize': _customize_draw,\n"
    "    'Save':      _save_draw,\n"
    "    'LineStyle': _line_style_draw,\n"
    '}\n'
    '\n'
    '_icon_cache = {}\n'
    '\n'
    'def _get_icon(name):\n'
    '    if name not in _icon_cache:\n'
    '        _icon_cache[name] = _paint_icon(_ICON_DRAW_FUNCS[name])\n'
    '    return _icon_cache[name]\n'
    '\n'
    'TOOLTIP_CN = {\n'
    "    'Home':      '重置为原始视图',\n"
    "    'Back':      '返回上一个视图',\n"
    "    'Forward':   '前进到下一个视图',\n"
    "    'Pan':       '平移画布\\n左键拖拽平移，右键拖拽缩放\\nX轴/Y轴固定坐标轴，Ctrl键固定纵横比',\n"
    "    'Zoom':      '矩形缩放\\n框选区域进行放大\\nX轴/Y轴固定坐标轴',\n"
    "    'Subplots':  '配置子图参数',\n"
    "    'Customize': '编辑坐标轴、曲线和图像参数',\n"
    "    'Save':      '保存当前图表',\n"
    "    'LineStyle': '修改线条样式',\n"
    '}\n'
    '\n'
    '# ── 颜色面板数据（C3） ────────────────────────────────────\n'
    '# 这里只是「颜色选择器」的货源；真正画线用的分类色来自主题 token\n'
    '# （PALETTE_LIGHT / PALETTE_DARK 与 palette_for），并且一律按图表底色做\n'
    '# WCAG ≥ 3:1 过滤，所以亮黄（1.05:1）、中黄（1.18:1）这类在宣纸上\n'
    '# 几乎看不见的颜色不会再被画到图上，也不会再出现在面板里。\n'
    '#\n'
    '# C1：这些是 matplotlib / Okabe-Ito / NPG 的**固定参考色板**（跟主题无关，\n'
    '# 供用户手动挑一个具体色值），因此不放进 theme_tokens.py。为了不违反\n'
    '# 「源码里不出现颜色字面量」，统一以 RGB 整数三元组存放，再用\n'
    '# ``_hex()`` 渲染成 ``#RRGGBB``；数字仍然是数据，只是换了表示法。\n'
    'def _hex(rgb):\n'
    '    """``(31, 119, 180)`` -> 六位十六进制字符串（C1：字面量集中到一处构造）。"""\n'
    "    return '#%02X%02X%02X' % tuple(rgb)\n"
    '\n'
    '\n'
    '#: 固定参考色板：名称 -> RGB 整数三元组。\n'
    '_BASE_SWATCHES = [\n'
    "    ('深蓝',   (31, 119, 180)),    # tab10 蓝\n"
    "    ('橙色',   (255, 127, 14)),    # tab10 橙\n"
    "    ('绿色',   (44, 160, 44)),     # tab10 绿\n"
    "    ('红色',   (214, 39, 40)),     # tab10 红\n"
    "    ('紫色',   (148, 103, 189)),   # tab10 紫\n"
    "    ('棕色',   (140, 86, 75)),     # tab10 棕\n"
    "    ('粉色',   (227, 119, 194)),   # tab10 粉\n"
    "    ('灰色',   (127, 127, 127)),   # tab10 灰\n"
    "    ('橄榄绿', (188, 189, 34)),    # tab10 橄榄\n"
    "    ('青色',   (23, 190, 207)),    # tab10 青\n"
    "    ('黑色',   (0, 0, 0)),         # 中性黑\n"
    "    ('天蓝色', (86, 180, 233)),    # Okabe-Ito 天蓝\n"
    "    ('朱红色', (213, 94, 0)),      # Okabe-Ito 朱红\n"
    "    ('蓝绿色', (0, 158, 115)),     # Okabe-Ito 蓝绿\n"
    "    ('黄色',   (240, 228, 66)),    # Okabe-Ito 黄\n"
    "    ('中蓝色', (0, 114, 178)),     # Okabe-Ito 中蓝\n"
    "    ('紫红色', (204, 121, 167)),   # Okabe-Ito 紫红\n"
    "    ('浅蓝色', (174, 199, 232)),   # tab20 浅蓝\n"
    "    ('浅橙色', (255, 187, 120)),   # tab20 浅橙\n"
    "    ('浅绿色', (152, 223, 138)),   # tab20 浅绿\n"
    "    ('浅红色', (255, 152, 150)),   # tab20 浅红\n"
    "    ('NPG红色', (230, 75, 53)),    # NPG 红\n"
    "    ('石板蓝', (60, 84, 136)),     # NPG 石板蓝\n"
    "    ('亮黄色', (255, 255, 51)),    # 高亮黄（浅色底上会被 3:1 过滤掉）\n"
    ']\n'
    '\n'
    '_BASE_PALETTE = [(name, _hex(rgb)) for name, rgb in _BASE_SWATCHES]\n'
    '\n'
    '\n'
    'def _theme_palette_entries():\n'
    '    """把两套主题的系列 / 预测 / 失效色也放进候选池，方便手动挑同一套色。"""\n'
    '    entries = []\n'
    "    for label, tokens in (('浅色', LIGHT), ('深色', DARK)):\n"
    "        for index, color in enumerate(tokens['chart_series']):\n"
    "            entries.append((f'{label}系列{index + 1}', color))\n"
    "        entries.append((f'{label}预测', tokens['chart_forecast']))\n"
    "        entries.append((f'{label}失效', tokens['chart_threshold']))\n"
    '    return entries\n'
    '\n'
    '\n'
    'def _build_candidate_pool():\n'
    '    """候选池 = 基础色板 + 主题色，按 hex 去重并保持首次出现的顺序。"""\n'
    '    pool, seen = [], set()\n'
    '    for name, color in list(_BASE_PALETTE) + _theme_palette_entries():\n'
    '        key = color.upper()\n'
    '        if key in seen:\n'
    '            continue\n'
    '        seen.add(key)\n'
    '        pool.append((name, color))\n'
    '    return pool\n'
    '\n'
    '\n'
    '#: 兼容旧引用：颜色选择面板的**完整候选池**（不随主题变化）。\n'
    'COLOR_PALETTE = _build_candidate_pool()\n'
    '\n'
    '#: 默认多电池叠加分类色，直接取自主题 token（唯一真相来源）。\n'
    "PALETTE_LIGHT = list(LIGHT['chart_series'])\n"
    "PALETTE_DARK = list(DARK['chart_series'])\n"
    '\n'
    '#: 主题名 -> 分类色。\n'
    "PALETTE_BY_THEME = {'light': PALETTE_LIGHT, 'dark': PALETTE_DARK}\n"
    '\n'
    '#: 本模块缓存的当前主题 token，由 :func:`apply_mpl_style` 更新。\n'
    '_ACTIVE_TOKENS = LIGHT\n'
    '\n'
    '\n'
    'def active_tokens():\n'
    '    """当前生效的主题 token：优先问 ``ui.style``，取不到就用本模块缓存。"""\n'
    '    try:\n'
    '        from ui.style import theme_tokens as _style_theme_tokens\n'
    '        return _style_theme_tokens()\n'
    '    except Exception:\n'
    '        return _ACTIVE_TOKENS\n'
    '\n'
    '\n'
    'def palette_for(tokens):\n'
    '    """某套主题下的默认分类色（对比不足的颜色自动剔除）。"""\n'
    '    tokens = tokens or LIGHT\n'
    "    return (usable_colors(tokens['chart_series'], tokens['chart_bg'], 3.0)\n"
    "            or [tokens['chart_forecast']])\n"
    '\n'
    '\n'
    'def usable_palette(tokens=None, minimum=3.0):\n'
    '    """按当前主题过滤后的候选色，颜色选择面板只提供这些。"""\n'
    '    tokens = tokens or active_tokens()\n'
    '    return usable_colors(\n'
    "        [color for _name, color in COLOR_PALETTE], tokens['chart_bg'], minimum)\n"
    '\n'
    '\n'
    'def offered_colors(tokens=None, minimum=3.0):\n'
    '    """``[(名称, hex), ...]``：颜色面板实际展示的色块（已按主题过滤）。"""\n'
    '    tokens = tokens or active_tokens()\n'
    '    allowed = {color.upper() for color in usable_palette(tokens, minimum)}\n'
    '    entries = [\n'
    '        (name, color) for name, color in COLOR_PALETTE\n'
    '        if color.upper() in allowed\n'
    '    ]\n'
    '    return entries or list(COLOR_PALETTE)\n'
    '\n'
    '\n'
    'def apply_mpl_style(tokens):\n'
    '    """把主题 token 推进 matplotlib 的 rcParams（C2）。\n'
    '\n'
    '    切换主题后调用一次，图表底色、描边、刻度、网格与文字就整体跟着换色；\n'
    '    返回传入的 token，方便 ``tokens = apply_mpl_style(get_theme(mode))`` 串联。\n'
    '    """\n'
    '    global _ACTIVE_TOKENS\n'
    '    if tokens is None:\n'
    '        tokens = LIGHT\n'
    '    _ACTIVE_TOKENS = tokens\n'
    '    mpl.rcParams.update({\n'
    "        'font.sans-serif': list(CJK_FONTS),\n"
    "        'axes.unicode_minus': False,\n"
    "        'figure.facecolor': tokens['chart_bg'],\n"
    "        'figure.edgecolor': tokens['chart_bg'],\n"
    "        'savefig.facecolor': tokens['chart_bg'],\n"
    "        'savefig.edgecolor': tokens['chart_bg'],\n"
    "        'axes.facecolor': tokens['chart_bg'],\n"
    "        'axes.edgecolor': tokens['chart_spine'],\n"
    "        'axes.labelcolor': tokens['text_muted'],\n"
    "        'axes.titlecolor': tokens['text'],\n"
    "        'xtick.color': tokens['text_muted'],\n"
    "        'ytick.color': tokens['text_muted'],\n"
    "        'text.color': tokens['text'],\n"
    "        'grid.color': tokens['chart_grid'],\n"
    "        'grid.alpha': 0.5,\n"
    "        'grid.linewidth': 0.5,\n"
    '        # 只留左 / 下两条轴线，图表不再被四面框死。\n'
    "        'axes.spines.top': False,\n"
    "        'axes.spines.right': False,\n"
    '    })\n'
    '    return tokens\n'
    '\n'
    '\n'
    'def _first_cross(values, threshold):\n'
    '    """``values`` 中第一个低于 ``threshold`` 的下标；从未低于则返回 None。"""\n'
    '    if threshold is None:\n'
    '        return None\n'
    '    array = np.asarray(values, dtype=np.float64).reshape(-1)\n'
    '    array = array[np.isfinite(array)]\n'
    '    if array.size == 0:\n'
    '        return None\n'
    '    positions = np.flatnonzero(array < threshold)\n'
    '    return int(positions[0]) if len(positions) else None\n'
    '\n'
    '\n'
    'def _series_values(entry):\n'
    '    """从 ``battery_data[name]`` 里取出容量序列（DataFrame / dict / 数组都行）。"""\n'
    '    if entry is None:\n'
    '        return []\n'
    "    if hasattr(entry, 'columns'):                 # pandas.DataFrame\n"
    "        column = 'capacity' if 'capacity' in entry.columns else None\n"
    '        if column is None:\n'
    '            return []\n'
    '        return [float(value) for value in entry[column].tolist()]\n'
    "    if isinstance(entry, dict):                   # {'capacity': [...], ...}\n"
    "        raw = entry.get('capacity')\n"
    '        if raw is None:\n'
    '            return []\n'
    '        # 注意：不能写 `raw or []`——numpy 数组的真值判断会抛 ValueError\n'
    '        return [float(value) for value in raw]\n'
    '    try:\n'
    '        return [float(value) for value in entry]\n'
    '    except TypeError:\n'
    '        return []\n'
    '\n'
    '\n'
    'def _series_cycles(entry, length):\n'
    '    """真实循环号：优先用数据里的 ``cycle`` 列 / 键，缺失时退回位置下标。"""\n'
    '    values = None\n'
    '    if entry is not None:\n'
    "        if hasattr(entry, 'columns'):\n"
    "            if 'cycle' in entry.columns:\n"
    "                values = [float(value) for value in entry['cycle'].tolist()]\n"
    '        elif isinstance(entry, dict):\n'
    "            raw = entry.get('cycle')\n"
    '            if raw is not None:\n'
    '                values = [float(value) for value in raw]\n'
    '    if values is None or len(values) != length:\n'
    '        return [float(index) for index in range(length)]\n'
    '    return values\n'
    '\n'
    '\n'
    'def _luminance(hex_color):\n'
    '    r = int(hex_color[1:3], 16)\n'
    '    g = int(hex_color[3:5], 16)\n'
    '    b = int(hex_color[5:7], 16)\n'
    '    return 0.299 * r + 0.587 * g + 0.114 * b\n'
    '\n'
    '\n'
    'def _as_float_list(values):\n'
    '    """把任意序列转成 float 列表；``None`` 或含非数值时返回 ``[]``。"""\n'
    '    if values is None:\n'
    '        return []\n'
    '    try:\n'
    '        return [float(value) for value in values]\n'
    '    except (TypeError, ValueError):\n'
    '        return []\n'
    '\n'
    '\n'
    'def _tick_interval(rated_capacity):\n'
    '    """按额定容量挑一个「好看」的 y 轴刻度间隔（U2 聚焦退化带时也用）。"""\n'
    '    if not rated_capacity or rated_capacity <= 0:\n'
    '        return 0.2\n'
    '    rough = rated_capacity / 5\n'
    '    nice = [0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0]\n'
    '    best = nice[0]\n'
    '    for candidate in nice:\n'
    '        if abs(candidate - rough) < abs(best - rough):\n'
    '            best = candidate\n'
    '    return best\n'
    '\n'
    '\n'
    '#: 刻度步长的「好看」候选：1 / 2 / 2.5 / 5 × 10ⁿ\n'
    '_NICE_STEPS = (1.0, 2.0, 2.5, 5.0, 10.0)\n'
    '\n'
    '\n'
    'def nice_step(span, target_divisions=12):\n'
    '    """把区间 ``span`` 切成人眼友好的步长（1/2/2.5/5 × 10ⁿ）。\n'
    '\n'
    '    目的是让刻度**足够密**——用户应当能从网格线上直接读出数值，\n'
    '    而不是在两条粗刻度之间靠眼睛估。\n'
    '    """\n'
    '    span = abs(float(span))\n'
    '    if not np.isfinite(span) or span <= 0:\n'
    '        return 1.0\n'
    '    rough = span / max(1, int(target_divisions))\n'
    '    if rough <= 0:\n'
    '        return 1.0\n'
    '    exponent = np.floor(np.log10(rough))\n'
    '    base = 10.0 ** exponent\n'
    '    for factor in _NICE_STEPS:\n'
    '        candidate = factor * base\n'
    '        if candidate >= rough:\n'
    '            return float(candidate)\n'
    '    return float(10.0 * base)\n'
    '\n'
    '\n'
    'def _tick_decimals(interval):\n'
    '    """返回能**精确表示该步长**的最少小数位。\n'
    '\n'
    '    这样既不会让相邻刻度显示成同一个数（0.25 步长如果只给 1 位就会变成\n'
    '    0.2 / 0.5 / 0.8），也不会过度补零（0.1 步长只需 1 位，不必写成 0.10）。\n'
    '    """\n'
    '    if not np.isfinite(interval) or interval <= 0:\n'
    '        return 3\n'
    '    for decimals in range(0, 7):\n'
    '        if abs(round(interval, decimals) - interval) <= max(\n'
    '                1e-9, abs(interval) * 1e-9):\n'
    '            return decimals\n'
    '    return 6\n'
    '\n'
    '\n'
    'def _format_tick(value, step):\n'
    '    """刻度标签：整数步长不带小数点，小步长按需要补位。"""\n'
    '    if not np.isfinite(value):\n'
    "        return ''\n"
    '    if abs(float(value)) < 1e-12:\n'
    "        return '0'\n"
    '    decimals = _tick_decimals(step)\n'
    "    text = f'{value:.{decimals}f}'\n"
    '    # 去掉 "-0.00" 这类负零\n'
    '    if float(text) == 0:\n'
    "        return '0'\n"
    '    return text\n'
    '\n'
    '\n'
    'def _ticks_in_range(low, high, step):\n'
    '    """在 ``[low, high]`` 内按 ``step`` 生成刻度数组。"""\n'
    '    if not np.isfinite(low) or not np.isfinite(high) or step <= 0:\n'
    '        return np.asarray([])\n'
    '    first = np.ceil(low / step - 1e-9) * step\n'
    '    if not np.isfinite(first):\n'
    '        return np.asarray([])\n'
    '    count = int(np.floor((high - first) / step + 1e-9)) + 1\n'
    '    if count <= 0:\n'
    '        return np.asarray([])\n'
    '    return first + step * np.arange(count)\n'
    '\n'
    '\n'
    'def _minor_ticks(major, divisions=5):\n'
    '    """在两个主刻度之间插 ``divisions - 1`` 条次刻度（不含主刻度本身）。"""\n'
    '    major = np.asarray(major, dtype=np.float64)\n'
    '    if len(major) < 2 or divisions < 2:\n'
    '        return np.asarray([])\n'
    '    extra = []\n'
    '    for left, right in zip(major[:-1], major[1:]):\n'
    '        span = (right - left) / divisions\n'
    '        if span <= 0:\n'
    '            continue\n'
    '        extra.extend(left + span * index for index in range(1, divisions))\n'
    '    return np.asarray(extra, dtype=np.float64)\n'
    '\n'
    '\n'
    'def _apply_ticks(axis, low, high, target_divisions, label_step=None):\n'
    '    """给某个轴铺上**显式**的主 / 次刻度。\n'
    '\n'
    '    刻意不用 ``MultipleLocator`` / ``AutoMinorLocator``：它们是**有状态**的\n'
    '    locator，会在每次绘制时重新查询轴对象；与本环境的 PyQt6 + offscreen\n'
    '    matplotlib 组合一起使用时，窗口反复创建 / 销毁会触发原生访问违例\n'
    '    （0xC0000005，实测可稳定复现）。显式刻度数组是一次性算好的定值，\n'
    '    既没有这个风险，读数效果完全一样。\n'
    '    """\n'
    '    if not (np.isfinite(low) and np.isfinite(high) and high > low):\n'
    '        return None\n'
    '    step = nice_step(high - low, target_divisions)\n'
    '    major = _ticks_in_range(low, high, step)\n'
    '    if len(major) < 2:\n'
    '        return None\n'
    '    axis.set_ticks(major)\n'
    '    axis.set_ticks(_minor_ticks(major), minor=True)\n'
    '    axis.set_major_formatter(FuncFormatter(\n'
    '        lambda value, _pos, _step=(label_step or step):\n'
    '        _format_tick(value, _step)))\n'
    '    return step\n'
    '\n'
    '\n'
    'def _focused_ylim(series_list, rated_capacity, threshold_val=None,\n'
    '                  target_divisions=12):\n'
    '    """返回聚焦退化带后的 ``(y_lo, y_hi, y_ticks)``；无有效数据时返回 None。\n'
    '\n'
    '    上下各留 4% 余量，绝不把 y 轴强行拉到 0——容量从 0 起画会让整条退化曲线\n'
    '    挤成一条平线，看不出任何趋势。\n'
    '\n'
    '    刻度密度由 ``target_divisions`` 控制（默认 12 条主刻度）。旧实现最多只给\n'
    '    9 条，读数只能靠估；现在用 1/2/2.5/5 × 10ⁿ 的友好步长填满整个区间。\n'
    '    """\n'
    '    lows, highs = [], []\n'
    '    for series in series_list:\n'
    '        values = np.asarray(series, dtype=np.float64).reshape(-1)\n'
    '        values = values[np.isfinite(values)]\n'
    '        if values.size:\n'
    '            lows.append(float(values.min()))\n'
    '            highs.append(float(values.max()))\n'
    '    if threshold_val is not None and np.isfinite(threshold_val):\n'
    '        lows.append(float(threshold_val))\n'
    '        highs.append(float(threshold_val))\n'
    '    if not lows:\n'
    '        return None\n'
    '    low, high = min(lows), max(highs)\n'
    '    if high - low < 1e-9:\n'
    '        high = low + max(abs(low) * 0.04, 0.05)\n'
    '    pad = (high - low) * 0.04\n'
    '    y_lo, y_hi = low - pad, high + pad\n'
    '\n'
    '    # 优先用与额定容量对齐的步长；太稀就换成更细的友好步长\n'
    '    interval = _tick_interval(rated_capacity)\n'
    '    friendly = nice_step(y_hi - y_lo, target_divisions)\n'
    '    if interval > friendly:\n'
    '        interval = friendly\n'
    '    if interval <= 0 or not np.isfinite(interval):\n'
    '        interval = friendly\n'
    '    ticks = np.arange(np.floor(y_lo / interval) * interval,\n'
    '                      y_hi + interval * 0.5, interval)\n'
    '    ticks = ticks[(ticks >= y_lo - interval * 0.01)\n'
    '                  & (ticks <= y_hi + interval * 0.01)]\n'
    '    if len(ticks) < 4:                     # 退化带很窄时别只剩两三条线\n'
    '        interval = max(nice_step(y_hi - y_lo, 8), 1e-6)\n'
    '        ticks = np.arange(np.floor(y_lo / interval) * interval,\n'
    '                          y_hi + interval * 0.5, interval)\n'
    '    return y_lo, y_hi, ticks\n'
    '\n'
    '\n'
    'class _ColorCell(QWidget):\n'
    '    """单色块：上方纯色按钮 + 下方十六进制值 + 颜色名称"""\n'
    '\n'
    '    def __init__(self, name, hex_color, parent=None):\n'
    '        super().__init__(parent)\n'
    '        self._hex = hex_color\n'
    '        layout = QVBoxLayout(self)\n'
    '        layout.setSpacing(1)\n'
    '        layout.setContentsMargins(0, 0, 0, 0)\n'
    '\n'
    '        # C1：色块描边 / 悬停高亮都用主题 token，不再写字面量。\n'
    '        tokens = active_tokens()\n'
    '        btn = QPushButton()\n'
    '        btn.setFixedSize(72, 36)\n'
    '        btn.setCursor(Qt.CursorShape.PointingHandCursor)\n'
    "        btn.setToolTip(f'{name}\\n{hex_color}')\n"
    "        btn.setStyleSheet(f'''\n"
    '            QPushButton {{\n'
    '                background-color: {hex_color};\n'
    "                border: 1px solid {tokens['border_soft']};\n"
    '                border-radius: 3px;\n'
    '            }}\n'
    '            QPushButton:hover {{\n'
    "                border: 2px solid {tokens['primary']};\n"
    '            }}\n'
    "        ''')\n"
    '        btn.clicked.connect(lambda: self._on_click())\n'
    '        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)\n'
    '\n'
    '        hex_lbl = QLabel(hex_color)\n'
    '        hex_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)\n'
    "        hex_lbl.setStyleSheet('font-size: 8px; font-weight: bold; background: transparent;')\n"
    '        layout.addWidget(hex_lbl)\n'
    '\n'
    '        name_lbl = QLabel(name)\n'
    '        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)\n'
    "        name_lbl.setStyleSheet('font-size: 7px; background: transparent;')\n"
    '        layout.addWidget(name_lbl)\n'
    '\n'
    '        self._click_callback = None\n'
    '\n'
    '    def set_click_callback(self, callback):\n'
    '        self._click_callback = callback\n'
    '\n'
    '    def _on_click(self):\n'
    '        if self._click_callback:\n'
    '            self._click_callback(self._hex)\n'
    '\n'
    '    @property\n'
    '    def hex_color(self):\n'
    '        return self._hex\n'
    '\n'
    '\n'
    'def _parse_color_input(text):\n'
    '    """解析用户输入的 RGB 或十六进制颜色，返回 hex 字符串或 None"""\n'
    '    t = text.strip()\n'
    '    if not t:\n'
    '        return None\n'
    '    # 十六进制\n'
    "    if t.startswith('#'):\n"
    "        if len(t) == 7 and all(c in '0123456789ABCDEFabcdef' for c in t[1:]):\n"
    '            return t.upper()\n'
    "        if len(t) == 4 and all(c in '0123456789ABCDEFabcdef' for c in t[1:]):\n"
    '            r, g, b = t[1], t[2], t[3]\n'
    "            return f'#{r}{r}{g}{g}{b}{b}'.upper()\n"
    '    # RGB: r,g,b 或 rgb(r,g,b)\n'
    '    import re\n'
    "    m = re.findall(r'\\d+', t)\n"
    '    if len(m) == 3:\n'
    '        try:\n'
    '            r, g, b = int(m[0]), int(m[1]), int(m[2])\n'
    '            if 0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255:\n'
    "                return f'#{r:02X}{g:02X}{b:02X}'\n"
    '        except ValueError:\n'
    '            pass\n'
    '    return None\n'
    '\n'
    '\n'
    '#: 颜色选择器的初始值：纯黑。这是「数据」而不是主题色，用 RGB 整数构造。\n'
    '_DEFAULT_PICK_HEX = _hex((0, 0, 0))\n'
    '\n'
    '\n'
    'class ColorGridDialog(QDialog):\n'
    '    """颜色面板弹窗 —— 网格色板 + 自定义 RGB/Hex 输入"""\n'
    '    color_selected = None\n'
    '\n'
    '    def __init__(self, parent=None, current_hex=_DEFAULT_PICK_HEX):\n'
    '        super().__init__(parent)\n'
    "        self.setWindowTitle('选择颜色')\n"
    "        self.setWindowIcon(get_dialog_icon('color'))\n"
    '        self.setModal(True)\n'
    '        self.resize(600, 550)\n'
    '        # C1：默认值由 RGB 整数构造，不再是颜色字面量。\n'
    '        self._selected_hex = current_hex\n'
    '        tokens = active_tokens()\n'
    '        self._border_style = f\'border: 1px solid {tokens["border_soft"]};\'\n'
    '        self._preview_style = (\n'
    '            f\'border: 1px solid {tokens["border_soft"]};\'\n'
    '            f\' background-color: {tokens["bg_hover"]};\')\n'
    '\n'
    '        layout = QVBoxLayout(self)\n'
    '\n'
    '        # ── 色板区域（C3：只提供当前主题下 ≥ 3:1 的颜色） ──\n'
    '        scroll = QScrollArea()\n'
    '        scroll.setWidgetResizable(True)\n'
    '        container = QWidget()\n'
    '        grid = QGridLayout(container)\n'
    '        grid.setSpacing(6)\n'
    '\n'
    '        cols = 4\n'
    '        for i, (name, hex_val) in enumerate(offered_colors()):\n'
    '            cell = _ColorCell(name, hex_val)\n'
    '            cell.set_click_callback(self._on_select)\n'
    '            r, c = i // cols, i % cols\n'
    '            grid.addWidget(cell, r, c)\n'
    '\n'
    '        scroll.setWidget(container)\n'
    '        layout.addWidget(scroll)\n'
    '\n'
    '        # ── 自定义颜色输入 ──\n'
    "        custom_group = QGroupBox('自定义颜色')\n"
    '        custom_layout = QHBoxLayout(custom_group)\n'
    '\n'
    "        custom_layout.addWidget(QLabel('颜色值：'))\n"
    '        self._custom_input = QLineEdit()\n'
    '        # 帮助文案只说明格式，不再写出一个具体色值（C1）。\n'
    "        self._custom_input.setPlaceholderText('例：# 后跟 6 位十六进制，或 255,0,0')\n"
    '        self._custom_input.textChanged.connect(self._on_custom_input_changed)\n'
    '        custom_layout.addWidget(self._custom_input)\n'
    '\n'
    '        self._custom_preview = QFrame()\n'
    '        self._custom_preview.setFixedSize(28, 28)\n'
    '        self._custom_preview.setStyleSheet(self._preview_style)\n'
    '        custom_layout.addWidget(self._custom_preview)\n'
    '\n'
    "        apply_custom = QPushButton('应用')\n"
    '        apply_custom.clicked.connect(self._apply_custom)\n'
    '        custom_layout.addWidget(apply_custom)\n'
    '\n'
    '        layout.addWidget(custom_group)\n'
    '\n'
    '        # ── 底部 ──\n'
    '        bottom = QHBoxLayout()\n'
    "        bottom.addWidget(QLabel('当前选中：'))\n"
    '        self._preview = QFrame()\n'
    '        self._preview.setFixedSize(60, 24)\n'
    '        self._preview.setStyleSheet(\n'
    "            f'background-color: {current_hex}; {self._border_style}')\n"
    '        bottom.addWidget(self._preview)\n'
    '        self._hex_label = QLabel(current_hex)\n'
    '        bottom.addWidget(self._hex_label)\n'
    '        bottom.addStretch()\n'
    '\n'
    '        btn_box = QDialogButtonBox()\n'
    "        ok_btn = btn_box.addButton('确定', QDialogButtonBox.ButtonRole.AcceptRole)\n"
    '        ok_btn.clicked.connect(self.accept)\n'
    "        cancel_btn = btn_box.addButton('取消', QDialogButtonBox.ButtonRole.RejectRole)\n"
    '        cancel_btn.clicked.connect(self.reject)\n'
    '        bottom.addWidget(btn_box)\n'
    '        layout.addLayout(bottom)\n'
    '\n'
    '    def _on_select(self, hex_val):\n'
    '        self._selected_hex = hex_val\n'
    '        self._preview.setStyleSheet(\n'
    "            f'background-color: {hex_val}; {self._border_style}')\n"
    '        self._hex_label.setText(hex_val)\n'
    '        self._custom_input.setText(hex_val)\n'
    '\n'
    '    def _on_custom_input_changed(self, text):\n'
    '        parsed = _parse_color_input(text)\n'
    '        if parsed:\n'
    '            self._custom_preview.setStyleSheet(\n'
    "                f'background-color: {parsed}; {self._border_style}')\n"
    '        else:\n'
    '            self._custom_preview.setStyleSheet(self._preview_style)\n'
    '\n'
    '    def _apply_custom(self):\n'
    '        parsed = _parse_color_input(self._custom_input.text())\n'
    '        if parsed:\n'
    '            self._on_select(parsed)\n'
    '\n'
    '    def accept(self):\n'
    '        self.color_selected = self._selected_hex\n'
    '        super().accept()\n'
    '\n'
    '\n'
    '# ── 线条样式设置面板 ───────────────────────────────────────\n'
    '_LINESTYLE_MAP = {\n'
    "    '实线':   'solid',\n"
    "    '虚线':   'dashed',\n"
    "    '点画线': 'dashdot',\n"
    '}\n'
    '\n'
    '_LINESTYLE_REVERSE = {v: k for k, v in _LINESTYLE_MAP.items()}\n'
    '\n'
    "_LINEWIDTH_OPTIONS = ['0.5', '1', '1.5', '2']\n"
    '\n'
    '\n'
    'class LineStyleDialog(QDialog):\n'
    '    """线条样式修改面板"""\n'
    '    def __init__(self, figure, canvas, parent=None):\n'
    '        super().__init__(parent)\n'
    "        self.setWindowTitle('线条样式设置')\n"
    "        self.setWindowIcon(get_dialog_icon('line'))\n"
    '        self.resize(700, 500)\n'
    '        self.setModal(False)\n'
    '        self._figure = figure\n'
    '        self._canvas = canvas\n'
    '        self._current_line = None\n'
    '        self._lines_info = []  # [(axis_idx, axis_title, line_idx, line, label)]\n'
    '        # C1：色块描边统一来自主题 token。\n'
    '        self._border_style = (\n'
    '            f\'border: 1px solid {active_tokens()["border_soft"]};\'\n'
    "            ' border-radius: 3px;')\n"
    '\n'
    '        self._build_ui()\n'
    '        self._populate_lines()\n'
    '        self._set_settings_enabled(False)\n'
    '\n'
    '    def _build_ui(self):\n'
    '        main_layout = QVBoxLayout(self)\n'
    '\n'
    '        splitter = QSplitter(Qt.Orientation.Horizontal)\n'
    '        splitter.setHandleWidth(2)\n'
    '\n'
    '        # ── 左侧：线条列表 ──\n'
    '        left = QWidget()\n'
    '        left_layout = QVBoxLayout(left)\n'
    '        left_layout.setContentsMargins(0, 0, 0, 0)\n'
    "        left_layout.addWidget(QLabel('<b>图表线条</b>'))\n"
    '        self._line_list = QListWidget()\n'
    '        self._line_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)\n'
    '        self._line_list.currentRowChanged.connect(self._on_line_selected)\n'
    '        left_layout.addWidget(self._line_list)\n'
    '        splitter.addWidget(left)\n'
    '\n'
    '        # ── 右侧：参数设置 ──\n'
    '        right = QWidget()\n'
    '        right_layout = QVBoxLayout(right)\n'
    '        right_layout.setContentsMargins(8, 0, 0, 0)\n'
    '\n'
    "        right_layout.addWidget(QLabel('<b>参数设置</b>'))\n"
    '\n'
    '        form = QFormLayout()\n'
    '        form.setSpacing(12)\n'
    '\n'
    '        self._style_combo = QComboBox()\n'
    "        self._style_combo.addItems(['实线', '虚线', '点画线'])\n"
    "        form.addRow('线条样式：', self._style_combo)\n"
    '\n'
    '        self._color_btn = QPushButton()\n'
    '        self._color_btn.setFixedSize(80, 28)\n'
    '        self._color_btn.setStyleSheet(\n'
    "            f'background-color: {_DEFAULT_PICK_HEX}; {self._border_style}')\n"
    '        self._color_btn.clicked.connect(self._pick_color)\n'
    '        self._color_hex = _DEFAULT_PICK_HEX\n'
    "        form.addRow('线条颜色：', self._color_btn)\n"
    '\n'
    '        self._width_combo = QComboBox()\n'
    '        self._width_combo.setEditable(True)\n'
    '        self._width_combo.addItems(_LINEWIDTH_OPTIONS)\n'
    "        self._width_combo.setCurrentText('1')\n"
    "        form.addRow('线条宽度：', self._width_combo)\n"
    '\n'
    '        right_layout.addLayout(form)\n'
    '        right_layout.addStretch()\n'
    '        splitter.addWidget(right)\n'
    '\n'
    '        splitter.setStretchFactor(0, 3)\n'
    '        splitter.setStretchFactor(1, 4)\n'
    '        main_layout.addWidget(splitter, 1)\n'
    '\n'
    '        # ── 底部按钮 ──\n'
    '        btn_layout = QHBoxLayout()\n'
    '        btn_layout.addStretch()\n'
    '\n'
    "        self._apply_btn = QPushButton('应用')\n"
    '        self._apply_btn.clicked.connect(self._apply_changes)\n'
    '        self._apply_btn.setMinimumWidth(80)\n'
    '\n'
    "        self._ok_btn = QPushButton('确定')\n"
    '        self._ok_btn.clicked.connect(self._ok)\n'
    '        self._ok_btn.setMinimumWidth(80)\n'
    '\n'
    "        self._cancel_btn = QPushButton('取消')\n"
    '        self._cancel_btn.clicked.connect(self.reject)\n'
    '        self._cancel_btn.setMinimumWidth(80)\n'
    '\n'
    '        btn_layout.addWidget(self._apply_btn)\n'
    '        btn_layout.addWidget(self._ok_btn)\n'
    '        btn_layout.addWidget(self._cancel_btn)\n'
    '        main_layout.addLayout(btn_layout)\n'
    '\n'
    '    def _populate_lines(self):\n'
    '        """收集图中所有线条，按子图分组显示"""\n'
    '        self._line_list.clear()\n'
    '        self._lines_info = []\n'
    '        axes = self._figure.get_axes()\n'
    '        # C1：分组标题用主题强调色，不再写死一个高亮蓝。\n'
    "        group_color = QColor(active_tokens()['primary'])\n"
    '\n'
    '        for ax_idx, ax in enumerate(axes):\n'
    '            lines = ax.get_lines()\n'
    '            if not lines:\n'
    '                continue\n'
    '            # 子图标题\n'
    '            ax_title = ax.get_title()\n'
    '            if not ax_title:\n'
    "                ax_title = f'子图 {ax_idx + 1}'\n"
    '            # 添加分组标题\n'
    "            group_item = QListWidgetItem(f'▸ {ax_title}')\n"
    '            group_item.setFlags(Qt.ItemFlag.NoItemFlags)\n'
    '            font = group_item.font()\n'
    '            font.setBold(True)\n'
    '            group_item.setFont(font)\n'
    '            group_item.setForeground(group_color)\n'
    '            self._line_list.addItem(group_item)\n'
    '\n'
    '            for line_idx, line in enumerate(lines):\n'
    '                label = line.get_label()\n'
    "                if not label or label.startswith('_'):\n"
    "                    label = f'线条 {line_idx + 1}'\n"
    "                item = QListWidgetItem(f'    {label}')\n"
    '                item.setData(Qt.ItemDataRole.UserRole, len(self._lines_info))\n'
    '                self._line_list.addItem(item)\n'
    '                self._lines_info.append((ax_idx, ax_title, line_idx, line, label))\n'
    '\n'
    '    def _on_line_selected(self, row):\n'
    '        item = self._line_list.item(row)\n'
    '        if item is None or item.data(Qt.ItemDataRole.UserRole) is None:\n'
    '            self._current_line = None\n'
    '            self._set_settings_enabled(False)\n'
    '            return\n'
    '        idx = item.data(Qt.ItemDataRole.UserRole)\n'
    '        self._current_line = self._lines_info[idx][3]\n'
    '        self._set_settings_enabled(True)\n'
    '        self._load_line_properties()\n'
    '\n'
    '    def _set_settings_enabled(self, enabled):\n'
    '        self._style_combo.setEnabled(enabled)\n'
    '        self._color_btn.setEnabled(enabled)\n'
    '        self._width_combo.setEnabled(enabled)\n'
    '        self._apply_btn.setEnabled(enabled)\n'
    '        self._ok_btn.setEnabled(enabled)\n'
    '\n'
    '    def _load_line_properties(self):\n'
    '        """将当前选中线条的属性加载到设置控件"""\n'
    '        line = self._current_line\n'
    '        if line is None:\n'
    '            return\n'
    '        # 线条样式\n'
    '        ls = line.get_linestyle()\n'
    "        style_name = _LINESTYLE_REVERSE.get(ls, '实线')\n"
    '        idx = self._style_combo.findText(style_name)\n'
    '        if idx >= 0:\n'
    '            self._style_combo.setCurrentIndex(idx)\n'
    '        # 颜色\n'
    '        from matplotlib.colors import to_hex\n'
    '        try:\n'
    '            rgba = line.get_color()\n'
    '            self._color_hex = to_hex(rgba, keep_alpha=False)\n'
    '        except Exception:\n'
    '            self._color_hex = _DEFAULT_PICK_HEX\n'
    '        self._color_btn.setStyleSheet(\n'
    "            f'background-color: {self._color_hex}; {self._border_style}')\n"
    '        # 宽度\n'
    '        lw = line.get_linewidth()\n'
    '        self._width_combo.setCurrentText(str(lw))\n'
    '\n'
    '    def _pick_color(self):\n'
    '        dlg = ColorGridDialog(self, self._color_hex)\n'
    '        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.color_selected:\n'
    '            self._color_hex = dlg.color_selected\n'
    '            self._color_btn.setStyleSheet(\n'
    "                f'background-color: {self._color_hex}; {self._border_style}')\n"
    '\n'
    '    def _apply_changes(self):\n'
    '        if self._current_line is None:\n'
    '            return\n'
    '        # 线条样式\n'
    '        style_cn = self._style_combo.currentText()\n'
    "        ls = _LINESTYLE_MAP.get(style_cn, 'solid')\n"
    '        self._current_line.set_linestyle(ls)\n'
    '        # 颜色\n'
    '        self._current_line.set_color(self._color_hex)\n'
    '        # 宽度\n'
    '        try:\n'
    '            lw = float(self._width_combo.currentText())\n'
    '            self._current_line.set_linewidth(lw)\n'
    '        except ValueError:\n'
    '            pass\n'
    '        # 强制立即重绘（draw_idle 在非模态对话框中可能延迟或不触发）\n'
    '        self._canvas.draw()\n'
    '\n'
    '    def _ok(self):\n'
    '        self._apply_changes()\n'
    '        self.accept()\n'
    '\n'
    '    # ── 对话框翻译工具 ─────────────────────────────────────────\n'
    '_SUBPLOT_TR = {\n'
    "    'Borders': '边距', 'Spacings': '间距',\n"
    "    'top': '上边距', 'bottom': '下边距', 'left': '左边距', 'right': '右边距',\n"
    "    'hspace': '水平间距', 'wspace': '垂直间距',\n"
    "    'Export values': '导出数值', 'Tight layout': '紧凑布局',\n"
    "    'Reset': '重置', 'Close': '关闭',\n"
    '}\n'
    '\n'
    "_FIGOPT_TAB_TR = {'Axes': '坐标轴', 'Curves': '曲线', 'Images, etc.': '图像等'}\n"
    '\n'
    '_FIGOPT_LABEL_TR = {\n'
    "    'Title': '标题',\n"
    "    'Bottom-Axis': 'X 轴', 'Top-Axis': 'Y 轴 (右)',\n"
    "    'Min': '最小值', 'Max': '最大值', 'Label': '标签', 'Scale': '刻度',\n"
    "    '(Re-)Generate automatic legend': '(重新)生成自动图例',\n"
    "    'Line': '线条', 'Line style': '线型', 'Draw style': '绘制样式',\n"
    "    'Width': '宽度', 'Color (RGBA)': '颜色 (RGBA)',\n"
    "    'Marker': '标记', 'Style': '样式', 'Size': '大小',\n"
    "    'Face color (RGBA)': '填充色 (RGBA)', 'Edge color (RGBA)': '边颜色 (RGBA)',\n"
    "    'Colormap': '颜色映射', 'Min. value': '最小值', 'Max. value': '最大值',\n"
    "    'Interpolation': '插值', 'Interpolation stage': '插值阶段',\n"
    '}\n'
    '\n'
    '_FIGOPT_LINESTYLE_TR = {\n'
    "    'Solid': '实线', 'Dashed': '虚线', 'DashDot': '点划线',\n"
    "    'Dotted': '点线', 'None': '无', 'none': '无',\n"
    '}\n'
    '\n'
    '_FIGOPT_DRAWSTYLE_TR = {\n'
    "    'Default': '默认', 'Steps (Pre)': '阶梯 (前)',\n"
    "    'Steps (Mid)': '阶梯 (中)', 'Steps (Post)': '阶梯 (后)',\n"
    '}\n'
    '\n'
    "_FIGOPT_BTN_TR = {'OK': '确定', 'Cancel': '取消', 'Apply': '应用',\n"
    "                   'Ok': '确定'}\n"
    '\n'
    '\n'
    '# ── Unicode 上下标字符映射 ──────────────────────────────────\n'
    '_SUPERSCRIPT_MAP = {\n'
    "    '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',\n"
    "    '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',\n"
    "    '+': '⁺', '-': '⁻', '=': '⁼', '(': '⁽', ')': '⁾',\n"
    "    'a': 'ᵃ', 'b': 'ᵇ', 'c': 'ᶜ', 'd': 'ᵈ', 'e': 'ᵉ',\n"
    "    'f': 'ᶠ', 'g': 'ᵍ', 'h': 'ʰ', 'i': 'ⁱ', 'j': 'ʲ',\n"
    "    'k': 'ᵏ', 'l': 'ˡ', 'm': 'ᵐ', 'n': 'ⁿ', 'o': 'ᵒ',\n"
    "    'p': 'ᵖ', 'r': 'ʳ', 's': 'ˢ', 't': 'ᵗ', 'u': 'ᵘ',\n"
    "    'v': 'ᵛ', 'w': 'ʷ', 'x': 'ˣ', 'y': 'ʸ', 'z': 'ᶻ',\n"
    "    'A': 'ᴬ', 'B': 'ᴮ', 'C': 'ᶜ', 'D': 'ᴰ', 'E': 'ᴱ',\n"
    "    'F': 'ᶠ', 'G': 'ᴳ', 'H': 'ᴴ', 'I': 'ᴵ', 'J': 'ᴶ',\n"
    "    'K': 'ᴷ', 'L': 'ᴸ', 'M': 'ᴹ', 'N': 'ᴺ', 'O': 'ᴼ',\n"
    "    'P': 'ᴾ', 'Q': 'ᵟ', 'R': 'ᴿ', 'S': 'ˢ', 'T': 'ᵀ',\n"
    "    'U': 'ᵁ', 'V': 'ⱽ', 'W': 'ᵂ', 'X': 'ˣ', 'Y': 'ʸ', 'Z': 'ᶻ',\n"
    '}\n'
    '\n'
    '_SUBSCRIPT_MAP = {\n'
    "    '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄',\n"
    "    '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉',\n"
    "    '+': '₊', '-': '₋', '=': '₌', '(': '₍', ')': '₎',\n"
    "    'a': 'ₐ', 'e': 'ₑ', 'h': 'ₕ', 'i': 'ᵢ', 'j': 'ⱼ',\n"
    "    'k': 'ₖ', 'l': 'ₗ', 'm': 'ₘ', 'n': 'ₙ', 'o': 'ₒ',\n"
    "    'p': 'ₚ', 'r': 'ᵣ', 's': 'ₛ', 't': 'ₜ', 'u': 'ᵤ',\n"
    "    'v': 'ᵥ', 'x': 'ₓ',\n"
    '}\n'
    '\n'
    '\n'
    '# ── 上标/下标快捷键 ─────────────────────────────────────────\n'
    'def apply_sup_sub(mode):\n'
    '    """将当前焦点 QLineEdit 中选中的文本转为 Unicode 上标(^)或下标(_)\n'
    '    无 Unicode 对应的字符保持原样"""\n'
    '    widget = QApplication.focusWidget()\n'
    '    if not isinstance(widget, QLineEdit) or not widget.isVisible():\n'
    '        return\n'
    '    text = widget.text()\n'
    '    s = widget.selectionStart()\n'
    '    e = widget.selectionEnd()\n'
    '    if s < 0 or e <= s:\n'
    '        return  # 未选中文本，不做任何操作\n'
    '    sel = text[s:e]\n'
    "    char_map = _SUPERSCRIPT_MAP if mode == '^' else _SUBSCRIPT_MAP\n"
    "    converted = ''.join(char_map.get(ch, ch) for ch in sel)\n"
    '    if converted != sel:\n'
    '        widget.setText(text[:s] + converted + text[e:])\n'
    '\n'
    '\n'
    'def _install_sup_sub_shortcuts(widget):\n'
    '    """在指定 widget 上安装上下标快捷键 (Ctrl+= / Ctrl+Shift+=)"""\n'
    '    from PyQt6.QtGui import QShortcut, QKeySequence\n'
    "    sup_sc = QShortcut(QKeySequence('Ctrl+='), widget)\n"
    '    sup_sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)\n'
    "    sup_sc.activated.connect(lambda: apply_sup_sub('^'))\n"
    "    sub_sc = QShortcut(QKeySequence('Ctrl+Shift+='), widget)\n"
    '    sub_sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)\n'
    "    sub_sc.activated.connect(lambda: apply_sup_sub('_'))\n"
    "    if not hasattr(widget, '_sup_sub_shortcuts'):\n"
    '        widget._sup_sub_shortcuts = []\n'
    '    widget._sup_sub_shortcuts.extend([sup_sc, sub_sc])\n'
    '\n'
    '\n'
    'class _LegendEditDialog(QDialog):\n'
    '    """支持上下标快捷键的图例文本编辑对话框"""\n'
    '    def __init__(self, parent, old_text):\n'
    '        super().__init__(parent)\n'
    "        self.setWindowTitle('编辑图例')\n"
    "        self.setWindowIcon(get_dialog_icon('legend'))\n"
    '        self.setModal(True)\n'
    '        self.resize(450, 150)\n'
    '        self.result_text = old_text\n'
    '\n'
    '        layout = QVBoxLayout(self)\n'
    "        layout.addWidget(QLabel('图例文本：'))\n"
    '        self._edit = QLineEdit(old_text)\n'
    '        self._edit.selectAll()\n'
    '        layout.addWidget(self._edit)\n'
    '\n'
    '        btn_box = QDialogButtonBox()\n'
    "        ok_btn = btn_box.addButton('确定', QDialogButtonBox.ButtonRole.AcceptRole)\n"
    '        ok_btn.clicked.connect(self._on_ok)\n'
    "        cancel_btn = btn_box.addButton('取消', QDialogButtonBox.ButtonRole.RejectRole)\n"
    '        cancel_btn.clicked.connect(self.reject)\n'
    '        layout.addWidget(btn_box)\n'
    '\n'
    '        _install_sup_sub_shortcuts(self)\n'
    '\n'
    '    def _on_ok(self):\n'
    '        self.result_text = self._edit.text()\n'
    '        self.accept()\n'
    '\n'
    '\n'
    'def _translate_figopt_dialog(dialog):\n'
    '    """递归翻译 figure options 对话框中的所有英文文本，并加入上下标快捷键"""\n'
    "    dialog.setWindowTitle('图表选项')\n"
    "    dialog.setWindowIcon(get_dialog_icon('chart'))\n"
    '\n'
    '    for bbox in dialog.findChildren(QDialogButtonBox):\n'
    '        for btn in bbox.buttons():\n'
    '            t = btn.text()\n'
    '            if t in _FIGOPT_BTN_TR:\n'
    '                btn.setText(_FIGOPT_BTN_TR[t])\n'
    '\n'
    '    for tab in dialog.findChildren(QTabWidget):\n'
    '        for i in range(tab.count()):\n'
    '            old = tab.tabText(i)\n'
    '            if old in _FIGOPT_TAB_TR:\n'
    '                tab.setTabText(i, _FIGOPT_TAB_TR[old])\n'
    '\n'
    '    for gb in dialog.findChildren(QGroupBox):\n'
    '        t = gb.title()\n'
    '        if t in _FIGOPT_TAB_TR:\n'
    '            gb.setTitle(_FIGOPT_TAB_TR[t])\n'
    '\n'
    '    for w in dialog.findChildren(QLabel):\n'
    '        t = w.text()\n'
    '        if t in _FIGOPT_LABEL_TR:\n'
    '            w.setText(_FIGOPT_LABEL_TR[t])\n'
    '        elif t in _FIGOPT_TAB_TR:\n'
    '            w.setText(_FIGOPT_TAB_TR[t])\n'
    '        elif t in _FIGOPT_LINESTYLE_TR:\n'
    '            w.setText(_FIGOPT_LINESTYLE_TR[t])\n'
    '        elif t in _FIGOPT_DRAWSTYLE_TR:\n'
    '            w.setText(_FIGOPT_DRAWSTYLE_TR[t])\n'
    '\n'
    '    for cb in dialog.findChildren(QCheckBox):\n'
    '        t = cb.text()\n'
    '        if t in _FIGOPT_LABEL_TR:\n'
    '            cb.setText(_FIGOPT_LABEL_TR[t])\n'
    '\n'
    '    for combo in dialog.findChildren(QComboBox):\n'
    '        for i in range(combo.count()):\n'
    '            item = combo.itemText(i)\n'
    '            if item in _FIGOPT_LINESTYLE_TR:\n'
    '                combo.setItemText(i, _FIGOPT_LINESTYLE_TR[item])\n'
    '            elif item in _FIGOPT_DRAWSTYLE_TR:\n'
    '                combo.setItemText(i, _FIGOPT_DRAWSTYLE_TR[item])\n'
    '            elif item in _FIGOPT_LABEL_TR:\n'
    '                combo.setItemText(i, _FIGOPT_LABEL_TR[item])\n'
    '\n'
    '    _install_sup_sub_shortcuts(dialog)\n'
    '\n'
    '\n'
    '# ── 悬停延时过滤器 ─────────────────────────────────────────\n'
    'class _HoverDelayFilter(QObject):\n'
    '    """鼠标悬停 2s 后才弹出 tooltip"""\n'
    '    def __init__(self, tooltip_text, delay=2000):\n'
    '        super().__init__()\n'
    '        self._text = tooltip_text\n'
    '        self._delay = delay\n'
    '        self._timer = QTimer()\n'
    '        self._timer.setSingleShot(True)\n'
    '        self._timer.timeout.connect(self._fire)\n'
    '        self._widget = None\n'
    '\n'
    '    def eventFilter(self, obj, event):\n'
    '        t = event.type()\n'
    '        if t == QEvent.Type.Enter:\n'
    '            self._widget = obj\n'
    '            self._timer.start(self._delay)\n'
    '        elif t == QEvent.Type.Leave:\n'
    '            self._timer.stop()\n'
    '            QToolTip.hideText()\n'
    '            self._widget = None\n'
    '        elif t == QEvent.Type.MouseButtonPress:\n'
    '            self._timer.stop()\n'
    '            QToolTip.hideText()\n'
    '        return False\n'
    '\n'
    '    def _fire(self):\n'
    '        if self._widget:\n'
    '            pos = self._widget.mapToGlobal(\n'
    '                QPoint(self._widget.width() // 2, self._widget.height() + 2))\n'
    '            QToolTip.showText(pos, self._text, self._widget)\n'
    '\n'
    '\n'
    'class CustomToolbar(NavigationToolbar2QT):\n'
    '    toolitems = tuple(\n'
    '        item for item in NavigationToolbar2QT.toolitems\n'
    "        if item[0] in {'Home', 'Pan', 'Zoom', 'Save'}\n"
    '    )\n'
    '\n'
    '    def __init__(self, canvas, parent=None):\n'
    '        super().__init__(canvas, parent)\n'
    '        canvas._navigation_toolbar = self\n'
    '        self._apply_style()\n'
    '        self._add_line_style_button()\n'
    '\n'
    '    def _apply_style(self):\n'
    '        self.setIconSize(QSize(22, 22))\n'
    '        # 不再硬编码颜色，让全局宣纸水墨主题接管；仅设置尺寸与间距。\n'
    '        self.setStyleSheet("""\n'
    '            QToolBar {\n'
    '                background: transparent;\n'
    '                border: none;\n'
    '                spacing: 2px;\n'
    '            }\n'
    '            QToolButton {\n'
    '                background: transparent;\n'
    '                border: 1px solid transparent;\n'
    '                border-radius: 4px;\n'
    '                padding: 4px 6px;\n'
    '                margin: 1px;\n'
    '            }\n'
    '        """)\n'
    '\n'
    '        action_name_map = {}\n'
    '        for a in self.actions():\n'
    '            if a.text():\n'
    '                action_name_map[a.text()] = a\n'
    '\n'
    '        for name in _ICON_DRAW_FUNCS:\n'
    '            if name in action_name_map:\n'
    '                action_name_map[name].setIcon(_get_icon(name))\n'
    '\n'
    '        for child in self.findChildren(QToolButton):\n'
    "            action = child.defaultAction() if hasattr(child, 'defaultAction') else None\n"
    '            key = None\n'
    '            if action:\n'
    '                for name, a in action_name_map.items():\n'
    '                    if a is action:\n'
    '                        key = name\n'
    '                        break\n'
    '            if not key:\n'
    '                continue\n'
    '            if key in TOOLTIP_CN:\n'
    "                child.setToolTip('')\n"
    '                f = _HoverDelayFilter(TOOLTIP_CN[key], 1500)\n'
    '                child.installEventFilter(f)\n'
    "                if not hasattr(self, '_hover_filters'):\n"
    '                    self._hover_filters = []\n'
    '                self._hover_filters.append(f)\n'
    '\n'
    '    # 线条样式按钮\n'
    '    def _add_line_style_button(self):\n'
    "        icon = _get_icon('LineStyle')\n"
    "        self._line_style_action = self.addAction(icon, 'LineStyle')\n"
    "        self._line_style_action.setToolTip('')\n"
    '        self._line_style_action.triggered.connect(self._open_line_style_dialog)\n'
    '        # 为新按钮安装悬停延迟\n'
    '        for child in self.findChildren(QToolButton):\n'
    "            action = child.defaultAction() if hasattr(child, 'defaultAction') else None\n"
    '            if action is self._line_style_action:\n'
    "                child.setToolTip('')\n"
    "                f = _HoverDelayFilter(TOOLTIP_CN['LineStyle'], 2000)\n"
    '                child.installEventFilter(f)\n'
    "                if not hasattr(self, '_hover_filters'):\n"
    '                    self._hover_filters = []\n'
    '                self._hover_filters.append(f)\n'
    '                break\n'
    '\n'
    '    def _open_line_style_dialog(self):\n'
    '        dlg = LineStyleDialog(self.canvas.figure, self.canvas, self)\n'
    '        dlg.show()\n'
    '\n'
    '    # ── 汉化 configure_subplots ──────────────────────────\n'
    '    def configure_subplots(self):\n'
    '        super().configure_subplots()\n'
    '        dlg = self._subplot_dialog\n'
    '        if dlg is None:\n'
    '            return dlg\n'
    "        dlg.setWindowTitle('子图参数配置')\n"
    "        dlg.setWindowIcon(get_dialog_icon('subplot'))\n"
    '        # 新增：子图个数设置（控件置于对话框右侧）\n'
    "        if not hasattr(dlg, '_subplot_count_added'):\n"
    '            layout = dlg.layout()\n'
    '            if layout is not None:\n'
    "                count_label = QLabel('子图个数：', dlg)\n"
    '                count_spin = QSpinBox(dlg)\n'
    '                count_spin.setRange(1, 16)\n'
    '                count_spin.setValue(4)\n'
    "                count_btn = QPushButton('应用', dlg)\n"
    '\n'
    '                # 记录控件，便于后续使用\n'
    '                dlg._subplot_count_spin = count_spin\n'
    '                dlg._subplot_count_btn = count_btn\n'
    '\n'
    '                inserted = False\n'
    '\n'
    '                # 尝试将控件插入到“边距/间距”参数区域所在布局的右侧\n'
    '                for i in range(layout.count()):\n'
    '                    item = layout.itemAt(i)\n'
    '                    sub_layout = item.layout()\n'
    '                    if sub_layout is None:\n'
    '                        continue\n'
    '\n'
    '                    # 处理 QFormLayout：把“子图个数”作为新的一行加入\n'
    '                    if isinstance(sub_layout, QFormLayout):\n'
    '                        row = QHBoxLayout()\n'
    '                        row.addWidget(count_spin)\n'
    '                        row.addWidget(count_btn)\n'
    '                        row.addStretch()\n'
    '                        sub_layout.addRow(count_label, row)\n'
    '                        inserted = True\n'
    '                        break\n'
    '\n'
    '                    # 处理普通布局：在其右侧追加一组控件\n'
    '                    if isinstance(sub_layout, (QVBoxLayout, QHBoxLayout)):\n'
    '                        row = QHBoxLayout()\n'
    '                        row.addWidget(count_label)\n'
    '                        row.addWidget(count_spin)\n'
    '                        row.addWidget(count_btn)\n'
    '                        row.addStretch()\n'
    '                        sub_layout.addLayout(row)\n'
    '                        inserted = True\n'
    '                        break\n'
    '\n'
    '                # 如果没找到合适的参数区布局，则退回到底部追加\n'
    '                if not inserted:\n'
    '                    count_layout = QHBoxLayout()\n'
    '                    count_layout.addStretch()\n'
    '                    count_layout.addWidget(count_label)\n'
    '                    count_layout.addWidget(count_spin)\n'
    '                    count_layout.addWidget(count_btn)\n'
    '                    layout.addLayout(count_layout)\n'
    '\n'
    '                dlg._subplot_count_added = True\n'
    '        for gb in dlg.findChildren(QGroupBox):\n'
    '            t = gb.title()\n'
    '            if t in _SUBPLOT_TR:\n'
    '                gb.setTitle(_SUBPLOT_TR[t])\n'
    '        for btn in dlg.findChildren(QPushButton):\n'
    '            t = btn.text()\n'
    '            if t in _SUBPLOT_TR:\n'
    '                btn.setText(_SUBPLOT_TR[t])\n'
    '        for label in dlg.findChildren(QLabel):\n'
    '            t = label.text()\n'
    '            if t in _SUBPLOT_TR:\n'
    '                label.setText(_SUBPLOT_TR[t])\n'
    '        return dlg\n'
    '\n'
    '    # ── 汉化 edit_parameters ─────────────────────────────\n'
    '    def edit_parameters(self):\n'
    '        from matplotlib.backends.qt_editor import figureoptions\n'
    '        axes = self.canvas.figure.get_axes()\n'
    '        if not axes:\n'
    "            show_message(self.canvas.parent(), 'error', '错误', '没有可编辑的坐标轴。')\n"
    '            return\n'
    '        if len(axes) == 1:\n'
    '            ax = axes[0]\n'
    '        else:\n'
    '            titles = [\n'
    '                ax.get_label() or\n'
    '                ax.get_title() or\n'
    "                ax.get_title('left') or\n"
    "                ax.get_title('right') or\n"
    "                ' - '.join(filter(None, [ax.get_xlabel(), ax.get_ylabel()])) or\n"
    "                f'<anonymous {type(ax).__name__}>'\n"
    '                for ax in axes]\n'
    '            duplicate_titles = [\n'
    '                title for title in titles if titles.count(title) > 1]\n'
    '            for i, ax in enumerate(axes):\n'
    '                if titles[i] in duplicate_titles:\n'
    "                    titles[i] += f' (id: {id(ax):#x})'\n"
    '            item, ok = input_get_item(\n'
    '                self.canvas.parent(),\n'
    "                '自定义', '选择坐标轴：', titles, 0, False, icon_kind='axis')\n"
    '            if not ok:\n'
    '                return\n'
    '            ax = axes[titles.index(item)]\n'
    '        figureoptions.figure_edit(ax, self)\n'
    "        if hasattr(self, '_fedit_dialog') and self._fedit_dialog is not None:\n"
    '            _translate_figopt_dialog(self._fedit_dialog)\n'
    '\n'
    '\n'
    'class LivePlot:\n'
    '    """U5：TCP 实时图的增量更新器。\n'
    '\n'
    '    坐标轴和两条线在构造时**只建一次**；之后每条消息只做 ``push``（存下最新\n'
    '    数据）+ ``flush``（``set_data`` / ``relim`` / ``autoscale_view`` /\n'
    '    ``draw_idle``），因此不再整图 ``clear`` 重建，也不会丢掉用户的缩放与图例。\n'
    '    """\n'
    '\n'
    '    def __init__(self, ax, tokens):\n'
    '        self.ax = ax\n'
    '        self.tokens = tokens\n'
    '        self._history = []\n'
    '        self._forecast = []\n'
    '        self._threshold = None\n'
    '        self._rated_capacity = None\n'
    '        self._threshold_ratio = None\n'
    '        self._soh_axis = None\n'
    '        # 事实 = 中性墨色实线 + 小圆点；模型输出 = 强调色加粗虚线。\n'
    '        self.observed_line, = ax.plot(\n'
    "            [], [], color=tokens['chart_measured'], marker='o', markersize=3,\n"
    "            linewidth=1.2, label='实测容量', zorder=3)\n"
    '        self.forecast_line, = ax.plot(\n'
    "            [], [], color=tokens['chart_forecast'], linewidth=2.0,\n"
    "            linestyle='--', label='预测容量', zorder=4)\n"
    '        self.threshold_line = ax.axhline(\n'
    "            y=0.0, color=tokens['chart_threshold'], linestyle='--',\n"
    "            linewidth=1.3, label='失效阈值线', zorder=5)\n"
    '\n'
    '    def set_threshold(self, threshold, rated_capacity=None, threshold_ratio=None):\n'
    '        """更新失效阈值线（额定容量 / 比例变了也不重建坐标轴）。"""\n'
    '        self._threshold = None if threshold is None else float(threshold)\n'
    '        if rated_capacity is not None:\n'
    '            self._rated_capacity = float(rated_capacity)\n'
    '        if threshold_ratio is not None:\n'
    '            self._threshold_ratio = float(threshold_ratio)\n'
    '        if self._threshold is None:\n'
    '            return\n'
    '        self.threshold_line.set_ydata([self._threshold, self._threshold])\n'
    '        if self._threshold_ratio is not None:\n'
    '            self.threshold_line.set_label(\n'
    "                f'失效阈值 {self._threshold:.3f} Ah'\n"
    "                f'（{self._threshold_ratio:.0%} 额定）')\n"
    '\n'
    '    def attach_soh_axis(self, soh_axis):\n'
    '        """记录右侧 SOH% 副轴，便于主题切换时重新着色。"""\n'
    '        self._soh_axis = soh_axis\n'
    '\n'
    '    def push(self, history, forecast):\n'
    '        """只存下最新的一帧数据，不做任何绘图。"""\n'
    '        self._history = _as_float_list(history)\n'
    '        self._forecast = _as_float_list(forecast)\n'
    '\n'
    '    def flush(self, canvas):\n'
    '        """把最新数据刷进已存在的线条，然后只重算数据范围并重绘。"""\n'
    '        history, forecast = self._history, self._forecast\n'
    '        self.observed_line.set_data(list(range(len(history))), history)\n'
    '        if forecast:\n'
    '            start = max(0, len(history) - 1)\n'
    '            self.forecast_line.set_data(\n'
    '                list(range(start, start + len(forecast))), forecast)\n'
    '        else:\n'
    '            self.forecast_line.set_data([], [])\n'
    '        self._autoscale_y(history, forecast)\n'
    '        self.ax.relim()\n'
    '        self.ax.autoscale_view(scalex=True, scaley=False)\n'
    '        canvas.draw_idle()\n'
    '\n'
    '    def _autoscale_y(self, history, forecast):\n'
    '        """U2 的同一套 y 轴策略：聚焦退化带，不强制从 0 起。"""\n'
    '        focused = _focused_ylim(\n'
    '            [history, forecast], self._rated_capacity, self._threshold)\n'
    '        if focused is None:\n'
    '            return\n'
    '        y_lo, y_hi, ticks = focused\n'
    '        self.ax.set_ylim(y_lo, y_hi)\n'
    '        self.ax.set_yticks(ticks)\n'
    '\n'
    '\n'
    'class MplCanvas(FigureCanvas):\n'
    '    def __init__(self, parent=None, allow_fullscreen=True,\n'
    '                 interactive_navigation=False):\n'
    '        # 主题 token 决定图表底色；默认跟随当前生效主题（C2）。\n'
    '        self._tokens = active_tokens()\n'
    '        apply_mpl_style(self._tokens)\n'
    '        self.fig, self.ax = plt.subplots(1, 1, figsize=(8, 6))\n'
    "        self.fig.patch.set_facecolor(self._tokens['chart_bg'])\n"
    "        self.ax.set_facecolor(self._tokens['chart_bg'])\n"
    '        super().__init__(self.fig)\n'
    '        self.setParent(parent)\n'
    '        self._allow_fullscreen = allow_fullscreen\n'
    '        self._interactive_navigation = interactive_navigation\n'
    '        self._last_plot_kind = None\n'
    '        self._last_plot_payload = None\n'
    '        self._fullscreen_dialog = None\n'
    '        self._fullscreen_subplot_key = None\n'
    '        self._hover_annot = None\n'
    '        self._hover_cid = None\n'
    '        self._subplot_keys_by_axis = {}\n'
    '        self._pan_state = None\n'
    '        self._navigation_toolbar = None\n'
    '        # U5：实时 TCP 图只建一次坐标轴，之后只更新数据。\n'
    '        self._live_ax = None\n'
    '        self._live_plot = None\n'
    '        if self._interactive_navigation:\n'
    "            self.mpl_connect('scroll_event', self._on_scroll_zoom)\n"
    "            self.mpl_connect('button_press_event', self._on_pan_press)\n"
    "            self.mpl_connect('motion_notify_event', self._on_pan_motion)\n"
    "            self.mpl_connect('button_release_event', self._on_pan_release)\n"
    '        self._show_placeholder()\n'
    '\n'
    '    def apply_theme_tokens(self, tokens):\n'
    '        """C5/C2：主题切换后重设画布底色并刷新 matplotlib 全局样式。"""\n'
    '        self._tokens = apply_mpl_style(tokens)\n'
    "        self.fig.patch.set_facecolor(self._tokens['chart_bg'])\n"
    '        for axis in self.fig.axes:\n'
    "            axis.set_facecolor(self._tokens['chart_bg'])\n"
    '        if self._last_plot_kind is not None and self._last_plot_payload:\n'
    '            self.replay_last_plot(self)\n'
    '        else:\n'
    '            self._show_placeholder()\n'
    '        return self._tokens\n'
    '\n'
    '    def _show_placeholder(self):\n'
    '        self.ax.set_xticks([])\n'
    '        self.ax.set_yticks([])\n'
    '        for spine in self.ax.spines.values():\n'
    '            spine.set_visible(False)\n'
    "        self.ax.text(0.5, 0.5, '导入数据并点击“开始评估”\\n曲线与失效阈值将在这里显示',\n"
    "                     transform=self.ax.transAxes, ha='center', va='center',\n"
    "                     fontsize=12, color=self._tokens['text_dim'], linespacing=1.6)\n"
    '        self.draw()\n'
    '\n'
    '    def mouseDoubleClickEvent(self, event):\n'
    '        """双击主图进入全屏；在全屏图中双击则返回。"""\n'
    '        if event.button() == Qt.MouseButton.LeftButton:\n'
    '            if self._allow_fullscreen:\n'
    '                self.open_fullscreen()\n'
    '            else:\n'
    '                self.window().close()\n'
    '            event.accept()\n'
    '            return\n'
    '        super().mouseDoubleClickEvent(event)\n'
    '\n'
    '    def contextMenuEvent(self, event):\n'
    '        """右键提供当前子图与全部子图两种全屏入口。"""\n'
    '        if not self._allow_fullscreen or self._last_plot_kind is None:\n'
    '            super().contextMenuEvent(event)\n'
    '            return\n'
    '        subplot_key = self._subplot_key_at(event.pos())\n'
    '        menu = self._build_fullscreen_menu(subplot_key)\n'
    '        menu.exec(event.globalPos())\n'
    '        event.accept()\n'
    '\n'
    '    def _subplot_key_at(self, position):\n'
    '        if not self._subplot_keys_by_axis or self.width() <= 0 or self.height() <= 0:\n'
    '            return None\n'
    '        figure_x = float(position.x()) / self.width() * self.fig.bbox.width\n'
    '        figure_y = (\n'
    '            1.0 - float(position.y()) / self.height()\n'
    '        ) * self.fig.bbox.height\n'
    '        for axis, subplot_key in self._subplot_keys_by_axis.items():\n'
    '            if axis.get_visible() and axis.bbox.contains(figure_x, figure_y):\n'
    '                return subplot_key\n'
    '        return None\n'
    '\n'
    '    def _build_fullscreen_menu(self, subplot_key):\n'
    '        menu = QMenu(self)\n'
    "        current_action = menu.addAction('全屏查看当前子图')\n"
    '        current_action.setEnabled(subplot_key is not None)\n'
    '        current_action.triggered.connect(\n'
    '            lambda _checked=False, key=subplot_key: self.open_fullscreen(key))\n'
    "        all_action = menu.addAction('全屏查看全部子图')\n"
    '        all_action.triggered.connect(\n'
    '            lambda _checked=False: self.open_fullscreen(None))\n'
    '        return menu\n'
    '\n'
    '    def open_fullscreen(self, subplot_key=None):\n'
    '        """打开独立全屏图表，不移动或破坏主窗口中的原图。"""\n'
    '        if self._fullscreen_dialog is not None and self._fullscreen_dialog.isVisible():\n'
    '            if self._fullscreen_subplot_key == subplot_key:\n'
    '                self._fullscreen_dialog.raise_()\n'
    '                self._fullscreen_dialog.activateWindow()\n'
    '                return\n'
    '            self._fullscreen_dialog.close()\n'
    '        dialog = ChartFullscreenDialog(\n'
    '            self, self.window(), subplot_key=subplot_key)\n'
    '        self._fullscreen_dialog = dialog\n'
    '        self._fullscreen_subplot_key = subplot_key\n'
    '\n'
    '        def _forget_dialog(_result):\n'
    '            if self._fullscreen_dialog is dialog:\n'
    '                self._fullscreen_dialog = None\n'
    '                self._fullscreen_subplot_key = None\n'
    '\n'
    '        dialog.finished.connect(_forget_dialog)\n'
    '        dialog.showFullScreen()\n'
    '\n'
    '    def replay_last_plot(self, target_canvas, subplot_key=None):\n'
    '        """把当前图表数据重绘到独立画布，保留缩放和平移能力。"""\n'
    "        if self._last_plot_kind == 'results':\n"
    '            payload = self._last_plot_payload\n'
    '            battery_names = list(payload[0])\n'
    '            if subplot_key is not None:\n'
    '                if subplot_key not in battery_names:\n'
    "                    raise ValueError(f'找不到子图：{subplot_key}')\n"
    '                battery_names = [subplot_key]\n'
    '            target_canvas.plot_results(battery_names, *payload[1:])\n'
    "        elif self._last_plot_kind == 'tcp':\n"
    '            target_canvas.plot_tcp_predictions(*self._last_plot_payload)\n'
    '\n'
    '    def _toolbar_navigation_is_active(self):\n'
    '        toolbar = self._navigation_toolbar\n'
    "        return toolbar is not None and bool(getattr(toolbar, 'mode', ''))\n"
    '\n'
    '    def _on_scroll_zoom(self, event):\n'
    '        if (not self._interactive_navigation or event.inaxes is None or\n'
    '                event.xdata is None or event.ydata is None):\n'
    '            return\n'
    "        if event.button == 'up':\n"
    '            scale = 1.0 / 1.2\n'
    "        elif event.button == 'down':\n"
    '            scale = 1.2\n'
    '        else:\n'
    '            return\n'
    '\n'
    '        axis = event.inaxes\n'
    '        x_min, x_max = axis.get_xlim()\n'
    '        y_min, y_max = axis.get_ylim()\n'
    '        axis.set_xlim(\n'
    '            event.xdata - (event.xdata - x_min) * scale,\n'
    '            event.xdata + (x_max - event.xdata) * scale,\n'
    '        )\n'
    '        axis.set_ylim(\n'
    '            event.ydata - (event.ydata - y_min) * scale,\n'
    '            event.ydata + (y_max - event.ydata) * scale,\n'
    '        )\n'
    '        self.draw_idle()\n'
    '\n'
    '    def _on_pan_press(self, event):\n'
    '        if (not self._interactive_navigation or event.button != 1 or\n'
    '                event.inaxes is None or self._toolbar_navigation_is_active()):\n'
    '            return\n'
    '        self._pan_state = {\n'
    "            'axis': event.inaxes,\n"
    "            'x': float(event.x),\n"
    "            'y': float(event.y),\n"
    "            'xlim': event.inaxes.get_xlim(),\n"
    "            'ylim': event.inaxes.get_ylim(),\n"
    '        }\n'
    '\n'
    '    def _on_pan_motion(self, event):\n'
    '        if self._pan_state is None:\n'
    '            return\n'
    "        axis = self._pan_state['axis']\n"
    '        if axis.bbox.width <= 0 or axis.bbox.height <= 0:\n'
    '            return\n'
    "        x_min, x_max = self._pan_state['xlim']\n"
    "        y_min, y_max = self._pan_state['ylim']\n"
    '        delta_x = (\n'
    "            float(event.x) - self._pan_state['x']\n"
    '        ) * (x_max - x_min) / axis.bbox.width\n'
    '        delta_y = (\n'
    "            float(event.y) - self._pan_state['y']\n"
    '        ) * (y_max - y_min) / axis.bbox.height\n'
    '        axis.set_xlim(x_min - delta_x, x_max - delta_x)\n'
    '        axis.set_ylim(y_min - delta_y, y_max - delta_y)\n'
    '        self.draw_idle()\n'
    '\n'
    '    def _on_pan_release(self, event):\n'
    '        if event.button == 1:\n'
    '            self._pan_state = None\n'
    '\n'
    '    def _calc_tick_interval(self, rated_capacity):\n'
    '        return _tick_interval(rated_capacity)\n'
    '\n'
    "    def _install_hover(self, xlabel='放电循环', ylabel='容量 (Ah)'):\n"
    '        """为当前图表安装数据点悬停提示"""\n'
    '        if self._hover_cid is not None:\n'
    '            self.fig.canvas.mpl_disconnect(self._hover_cid)\n'
    '        self._hover_annot = None\n'
    '        self._hover_xlabel = xlabel\n'
    '        self._hover_ylabel = ylabel\n'
    '        self._hover_cid = self.fig.canvas.mpl_connect(\n'
    "            'motion_notify_event', self._on_hover)\n"
    '\n'
    '    def _on_hover(self, event):\n'
    '        if event.inaxes is None or event.xdata is None or event.ydata is None:\n'
    '            if self._hover_annot:\n'
    '                self._hover_annot.set_visible(False)\n'
    '                self.draw_idle()\n'
    '            return\n'
    '\n'
    '        # 在当前坐标轴中找最近的数据点\n'
    "        min_dist = float('inf')\n"
    '        nearest = None\n'
    '\n'
    '        for line in event.inaxes.get_lines():\n'
    '            if not line.get_visible():\n'
    '                continue\n'
    '            xdata, ydata = line.get_xdata(), line.get_ydata()\n'
    '            if len(xdata) == 0:\n'
    '                continue\n'
    '            # 将数据点转为像素坐标\n'
    '            x_px, y_px = event.inaxes.transData.transform(\n'
    '                np.column_stack([xdata, ydata])).T\n'
    '            mx, my = event.x, event.y\n'
    '            dist = np.sqrt((x_px - mx) ** 2 + (y_px - my) ** 2)\n'
    '            idx = np.argmin(dist)\n'
    '            d = dist[idx]\n'
    '            if d < min_dist:\n'
    '                min_dist = d\n'
    '                nearest = (xdata[idx], ydata[idx], line.get_label())\n'
    '\n'
    '        # 15 像素以内才显示提示\n'
    '        if nearest is not None and min_dist < 15:\n'
    '            x_val, y_val, label = nearest\n'
    "            text = f'{self._hover_xlabel}: {int(x_val)}\\n' \\\n"
    "                   f'{self._hover_ylabel}: {y_val:.2f}'\n"
    "            if label and not label.startswith('_'):\n"
    "                text = f'{label}\\n{text}'\n"
    '\n'
    '            # 在画布像素坐标下定位提示框，确保实时跟随鼠标\n'
    '            # 偏移：鼠标右下方 14 像素\n'
    '            OFFSET_X, OFFSET_Y = 14, -14\n'
    '            tx_px = event.x + OFFSET_X\n'
    '            ty_px = event.y + OFFSET_Y\n'
    '\n'
    '            # 限制在画布范围内\n'
    '            canvas_w = self.fig.canvas.get_width_height()[0]\n'
    '            canvas_h = self.fig.canvas.get_width_height()[1]\n'
    '            # 假设提示框宽 120 高 50 像素，避免溢出\n'
    '            tw, th = 130, 56\n'
    '            if tx_px + tw > canvas_w:\n'
    '                tx_px = event.x - OFFSET_X - tw\n'
    '            if ty_px - th < 0:\n'
    '                ty_px = event.y + abs(OFFSET_Y) + th\n'
    '\n'
    '            # 转 figure 归一化坐标\n'
    '            inv = self.fig.transFigure.inverted()\n'
    '            fx, fy = inv.transform((tx_px, ty_px))\n'
    '\n'
    '            tokens = self._tokens\n'
    '            if self._hover_annot is None:\n'
    '                self._hover_annot = self.fig.text(\n'
    '                    fx, fy, text,\n'
    '                    transform=self.fig.transFigure,\n'
    "                    ha='left', va='top',\n"
    "                    bbox=dict(boxstyle='round,pad=0.4',\n"
    "                              facecolor=tokens['bg_surface'],\n"
    "                              edgecolor=tokens['chart_forecast'],\n"
    '                              alpha=0.95, linewidth=1.2),\n'
    "                    fontsize=9, color=tokens['text'], zorder=1000)\n"
    '            else:\n'
    '                self._hover_annot.set_position((fx, fy))\n'
    '                self._hover_annot.set_text(text)\n'
    '                self._hover_annot.set_visible(True)\n'
    '            self.draw_idle()\n'
    '        else:\n'
    '            if self._hover_annot:\n'
    '                self._hover_annot.set_visible(False)\n'
    '                self.draw_idle()\n'
    '\n'
    '    def _make_legend_interactive(self, ax):\n'
    '        """设置图例可拖动、可编辑、无边框"""\n'
    '        legend = ax.legend()\n'
    '        legend.set_draggable(True)\n'
    '        legend.set_frame_on(False)\n'
    '        for text in legend.get_texts():\n'
    "            text.set_color(self._tokens['text'])\n"
    '            text.set_picker(True)\n'
    '\n'
    '    def _on_legend_pick(self, event):\n'
    '        """单击图例文本触发编辑"""\n'
    '        artist = event.artist\n'
    "        if not hasattr(artist, 'get_text'):\n"
    '            return\n'
    '        ax = artist.axes\n'
    '        legend = ax.get_legend()\n'
    '        if legend is not None:\n'
    '            legend.set_draggable(False)\n'
    '        old_text = artist.get_text()\n'
    '        parent = self.parent() if self.parent() else self\n'
    '\n'
    '        dlg = _LegendEditDialog(parent, old_text)\n'
    '        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.result_text != old_text:\n'
    '            new_text = dlg.result_text\n'
    '            for line in ax.get_lines():\n'
    '                if line.get_label() == old_text:\n'
    '                    line.set_label(new_text)\n'
    '                    break\n'
    '            self._make_legend_interactive(ax)\n'
    '            self.draw()\n'
    '        elif legend is not None:\n'
    '            legend.set_draggable(True)\n'
    '\n'
    '    # ── U2：主结果图的数据装配 ─────────────────────────────\n'
    '    @staticmethod\n'
    '    def _resolve_detail(details, battery_name):\n'
    '        """从 ``details`` 里取出某块电池的 detail（dict 按名字 / list 按 battery）。"""\n'
    '        if not details:\n'
    '            return {}\n'
    '        if isinstance(details, dict):\n'
    '            found = details.get(battery_name)\n'
    '            return found if isinstance(found, dict) else {}\n'
    '        for item in details:\n'
    "            if isinstance(item, dict) and item.get('battery') == battery_name:\n"
    '                return item\n'
    '        return {}\n'
    '\n'
    '    @staticmethod\n'
    '    def _primary_rolling_row(detail):\n'
    '        """主预测起点的滚动行：先对齐 forecast_start，再退回 0.5 起点 / 首个有效行。"""\n'
    "        rows = detail.get('rolling_rows') or []\n"
    '        if not rows:\n'
    '            return None\n'
    "        start = detail.get('forecast_start')\n"
    '        if start is not None:\n'
    '            for row in rows:\n'
    "                if row.get('start') == start:\n"
    '                    return row\n'
    "        primary_frac = detail.get('primary_start_frac')\n"
    '        if primary_frac is not None:\n'
    '            for row in rows:\n'
    '                try:\n'
    "                    if abs(float(row.get('start_frac', -1)) -\n"
    '                           float(primary_frac)) < 1e-9:\n'
    '                        return row\n'
    '                except (TypeError, ValueError):\n'
    '                    continue\n'
    '        for row in rows:\n'
    "            if row.get('status') == 'ok':\n"
    '                return row\n'
    '        return rows[0]\n'
    '\n'
    '    def _eol_positions(self, detail, measured, forecast, threshold_val):\n'
    '        """返回 ``(真实 EOL 下标, 预测 EOL 下标)``；判不出来时该位为 None。\n'
    '\n'
    '        优先用滚动行的 ``true_rul`` / ``pred_rul``（相对预测起点），缺失时才退回\n'
    '        用 :func:`_first_cross` 在实测 / 预测序列上找第一次跌破阈值的位置。\n'
    '        """\n'
    '        row = self._primary_rolling_row(detail)\n'
    "        start = detail.get('forecast_start')\n"
    '        true_index = pred_index = None\n'
    '        if row is not None:\n'
    "            base = row.get('start')\n"
    '            if base is None:\n'
    '                base = start if start is not None else 0\n'
    '            base = int(base)\n'
    "            true_rul = row.get('true_rul')\n"
    "            pred_rul = row.get('pred_rul')\n"
    '            if true_rul is not None:\n'
    '                true_index = base + int(true_rul)\n'
    '            if pred_rul is not None:\n'
    '                pred_index = base + int(pred_rul)\n'
    '        if true_index is None:\n'
    '            true_index = _first_cross(measured, threshold_val)\n'
    '        if pred_index is None and forecast:\n'
    '            offset = _first_cross(forecast, threshold_val)\n'
    '            if offset is not None:\n'
    '                base = start if start is not None else max(\n'
    '                    0, len(measured) - len(forecast))\n'
    '                pred_index = int(base) + int(offset)\n'
    '        if pred_index is None:\n'
    '            pred_index = true_index\n'
    '        return true_index, pred_index\n'
    '\n'
    '    @staticmethod\n'
    '    def _index_to_cycle(cycles, index):\n'
    '        """把序列下标换算成真实循环号；越界时按最后一个循环步长外推。"""\n'
    '        if index is None:\n'
    '            return None\n'
    '        index = int(index)\n'
    '        if index < 0:\n'
    '            return None\n'
    '        if not len(cycles):\n'
    '            return float(index)\n'
    '        if index < len(cycles):\n'
    '            return float(cycles[index])\n'
    '        step = float(cycles[-1] - cycles[-2]) if len(cycles) > 1 else 1.0\n'
    '        return float(cycles[-1]) + step * (index - len(cycles) + 1)\n'
    '\n'
    '    def _style_axis(self, ax, tokens, target_divisions=12):\n'
    '        """把主题 token 落到单个坐标轴：描边、刻度、网格（C2）。\n'
    '\n'
    '        U9：刻度要**密到能直接读数**。主刻度按 1/2/2.5/5 × 10ⁿ 的友好步长铺满，\n'
    '        中间再插 4 条次刻度（只画短刻度线、不写标签），这样既看得清数值，\n'
    '        又不会让标签互相压住。\n'
    '\n'
    '        刻度用**显式数组**下发（见 :func:`_apply_ticks` 的说明），不使用\n'
    '        有状态的 locator。\n'
    '        """\n'
    '        for name, spine in ax.spines.items():\n'
    "            spine.set_visible(name in ('left', 'bottom'))\n"
    "            spine.set_color(tokens['chart_spine'])\n"
    '            spine.set_linewidth(1.0)\n'
    "        ax.tick_params(axis='both', which='major', direction='in',\n"
    "                       length=6, width=1, colors=tokens['text_muted'],\n"
    "                       labelsize=9, labelcolor=tokens['text'])\n"
    "        ax.tick_params(axis='both', which='minor', direction='in',\n"
    "                       length=3, width=0.8, colors=tokens['text_dim'])\n"
    "        ax.grid(True, which='major', color=tokens['chart_grid'],\n"
    '                linewidth=0.5, alpha=0.5, zorder=0)\n'
    "        ax.grid(True, which='minor', color=tokens['chart_grid'],\n"
    '                linewidth=0.3, alpha=0.25, zorder=0)\n'
    '        ax.set_axisbelow(True)\n'
    '\n'
    '        x_lo, x_hi = sorted(ax.get_xlim())\n'
    '        _apply_ticks(ax.xaxis, x_lo, x_hi, target_divisions)\n'
    '        y_lo, y_hi = sorted(ax.get_ylim())\n'
    '        _apply_ticks(ax.yaxis, y_lo, y_hi, target_divisions)\n'
    '\n'
    '    def _attach_soh_axis(self, ax, rated_capacity, tokens):\n'
    '        """右侧 SOH% 副轴：容量 / 额定容量 × 100。\n'
    '\n'
    '        U9：SOH 刻度对齐到整数百分比步长，这样左右两轴都能读出准确数值\n'
    '        （左轴 Ah，右轴 %），不必在两条线之间目测换算。\n'
    '        """\n'
    '        if not rated_capacity or rated_capacity <= 0:\n'
    '            return None\n'
    '        secondary = ax.secondary_yaxis(\n'
    "            'right',\n"
    '            functions=(lambda y: y / rated_capacity * 100.0,\n'
    '                       lambda s: s * rated_capacity / 100.0))\n'
    "        secondary.set_ylabel('SOH (%)', fontsize=10, color=tokens['text_muted'])\n"
    "        secondary.tick_params(axis='y', which='major', direction='in',\n"
    "                              colors=tokens['text_muted'], labelsize=9,\n"
    '                              length=6, width=1,\n'
    "                              labelcolor=tokens['text'])\n"
    "        secondary.tick_params(axis='y', which='minor', direction='in',\n"
    "                              colors=tokens['text_dim'], length=3, width=0.8)\n"
    '        for name, spine in secondary.spines.items():\n'
    "            spine.set_visible(name == 'right')\n"
    "            spine.set_color(tokens['chart_spine'])\n"
    '\n'
    '        # 用当前容量范围换算出 SOH% 范围，再铺上整数百分比的显式刻度\n'
    '        y_lo, y_hi = sorted(ax.get_ylim())\n'
    '        if np.isfinite(y_lo) and np.isfinite(y_hi) and y_hi > y_lo:\n'
    '            soh_lo = y_lo / rated_capacity * 100.0\n'
    '            soh_hi = y_hi / rated_capacity * 100.0\n'
    '            # 百分比轴上 2.5% 这类步长显得别扭，优先 1/2/5/10/20/25/50\n'
    '            allowed = (0.5, 1.0, 2.0, 2.5, 5.0, 10.0, 20.0, 25.0, 50.0)\n'
    '            step = nice_step(soh_hi - soh_lo, 10)\n'
    '            step = min(allowed, key=lambda candidate: abs(candidate - step))\n'
    '            _apply_ticks(secondary.yaxis, soh_lo, soh_hi, 10,\n'
    '                         label_step=step)\n'
    '        return secondary\n'
    '\n'
    '    def _focus_y(self, ax, series_list, rated_capacity, threshold_val=None):\n'
    '        """U2：y 轴不再从 0 起，而是聚焦退化带（上下各留 4% 余量）。"""\n'
    '        focused = _focused_ylim(series_list, rated_capacity, threshold_val)\n'
    '        if focused is None:\n'
    '            return\n'
    '        y_lo, y_hi, ticks = focused\n'
    '        ax.set_ylim(y_lo, y_hi)\n'
    '        ax.set_yticks(ticks)\n'
    '\n'
    '    def _annotate_persistence_note(self, ax, tokens):\n'
    '        """U2：α≈0 时在图例旁标注「模型未超越平推」。"""\n'
    "        text = '模型未超越平推（α≈0）'\n"
    '        legend = ax.get_legend()\n'
    '        if legend is not None:\n'
    '            try:\n'
    '                ax.annotate(\n'
    '                    text, xy=(0.5, 0.0), xycoords=legend,\n'
    "                    xytext=(0, -6), textcoords='offset points',\n"
    "                    ha='center', va='top', fontsize=8.5,\n"
    "                    color=tokens['chart_threshold'],\n"
    '                    annotation_clip=False, zorder=10)\n'
    '                return\n'
    '            except (TypeError, ValueError):\n'
    '                pass\n'
    "        ax.text(0.99, 0.02, text, transform=ax.transAxes, ha='right',\n"
    "                va='bottom', fontsize=8.5, color=tokens['chart_threshold'])\n"
    '\n'
    '    def plot_results(self, battery_names, battery_data,\n'
    '                     prediction_by_battery, rated_capacity, threshold_ratio,\n'
    '                     details=None):\n'
    '        """主结果图（C2 + U2）：事实用墨色、模型输出用强调色、失效用朱砂。\n'
    '\n'
    '        ``details`` 可选，形如 ``{电池名: detail}`` 或 ``[detail, ...]``；认识的键：\n'
    '        ``forecast`` / ``forecast_start`` / ``forecast_band`` / ``rolling_rows`` /\n'
    '        ``primary_start_frac`` / ``persistence_blend``。缺任何一个都能正常出图。\n'
    '        """\n'
    "        self._last_plot_kind = 'results'\n"
    '        # 把 details 一并存进 payload：全屏重绘时 U2 的预测起点 / 区间 / EOL\n'
    '        # 标注不会丢（``replay_last_plot`` 用 ``*payload[1:]`` 原样转发）。\n'
    '        self._last_plot_payload = (\n'
    '            battery_names, battery_data, prediction_by_battery,\n'
    '            rated_capacity, threshold_ratio, details)\n'
    '        self.fig.clear()\n'
    '        self._subplot_keys_by_axis = {}\n'
    '        self._pan_state = None\n'
    '        # 重新走一次「首帧」路径：清掉旧坐标轴引用，LivePlot 会随新轴重建。\n'
    '        self._live_ax = None\n'
    '        self._live_plot = None\n'
    "        if hasattr(self, '_pick_cid'):\n"
    '            self.fig.canvas.mpl_disconnect(self._pick_cid)\n'
    '            self._pick_cid = None\n'
    '\n'
    "        tokens = apply_mpl_style(getattr(self, '_tokens', None) or active_tokens())\n"
    '        self._tokens = tokens\n'
    "        bg_color = tokens['chart_bg']\n"
    '        self.fig.patch.set_facecolor(bg_color)\n'
    '\n'
    '        valid_names = [\n'
    '            name for name in battery_names\n'
    '            if name in battery_data and name in prediction_by_battery\n'
    '        ]\n'
    '        total = len(valid_names)\n'
    '        if total == 0:\n'
    '            self.ax = self.fig.add_subplot(111)\n'
    "            self.ax.axis('off')\n"
    '            self.ax.set_facecolor(bg_color)\n'
    '            self.draw()\n'
    '            return\n'
    '\n'
    '        cols = 2 if total > 1 else 1\n'
    '        rows = (total + 1) // 2\n'
    '        axes = self.fig.subplots(rows, cols, squeeze=False)\n'
    '        axes = np.array(axes).flatten()\n'
    '\n'
    '        threshold_val = rated_capacity * threshold_ratio\n'
    '        threshold_label = (\n'
    "            f'失效阈值 {threshold_val:.3f} Ah（{threshold_ratio:.0%} 额定）')\n"
    '\n'
    '        for idx in range(total):\n'
    '            ax = axes[idx]\n'
    '            ax.set_facecolor(bg_color)\n'
    '            battery_name = valid_names[idx]\n'
    '            self._subplot_keys_by_axis[ax] = battery_name\n'
    '            detail = self._resolve_detail(details, battery_name)\n'
    '\n'
    '            entry = battery_data[battery_name]\n'
    '            measured = np.asarray(_series_values(entry), dtype=np.float64)\n'
    '            cycles = _series_cycles(entry, len(measured))\n'
    "            forecast = _as_float_list(detail.get('forecast'))\n"
    "            band = detail.get('forecast_band')\n"
    '\n'
    '            # ── 事实：实测容量 = 中性墨色细线 + 小圆点 ──\n'
    '            # 单电池时严格用墨色；多电池叠加时用主题分类色区分不同电池，\n'
    '            # 但仍保持实线（事实是实线、模型输出是虚线）。\n'
    '            if total > 1:\n'
    '                style = series_style(idx, tokens)\n'
    "                measured_color = style['color']\n"
    '            else:\n'
    "                measured_color = tokens['chart_measured']\n"
    '            if len(measured):\n'
    '                marker_step = max(1, len(cycles) // 24)\n'
    '                ax.plot(cycles, measured, color=measured_color, linewidth=1.2,\n'
    "                        marker='o', markersize=3, markevery=marker_step,\n"
    "                        label='真实值', zorder=3)\n"
    '\n'
    '            # ── 模型输出：递归预测（强调色、加粗虚线） ──\n'
    '            if forecast:\n'
    "                start = detail.get('forecast_start')\n"
    '                base = (int(start) if start is not None\n'
    '                        else max(0, len(measured) - len(forecast)))\n'
    '                forecast_x = [self._index_to_cycle(cycles, base + i)\n'
    '                              for i in range(len(forecast))]\n'
    "                ax.plot(forecast_x, forecast, color=tokens['chart_forecast'],\n"
    "                        linewidth=2.0, linestyle='--', label='预测值', zorder=4)\n"
    '                if band:\n'
    '                    try:\n'
    '                        band_lo, band_hi = band\n'
    '                    except (TypeError, ValueError):\n'
    '                        band_lo = band_hi = None\n'
    '                    if (band_lo is not None and len(band_lo) == len(forecast)\n'
    '                            and len(band_hi) == len(forecast)):\n'
    '                        ax.fill_between(\n'
    '                            forecast_x, band_lo, band_hi,\n'
    "                            color=tokens['chart_forecast'],\n"
    "                            alpha=tokens['chart_band_alpha'], lw=0,\n"
    "                            label='预测区间(10–90%)', zorder=1)\n"
    '                # 预测起点：竖向点线 + 小标签\n'
    '                start_x = self._index_to_cycle(cycles, base)\n'
    '                if start_x is not None:\n'
    "                    ax.axvline(start_x, color=tokens['chart_forecast'],\n"
    "                               linestyle=':', linewidth=1.1, alpha=0.85,\n"
    '                               zorder=2)\n'
    '                    ax.annotate(\n'
    "                        '预测起点', xy=(start_x, 1.0),\n"
    "                        xycoords=('data', 'axes fraction'),\n"
    "                        xytext=(3, -4), textcoords='offset points',\n"
    "                        fontsize=8.5, color=tokens['chart_forecast'],\n"
    "                        ha='left', va='top', annotation_clip=False)\n"
    '            else:\n'
    '                # 没有 forecast 时退回老行为：递归预测序列 → 一步预测序列。\n'
    "                recursive = _as_float_list(detail.get('recursive_prediction'))\n"
    '                if recursive:\n'
    '                    base = max(0, len(measured) - len(recursive))\n'
    '                    recursive_x = [self._index_to_cycle(cycles, base + i)\n'
    '                                   for i in range(len(recursive))]\n'
    '                    ax.plot(recursive_x, recursive,\n'
    "                            color=tokens['chart_forecast'], linewidth=2.0,\n"
    "                            linestyle='--', label='预测值（递归）', zorder=4)\n"
    '                else:\n'
    '                    series = _as_float_list(\n'
    '                        prediction_by_battery.get(battery_name))\n'
    '                    if series and len(measured):\n'
    '                        if len(series) < len(measured):\n'
    '                            series = series + [np.nan] * (\n'
    '                                len(measured) - len(series))\n'
    '                        elif len(series) > len(measured):\n'
    '                            series = series[:len(measured)]\n'
    "                        ax.plot(cycles, series, color=tokens['chart_forecast'],\n"
    "                                linewidth=2.0, linestyle='--',\n"
    "                                label='预测值', zorder=4)\n"
    '\n'
    '            # ── 失效：朱砂虚线 ──\n'
    "            ax.axhline(y=threshold_val, color=tokens['chart_threshold'],\n"
    "                       linestyle='--', linewidth=1.3,\n"
    '                       label=threshold_label, zorder=5)\n'
    '\n'
    '            # ── EOL 标记：菱形=真实，三角形=预测（形状冗余，不靠颜色） ──\n'
    '            true_index, pred_index = self._eol_positions(\n'
    '                detail, measured, forecast, threshold_val)\n'
    "            for index, marker, label in ((true_index, 'D', '真实 EOL'),\n"
    "                                         (pred_index, '^', '预测 EOL')):\n"
    '                mark_x = self._index_to_cycle(cycles, index)\n'
    '                if mark_x is None:\n'
    '                    continue\n'
    "                ax.plot([mark_x], [threshold_val], linestyle='none',\n"
    '                        marker=marker, markersize=7,\n'
    "                        color=tokens['chart_threshold'],\n"
    "                        markeredgecolor=tokens['chart_bg'], zorder=6,\n"
    '                        label=label)\n'
    '\n'
    '            self._style_axis(ax, tokens)\n'
    '            self._focus_y(ax, [measured, forecast], rated_capacity, threshold_val)\n'
    '            self._attach_soh_axis(ax, rated_capacity, tokens)\n'
    '\n'
    '            self._make_legend_interactive(ax)\n'
    "            alpha = detail.get('persistence_blend')\n"
    '            if alpha is not None and float(alpha) < 0.05:\n'
    '                self._annotate_persistence_note(ax, tokens)\n'
    "            ax.set_xlabel('放电循环', fontsize=10, color=tokens['text_muted'])\n"
    "            ax.set_ylabel('容量 (Ah)', fontsize=10, color=tokens['text_muted'])\n"
    "            ax.set_title(battery_name + ' 预测值与真实值对比',\n"
    "                         fontsize=12, color=tokens['text'], fontweight='bold')\n"
    '\n'
    '        for idx in range(total, len(axes)):\n'
    "            axes[idx].axis('off')\n"
    '            axes[idx].set_facecolor(bg_color)\n'
    '\n'
    '        self.ax = axes[0]\n'
    '        self.fig.tight_layout(rect=[0, 0, 1, 0.98])\n'
    "        self._pick_cid = self.fig.canvas.mpl_connect('pick_event', self._on_legend_pick)\n"
    "        self._install_hover('放电循环', '容量 (Ah)')\n"
    '        self.draw()\n'
    '\n'
    '    def plot_tcp_predictions(self, measured, predicted, rated_capacity, threshold_ratio):\n'
    '        """实时 TCP 数据预测图：实测容量曲线 + 预测容量曲线 + 失效阈值线。\n'
    '\n'
    '        U5：坐标轴与两条线**只建一次**，之后每条消息只更新数据（``LivePlot``），\n'
    '        不再 ``fig.clear()`` 整图重建。方法签名保持不变。\n'
    '        """\n'
    "        self._last_plot_kind = 'tcp'\n"
    '        self._last_plot_payload = (\n'
    '            measured, predicted, rated_capacity, threshold_ratio)\n'
    '\n'
    "        tokens = apply_mpl_style(getattr(self, '_tokens', None) or active_tokens())\n"
    '        self._tokens = tokens\n'
    "        self.fig.patch.set_facecolor(tokens['chart_bg'])\n"
    '\n'
    '        first_time = self._live_plot is None or self._live_ax is None\n'
    '        if first_time:\n'
    '            self.fig.clear()\n'
    '            self._subplot_keys_by_axis = {}\n'
    '            self._pan_state = None\n'
    "            if hasattr(self, '_pick_cid'):\n"
    '                self.fig.canvas.mpl_disconnect(self._pick_cid)\n'
    '                self._pick_cid = None\n'
    '            self.ax = self.fig.add_subplot(111)\n'
    "            self.ax.set_facecolor(tokens['chart_bg'])\n"
    '            self._live_ax = self.ax\n'
    '            self._live_plot = LivePlot(self.ax, tokens)\n'
    '            self._live_plot.set_threshold(\n'
    '                rated_capacity * threshold_ratio, rated_capacity, threshold_ratio)\n'
    '            self._live_plot.attach_soh_axis(self._attach_soh_axis(\n'
    '                self.ax, rated_capacity, tokens))\n'
    '            self._style_axis(self.ax, tokens)\n'
    "            self.ax.set_xlabel('循环次数', fontsize=10,\n"
    "                               color=tokens['text_muted'])\n"
    "            self.ax.set_ylabel('容量 (Ah)', fontsize=10,\n"
    "                               color=tokens['text_muted'])\n"
    "            self.ax.set_title('实时 SOH 预测', fontsize=12,\n"
    "                              color=tokens['text'], fontweight='bold')\n"
    '            self._make_legend_interactive(self.ax)\n'
    '            self.fig.tight_layout()\n'
    "            self._install_hover('循环次数', '容量 (Ah)')\n"
    '        else:\n'
    '            self.ax = self._live_ax\n'
    '            self._live_plot.set_threshold(\n'
    '                rated_capacity * threshold_ratio, rated_capacity, threshold_ratio)\n'
    '\n'
    '        self._live_plot.push(measured, predicted)\n'
    '        self._live_plot.flush(self)\n'
    '\n'
    '    def save_figure(self, file_path):\n'
    "        self.fig.savefig(file_path, dpi=300, bbox_inches='tight')\n"
    '\n'
    '\n'
    'class ChartFullscreenDialog(QDialog):\n'
    '    """可缩放、可平移的独立全屏训练结果视图。"""\n'
    '\n'
    '    def __init__(self, source_canvas, parent=None, subplot_key=None):\n'
    '        super().__init__(parent)\n'
    "        title = subplot_key if subplot_key is not None else '全部子图'\n"
    "        self.setWindowTitle(f'训练结果 · {title} · 全屏观察')\n"
    "        self.setWindowIcon(get_dialog_icon('chart'))\n"
    '        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)\n'
    '\n'
    '        layout = QVBoxLayout(self)\n'
    '        layout.setContentsMargins(12, 10, 12, 12)\n'
    '        layout.setSpacing(6)\n'
    '\n'
    "        hint = QLabel('滚轮缩放 · 按住鼠标左键拖动平移 · 双击图表或按 Esc 返回')\n"
    "        hint.setProperty('role', 'subtitle')\n"
    '        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)\n'
    "        hint.setAccessibleName('全屏图表操作提示')\n"
    '\n'
    '        self.canvas = MplCanvas(\n'
    '            self, allow_fullscreen=False, interactive_navigation=True)\n'
    '        self.toolbar = CustomToolbar(self.canvas, self)\n'
    '        layout.addWidget(hint)\n'
    '        layout.addWidget(self.toolbar)\n'
    '        layout.addWidget(self.canvas, 1)\n'
    '\n'
    '        source_canvas.replay_last_plot(\n'
    '            self.canvas, subplot_key=subplot_key)\n'
    "        self._escape_shortcut = QShortcut(QKeySequence('Escape'), self)\n"
    '        self._escape_shortcut.activated.connect(self.close)\n'
)

# ---- ui/worker.py ----
_MODULE_SOURCES['ui.worker'] = (
    'from copy import deepcopy\n'
    'import time\n'
    'import numpy as np\n'
    'from PyQt6.QtCore import QThread, pyqtSignal\n'
    '\n'
    'from core.dataload import load_battery_from_paths\n'
    'from core.progress import make_progress_event\n'
    'from core.train import train\n'
    'from utils.config import TrainConfig\n'
    'from utils.logger import setup_logger\n'
    '\n'
    '\n'
    'class EvalWorker(QThread):\n'
    '    log_signal = pyqtSignal(str)\n'
    '    result_signal = pyqtSignal(object, float)\n'
    '    error_signal = pyqtSignal(str)\n'
    '    finished_signal = pyqtSignal()\n'
    '    progress_signal = pyqtSignal(object)\n'
    '    final_model_signal = pyqtSignal(object, dict)\n'
    '\n'
    '    def __init__(self, config, imported_paths, parent=None):\n'
    '        super().__init__(parent)\n'
    '        self.config = deepcopy(config)\n'
    '        self.imported_paths = tuple(deepcopy(imported_paths))\n'
    '        self._stop_requested = False\n'
    '        self.battery_dict = {}\n'
    '        self.battery_list = []\n'
    '\n'
    '    def request_stop(self):\n'
    '        self._stop_requested = True\n'
    '        self.requestInterruption()\n'
    '\n'
    '    def stop_requested(self):\n'
    '        return self._stop_requested or self.isInterruptionRequested()\n'
    '\n'
    '    def run(self):\n'
    '        try:\n'
    '            start_time = time.time()\n'
    '            progress_started_at = time.monotonic()\n'
    '\n'
    '            self.progress_signal.emit(make_progress_event(\n'
    "                'loading', started_at=progress_started_at,\n"
    '                current=0, total=1))\n'
    "            self.log_signal.emit('开始加载数据...')\n"
    '            self.battery_dict, self.battery_list = load_battery_from_paths(\n'
    '                self.imported_paths,\n'
    '                log_callback=self.log_signal.emit,\n'
    '                stop_flag=self.stop_requested,\n'
    '                voltage_upper=self.config.voltage_upper,\n'
    '                voltage_lower=self.config.voltage_lower,\n'
    '                adapter_type=self.config.adapter_type,\n'
    '                cc_step=self.config.cc_step,\n'
    '                cv_step=self.config.cv_step,\n'
    '                discharge_step=self.config.discharge_step,\n'
    '            )\n'
    '\n'
    '            if len(self.battery_dict) == 0:\n'
    "                self.error_signal.emit('未成功加载任何有效电池数据，请检查所选路径中是否包含符合格式的 .xlsx 或 .csv 文件。')\n"
    '                self.finished_signal.emit()\n'
    '                return\n'
    '\n'
    '            if self._stop_requested:\n'
    "                self.log_signal.emit('数据加载已被用户停止。')\n"
    '                self.finished_signal.emit()\n'
    '                return\n'
    '\n'
    "            self.log_signal.emit('────────────────────────────────────────')\n"
    "            self.log_signal.emit('开始训练评估...')\n"
    '            self.progress_signal.emit(make_progress_event(\n'
    "                'evaluation', started_at=progress_started_at,\n"
    '                seed=self.config.seed,\n'
    '                current=0, total=len(self.battery_list)))\n'
    '            self.log_signal.emit(\n'
    "                f'留一法验证：共 {len(self.battery_list)} 个电池，每次留 1 个作测试、其余训练，'\n"
    "                f'随机种子固定为 {self.config.seed}，确保结果可复现'\n"
    '            )\n'
    '\n'
    '            results = train(\n'
    '                config=self.config,\n'
    '                battery_dict=self.battery_dict,\n'
    '                battery_list=self.battery_list,\n'
    '                stop_flag=self.stop_requested,\n'
    '                log_callback=self.log_signal.emit,\n'
    '                progress_callback=self.progress_signal.emit,\n'
    '            )\n'
    '\n'
    '            if self._stop_requested:\n'
    "                self.log_signal.emit('训练已被用户停止。')\n"
    '                self.finished_signal.emit()\n'
    '                return\n'
    '\n'
    "            self.log_signal.emit('────────────────────────────────────────')\n"
    "            self.log_signal.emit('正在基于全部数据训练最终模型...')\n"
    '            self.progress_signal.emit(make_progress_event(\n'
    "                'final_training', started_at=progress_started_at,\n"
    '                seed=self.config.seed, current=0, total=1))\n'
    '            try:\n'
    '                from core.model_persistence import train_model_on_all_data\n'
    '                final_model, final_metadata = train_model_on_all_data(\n'
    '                    config=self.config,\n'
    '                    battery_dict=self.battery_dict,\n'
    '                    battery_list=self.battery_list,\n'
    '                    stop_flag=self.stop_requested,\n'
    '                    log_callback=self.log_signal.emit\n'
    '                )\n'
    '                self.final_model_signal.emit(final_model, final_metadata)\n'
    '                self.log_signal.emit(\'最终模型训练完成，可点击"保存模型"导出。\')\n'
    '            except Exception as e:\n'
    '                from core.cancellation import TrainingCancelled\n'
    '                if isinstance(e, TrainingCancelled):\n'
    '                    raise\n'
    "                self.log_signal.emit(f'最终模型训练失败：{e}')\n"
    '\n'
    "            self.log_signal.emit('\\n\\n')\n"
    '            metric_name = {\n'
    "                'rmse': 'RMSE', 'mae': 'MAE', 'r2': 'R²',\n"
    "                'pearson': 'Pearson', 're': 'RE', 'all': '全部'\n"
    '            }.get(self.config.metric, self.config.metric)\n'
    '            self.log_signal.emit(\n'
    "                f'各电池 {metric_name} 分数：'\n"
    '            )\n'
    '            for name, result in results.items():\n'
    "                item = result['detail']\n"
    "                ci = item.get('ci', {})\n"
    "                n_seeds = item.get('n_seeds', 1)\n"
    "                if n_seeds > 1 and 'rmse' in ci:\n"
    "                    c = ci['rmse']\n"
    '                    self.log_signal.emit(\n'
    '                        f\'  {name}：RMSE={c["mean"]:.6f} ± {c["std"]:.6f} \'\n'
    '                        f\'95%CI=[{c["lower"]:.6f}, {c["upper"]:.6f}]\')\n'
    '                else:\n'
    "                    score = result['score']\n"
    '                    score_text = (\n'
    "                        'N/A（截尾）' if score is None else f'{score:.6f}')\n"
    "                    self.log_signal.emit(f'  {name}：{score_text}')\n"
    '            if results:\n'
    '                scores = [\n'
    "                    result['score'] for result in results.values()\n"
    "                    if result['score'] is not None\n"
    "                    and np.isfinite(result['score'])\n"
    '                ]\n'
    '                avg_text = (\n'
    "                    f'{np.mean(scores):.6f}' if scores else 'N/A（截尾）')\n"
    "                self.log_signal.emit(f'→ 平均 {metric_name}: {avg_text}')\n"
    '                hint_map = {\n'
    "                    'rmse': 'RMSE 为均方根误差（Ah），越小越准，<0.02 优秀、<0.05 良好',\n"
    "                    'mae': 'MAE 为平均绝对误差，越小越准，对离群点不敏感',\n"
    "                    'r2': 'R² 为决定系数，越接近 1 越好，反映模型解释力',\n"
    "                    'pearson': 'Pearson 相关系数衡量预测与真实值的线性相关度，越接近 1 越好',\n"
    "                    're': 'RE 为寿命预测误差（0~1），越小越准',\n"
    "                    'all': '已展示全部指标',\n"
    '                }\n'
    "                hint = hint_map.get(self.config.metric, '')\n"
    '                if hint:\n'
    '                    self.log_signal.emit(hint)\n'
    '            else:\n'
    "                self.log_signal.emit(f'平均 {metric_name}: 0.0000')\n"
    '\n'
    '            elapsed = time.time() - start_time\n'
    '            hours, rem = divmod(elapsed, 3600)\n'
    '            minutes, seconds = divmod(rem, 60)\n'
    '            if hours > 0:\n'
    "                time_str = f'{int(hours)}小时{int(minutes)}分{seconds:.1f}秒'\n"
    '            elif minutes > 0:\n'
    "                time_str = f'{int(minutes)}分{seconds:.1f}秒'\n"
    '            else:\n'
    "                time_str = f'{seconds:.1f}秒'\n"
    "            self.log_signal.emit(f'训练总耗时：{time_str}')\n"
    '            self.progress_signal.emit(make_progress_event(\n'
    "                'complete', started_at=progress_started_at,\n"
    '                current=1, total=1))\n'
    '            self.result_signal.emit(results, elapsed)\n'
    '            self.finished_signal.emit()\n'
    '        except Exception as e:\n'
    '            from core.cancellation import TrainingCancelled\n'
    '            if isinstance(e, TrainingCancelled):\n'
    "                self.log_signal.emit('训练已在安全检查点停止。')\n"
    '                self.finished_signal.emit()\n'
    '                return\n'
    "            setup_logger().exception('评估工作线程异常')\n"
    '            concise = str(e).splitlines()[0][:500]\n'
    "            self.error_signal.emit(f'评估失败：{concise}')\n"
    '            self.finished_signal.emit()\n'
)

# ---- ui/predict_worker.py ----
_MODULE_SOURCES['ui.predict_worker'] = (
    'from copy import deepcopy\n'
    'import time\n'
    'import numpy as np\n'
    '\n'
    'from PyQt6.QtCore import QThread, pyqtSignal\n'
    '\n'
    'from core.prediction import predict_capacity_batch\n'
    'from core.progress import make_progress_event\n'
    'from core.train import evaluate_prediction_protocols\n'
    'from utils.logger import setup_logger\n'
    '\n'
    '\n'
    'METRIC_LABELS = {\n'
    "    'rmse': 'RMSE',\n"
    "    'mae': 'MAE',\n"
    "    'r2': 'R²',\n"
    "    'pearson': 'Pearson',\n"
    "    're': 'RE',\n"
    '}\n'
    '\n'
    '\n'
    'def evaluate_loaded_sequence(model, metadata, capacity, threshold_ratio,\n'
    "                             device='cpu'):\n"
    '    """Evaluate a loaded model with the same metrics and protocols as training."""\n'
    '    capacity = np.asarray(capacity, dtype=np.float32).reshape(-1)\n'
    "    window_size = int(metadata['window_size'])\n"
    "    rated_capacity = float(metadata['rated_capacity'])\n"
    '\n'
    '    def predict_batch(windows):\n'
    '        return predict_capacity_batch(\n'
    '            model, metadata, windows, device=device)\n'
    '\n'
    '    protocols = evaluate_prediction_protocols(\n'
    '        capacity, window_size, predict_batch,\n'
    '        rated_capacity, threshold_ratio)\n'
    "    one_step = protocols['one_step']\n"
    "    recursive = protocols['recursive']\n"
    "    metrics = dict(one_step['metrics'])\n"
    "    metrics['re'] = protocols['rul_re']\n"
    "    metrics['re_status'] = recursive['metrics'].get('re_status')\n"
    '    prediction = capacity[:window_size].tolist()\n'
    "    prediction.extend(one_step['prediction'].tolist())\n"
    '    detail = {\n'
    '        **metrics,\n'
    "        'one_step_metrics': one_step['metrics'],\n"
    "        'recursive_metrics': recursive['metrics'],\n"
    "        'one_step_prediction': one_step['prediction'].tolist(),\n"
    "        'recursive_prediction': recursive['prediction'].tolist(),\n"
    "        'rul_protocol': 'recursive_future',\n"
    '    }\n'
    '    return prediction, detail\n'
    '\n'
    '\n'
    'def summarize_selected_metrics(detail_list, metric):\n'
    '    """Return means for the selected metric, or all five metric means."""\n'
    '    if not detail_list:\n'
    '        return {}\n'
    "    if metric == 'all':\n"
    '        keys = tuple(METRIC_LABELS)\n'
    '    elif metric in METRIC_LABELS:\n'
    '        keys = (metric,)\n'
    '    else:\n'
    "        raise ValueError(f'不支持的评估指标: {metric}')\n"
    '    return {\n'
    '        key: mean_available_metric([item.get(key) for item in detail_list])\n'
    '        for key in keys\n'
    '    }\n'
    '\n'
    '\n'
    'def mean_available_metric(values):\n'
    '    available = [\n'
    '        float(value) for value in values\n'
    '        if value is not None and np.isfinite(value)\n'
    '    ]\n'
    '    if not available:\n'
    '        return None\n'
    '    return float(np.mean(available))\n'
    '\n'
    '\n'
    'def _format_metric(value):\n'
    "    return 'N/A（截尾）' if value is None else f'{value:.6f}'\n"
    '\n'
    '\n'
    'class PredictWorker(QThread):\n'
    '    log_signal = pyqtSignal(str)\n'
    '    result_signal = pyqtSignal(object, float)\n'
    '    error_signal = pyqtSignal(str)\n'
    '    finished_signal = pyqtSignal()\n'
    '    progress_signal = pyqtSignal(object)\n'
    '\n'
    '    def __init__(self, model, metadata, imported_paths, config, parent=None):\n'
    '        super().__init__(parent)\n'
    '        self._model = model\n'
    '        self._metadata = metadata\n'
    '        self.imported_paths = tuple(deepcopy(imported_paths))\n'
    '        self.battery_dict = {}\n'
    '        self.battery_list = []\n'
    '        self.config = deepcopy(config)\n'
    '        self._stop_requested = False\n'
    '\n'
    '    def request_stop(self):\n'
    '        self._stop_requested = True\n'
    '        self.requestInterruption()\n'
    '\n'
    '    def stop_requested(self):\n'
    '        return self._stop_requested or self.isInterruptionRequested()\n'
    '\n'
    '    def run(self):\n'
    '        try:\n'
    '            start_time = time.time()\n'
    '            progress_started_at = time.monotonic()\n'
    '\n'
    '            from core.dataload import load_battery_from_paths\n'
    '            self.progress_signal.emit(make_progress_event(\n'
    "                'loading', started_at=progress_started_at,\n"
    '                current=0, total=1))\n'
    "            self.log_signal.emit('开始加载数据...')\n"
    '            self.battery_dict, self.battery_list = load_battery_from_paths(\n'
    '                self.imported_paths,\n'
    '                log_callback=self.log_signal.emit,\n'
    '                stop_flag=self.stop_requested,\n'
    '                voltage_upper=self.config.voltage_upper,\n'
    '                voltage_lower=self.config.voltage_lower,\n'
    '                adapter_type=self.config.adapter_type,\n'
    '                cc_step=self.config.cc_step,\n'
    '                cv_step=self.config.cv_step,\n'
    '                discharge_step=self.config.discharge_step,\n'
    '            )\n'
    '            if len(self.battery_dict) == 0:\n'
    "                self.error_signal.emit('未成功加载任何有效电池数据。')\n"
    '                self.finished_signal.emit()\n'
    '                return\n'
    '\n'
    "            mode = self._metadata['mode']\n"
    "            window_size = self._metadata['window_size']\n"
    "            rated_capacity = self._metadata.get('rated_capacity', self.config.rated_capacity)\n"
    '            threshold_ratio = self.config.threshold_ratio\n'
    '            device = self.config.device\n'
    '\n'
    '            results = {}\n'
    '\n'
    '            for index, name in enumerate(self.battery_list):\n'
    '                if self._stop_requested:\n'
    '                    break\n'
    '                if name not in self.battery_dict:\n'
    '                    continue\n'
    "                capacity = self.battery_dict[name]['capacity'].tolist()\n"
    '                if len(capacity) <= window_size + 1:\n'
    "                    self.log_signal.emit(f'跳过 {name}：循环数不足（需>{window_size}）')\n"
    '                    continue\n'
    '\n'
    '                self.log_signal.emit(\n'
    "                    f'[{name}] 预测中，测试样本 {len(capacity) - window_size}...')\n"
    '                self.progress_signal.emit(make_progress_event(\n'
    "                    'prediction',\n"
    '                    started_at=progress_started_at,\n'
    '                    battery=name,\n'
    '                    current=index + 1,\n'
    '                    total=len(self.battery_list),\n'
    '                ))\n'
    '\n'
    '                try:\n'
    '                    prediction, detail = evaluate_loaded_sequence(\n'
    '                        self._model, self._metadata, capacity,\n'
    '                        threshold_ratio=threshold_ratio, device=device)\n'
    '                    detail.update({\n'
    "                        'battery': name,\n"
    "                        'cycles': len(capacity),\n"
    "                        'model': mode,\n"
    '                    })\n'
    '                    selected_score = (\n'
    "                        detail['rmse'] if self.config.metric == 'all'\n"
    '                        else detail[self.config.metric]\n'
    '                    )\n'
    '                    results[name] = {\n'
    "                        'score': (\n"
    '                            float(selected_score)\n'
    '                            if selected_score is not None else None),\n'
    "                        'prediction': list(prediction),\n"
    "                        'detail': detail,\n"
    '                    }\n'
    '                    self.log_signal.emit(\n'
    '                        f\'[{name}] RMSE={detail["rmse"]:.4f} \'\n'
    '                        f\'MAE={detail["mae"]:.4f} R²={detail["r2"]:.4f} \'\n'
    '                        f\'Pearson={detail["pearson"]:.4f} \'\n'
    '                        f\'RE(递归)={_format_metric(detail["re"])}\')\n'
    '                except Exception as e:\n'
    "                    self.log_signal.emit(f'[{name}] 预测异常：{e}')\n"
    '                    continue\n'
    '\n'
    '            detail_list = [\n'
    "                result['detail'] for result in results.values()\n"
    '            ]\n'
    '            summaries = summarize_selected_metrics(\n'
    '                detail_list, self.config.metric)\n'
    "            if self.config.metric == 'all':\n"
    "                self.log_signal.emit('各电池全部指标已计算：')\n"
    '                for item in detail_list:\n'
    '                    self.log_signal.emit(\n'
    '                        f\'  {item["battery"]}：\' + \'，\'.join(\n'
    "                            f'{METRIC_LABELS[key]}='\n"
    "                            f'{_format_metric(item.get(key))}'\n"
    '                            for key in METRIC_LABELS))\n'
    '                for key, value in summaries.items():\n'
    '                    self.log_signal.emit(\n'
    "                        f'→ 平均 {METRIC_LABELS[key]}: '\n"
    "                        f'{_format_metric(value)}')\n"
    '            else:\n'
    '                metric_name = METRIC_LABELS[self.config.metric]\n'
    "                self.log_signal.emit(f'各电池 {metric_name} 分数：')\n"
    '                for item in detail_list:\n'
    '                    self.log_signal.emit(\n'
    '                        f\'  {item["battery"]}：\'\n'
    "                        f'{_format_metric(item.get(self.config.metric))}')\n"
    '                if summaries:\n'
    '                    self.log_signal.emit(\n'
    "                        f'→ 平均 {metric_name}: '\n"
    "                        f'{_format_metric(summaries[self.config.metric])}')\n"
    '\n'
    '            elapsed = time.time() - start_time\n'
    '            self.progress_signal.emit(make_progress_event(\n'
    "                'complete', started_at=progress_started_at,\n"
    '                current=1, total=1))\n'
    '            self.result_signal.emit(results, elapsed)\n'
    '            self.finished_signal.emit()\n'
    '        except Exception as e:\n'
    "            setup_logger().exception('加载模型预测线程异常')\n"
    '            concise = str(e).splitlines()[0][:500]\n'
    "            self.error_signal.emit(f'预测失败：{concise}')\n"
    '            self.finished_signal.emit()\n'
)

# ---- ui/tcp_server.py ----
_MODULE_SOURCES['ui.tcp_server'] = (
    '"""实验性 TCP 实时预测服务。\n'
    '\n'
    '改进方案 A1 / A10 的落地：\n'
    '\n'
    '- **A1**：旧实现里 ``initial_capacity`` 从未定义，只要预测序列越过 SOH=80%\n'
    '  就会抛 ``NameError``；而它在 ``QThread.run()`` 里执行，未捕获异常会让整个进程\n'
    '  闪退。现在 SOH 一律按 ``C / C_rated`` 计算，并且 ``run()`` 有异常兜底。\n'
    '- **A10**：默认只绑定 ``127.0.0.1``；可选局域网模式 + token 握手；消息解析\n'
    '  （``core.stream_protocol.parse_message``，19 种畸形输入全部返回 error、不抛异常）；\n'
    '  缓冲有上限（``deque(maxlen=5000)``）；每条消息不再同步跑上千步递归（限流 +\n'
    '  独立预测线程）；RUL 语义修正为「距最新已观测循环还有几个未来循环越过阈值」。\n'
    '"""\n'
    '\n'
    'import secrets\n'
    'import socket\n'
    'import threading\n'
    '\n'
    'from PyQt6.QtCore import QThread, pyqtSignal\n'
    '\n'
    'from core.prediction import predict_capacity_batch\n'
    'from core.stream_protocol import (\n'
    '    MAX_LINE,\n'
    '    LatestOnlyQueue,\n'
    '    PredictionJob,\n'
    '    parse_message,\n'
    ')\n'
    'from utils.crash_guard import guarded_run\n'
    '\n'
    '\n'
    "DEFAULT_HOST = '127.0.0.1'\n"
    "LAN_HOST = '0.0.0.0'\n"
    'DEFAULT_PORT = 8888\n'
    '\n'
    '\n'
    'class TCPServerWorker(QThread):\n'
    '    status_signal = pyqtSignal(str)\n'
    '    data_received_signal = pyqtSignal(float, float)\n'
    '    soh_update_signal = pyqtSignal(dict)\n'
    '    rul_update_signal = pyqtSignal(dict)\n'
    '    prediction_signal = pyqtSignal(list, list)\n'
    '    error_signal = pyqtSignal(str)\n'
    '\n'
    '    def __init__(self, model, metadata, config, port=DEFAULT_PORT,\n'
    '                 host=DEFAULT_HOST, allow_lan=False, auth_token=None,\n'
    '                 min_interval=1.0, parent=None):\n'
    '        super().__init__(parent)\n'
    '        self._model = model\n'
    '        self._metadata = metadata\n'
    '        self.config = config\n'
    '        self.port = int(port)\n'
    '        self.allow_lan = bool(allow_lan)\n'
    '        # 只有显式开启局域网模式才监听 0.0.0.0\n'
    '        self.host = LAN_HOST if self.allow_lan else DEFAULT_HOST\n'
    '        self._auth_token = auth_token if auth_token else (\n'
    '            secrets.token_hex(8) if self.allow_lan else None)\n'
    '        self.min_interval = float(min_interval)\n'
    '        self._stop_requested = False\n'
    '        # 用普通 Lock + try/finally 取代手动 QMutex.lock()/unlock()：\n'
    '        # 两者之间一旦抛异常，旧代码会永久死锁\n'
    '        self._lock = threading.Lock()\n'
    '\n'
    '        # 解析 / 缓冲 / 限流 / 预测都在纯 Python 的 PredictionJob 里，\n'
    '        # 因此这些逻辑可以在没有 Qt 的环境下完整单测（A10）。\n'
    '        metadata = metadata or {}\n'
    '        self._rated_capacity = float(\n'
    "            metadata.get('rated_capacity', config.rated_capacity))\n"
    '        self._window_size = int(\n'
    "            metadata.get('window_size', config.window_size))\n"
    "        self._device = getattr(config, 'device', 'cpu')\n"
    '        self._threshold = self._rated_capacity * float(config.threshold_ratio)\n'
    '        self._job = PredictionJob(\n'
    '            window=self._window_size,\n'
    '            step_fn=self._predict_windows,\n'
    '            threshold=self._threshold,\n'
    '            rated_capacity=self._rated_capacity,\n'
    '            min_interval=self.min_interval,\n'
    '        )\n'
    '        # 预测线程 + 「最新优先」队列（A10：预测不阻塞接收）\n'
    '        self._pending = LatestOnlyQueue()\n'
    '        self._predict_thread = None\n'
    '\n'
    '    def _predict_windows(self, windows):\n'
    '        """递归预测的 step_fn：走共用的 predict_capacity_batch。"""\n'
    '        return predict_capacity_batch(\n'
    '            self._model, self._metadata, windows, device=self._device)\n'
    '\n'
    '    # ── 生命周期 ──────────────────────────────────────────────\n'
    '    def request_stop(self):\n'
    '        self._stop_requested = True\n'
    '\n'
    '    def stop_requested(self):\n'
    '        return self._stop_requested\n'
    '\n'
    '    @property\n'
    '    def buffer(self):\n'
    '        with self._lock:\n'
    '            return self._job.history()\n'
    '\n'
    '    @property\n'
    '    def auth_token(self):\n'
    '        """局域网模式下需要客户端在首条消息里提供的 token。"""\n'
    '        return self._auth_token\n'
    '\n'
    '    # ── 主循环 ────────────────────────────────────────────────\n'
    "    @guarded_run(log_context='TCP 服务线程异常')\n"
    '    def run(self):\n'
    '        window_size = self._window_size\n'
    '        rated_capacity = self._rated_capacity\n'
    '\n'
    '        server_socket = None\n'
    '        try:\n'
    '            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)\n'
    '            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)\n'
    '            server_socket.bind((self.host, self.port))\n'
    '            server_socket.listen(1)\n'
    '            server_socket.settimeout(1.0)\n'
    '            self._start_prediction_thread()\n'
    '            if self.allow_lan:\n'
    '                self.status_signal.emit(\n'
    "                    f'TCP 服务已启动（局域网模式），监听 {self.host}:{self.port}；'\n"
    "                    f'客户端首条消息需带 token：{self._auth_token}')\n"
    '            else:\n'
    '                self.status_signal.emit(\n'
    "                    f'TCP 服务已启动，仅监听本机 {self.host}:{self.port}，'\n"
    "                    '等待客户端连接...')\n"
    '\n'
    '            while not self._stop_requested:\n'
    '                try:\n'
    '                    conn, addr = server_socket.accept()\n'
    '                except socket.timeout:\n'
    '                    continue\n'
    '                except OSError:\n'
    '                    break\n'
    '\n'
    "                self.status_signal.emit(f'客户端已连接：{addr[0]}:{addr[1]}')\n"
    '                conn.settimeout(1.0)\n'
    '                try:\n'
    '                    self._serve_connection(conn, rated_capacity, window_size)\n'
    '                except OSError as exc:\n'
    "                    self.status_signal.emit(f'连接中断：{exc}')\n"
    '                finally:\n'
    '                    try:\n'
    '                        conn.close()\n'
    '                    except OSError:\n'
    '                        pass\n'
    "                    self.status_signal.emit('客户端已断开')\n"
    '\n'
    '        except OSError as exc:\n'
    "            self.error_signal.emit(f'TCP 服务启动失败：{exc}')\n"
    '        finally:\n'
    '            if server_socket:\n'
    '                try:\n'
    '                    server_socket.close()\n'
    '                except OSError:\n'
    '                    pass\n'
    '            self._join_prediction_thread()\n'
    "            self.status_signal.emit('TCP 服务已停止')\n"
    '\n'
    '    def _start_prediction_thread(self):\n'
    '        """启动独立预测线程（A10：预测不阻塞接收）。"""\n'
    '        self._predict_thread = threading.Thread(\n'
    '            target=self._prediction_loop,\n'
    "            name='tcp-prediction',\n"
    '            daemon=True,\n'
    '        )\n'
    '        self._predict_thread.start()\n'
    '\n'
    '    def _join_prediction_thread(self, timeout=10.0):\n'
    '        thread = self._predict_thread\n'
    '        if thread is not None and thread.is_alive():\n'
    '            thread.join(timeout=timeout)\n'
    '        self._predict_thread = None\n'
    '\n'
    '    def _serve_connection(self, conn, rated_capacity, window_size):\n'
    '        """逐行处理一个客户端的消息；畸形输入只产生警告，不抛异常。"""\n'
    "        remaining = b''\n"
    '        authenticated = self._auth_token is None\n'
    '\n'
    '        while not self._stop_requested:\n'
    '            try:\n'
    '                data = conn.recv(4096)\n'
    '            except socket.timeout:\n'
    '                continue\n'
    '            if not data:\n'
    '                return\n'
    '            remaining += data\n'
    '            # 防止无换行的长报文把内存吃满\n'
    '            if len(remaining) > 16 * MAX_LINE:\n'
    "                self.status_signal.emit('警告：未换行数据过长，已丢弃缓冲')\n"
    "                remaining = b''\n"
    '                continue\n'
    '\n'
    "            while b'\\n' in remaining:\n"
    "                line, remaining = remaining.split(b'\\n', 1)\n"
    '                line = line.strip()\n'
    '                if not line:\n'
    '                    continue\n'
    '\n'
    '                if not authenticated:\n'
    '                    authenticated = self._check_token(line)\n'
    '                    continue\n'
    '\n'
    '                kind, value = parse_message(line, rated_capacity)\n'
    "                if kind == 'error':\n"
    "                    self.status_signal.emit(f'警告：{value}')\n"
    '                    continue\n'
    "                if kind == 'reset':\n"
    '                    self._job.reset()\n'
    "                    self.status_signal.emit('缓冲区已重置')\n"
    '                    continue\n'
    '\n'
    '                should_predict, history = self._job.feed(value)\n'
    '                self.data_received_signal.emit(\n'
    '                    value, value / rated_capacity * 100.0\n'
    '                    if rated_capacity > 0 else 0.0)\n'
    '                if should_predict:\n'
    '                    # A10：只把快照塞进「最新优先」队列，预测在独立线程里跑，\n'
    '                    # 接收线程立刻回去读下一条消息，不会被上千步递归堵住。\n'
    '                    self._pending.put_latest(history)\n'
    '\n'
    '    def _prediction_loop(self):\n'
    '        """独立预测线程：阻塞式消费最新快照，发完信号再取下一个。"""\n'
    '        while not self._stop_requested:\n'
    '            history = self._pending.get(timeout=0.2)\n'
    '            if history is None:\n'
    '                continue\n'
    '            if self._stop_requested:\n'
    '                break\n'
    '            self._predict_and_emit(history)\n'
    '\n'
    '    def _check_token(self, line):\n'
    '        """局域网模式的 token 握手：首条消息必须是 ``{"token": "..."}``。"""\n'
    '        import json\n'
    '\n'
    '        try:\n'
    "            message = json.loads(line.decode('utf-8'))\n"
    '        except (ValueError, UnicodeDecodeError):\n'
    "            self.status_signal.emit('警告：认证失败，连接已关闭')\n"
    "            raise OSError('认证失败')\n"
    "        token = message.get('token') if isinstance(message, dict) else None\n"
    '        if not isinstance(token, str) or not secrets.compare_digest(\n'
    '                token, self._auth_token):\n'
    "            self.status_signal.emit('警告：token 不匹配，连接已关闭')\n"
    "            raise OSError('认证失败')\n"
    "        self.status_signal.emit('客户端认证通过')\n"
    '        return True\n'
    '\n'
    '    def _predict_and_emit(self, history):\n'
    '        """做一次真正的 RUL 预测；出错时记录并上报，而不是静默 break。\n'
    '\n'
    '        本方法在**预测线程**里执行（见 :meth:`_prediction_loop`），因此可以\n'
    '        安全地耗上数秒而不影响接收。\n'
    '        """\n'
    '        try:\n'
    '            result = self._job.predict(history)\n'
    '        except Exception as exc:                      # noqa: BLE001\n'
    "            self.status_signal.emit(f'警告：预测失败（{type(exc).__name__}: {exc}）')\n"
    '            return\n'
    "        forecast = result['forecast']\n"
    "        self.prediction_signal.emit(result['history'], forecast)\n"
    "        self.soh_update_signal.emit(result['soh_stages'])\n"
    '        self.rul_update_signal.emit({\n'
    "            'rul': result['rul'],\n"
    "            'threshold': self._job.threshold,\n"
    "            'rated_capacity': self._job.rated_capacity,\n"
    "            'unit': 'cycles',\n"
    "            'definition': '距最新已观测循环还有几个未来循环越过失效阈值',\n"
    '        })\n'
    '\n'
    '\n'
    'class TcpPredictionServer(TCPServerWorker):\n'
    '    """向后兼容别名（旧代码可能按这个名字导入）。"""\n'
)

# ---- ui/tcp_display.py ----
_MODULE_SOURCES['ui.tcp_display'] = (
    '"""TCP 实时数据接入独立显示窗口。\n'
    '\n'
    'A10 后服务端发出的数据形状变了：\n'
    '\n'
    "- ``soh_update_signal``  → ``{pct: {'cycle_offset': int|None, 'reached': bool}}``\n"
    "- ``rul_update_signal``  → ``{'rul': int|None, 'threshold': float,\n"
    "  'rated_capacity': float, 'unit': 'cycles', 'definition': str}``\n"
    '\n'
    '旧实现把 RUL 当成「SOH 从 pct% 掉到 80% 需要多少个循环」，那**不是**从现在起的\n'
    '剩余寿命；这里按新语义展示。\n'
    '"""\n'
    '\n'
    'from PyQt6.QtCore import Qt\n'
    'from PyQt6.QtWidgets import (\n'
    '    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QWidget,\n'
    '    QSizePolicy,\n'
    ')\n'
    'from ui.chart_show import MplCanvas\n'
    'from ui.style import theme_tokens\n'
    'from utils.icon_generator import get_dialog_icon\n'
    '\n'
    '\n'
    'class TcpDisplayWindow(QDialog):\n'
    '    """TCP 实时数据接入独立显示窗口"""\n'
    '\n'
    '    def __init__(self, parent=None):\n'
    '        super().__init__(parent)\n'
    "        self.setWindowTitle('实时数据接入 — SOH / RUL 预测')\n"
    "        self.setWindowIcon(get_dialog_icon('tcp'))\n"
    '        self.resize(1200, 800)\n'
    '        self.setMinimumSize(900, 600)\n'
    '\n'
    '        self._measured = []\n'
    '        self._predicted = []\n'
    '        self._current_capacity = None\n'
    '        self._current_soh = None\n'
    '        self._tokens = theme_tokens()\n'
    '\n'
    '        self._build_ui()\n'
    '\n'
    '    def _build_ui(self):\n'
    '        tokens = self._tokens\n'
    '        layout = QVBoxLayout(self)\n'
    '\n'
    '        # ── 状态栏 ──\n'
    "        self.status_label = QLabel('等待数据...')\n"
    '        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)\n'
    "        self.status_label.setProperty('role', 'resultSummaryTitle')\n"
    '        self.status_label.setStyleSheet(\n'
    "            f'font-size: 14px; font-weight: bold; padding: 10px;'\n"
    '            f\' color: {tokens["primary_d"]};\'\n'
    '            f\' background: {tokens["bg_surface"]};\'\n'
    '            f\' border: 1px solid {tokens["border"]}; border-radius: 4px;\'\n'
    "            ' letter-spacing: 1px;'\n"
    '        )\n'
    '        layout.addWidget(self.status_label)\n'
    '\n'
    '        # ── 图表 ──\n'
    '        self.canvas = MplCanvas()\n'
    '        self.canvas.setSizePolicy(\n'
    '            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)\n'
    '        layout.addWidget(self.canvas, 2)\n'
    '\n'
    '        # ── 底部：SOH 表 / RUL 表 ──\n'
    '        bottom = QWidget()\n'
    '        bottom_layout = QHBoxLayout(bottom)\n'
    '        bottom_layout.setContentsMargins(0, 0, 0, 0)\n'
    '        bottom_layout.setSpacing(10)\n'
    '\n'
    "        soh_group = QGroupBox('SOH 阶段预测')\n"
    '        soh_layout = QVBoxLayout()\n'
    "        self.soh_label = QLabel('等待数据...')\n"
    '        self.soh_label.setTextFormat(Qt.TextFormat.RichText)\n'
    '        self.soh_label.setAlignment(Qt.AlignmentFlag.AlignTop)\n'
    '        self.soh_label.setWordWrap(True)\n'
    '        soh_layout.addWidget(self.soh_label)\n'
    '        soh_group.setLayout(soh_layout)\n'
    '\n'
    "        rul_group = QGroupBox('剩余使用寿命 (RUL)')\n"
    '        rul_layout = QVBoxLayout()\n'
    "        self.rul_label = QLabel('等待数据...')\n"
    '        self.rul_label.setTextFormat(Qt.TextFormat.RichText)\n'
    '        self.rul_label.setAlignment(Qt.AlignmentFlag.AlignTop)\n'
    '        self.rul_label.setWordWrap(True)\n'
    '        rul_layout.addWidget(self.rul_label)\n'
    '        rul_group.setLayout(rul_layout)\n'
    '\n'
    '        bottom_layout.addWidget(soh_group, 1)\n'
    '        bottom_layout.addWidget(rul_group, 1)\n'
    '        layout.addWidget(bottom, 1)\n'
    '\n'
    '    # ── 主题 ─────────────────────────────────────────────────\n'
    '    def apply_theme_tokens(self, tokens):\n'
    '        self._tokens = tokens\n'
    '        if self._measured or self._predicted:\n'
    '            self.canvas.apply_theme_tokens(tokens)\n'
    '            self.canvas.plot_tcp_predictions(\n'
    '                self._measured, self._predicted,\n'
    '                self._rated_capacity, self._threshold_ratio)\n'
    '\n'
    '    # ── 更新 ─────────────────────────────────────────────────\n'
    '    def update_status(self, capacity, soh):\n'
    '        self._current_capacity = capacity\n'
    '        self._current_soh = soh\n'
    '        self.status_label.setText(\n'
    "            f'当前容量：{capacity:.4f} Ah  |  SOH：{soh:.1f}%  |  '\n"
    "            f'已接收 {len(self._measured)} 个循环')\n"
    '\n'
    '    def update_chart(self, measured, predicted, rated_capacity, threshold_ratio):\n'
    '        self._measured = list(measured)\n'
    '        self._predicted = list(predicted)\n'
    '        self._rated_capacity = rated_capacity\n'
    '        self._threshold_ratio = threshold_ratio\n'
    '        self.canvas.plot_tcp_predictions(\n'
    '            measured, predicted, rated_capacity, threshold_ratio)\n'
    '\n'
    '    def update_soh(self, soh_info):\n'
    '        tokens = self._tokens\n'
    '        rows = [\n'
    '            \'<table border="0" cellpadding="6" cellspacing="0" width="100%"\',\n'
    '            \'       style="border-collapse:collapse;\'\n'
    '            f\' color:{tokens["text"]}; font-size:10pt;">\',\n'
    '            f\'<tr style="background:{tokens["primary"]};\'\n'
    '            f\' color:{tokens["on_accent"]}; font-weight:bold;">\',\n'
    "            '<th>SOH (%)</th><th>距最新循环</th><th>状态</th></tr>',\n"
    '        ]\n'
    '        for pct in (100, 95, 90, 85, 80):\n'
    '            info = soh_info.get(pct, {}) or {}\n'
    "            offset = info.get('cycle_offset')\n"
    "            reached = info.get('reached')\n"
    "            offset_str = '—' if offset is None else f'{offset:+d}'\n"
    '            if offset is None:\n'
    "                state = '预测期内未到达'\n"
    '            elif reached:\n'
    "                state = '✓ 已到达'\n"
    '            else:\n'
    "                state = '预测中'\n"
    '            rows.append(\n'
    '                f\'<tr style="background:{tokens["bg_base"]};\'\n'
    '                f\' border-bottom:1px solid {tokens["border_soft"]};">\'\n'
    '                f\'<td style="color:{tokens["primary"]}; font-weight:bold;">\'\n'
    "                f'{pct}%</td>'\n"
    "                f'<td>{offset_str}</td><td>{state}</td></tr>'\n"
    '            )\n'
    "        rows.append('</table>')\n"
    "        self.soh_label.setText(''.join(rows))\n"
    '\n'
    '    def update_rul(self, rul_info):\n'
    '        tokens = self._tokens\n'
    "        rul = rul_info.get('rul')\n"
    "        threshold = rul_info.get('threshold')\n"
    "        rated = rul_info.get('rated_capacity')\n"
    '        if rul is None:\n'
    "            value_text = '预测期内不会越过失效阈值'\n"
    '        elif rul == 0:\n'
    "            value_text = '0 个循环（当前已低于失效阈值）'\n"
    '        else:\n'
    "            value_text = f'{int(rul)} 个循环'\n"
    '        threshold_text = (\n'
    "            f'{threshold:.4f} Ah'\n"
    "            f'（额定 {rated:.4f} Ah 的 '\n"
    "            f'{(threshold / rated * 100) if rated else 0:.0f}%）'\n"
    "            if threshold is not None and rated else '—')\n"
    '        rows = [\n'
    '            \'<table border="0" cellpadding="6" cellspacing="0" width="100%"\',\n'
    '            \'       style="border-collapse:collapse;\'\n'
    '            f\' color:{tokens["text"]}; font-size:10pt;">\',\n'
    '            f\'<tr style="background:{tokens["success"]};\'\n'
    '            f\' color:{tokens["on_accent"]}; font-weight:bold;">\',\n'
    "            '<th>项目</th><th>数值</th></tr>',\n"
    '            f\'<tr style="background:{tokens["bg_base"]};">\'\n'
    "            f'<td>剩余寿命 (RUL)</td><td>{value_text}</td></tr>',\n"
    '            f\'<tr style="background:{tokens["bg_base"]};">\'\n'
    "            f'<td>失效阈值</td><td>{threshold_text}</td></tr>',\n"
    "            '</table>',\n"
    '            f\'<p style="color:{tokens["text_muted"]}; font-size:9pt;">\'\n'
    '            f\'{rul_info.get("definition", "")}</p>\',\n'
    '        ]\n'
    "        self.rul_label.setText(''.join(rows))\n"
    '\n'
    '    def closeEvent(self, event):\n'
    '        self.hide()\n'
    '        event.ignore()\n'
)

# ---- ui/main_window.py ----
_MODULE_SOURCES['ui.main_window'] = (
    'import os\n'
    'import sys\n'
    'import ctypes\n'
    'import json\n'
    'import glob\n'
    '\n'
    'import torch\n'
    'import numpy as np\n'
    '\n'
    'from PyQt6.QtCore import (\n'
    '    Qt, QTimer, QSignalBlocker, QSettings,\n'
    '    QSortFilterProxyModel,\n'
    ')\n'
    'from PyQt6.QtWidgets import (\n'
    '    QApplication, QWidget, QMainWindow, QFileDialog, QLabel, QListWidget,\n'
    '    QTextEdit, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QDoubleSpinBox,\n'
    '    QSpinBox, QComboBox, QLineEdit, QMessageBox, QSizePolicy,\n'
    '    QSplitter, QScrollArea, QAbstractSpinBox, QAbstractItemView, QProgressBar, QStatusBar,\n'
    '    QDialog, QFrame, QToolButton, QTabWidget, QTableView, QHeaderView,\n'
    '    QPushButton, QCheckBox,\n'
    ')\n'
    'from PyQt6.QtGui import (\n'
    '    QTextCursor, QShortcut, QKeySequence, QFontMetrics, QIntValidator,\n'
    ')\n'
    'from ui.chart_show import MplCanvas, CustomToolbar, apply_sup_sub\n'
    'from ui.worker import EvalWorker\n'
    'from ui.animated_button import AnimatedButton\n'
    'from ui.style import apply_theme, theme_tokens\n'
    'from ui.result_model import (\n'
    '    COLUMNS,\n'
    '    COLUMN_WIDTHS,\n'
    '    ResultTableModel,\n'
    '    bootstrap_summary,\n'
    '    rows_from_details,\n'
    '    summary_row,\n'
    '    to_csv,\n'
    ')\n'
    'from utils.config import (\n'
    '    DEVICE_UI,\n'
    '    FEATURE_OPTIONS,\n'
    '    NORM_UI,\n'
    '    THEME_UI,\n'
    '    TrainConfig,\n'
    '    from_ui,\n'
    '    load_config,\n'
    '    normalize_device,\n'
    '    normalize_model_name,\n'
    '    save_config,\n'
    '    to_ui,\n'
    ')\n'
    'from utils.logger import setup_logger\n'
    'from utils.paths import FIGURE_DIR, MODEL_DIR, OUTPUTS_DIR\n'
    'from utils.icon_generator import get_app_icon, get_dialog_icon, show_message\n'
    'from core.adapters import get_adapter_list\n'
    'from core.result_semantics import analyze_failure_cycles\n'
    'from core.report_export import (\n'
    '    ExportCancelled,\n'
    '    ReportExportError,\n'
    '    atomic_save_figure,\n'
    '    export_run_report,\n'
    ')\n'
    'from core.run_snapshot import RunSnapshot\n'
    'from theme_tokens import DEFAULT_THEME, THEMES, THEME_SETTINGS_KEY\n'
    '# ── JSON 配置导入映射 ──────────────────────────────────────\n'
    '\n'
    '#: 主题与窗口几何的持久化设置（U4 / C5）\n'
    "SETTINGS_ORG = 'BatterySOH'\n"
    "SETTINGS_APP = 'AssessmentSystem'\n"
    '\n'
    '\n'
    'def _settings():\n'
    '    return QSettings(SETTINGS_ORG, SETTINGS_APP)\n'
    '\n'
    '\n'
    'def restore_or_default_geometry(window):\n'
    '    """恢复上次的窗口几何；没有记录时按可用屏幕自适应（U4）。\n'
    '\n'
    '    旧实现固定 ``resize(1600, 900)``，在 1366×768 的笔记本上起始尺寸就超出屏幕。\n'
    '    """\n'
    '    settings = _settings()\n'
    "    geometry = settings.value('geometry')\n"
    '    if geometry is not None and window.restoreGeometry(geometry):\n'
    '        return False\n'
    '    screen = window.screen()\n'
    '    if screen is not None:\n'
    '        available = screen.availableGeometry()\n'
    '        window.resize(\n'
    '            min(1600, int(available.width() * 0.9)),\n'
    '            min(900, int(available.height() * 0.9)))\n'
    '    else:\n'
    '        window.resize(1280, 800)\n'
    '    return True\n'
    '\n'
    '\n'
    'def save_geometry(window):\n'
    "    _settings().setValue('geometry', window.saveGeometry())\n"
    '\n'
    '\n'
    'def saved_theme_mode():\n'
    '    """读取已保存的主题模式（供启动闪屏在重库加载前使用）。\n'
    '\n'
    '    默认 **深色（墨夜）**：这是产品默认外观，浅色（宣纸）为可选。\n'
    '    用户选择会被 QSettings 记住，下次启动沿用。\n'
    '    """\n'
    '    value = _settings().value(THEME_SETTINGS_KEY, DEFAULT_THEME)\n'
    '    return str(value).strip().lower() if value else DEFAULT_THEME\n'
    '\n'
    '\n'
    'def _map_metric(val):\n'
    '    m = str(val).lower()\n'
    "    return {'rmse': 'RMSE', 'mae': 'MAE', 'r2': 'R²', 'pearson': 'Pearson',\n"
    "            're': 'RE', 'all': '全部'}.get(m, 'RMSE')\n"
    '\n'
    'def _map_norm(val):\n'
    '    """规范键 -> 界面文本（同时兼容旧的界面文本输入）。"""\n'
    '    return to_ui(NORM_UI, from_ui(NORM_UI, val))\n'
    '\n'
    'def _map_device(val):\n'
    '    return to_ui(DEVICE_UI, normalize_device(val))\n'
    '\n'
    '\n'
    'def format_metric_value(value):\n'
    '    if value is None or not np.isfinite(value):\n'
    "        return 'N/A（截尾）'\n"
    "    return f'{value:.6f}'\n"
    '\n'
    '_JSON_CONFIG_MAP = [\n'
    "    (('rated_capacity',),           'rated_capacity_spin',      float),\n"
    "    (('threshold_ratio', 'THRESHOLD_RATIO'), 'threshold_ratio_spin', float),\n"
    "    (('voltage_upper',),                     'voltage_upper_spin',       float),\n"
    "    (('voltage_lower',),                     'voltage_lower_spin',       float),\n"
    "    (('window_size', 'Feature Size'),        'feature_size_spin',     int),\n"
    "    (('metric',),                            'metric_combo',          _map_metric),\n"
    "    (('seed', 'random_seed'),                'seed_spin',             int),\n"
    "    (('hidden_dim',),                'hidden_dim_spin',         int),\n"
    "    (('epochs', 'num_epochs'),       'epochs_spin',             int),\n"
    "    (('norm_method', 'normalization'), 'norm_combo',            _map_norm),\n"
    "    (('device',),                     'device_combo',           _map_device),\n"
    "    (('n_estimators', 'xgb_n_estimators'),      'xgb_n_estimators_spin',      int),\n"
    "    (('xgb_learning_rate',),                    'xgb_learning_rate_spin',     float),\n"
    "    (('max_depth', 'xgb_max_depth'),            'xgb_max_depth_spin',         int),\n"
    "    (('subsample', 'xgb_subsample'),            'xgb_subsample_spin',         float),\n"
    "    (('colsample_bytree', 'xgb_colsample_bytree'), 'xgb_colsample_bytree_spin', float),\n"
    "    (('patience', 'early_stopping_rounds'),     'xgb_patience_spin',          int),\n"
    "    (('rf_n_estimators',),            'rf_n_estimators_spin',       int),\n"
    "    (('rf_max_depth',),               'rf_max_depth_spin',          int),\n"
    "    (('min_samples_leaf', 'rf_min_samples_leaf'), 'rf_min_samples_leaf_spin', int),\n"
    "    (('max_features', 'rf_max_features'), 'rf_max_features_spin',       float),\n"
    "    (('rf_patience',),                'rf_patience_spin',           int),\n"
    ']\n'
    '\n'
    '_FOLDER_DIALOG_TOOLTIPS = {\n'
    "    'backButton': '后退',\n"
    "    'forwardButton': '前进',\n"
    "    'toParentButton': '返回上一级',\n"
    "    'newFolderButton': '新建文件夹',\n"
    "    'listModeButton': '列表视图',\n"
    "    'detailModeButton': '详细信息视图',\n"
    '}\n'
    '\n'
    '\n'
    'def _hex_to_colorref(hex_color):\n'
    '    """``\'#RRGGBB\'`` -> Windows COLORREF（``0x00BBGGRR``）。"""\n'
    "    value = str(hex_color).lstrip('#')\n"
    '    if len(value) == 3:\n'
    "        value = ''.join(char * 2 for char in value)\n"
    '    red, green, blue = (int(value[index:index + 2], 16)\n'
    '                        for index in (0, 2, 4))\n'
    '    return (blue << 16) | (green << 8) | red\n'
    '\n'
    '\n'
    'def _apply_windows_paper_caption(dlg):\n'
    '    """在 Windows 11 上让此对话框的原生标题栏匹配当前主题。"""\n'
    "    if sys.platform != 'win32':\n"
    '        return\n'
    '    try:\n'
    '        hwnd = int(dlg.winId())\n'
    '        dwm = ctypes.windll.dwmapi\n'
    '        tokens = theme_tokens()\n'
    "        dark_mode = ctypes.c_int(1 if tokens is THEMES['dark'] else 0)\n"
    '        dwm.DwmSetWindowAttribute(\n'
    '            hwnd, 20, ctypes.byref(dark_mode), ctypes.sizeof(dark_mode))\n'
    '\n'
    '        DWMWA_BORDER_COLOR = 34\n'
    '        DWMWA_CAPTION_COLOR = 35\n'
    '        DWMWA_TEXT_COLOR = 36\n'
    '        # 颜色全部来自主题 token，深色主题下标题栏也会跟着变\n'
    '        for attribute, token_name in (\n'
    "                (DWMWA_BORDER_COLOR, 'border'),\n"
    "                (DWMWA_CAPTION_COLOR, 'bg_deep'),\n"
    "                (DWMWA_TEXT_COLOR, 'text')):\n"
    '            value = ctypes.c_uint(_hex_to_colorref(tokens[token_name]))\n'
    '            dwm.DwmSetWindowAttribute(\n'
    '                hwnd, attribute, ctypes.byref(value), ctypes.sizeof(value))\n'
    '    except (AttributeError, OSError, TypeError, KeyError):\n'
    '        # 旧版 Windows 不支持标题栏颜色属性时，内容区主题仍正常生效。\n'
    '        pass\n'
    '\n'
    '\n'
    'def _configure_folder_dialog(dlg):\n'
    '    """汉化文件夹对话框标签、工具提示和无障碍名称。"""\n'
    "    dlg.setLabelText(QFileDialog.DialogLabel.LookIn, '查找范围：')\n"
    "    dlg.setLabelText(QFileDialog.DialogLabel.FileName, '文件夹：')\n"
    "    dlg.setLabelText(QFileDialog.DialogLabel.FileType, '文件类型：')\n"
    "    dlg.setLabelText(QFileDialog.DialogLabel.Accept, '选择文件夹')\n"
    "    dlg.setLabelText(QFileDialog.DialogLabel.Reject, '取消')\n"
    '    for button in dlg.findChildren(QToolButton):\n'
    '        tooltip = _FOLDER_DIALOG_TOOLTIPS.get(button.objectName())\n'
    '        if tooltip:\n'
    '            button.setToolTip(tooltip)\n'
    '            button.setAccessibleName(tooltip)\n'
    '    _apply_windows_paper_caption(dlg)\n'
    '\n'
    '\n'
    'def _configure_button_row(layout, buttons, spacing=8):\n'
    '    """统一按钮行的尺寸策略，让控件等宽伸展且不会相互覆盖。"""\n'
    '    layout.setSpacing(spacing)\n'
    '    layout.setContentsMargins(0, 0, 0, 0)\n'
    '    for button in buttons:\n'
    '        text_width = QFontMetrics(button.font()).horizontalAdvance(button.text())\n'
    '        button.setMinimumWidth(max(72, text_width + 28))\n'
    '        button.setMinimumHeight(36)\n'
    '        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)\n'
    '        layout.addWidget(button, 1)\n'
    '\n'
    '\n'
    'def _create_step_input(accessible_name):\n'
    '    step_input = QLineEdit()\n'
    '    step_input.setAccessibleName(accessible_name)\n'
    "    step_input.setPlaceholderText('无')\n"
    '    step_input.setValidator(QIntValidator(0, 2_147_483_647, step_input))\n'
    '    step_input.setClearButtonEnabled(True)\n'
    '    step_input.setInputMethodHints(Qt.InputMethodHint.ImhDigitsOnly)\n'
    '    return step_input\n'
    '\n'
    '\n'
    'def _set_step_input(step_input, value):\n'
    "    step_input.setText('' if value is None else str(value))\n"
    '\n'
    '\n'
    'def _step_input_value(step_input):\n'
    '    text = step_input.text().strip()\n'
    '    if not text:\n'
    '        return None\n'
    '    state, _, _ = step_input.validator().validate(text, len(text))\n'
    '    return int(text) if state == QIntValidator.State.Acceptable else None\n'
    '\n'
    '\n'
    'class _HelpDialog(QDialog):\n'
    '    """模型参数帮助对话框（非模态，随模型切换实时更新）"""\n'
    '    def __init__(self, parent, mode):\n'
    '        super().__init__(parent)\n'
    "        self.setWindowTitle('参数设置帮助')\n"
    "        self.setWindowIcon(get_dialog_icon('help'))\n"
    '        self.resize(550, 600)\n'
    '        self.setMinimumSize(450, 400)\n'
    '\n'
    '        layout = QVBoxLayout(self)\n'
    '        self._text = QTextEdit()\n'
    '        self._text.setReadOnly(True)\n'
    '        layout.addWidget(self._text)\n'
    '\n'
    '        self.set_content(mode)\n'
    '\n'
    '    def set_content(self, mode):\n'
    "        content = MainWindow._HELP_CONTENT.get(mode, '<p>暂无该模型的帮助信息。</p>')\n"
    '        self._text.setHtml(content)\n'
    '\n'
    '\n'
    'class CollapsibleSection(QFrame):\n'
    '    """紧凑参数分区，可按需展开高级设置。"""\n'
    '\n'
    '    def __init__(self, title, expanded=True, parent=None):\n'
    '        super().__init__(parent)\n'
    "        self.setProperty('role', 'parameterSection')\n"
    '\n'
    '        layout = QVBoxLayout(self)\n'
    '        layout.setContentsMargins(4, 4, 4, 6)\n'
    '        layout.setSpacing(2)\n'
    '\n'
    '        self.toggle = QToolButton()\n'
    '        self.toggle.setText(title)\n'
    "        self.toggle.setProperty('role', 'sectionToggle')\n"
    '        self.toggle.setCheckable(True)\n'
    '        self.toggle.setChecked(expanded)\n'
    '        self.toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)\n'
    "        self.toggle.setAccessibleName(f'{title}，按空格展开或收起')\n"
    '        self.toggle.toggled.connect(self._set_expanded)\n'
    '        layout.addWidget(self.toggle)\n'
    '\n'
    '        self.content = QWidget()\n'
    '        self.form_layout = QFormLayout(self.content)\n'
    '        self.form_layout.setContentsMargins(10, 4, 10, 8)\n'
    '        self.form_layout.setHorizontalSpacing(12)\n'
    '        self.form_layout.setVerticalSpacing(7)\n'
    '        self.form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)\n'
    '        layout.addWidget(self.content)\n'
    '\n'
    '        self._set_expanded(expanded)\n'
    '\n'
    '    def _set_expanded(self, expanded):\n'
    '        self.content.setVisible(expanded)\n'
    '        arrow = Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow\n'
    '        self.toggle.setArrowType(arrow)\n'
    '\n'
    '\n'
    'class MainWindow(QMainWindow):\n'
    '    _independent_windows = []\n'
    '\n'
    '    def __init__(self):\n'
    '        super().__init__()\n'
    '        # 字体在**进程启动时**装好（battery_soh_app.py 在 QApplication 之后、\n'
    '        # 任何控件之前调用 ui.fonts.install_fonts）。这里刻意**不**碰\n'
    '        # QFontDatabase：在控件已存在之后再调用它的静态方法，会让本环境里\n'
    '        # 字体库缺失的 PyQt6（Qt6/lib/fonts 不存在）在后续绘制时段错误\n'
    '        # （0xC0000005，实测可稳定复现）。窗口只负责画界面，不负责装字体。\n'
    "        self.setWindowTitle('Battery SOH Assessment System')\n"
    '        self.setWindowIcon(get_app_icon())\n'
    '        self.setMinimumSize(1180, 700)\n'
    '        # U4：恢复上次几何；没有记录时按可用屏幕自适应，而不是硬编码 1600×900\n'
    '        restore_or_default_geometry(self)\n'
    '\n'
    '        self.imported_paths = []\n'
    "        self.current_mode = 'RNN'\n"
    '        self.worker = None\n'
    '        self._active_run_kind = None\n'
    "        self._finish_status_message = '准备就绪'\n"
    '        self._eval_rated_capacity = 1.1\n'
    '        self._eval_threshold_ratio = 0.8\n'
    '        self.battery_dict = {}\n'
    '        self.battery_list = []\n'
    '        self._active_run_snapshot = None\n'
    '        self._last_run_snapshot = None\n'
    '        self._result_batches = []\n'
    '        self._has_completed_training_run = False\n'
    '        self._child_training_windows = []\n'
    '        self._error_toast = None\n'
    '        self._theme_mode = saved_theme_mode()\n'
    '\n'
    '        self.loaded_model = None\n'
    '        self.loaded_metadata = None\n'
    '        self.final_trained_model = None\n'
    '        self.final_trained_metadata = None\n'
    '        self.tcp_server = None\n'
    '        self.tcp_running = False\n'
    '        self._tcp_window = None\n'
    '\n'
    '        self.logger = setup_logger()\n'
    '        self.init_ui()\n'
    '        self._install_sup_sub_shortcuts()\n'
    '        self._load_persisted_config()\n'
    '\n'
    '    def apply_theme(self, mode=None):\n'
    '        """应用全局宣纸水墨主题样式；``mode`` 为 ``\'light\'`` / ``\'dark\'``。"""\n'
    '        if mode is not None:\n'
    '            self._theme_mode = str(mode).strip().lower()\n'
    '        tokens = apply_theme(QApplication.instance(), self._theme_mode)\n'
    '        _settings().setValue(THEME_SETTINGS_KEY, self._theme_mode)\n'
    '        # 让结果表与图表跟着换色\n'
    "        if getattr(self, 'result_model', None) is not None:\n"
    '            self.result_model.set_tokens(tokens)\n'
    "        if getattr(self, 'canvas', None) is not None:\n"
    '            try:\n'
    '                self.canvas.apply_theme_tokens(tokens)\n'
    '            except AttributeError:\n'
    '                pass\n'
    '        self._sync_theme_button()\n'
    '        return tokens\n'
    '\n'
    '    def toggle_theme(self):\n'
    '        """浅色 / 深色主题切换（C5）。"""\n'
    "        self.apply_theme('light' if self._theme_mode == 'dark' else 'dark')\n"
    '        self.append_log(\n'
    "            f'主题已切换为：{THEME_UI.get(self._theme_mode, self._theme_mode)}')\n"
    '\n'
    '    def _load_persisted_config(self):\n'
    '        cfg = load_config()\n'
    '        if not cfg:\n'
    '            return\n'
    '        widget_map = {\n'
    "            'rated_capacity': self.rated_capacity_spin,\n"
    "            'threshold_ratio': self.threshold_ratio_spin,\n"
    "            'voltage_upper': self.voltage_upper_spin,\n"
    "            'voltage_lower': self.voltage_lower_spin,\n"
    "            'window_size': self.feature_size_spin,\n"
    "            'epochs': self.epochs_spin,\n"
    "            'hidden_dim': self.hidden_dim_spin,\n"
    "            'seed': self.seed_spin,\n"
    "            'n_seeds': self.n_seeds_spin,\n"
    "            'n_estimators': self.xgb_n_estimators_spin,\n"
    "            'learning_rate': self.xgb_learning_rate_spin,\n"
    "            'max_depth': self.xgb_max_depth_spin,\n"
    "            'subsample': self.xgb_subsample_spin,\n"
    "            'colsample_bytree': self.xgb_colsample_bytree_spin,\n"
    "            'min_samples_leaf': self.rf_min_samples_leaf_spin,\n"
    "            'max_features': self.rf_max_features_spin,\n"
    "            'patience': self.xgb_patience_spin,\n"
    '        }\n'
    '        for key, widget in widget_map.items():\n'
    '            if key in cfg:\n'
    '                try:\n'
    '                    widget.setValue(cfg[key])\n'
    '                except (TypeError, ValueError):\n'
    '                    pass\n'
    "        if 'mode' in cfg:\n"
    '            try:\n'
    "                self.select_mode(normalize_model_name(cfg['mode']))\n"
    '            except ValueError:\n'
    '                pass\n'
    "        if 'metric' in cfg and hasattr(self, 'metric_combo'):\n"
    "            idx = self.metric_combo.findText(cfg['metric'])\n"
    '            if idx >= 0:\n'
    '                self.metric_combo.setCurrentIndex(idx)\n'
    "        # A11：配置里存的是规范键（'cuda'），界面显示的是 'GPU (CUDA)'。\n"
    '        # 旧配置文件可能存了界面文本，from_ui 两种都接受。\n'
    "        if 'device' in cfg and hasattr(self, 'device_combo'):\n"
    "            idx = self.device_combo.findText(to_ui(DEVICE_UI, cfg['device']))\n"
    '            if idx >= 0:\n'
    '                self.device_combo.setCurrentIndex(idx)\n'
    "        if 'norm_method' in cfg and hasattr(self, 'norm_combo'):\n"
    '            idx = self.norm_combo.findText(\n'
    "                to_ui(NORM_UI, from_ui(NORM_UI, cfg['norm_method'])))\n"
    '            if idx >= 0:\n'
    '                self.norm_combo.setCurrentIndex(idx)\n'
    "        if 'feature_columns' in cfg and hasattr(self, 'feature_checks'):\n"
    "            selected = set(cfg['feature_columns'] or ['capacity'])\n"
    '            for name, checkbox in self.feature_checks.items():\n'
    '                checkbox.setChecked(name in selected)\n'
    "            self.feature_checks['capacity'].setChecked(True)\n"
    '        # 数据源配置\n'
    "        if 'adapter_type' in cfg and hasattr(self, 'adapter_combo'):\n"
    "            idx = self.adapter_combo.findData(cfg['adapter_type'])\n"
    '            if idx >= 0:\n'
    '                self.adapter_combo.setCurrentIndex(idx)\n'
    "        if 'cc_step' in cfg and hasattr(self, 'cc_step_input'):\n"
    "            _set_step_input(self.cc_step_input, cfg['cc_step'])\n"
    "        if 'cv_step' in cfg and hasattr(self, 'cv_step_input'):\n"
    "            _set_step_input(self.cv_step_input, cfg['cv_step'])\n"
    "        if 'discharge_step' in cfg and hasattr(self, 'discharge_step_input'):\n"
    '            _set_step_input(\n'
    "                self.discharge_step_input, cfg['discharge_step'])\n"
    '        # 触发适配器切换以更新控件状态\n'
    "        if hasattr(self, '_on_adapter_changed'):\n"
    '            self._on_adapter_changed()\n'
    '\n'
    '    def _save_persisted_config(self):\n'
    '        # A11：配置里只存"规范键"（\'cuda\' / \'rated\' / \'NASA\'），\n'
    "        # 界面文本只在界面层转换。旧版本把 'GPU (CUDA)' 直接写进 JSON，\n"
    '        # 导致导入自己保存的配置时 GPU 被静默切回 CPU。\n'
    '        cfg = {\n'
    "            'rated_capacity': self.rated_capacity_spin.value(),\n"
    "            'threshold_ratio': self.threshold_ratio_spin.value(),\n"
    "            'voltage_upper': self.voltage_upper_spin.value(),\n"
    "            'voltage_lower': self.voltage_lower_spin.value(),\n"
    "            'window_size': self.feature_size_spin.value(),\n"
    "            'epochs': self.epochs_spin.value(),\n"
    "            'hidden_dim': self.hidden_dim_spin.value(),\n"
    "            'seed': self.seed_spin.value(),\n"
    "            'n_seeds': self.n_seeds_spin.value(),\n"
    "            'mode': self.current_mode,\n"
    "            'metric': from_ui(\n"
    "                {'rmse': 'RMSE', 'mae': 'MAE', 'r2': 'R²',\n"
    "                 'pearson': 'Pearson', 're': 'RE', 'all': '全部'},\n"
    "                self.metric_combo.currentText(), 'rmse'),\n"
    "            'device': normalize_device(self.device_combo.currentText()),\n"
    "            'norm_method': from_ui(\n"
    "                NORM_UI, self.norm_combo.currentText(), 'rated'),\n"
    "            'feature_columns': self._selected_features(),\n"
    "            'n_estimators': self.xgb_n_estimators_spin.value(),\n"
    "            'learning_rate': self.xgb_learning_rate_spin.value(),\n"
    "            'max_depth': self.xgb_max_depth_spin.value(),\n"
    "            'subsample': self.xgb_subsample_spin.value(),\n"
    "            'colsample_bytree': self.xgb_colsample_bytree_spin.value(),\n"
    "            'min_samples_leaf': self.rf_min_samples_leaf_spin.value(),\n"
    "            'max_features': self.rf_max_features_spin.value(),\n"
    "            'patience': self.xgb_patience_spin.value(),\n"
    "            'adapter_type': self.adapter_combo.currentData(),\n"
    "            'cc_step': _step_input_value(self.cc_step_input),\n"
    "            'cv_step': _step_input_value(self.cv_step_input),\n"
    "            'discharge_step': _step_input_value(self.discharge_step_input),\n"
    '        }\n'
    '        try:\n'
    '            save_config(cfg)\n'
    '        except OSError as error:\n'
    "            self.logger.error(f'配置保存失败：{error}')\n"
    '            show_message(\n'
    "                self, 'error', '配置保存失败',\n"
    "                '无法保存当前配置。请检查 config.json 是否被占用，'\n"
    "                '以及项目目录是否具有写入权限。')\n"
    '            return False\n'
    '        return True\n'
    '\n'
    '    def _selected_features(self):\n'
    '        """当前勾选的多特征列（容量必选且排第一）。"""\n'
    "        if not hasattr(self, 'feature_checks'):\n"
    "            return ['capacity']\n"
    '        names = [\n'
    '            name for name, checkbox in self.feature_checks.items()\n'
    '            if checkbox.isChecked()\n'
    '        ]\n'
    "        if 'capacity' not in names:\n"
    "            names.insert(0, 'capacity')\n"
    '        return names\n'
    '\n'
    '    def closeEvent(self, event):\n'
    '        if not self._request_worker_stop(timeout_ms=5000, closing=True):\n'
    '            show_message(\n'
    "                self, 'warning', '仍在安全停止',\n"
    "                '训练线程尚未到达安全检查点，窗口暂不关闭。请稍候后再次关闭，避免损坏模型或报告。')\n"
    '            event.ignore()\n'
    '            return\n'
    '        self._save_persisted_config()\n'
    '        save_geometry(self)          # U4：记住窗口几何\n'
    '        super().closeEvent(event)\n'
    '\n'
    '    def build_top_bar(self):\n'
    '        """右上顶角的主题切换按钮（C5 / U8）。\n'
    '\n'
    '        默认深色（墨夜）。按钮同时带**图标 + 文字**描述当前目标主题，\n'
    '        不只靠颜色区分状态（U6 的无障碍要求）。\n'
    '        """\n'
    '        bar = QFrame()\n'
    "        bar.setObjectName('topBar')\n"
    "        bar.setProperty('role', 'topBar')\n"
    '        bar.setFixedHeight(44)\n'
    '\n'
    '        layout = QHBoxLayout(bar)\n'
    '        layout.setContentsMargins(12, 4, 8, 4)\n'
    '        layout.setSpacing(10)\n'
    '\n'
    "        title = QLabel('Battery SOH Assessment System')\n"
    "        title.setProperty('role', 'topBarTitle')\n"
    '        layout.addWidget(title)\n'
    '\n'
    "        subtitle = QLabel('电池健康状态评估 · Research Preview')\n"
    "        subtitle.setProperty('role', 'topBarSubtitle')\n"
    '        layout.addWidget(subtitle)\n'
    '        layout.addStretch(1)\n'
    '\n'
    "        self.theme_btn = AnimatedButton('', 'ghost')\n"
    "        self.theme_btn.setObjectName('themeToggle')\n"
    "        self.theme_btn.setAccessibleName('切换浅色或深色主题')\n"
    '        self.theme_btn.setMinimumWidth(132)\n'
    '        self.theme_btn.clicked.connect(self.toggle_theme)\n'
    '        layout.addWidget(self.theme_btn)\n'
    '        self._sync_theme_button()\n'
    '        return bar\n'
    '\n'
    '    def _sync_theme_button(self):\n'
    '        """让按钮文案反映**当前**主题与**点击后**会切到的主题。"""\n'
    "        button = getattr(self, 'theme_btn', None)\n"
    '        if button is None:\n'
    '            return\n'
    "        if self._theme_mode == 'dark':\n"
    "            button.setText('🌙 墨夜（深色）')\n"
    "            target = '宣纸（浅色）'\n"
    '        else:\n'
    "            button.setText('☀ 宣纸（浅色）')\n"
    "            target = '墨夜（深色）'\n"
    '        button.setToolTip(\n'
    "            f'当前：{THEME_UI.get(self._theme_mode, self._theme_mode)}；'\n"
    "            f'点击切换到{target}（Ctrl+T）')\n"
    '\n'
    '    def init_ui(self):\n'
    '        # 先应用主题（必须在控件创建前）\n'
    '        self.apply_theme()\n'
    '\n'
    '        central = QWidget()\n'
    '        self.setCentralWidget(central)\n'
    "        central.setObjectName('central')\n"
    '\n'
    '        main_layout = QVBoxLayout()\n'
    '        main_layout.setContentsMargins(10, 10, 10, 8)\n'
    '        main_layout.setSpacing(8)\n'
    '        central.setLayout(main_layout)\n'
    '\n'
    '        # ── 顶部条：左侧应用名，右侧主题切换（右上顶角） ──\n'
    '        main_layout.addWidget(self.build_top_bar())\n'
    '\n'
    '        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)\n'
    '\n'
    '        left_widget = QWidget()\n'
    '        center_widget = QWidget()\n'
    '        right_widget = QWidget()\n'
    '\n'
    '        self.main_splitter.addWidget(left_widget)\n'
    '        self.main_splitter.addWidget(center_widget)\n'
    '        self.main_splitter.addWidget(right_widget)\n'
    '\n'
    '        self.main_splitter.setStretchFactor(0, 0)\n'
    '        self.main_splitter.setStretchFactor(1, 1)\n'
    '        self.main_splitter.setStretchFactor(2, 0)\n'
    '        # 注意：右栏宽度受「最小窗口下图表仍占主导」的约束（见\n'
    '        # tests/test_ui_polish_layout.py::test_minimum_workspace_keeps_chart_column_dominant），\n'
    '        # 因此结果表在窄面板里靠横向滚动 + 省略号 + 工具提示呈现完整信息。\n'
    '        self.main_splitter.setSizes([285, 820, 315])\n'
    '        self.main_splitter.setMinimumWidth(100)\n'
    '        self.main_splitter.setHandleWidth(2)\n'
    '        left_widget.setMinimumWidth(280)\n'
    '        center_widget.setMinimumWidth(500)\n'
    '        right_widget.setMinimumWidth(300)\n'
    '\n'
    '        main_layout.addWidget(self.main_splitter, 1)\n'
    '\n'
    '        self.build_left_panel(left_widget)\n'
    '        self.build_center_panel(center_widget)\n'
    '        self.build_right_panel(right_widget)\n'
    '\n'
    '        self.status_bar = QStatusBar()\n'
    '        self.setStatusBar(self.status_bar)\n'
    "        self._set_running_state(False, '准备就绪')\n"
    '\n'
    '    def build_left_panel(self, parent):\n'
    '        layout = QVBoxLayout(parent)\n'
    '        layout.setContentsMargins(0, 0, 6, 0)\n'
    '        layout.setSpacing(8)\n'
    '\n'
    "        file_group = QGroupBox('文件导入')\n"
    '        file_layout = QVBoxLayout()\n'
    '\n'
    '        btn_row = QHBoxLayout()\n'
    "        self.import_btn = AnimatedButton('导入文件', 'default')\n"
    "        self.import_btn.setShortcut(QKeySequence('Ctrl+O'))\n"
    "        self.import_btn.setToolTip('导入电池数据文件 (Ctrl+O)')\n"
    '        self.import_btn.clicked.connect(self.import_files)\n'
    "        self.import_dir_btn = AnimatedButton('导入文件夹', 'default')\n"
    "        self.import_dir_btn.setShortcut(QKeySequence('Ctrl+Shift+O'))\n"
    "        self.import_dir_btn.setToolTip('批量导入电池数据文件夹 (Ctrl+Shift+O)')\n"
    '        self.import_dir_btn.clicked.connect(self.import_folder)\n'
    "        self.import_json_btn = AnimatedButton('导入JSON', 'default')\n"
    "        self.import_json_btn.setShortcut(QKeySequence('Ctrl+Alt+O'))\n"
    '        self.import_json_btn.setToolTip(\n'
    "            '从 JSON 配置文件导入全部参数，适用于团队共享配置或复现实验 (Ctrl+Alt+O)')\n"
    '        self.import_json_btn.clicked.connect(self.import_json_config)\n'
    '        _configure_button_row(btn_row, (self.import_btn, self.import_dir_btn))\n'
    '\n'
    '        file_layout.addLayout(btn_row)\n'
    '\n'
    '        data_summary = QFrame()\n'
    "        data_summary.setProperty('role', 'dataSummary')\n"
    '        data_summary_layout = QHBoxLayout(data_summary)\n'
    '        data_summary_layout.setContentsMargins(10, 7, 10, 7)\n'
    '        data_summary_layout.setSpacing(8)\n'
    '        self.data_summary_label = QLabel()\n'
    "        self.data_summary_label.setProperty('role', 'dataSummaryText')\n"
    '        self.data_summary_label.setWordWrap(True)\n'
    "        self.data_summary_count = QLabel('0')\n"
    "        self.data_summary_count.setProperty('role', 'dataSummaryCount')\n"
    '        self.data_summary_count.setAlignment(Qt.AlignmentFlag.AlignCenter)\n'
    '        data_summary_layout.addWidget(self.data_summary_label, 1)\n'
    '        data_summary_layout.addWidget(self.data_summary_count)\n'
    '        file_layout.addWidget(data_summary)\n'
    '        self._update_data_summary()\n'
    '\n'
    '        self.import_list = QListWidget()\n'
    "        self.import_list.setAccessibleName('已导入的数据文件和文件夹')\n"
    "        self.import_list.setToolTip('选择项目后按 Delete 可移除')\n"
    '        self.import_list.keyPressEvent = self.import_list_key_press\n'
    '        file_layout.addWidget(self.import_list)\n'
    '\n'
    "        self.delete_btn = AnimatedButton('删除选中', 'danger')\n"
    '        self.delete_btn.clicked.connect(self.delete_selected_items)\n'
    '        file_action_row = QHBoxLayout()\n'
    '        _configure_button_row(\n'
    '            file_action_row, (self.import_json_btn, self.delete_btn))\n'
    '        file_layout.addLayout(file_action_row)\n'
    '        file_group.setLayout(file_layout)\n'
    '\n'
    '        # ── 数据源配置 ──\n'
    "        source_group = QGroupBox('数据源')\n"
    '        source_layout = QFormLayout()\n'
    '\n'
    '        self.adapter_combo = QComboBox()\n'
    '        for adapter_name, adapter_display in get_adapter_list():\n'
    '            self.adapter_combo.addItem(adapter_display, adapter_name)\n'
    '        self.adapter_combo.currentIndexChanged.connect(self._on_adapter_changed)\n'
    "        source_layout.addRow('数据格式:', self.adapter_combo)\n"
    '\n'
    '        source_group.setLayout(source_layout)\n'
    '\n'
    "        param_group = QGroupBox('参数设置')\n"
    '        param_layout = QVBoxLayout()\n'
    '        param_layout.setContentsMargins(8, 10, 8, 8)\n'
    '        param_layout.setSpacing(8)\n'
    '\n'
    "        self.step_section = CollapsibleSection('设置工步', expanded=False)\n"
    "        self.cc_step_input = _create_step_input('恒流充电工步')\n"
    "        self.cv_step_input = _create_step_input('恒压充电工步')\n"
    "        self.discharge_step_input = _create_step_input('放电工步')\n"
    '        self.step_section.form_layout.addRow(\n'
    "            '恒流充电工步:', self.cc_step_input)\n"
    '        self.step_section.form_layout.addRow(\n'
    "            '恒压充电工步:', self.cv_step_input)\n"
    '        self.step_section.form_layout.addRow(\n'
    "            '放电工步:', self.discharge_step_input)\n"
    '\n'
    "        battery_section = CollapsibleSection('电池与失效判据')\n"
    "        evaluation_section = CollapsibleSection('评估与验证')\n"
    "        advanced_section = CollapsibleSection('模型高级参数', expanded=False)\n"
    '        param_layout.addWidget(self.step_section)\n'
    '        param_layout.addWidget(battery_section)\n'
    '        param_layout.addWidget(evaluation_section)\n'
    '        param_layout.addWidget(advanced_section)\n'
    '        self._param_rows = []\n'
    '\n'
    '        def _add_row(section, label_text, widget, modes):\n'
    '            label = QLabel(label_text)\n'
    '            section.form_layout.addRow(label, widget)\n'
    '            self._param_rows.append((label, widget, modes))\n'
    '\n'
    '        self.rated_capacity_spin = QDoubleSpinBox()\n'
    '        self.rated_capacity_spin.setDecimals(2)\n'
    '        self.rated_capacity_spin.setRange(0.01, 1000)\n'
    '        self.rated_capacity_spin.setValue(1.1)\n'
    '        self.rated_capacity_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)\n'
    "        _add_row(battery_section, '额定容量 (Ah)', self.rated_capacity_spin,\n"
    "                 ['RNN', 'GRU', 'LSTM', 'XGBoost', 'RF'])\n"
    '\n'
    '        self.threshold_ratio_spin = QDoubleSpinBox()\n'
    '        self.threshold_ratio_spin.setDecimals(2)\n'
    '        self.threshold_ratio_spin.setRange(0.01, 1.0)\n'
    '        self.threshold_ratio_spin.setValue(0.8)\n'
    '        self.threshold_ratio_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)\n'
    "        _add_row(battery_section, '失效阈值比例', self.threshold_ratio_spin,\n"
    "                 ['RNN', 'GRU', 'LSTM', 'XGBoost', 'RF'])\n"
    '\n'
    '        self.voltage_upper_spin = QDoubleSpinBox()\n'
    '        self.voltage_upper_spin.setDecimals(2)\n'
    '        self.voltage_upper_spin.setRange(1.0, 5.0)\n'
    '        self.voltage_upper_spin.setSingleStep(0.05)\n'
    '        self.voltage_upper_spin.setValue(3.8)\n'
    '        self.voltage_upper_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)\n'
    "        _add_row(battery_section, 'SOH上电压 (V)', self.voltage_upper_spin,\n"
    "                 ['RNN', 'GRU', 'LSTM', 'XGBoost', 'RF'])\n"
    '\n'
    '        self.voltage_lower_spin = QDoubleSpinBox()\n'
    '        self.voltage_lower_spin.setDecimals(2)\n'
    '        self.voltage_lower_spin.setRange(0.5, 5.0)\n'
    '        self.voltage_lower_spin.setSingleStep(0.05)\n'
    '        self.voltage_lower_spin.setValue(3.4)\n'
    '        self.voltage_lower_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)\n'
    "        _add_row(battery_section, 'SOH下电压 (V)', self.voltage_lower_spin,\n"
    "                 ['RNN', 'GRU', 'LSTM', 'XGBoost', 'RF'])\n"
    '\n'
    '        self.feature_size_spin = QSpinBox()\n'
    '        self.feature_size_spin.setRange(1, 10000)\n'
    '        self.feature_size_spin.setValue(64)\n'
    '        self.feature_size_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)\n'
    "        _add_row(evaluation_section, '窗口大小', self.feature_size_spin,\n"
    "                 ['RNN', 'GRU', 'LSTM', 'XGBoost', 'RF'])\n"
    '\n'
    '        self.metric_combo = QComboBox()\n'
    "        self.metric_combo.addItems(['RMSE', 'MAE', 'R²', 'Pearson', 'RE', '全部'])\n"
    "        _add_row(evaluation_section, '评估指标', self.metric_combo,\n"
    "                 ['RNN', 'GRU', 'LSTM', 'XGBoost', 'RF'])\n"
    '\n'
    '        # ---- 多特征输入（A5）：默认只用容量，勾选后启用 HI 特征 ----\n'
    '        feature_widget = QWidget()\n'
    '        feature_layout = QVBoxLayout(feature_widget)\n'
    '        feature_layout.setContentsMargins(0, 0, 0, 0)\n'
    '        feature_layout.setSpacing(2)\n'
    '        self.feature_checks = {}\n'
    '        for name, label in FEATURE_OPTIONS.items():\n'
    '            checkbox = QCheckBox(label)\n'
    "            if name == 'capacity':\n"
    '                checkbox.setChecked(True)\n'
    '                checkbox.setEnabled(False)      # 容量是预测目标，必选\n'
    "                checkbox.setToolTip('容量是预测目标，始终参与输入')\n"
    '            else:\n'
    '                checkbox.setToolTip(\n'
    "                    '勾选后模型除容量外还使用该健康指标（HI）。'\n"
    "                    '注意：递归预测时非容量通道保持窗口末值。')\n"
    '            self.feature_checks[name] = checkbox\n'
    '            feature_layout.addWidget(checkbox)\n'
    "        _add_row(evaluation_section, '输入特征', feature_widget,\n"
    "                 ['RNN', 'GRU', 'LSTM', 'XGBoost', 'RF'])\n"
    '        self._feature_hint = QLabel(\n'
    "            '默认只用容量（纯自回归）。勾选 dq_v / CCCT / CVCT / 内阻后'\n"
    "            '启用多特征输入；dq_v 是电压窗口内的放电容量（健康指标 HI），'\n"
    "            '不是 SOH。')\n"
    "        self._feature_hint.setProperty('role', 'muted')\n"
    '        self._feature_hint.setWordWrap(True)\n'
    "        evaluation_section.form_layout.addRow('', self._feature_hint)\n"
    '\n'
    '        # ---- RNN/LSTM/GRU 专用 ----\n'
    '        self.hidden_dim_spin = QSpinBox()\n'
    '        self.hidden_dim_spin.setRange(1, 2048)\n'
    '        self.hidden_dim_spin.setValue(64)\n'
    '        self.hidden_dim_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)\n'
    "        _add_row(advanced_section, '隐藏层维度', self.hidden_dim_spin, ['RNN', 'GRU', 'LSTM'])\n"
    '\n'
    '        self.epochs_spin = QSpinBox()\n'
    '        self.epochs_spin.setRange(10, 100000)\n'
    '        self.epochs_spin.setSingleStep(10)\n'
    '        self.epochs_spin.setValue(100)\n'
    "        _add_row(advanced_section, '训练轮数', self.epochs_spin, ['RNN', 'GRU', 'LSTM'])\n"
    '\n'
    '        self.norm_combo = QComboBox()\n'
    "        self.norm_combo.addItems(['额定容量归一化', 'MinMax', 'ZScore'])\n"
    "        _add_row(advanced_section, '归一化方式', self.norm_combo,\n"
    "                 ['RNN', 'GRU', 'LSTM', 'XGBoost', 'RF'])\n"
    '\n'
    '        self.device_combo = QComboBox()\n'
    "        self.device_combo.addItems(['CPU', 'GPU (CUDA)'])\n"
    "        _add_row(advanced_section, '计算设备', self.device_combo, ['RNN', 'GRU', 'LSTM'])\n"
    '\n'
    '        self.seed_spin = QSpinBox()\n'
    '        self.seed_spin.setRange(0, 9999)\n'
    '        self.seed_spin.setValue(2)\n'
    '        self.seed_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)\n'
    "        _add_row(evaluation_section, '随机种子', self.seed_spin,\n"
    "                 ['RNN', 'GRU', 'LSTM', 'XGBoost', 'RF'])\n"
    '\n'
    '        self.n_seeds_spin = QSpinBox()\n'
    '        self.n_seeds_spin.setRange(1, 20)\n'
    '        self.n_seeds_spin.setValue(5)\n'
    '        self.n_seeds_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)\n'
    "        _add_row(evaluation_section, '多种子数(置信区间)', self.n_seeds_spin,\n"
    "                 ['RNN', 'GRU', 'LSTM', 'XGBoost', 'RF'])\n"
    '\n'
    '        # ---- XGBoost 专用 ----\n'
    '        self.xgb_n_estimators_spin = QSpinBox()\n'
    '        self.xgb_n_estimators_spin.setRange(10, 10000)\n'
    '        self.xgb_n_estimators_spin.setValue(100)\n'
    '        self.xgb_n_estimators_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)\n'
    "        _add_row(advanced_section, '树的数量', self.xgb_n_estimators_spin, ['XGBoost'])\n"
    '\n'
    '        self.xgb_learning_rate_spin = QDoubleSpinBox()\n'
    '        self.xgb_learning_rate_spin.setDecimals(2)\n'
    '        self.xgb_learning_rate_spin.setRange(0.01, 1.0)\n'
    '        self.xgb_learning_rate_spin.setSingleStep(0.01)\n'
    '        self.xgb_learning_rate_spin.setValue(0.05)\n'
    "        _add_row(advanced_section, '学习率', self.xgb_learning_rate_spin, ['XGBoost'])\n"
    '\n'
    '        self.xgb_max_depth_spin = QSpinBox()\n'
    '        self.xgb_max_depth_spin.setRange(1, 100)\n'
    '        self.xgb_max_depth_spin.setValue(6)\n'
    "        _add_row(advanced_section, '树的最大深度', self.xgb_max_depth_spin, ['XGBoost'])\n"
    '\n'
    '        self.xgb_subsample_spin = QDoubleSpinBox()\n'
    '        self.xgb_subsample_spin.setDecimals(1)\n'
    '        self.xgb_subsample_spin.setRange(0.1, 1.0)\n'
    '        self.xgb_subsample_spin.setSingleStep(0.1)\n'
    '        self.xgb_subsample_spin.setValue(1.0)\n'
    "        _add_row(advanced_section, '样本采样比例', self.xgb_subsample_spin, ['XGBoost'])\n"
    '\n'
    '        self.xgb_colsample_bytree_spin = QDoubleSpinBox()\n'
    '        self.xgb_colsample_bytree_spin.setDecimals(1)\n'
    '        self.xgb_colsample_bytree_spin.setRange(0.1, 1.0)\n'
    '        self.xgb_colsample_bytree_spin.setSingleStep(0.1)\n'
    '        self.xgb_colsample_bytree_spin.setValue(1.0)\n'
    "        _add_row(advanced_section, '特征采样比例', self.xgb_colsample_bytree_spin,\n"
    "                 ['XGBoost'])\n"
    '\n'
    '        self.xgb_patience_spin = QSpinBox()\n'
    '        self.xgb_patience_spin.setRange(1, 500)\n'
    '        self.xgb_patience_spin.setSingleStep(10)\n'
    '        self.xgb_patience_spin.setValue(20)\n'
    "        _add_row(advanced_section, '早停批次数', self.xgb_patience_spin, ['XGBoost'])\n"
    '\n'
    '        # ---- RF 专用 ----\n'
    '        self.rf_n_estimators_spin = QSpinBox()\n'
    '        self.rf_n_estimators_spin.setRange(10, 5000)\n'
    '        self.rf_n_estimators_spin.setValue(100)\n'
    '        self.rf_n_estimators_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)\n'
    "        _add_row(advanced_section, '树的数量', self.rf_n_estimators_spin, ['RF'])\n"
    '\n'
    '        self.rf_max_depth_spin = QSpinBox()\n'
    '        self.rf_max_depth_spin.setRange(1, 200)\n'
    '        self.rf_max_depth_spin.setValue(10)\n'
    "        _add_row(advanced_section, '树的最大深度', self.rf_max_depth_spin, ['RF'])\n"
    '\n'
    '        self.rf_min_samples_leaf_spin = QSpinBox()\n'
    '        self.rf_min_samples_leaf_spin.setRange(1, 100)\n'
    '        self.rf_min_samples_leaf_spin.setValue(1)\n'
    "        _add_row(advanced_section, '叶节点最小样本数', self.rf_min_samples_leaf_spin, ['RF'])\n"
    '\n'
    '        self.rf_max_features_spin = QDoubleSpinBox()\n'
    '        self.rf_max_features_spin.setDecimals(1)\n'
    '        self.rf_max_features_spin.setRange(0.1, 1.0)\n'
    '        self.rf_max_features_spin.setSingleStep(0.1)\n'
    '        self.rf_max_features_spin.setValue(1.0)\n'
    "        _add_row(advanced_section, '最大特征比例', self.rf_max_features_spin, ['RF'])\n"
    '\n'
    '        self.rf_patience_spin = QSpinBox()\n'
    '        self.rf_patience_spin.setRange(1, 500)\n'
    '        self.rf_patience_spin.setSingleStep(10)\n'
    '        self.rf_patience_spin.setValue(20)\n'
    "        _add_row(advanced_section, '早停批次数', self.rf_patience_spin, ['RF'])\n"
    '\n'
    '        param_group.setLayout(param_layout)\n'
    '\n'
    '        # 把“参数设置”放入可滚动区域，避免窗口高度不足时控件被压缩\n'
    '        param_scroll = QScrollArea()\n'
    '        param_scroll.setWidgetResizable(True)\n'
    '        param_scroll.setFrameShape(QFrame.Shape.NoFrame)\n'
    '        param_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)\n'
    '        param_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)\n'
    '        param_scroll.setWidget(param_group)\n'
    '\n'
    "        self.help_btn = AnimatedButton('帮助', 'ghost')\n"
    "        self.help_btn.setShortcut(QKeySequence('F1'))\n"
    "        self.help_btn.setToolTip('查看当前模型参数说明 (F1)')\n"
    '        self.help_btn.clicked.connect(self.show_help)\n'
    '        self.help_btn.setMaximumWidth(80)\n'
    '        param_layout.addWidget(self.help_btn, 0, Qt.AlignmentFlag.AlignLeft)\n'
    '\n'
    '        # 左侧三个面板（文件导入 / 数据源 / 参数设置）统一用垂直 splitter 分隔\n'
    '        self.left_splitter = QSplitter(Qt.Orientation.Vertical)\n'
    "        self.left_splitter.setObjectName('leftPanelSplitter')\n"
    '        self.left_splitter.addWidget(file_group)\n'
    '        self.left_splitter.addWidget(source_group)\n'
    '        self.left_splitter.addWidget(param_scroll)\n'
    '        self.left_splitter.setStretchFactor(0, 2)\n'
    '        self.left_splitter.setStretchFactor(1, 0)\n'
    '        self.left_splitter.setStretchFactor(2, 1)\n'
    '        self.left_splitter.setSizes([240, 80, 320])\n'
    '        # 10px 负责鼠标命中；样式仅在中间绘制 2px 分割线。\n'
    '        self.left_splitter.setHandleWidth(10)\n'
    '\n'
    '        layout.addWidget(self.left_splitter, 1)\n'
    '\n'
    '        self._help_dialog = None\n'
    "        self._update_param_panel('RNN')\n"
    '\n'
    '    def build_center_panel(self, parent):\n'
    '        layout = QVBoxLayout(parent)\n'
    '        layout.setContentsMargins(6, 0, 6, 0)\n'
    '        layout.setSpacing(8)\n'
    '\n'
    '        model_shelf = QFrame()\n'
    "        model_shelf.setProperty('role', 'modelShelf')\n"
    '        model_shelf_layout = QVBoxLayout(model_shelf)\n'
    '        model_shelf_layout.setContentsMargins(10, 7, 10, 9)\n'
    '        model_shelf_layout.setSpacing(6)\n'
    '\n'
    '        model_header_layout = QHBoxLayout()\n'
    "        model_label = QLabel('选择评估模型')\n"
    "        model_label.setProperty('role', 'sectionTitle')\n"
    '        self.model_hint_label = QLabel()\n'
    "        self.model_hint_label.setProperty('role', 'modelHint')\n"
    '        self.model_hint_label.setAlignment(\n'
    '            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)\n'
    '        model_header_layout.addWidget(model_label)\n'
    '        model_header_layout.addStretch(1)\n'
    '        model_header_layout.addWidget(self.model_hint_label)\n'
    '        model_shelf_layout.addLayout(model_header_layout)\n'
    '\n'
    '        btn_layout = QHBoxLayout()\n'
    "        self.rnn_btn = AnimatedButton('RNN', 'model')\n"
    "        self.gru_btn = AnimatedButton('GRU', 'model')\n"
    "        self.lstm_btn = AnimatedButton('LSTM', 'model')\n"
    "        self.xgboost_btn = AnimatedButton('XGBoost', 'model')\n"
    "        self.rf_btn = AnimatedButton('RF', 'model')\n"
    '\n'
    "        self.rnn_btn.clicked.connect(lambda: self.select_mode('RNN'))\n"
    "        self.gru_btn.clicked.connect(lambda: self.select_mode('GRU'))\n"
    "        self.lstm_btn.clicked.connect(lambda: self.select_mode('LSTM'))\n"
    "        self.xgboost_btn.clicked.connect(lambda: self.select_mode('XGBoost'))\n"
    "        self.rf_btn.clicked.connect(lambda: self.select_mode('RF'))\n"
    '\n'
    '        _configure_button_row(\n'
    '            btn_layout,\n'
    '            (self.rnn_btn, self.gru_btn, self.lstm_btn,\n'
    '             self.xgboost_btn, self.rf_btn),\n'
    '            spacing=6)\n'
    '        model_shelf_layout.addLayout(btn_layout)\n'
    '\n'
    '        action_layout = QHBoxLayout()\n'
    '\n'
    '        io_layout = QHBoxLayout()\n'
    "        self.save_model_btn = AnimatedButton('保存模型', 'default')\n"
    "        self.load_model_btn = AnimatedButton('加载模型', 'default')\n"
    "        self.unload_model_btn = AnimatedButton('卸载模型', 'default')\n"
    "        self.tcp_btn = AnimatedButton('接入数据', 'default')\n"
    '\n'
    '        self.save_model_btn.clicked.connect(self.save_model)\n'
    '        self.load_model_btn.clicked.connect(self.load_model)\n'
    '        self.unload_model_btn.clicked.connect(self.unload_model)\n'
    "        self.load_model_btn.setShortcut(QKeySequence('Ctrl+L'))\n"
    "        self.load_model_btn.setToolTip('加载已有模型 (Ctrl+L)')\n"
    "        self.unload_model_btn.setToolTip('卸载当前模型并切回训练模式')\n"
    '        self.tcp_btn.clicked.connect(self.toggle_tcp_server)\n'
    "        self.tcp_btn.setToolTip('接入实时容量数据（实验功能，默认仅监听本机）')\n"
    '\n'
    '        # A10：默认只监听 127.0.0.1；开放局域网必须显式勾选\n'
    "        self.tcp_lan_check = QCheckBox('允许局域网访问')\n"
    '        self.tcp_lan_check.setToolTip(\n'
    "            '勾选后服务将监听 0.0.0.0 并自动生成访问 token；'\n"
    "            '仅在可信网络中临时启用。')\n"
    "        self.tcp_lan_check.setAccessibleName('允许局域网访问 TCP 服务')\n"
    '\n'
    '        self.save_model_btn.setEnabled(False)\n'
    '        self.unload_model_btn.setEnabled(False)\n'
    '        self.tcp_btn.setEnabled(False)\n'
    '\n'
    '        _configure_button_row(\n'
    '            io_layout, (self.save_model_btn, self.load_model_btn,\n'
    '                        self.unload_model_btn, self.tcp_btn))\n'
    '        io_layout.addWidget(self.tcp_lan_check)\n'
    '\n'
    "        self.start_btn = AnimatedButton('开始评估', 'hero')\n"
    "        self.start_btn.setShortcut(QKeySequence('Ctrl+Return'))\n"
    "        self.start_btn.setToolTip('使用当前数据和参数开始评估 (Ctrl+Enter)')\n"
    '        self.start_btn.clicked.connect(self.start_evaluation)\n'
    '        self.start_btn.setMinimumHeight(48)\n'
    '\n'
    '        action_layout.addWidget(self.start_btn)\n'
    '\n'
    '        self.progress_bar = QProgressBar()\n'
    '        self.progress_bar.setRange(0, 0)\n'
    '        self.progress_bar.setTextVisible(False)\n'
    '        self.progress_bar.setVisible(False)\n'
    '\n'
    "        self.run_status_label = QLabel('准备就绪')\n"
    "        self.run_status_label.setProperty('role', 'runStatus')\n"
    "        self.run_status_label.setProperty('state', 'idle')\n"
    "        self.run_status_label.setAccessibleName('评估运行状态')\n"
    '\n'
    '        run_status_strip = QFrame()\n'
    "        run_status_strip.setProperty('role', 'runStatusStrip')\n"
    '        run_status_layout = QHBoxLayout(run_status_strip)\n'
    '        run_status_layout.setContentsMargins(10, 5, 10, 5)\n'
    '        run_status_layout.setSpacing(8)\n'
    '        self.run_status_dot = QFrame()\n'
    "        self.run_status_dot.setProperty('role', 'runStatusDot')\n"
    "        self.run_status_dot.setProperty('state', 'idle')\n"
    '        self.run_status_dot.setFixedSize(10, 10)\n'
    "        self.run_status_dot.setAccessibleName('评估状态指示')\n"
    '        run_status_layout.addWidget(self.run_status_dot)\n'
    '        run_status_layout.addWidget(self.run_status_label, 1)\n'
    '\n'
    "        context_label = QLabel('当前模型与参数仅在本地运行')\n"
    "        context_label.setProperty('role', 'runContext')\n"
    '        run_status_layout.addWidget(context_label)\n'
    '\n'
    '        self.canvas = MplCanvas()\n'
    '        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)\n'
    '        self.canvas.setToolTip(\n'
    "            '右键图表可选择全屏查看当前子图或全部子图；按 Esc 退出全屏')\n"
    '\n'
    '        self.toolbar = CustomToolbar(self.canvas, self)\n'
    '\n'
    '        layout.addWidget(model_shelf)\n'
    '        layout.addLayout(io_layout)\n'
    '        layout.addLayout(action_layout)\n'
    '        layout.addWidget(run_status_strip)\n'
    '        layout.addWidget(self.progress_bar)\n'
    '        layout.addWidget(self.toolbar)\n'
    '        layout.addWidget(self.canvas, 1)\n'
    '\n'
    "        self.select_mode('RNN')\n"
    '\n'
    '    def build_right_panel(self, parent):\n'
    '        layout = QVBoxLayout(parent)\n'
    '        layout.setContentsMargins(6, 0, 0, 0)\n'
    '        layout.setSpacing(8)\n'
    '\n'
    '        self.right_tabs = QTabWidget()\n'
    "        self.right_tabs.setObjectName('workspaceTabs')\n"
    '        self.right_tabs.setDocumentMode(True)\n'
    "        self.right_tabs.setAccessibleName('评估结果与训练日志')\n"
    '\n'
    '        result_page = QWidget()\n'
    '        result_layout = QVBoxLayout(result_page)\n'
    '        result_layout.setContentsMargins(8, 8, 8, 8)\n'
    '        result_layout.setSpacing(8)\n'
    '\n'
    '        self.result_batch_bar = QFrame()\n'
    "        self.result_batch_bar.setProperty('role', 'resultBatchBar')\n"
    '        batch_layout = QHBoxLayout(self.result_batch_bar)\n'
    '        batch_layout.setContentsMargins(8, 5, 8, 5)\n'
    '        batch_layout.setSpacing(8)\n'
    "        batch_label = QLabel('结果批次')\n"
    "        batch_label.setProperty('role', 'resultBatchLabel')\n"
    '        self.result_batch_combo = QComboBox()\n'
    '        self.result_batch_combo.setSizeAdjustPolicy(\n'
    '            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)\n'
    '        self.result_batch_combo.setMinimumContentsLength(18)\n'
    "        self.result_batch_combo.setAccessibleName('选择要查看的训练或预测结果批次')\n"
    '        self.result_batch_combo.currentIndexChanged.connect(\n'
    '            self._display_result_batch)\n'
    '        batch_layout.addWidget(batch_label)\n'
    '        batch_layout.addWidget(self.result_batch_combo, 1)\n'
    '        self.result_batch_bar.setVisible(False)\n'
    '        result_layout.addWidget(self.result_batch_bar)\n'
    '\n'
    '        self.result_summary = QFrame()\n'
    "        self.result_summary.setProperty('role', 'resultSummary')\n"
    '        summary_layout = QVBoxLayout(self.result_summary)\n'
    '        summary_layout.setContentsMargins(12, 9, 12, 9)\n'
    '        summary_layout.setSpacing(3)\n'
    '        summary_top = QHBoxLayout()\n'
    '        summary_top.setContentsMargins(0, 0, 0, 0)\n'
    '        self.result_summary_title = QLabel()\n'
    "        self.result_summary_title.setProperty('role', 'resultSummaryTitle')\n"
    '        self.result_summary_metric = QLabel()\n'
    "        self.result_summary_metric.setProperty('role', 'resultSummaryMetric')\n"
    '        self.result_summary_metric.setAlignment(\n'
    '            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)\n'
    '        summary_top.addWidget(self.result_summary_title, 1)\n'
    '        summary_top.addWidget(self.result_summary_metric)\n'
    '        self.result_summary_meta = QLabel()\n'
    "        self.result_summary_meta.setProperty('role', 'resultSummaryMeta')\n"
    '        summary_layout.addLayout(summary_top)\n'
    '        summary_layout.addWidget(self.result_summary_meta)\n'
    '        self.result_summary.setVisible(False)\n'
    '        result_layout.addWidget(self.result_summary)\n'
    '\n'
    '        self.result_scroll = QScrollArea()\n'
    '        self.result_scroll.setWidgetResizable(True)\n'
    '        self.result_scroll.setHorizontalScrollBarPolicy(\n'
    '            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)\n'
    '        self.result_container = QWidget()\n'
    "        self.result_container.setProperty('role', 'resultContainer')\n"
    '        self.result_container_layout = QVBoxLayout(self.result_container)\n'
    '        self.result_container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)\n'
    '        self.result_container_layout.setSpacing(8)\n'
    '\n'
    '        # ── U1：可排序结果表（取代 N 张卡片竖排） ──\n'
    '        self.result_model = ResultTableModel(\n'
    '            [], tokens=theme_tokens(self._theme_mode))\n'
    '        self.result_proxy = QSortFilterProxyModel()\n'
    '        self.result_proxy.setSourceModel(self.result_model)\n'
    '        # 用 UserRole 里的原始值排序，而不是格式化后的字符串\n'
    '        self.result_proxy.setSortRole(Qt.ItemDataRole.UserRole)\n'
    '        self.result_view = QTableView()\n'
    '        self.result_view.setModel(self.result_proxy)\n'
    '        self.result_view.setSortingEnabled(True)\n'
    '        self.result_view.setAlternatingRowColors(True)\n'
    '        self.result_view.setSelectionBehavior(\n'
    '            QAbstractItemView.SelectionBehavior.SelectRows)\n'
    '        self.result_view.setEditTriggers(\n'
    '            QAbstractItemView.EditTrigger.NoEditTriggers)\n'
    '        self.result_view.verticalHeader().setVisible(False)\n'
    '        # U1：显式列宽（ResizeToContents 会被汇总行撑到 1200px 以上），\n'
    '        # 超出部分省略号显示，完整值在工具提示里。\n'
    '        header = self.result_view.horizontalHeader()\n'
    '        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)\n'
    '        header.setStretchLastSection(True)\n'
    '        header.setDefaultAlignment(\n'
    '            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)\n'
    '        self.result_view.setTextElideMode(Qt.TextElideMode.ElideRight)\n'
    '        for index, column in enumerate(COLUMNS):\n'
    '            self.result_view.setColumnWidth(\n'
    '                index, COLUMN_WIDTHS.get(column[1], 74))\n'
    "        self.result_view.setAccessibleName('评估结果表，点击列头可排序')\n"
    '        self.result_view.setMinimumHeight(180)\n'
    '        self.result_container_layout.addWidget(self.result_view)\n'
    '\n'
    '        # 起点选择 + 导出 CSV（U1.6）\n'
    '        result_tools = QHBoxLayout()\n'
    '        result_tools.setContentsMargins(0, 0, 0, 0)\n'
    '        result_tools.setSpacing(6)\n'
    '        self.start_frac_combo = QComboBox()\n'
    "        self.start_frac_combo.setAccessibleName('选择滚动预测起点')\n"
    '        self.start_frac_combo.currentIndexChanged.connect(\n'
    '            self._on_start_frac_changed)\n'
    "        start_label = QLabel('预测起点')\n"
    "        start_label.setProperty('role', 'muted')\n"
    '        result_tools.addWidget(start_label)\n'
    '        result_tools.addWidget(self.start_frac_combo)\n'
    '        result_tools.addStretch(1)\n'
    "        self.copy_table_btn = QPushButton('复制表格')\n"
    "        self.copy_table_btn.setProperty('role', 'ghost')\n"
    '        self.copy_table_btn.clicked.connect(self._copy_result_table)\n'
    "        self.csv_btn = QPushButton('导出 CSV')\n"
    "        self.csv_btn.setProperty('role', 'ghost')\n"
    '        self.csv_btn.clicked.connect(self._export_result_csv)\n'
    '        result_tools.addWidget(self.copy_table_btn)\n'
    '        result_tools.addWidget(self.csv_btn)\n'
    '        self.result_container_layout.addLayout(result_tools)\n'
    '\n'
    '        # 基线与口径说明\n'
    '        self.result_notes = QLabel()\n'
    "        self.result_notes.setProperty('role', 'muted')\n"
    '        self.result_notes.setWordWrap(True)\n'
    '        self.result_notes.setVisible(False)\n'
    '        self.result_container_layout.addWidget(self.result_notes)\n'
    '\n'
    '        self.result_scroll.setWidget(self.result_container)\n'
    '        self._show_result_state(\n'
    "            '等待评估结果',\n"
    "            '导入数据并开始评估后，这里会显示滚动起点的 RMSE、'\n"
    "            'RUL 误差与相对平推的技能分。')\n"
    '\n'
    '        result_layout.addWidget(self.result_scroll)\n'
    '\n'
    '        op_layout = QHBoxLayout()\n'
    "        self.pause_btn = AnimatedButton('停止', 'danger')\n"
    '        self.pause_btn.setEnabled(False)\n'
    "        self.pause_btn.setShortcut(QKeySequence('Esc'))\n"
    "        self.pause_btn.setToolTip('停止当前评估 (Esc)')\n"
    '        self.pause_btn.clicked.connect(self.pause_evaluation)\n'
    '\n'
    "        self.save_chart_btn = AnimatedButton('保存图表', 'default')\n"
    '        self.save_chart_btn.clicked.connect(self.save_chart)\n'
    '\n'
    "        self.export_btn = AnimatedButton('导出报告', 'success')\n"
    '        self.export_btn.clicked.connect(self.export_report)\n'
    '        self.export_btn.setEnabled(False)\n'
    '\n'
    '        _configure_button_row(\n'
    '            op_layout, (self.pause_btn, self.save_chart_btn, self.export_btn))\n'
    '        result_layout.addLayout(op_layout)\n'
    '\n'
    '        log_page = QWidget()\n'
    '        log_layout = QVBoxLayout(log_page)\n'
    '        log_layout.setContentsMargins(8, 8, 8, 8)\n'
    '        self.log_text = QTextEdit()\n'
    '        self.log_text.setReadOnly(True)\n'
    '        log_layout.addWidget(self.log_text)\n'
    '\n'
    "        self.result_tab_index = self.right_tabs.addTab(result_page, '评估结果')\n"
    "        self.log_tab_index = self.right_tabs.addTab(log_page, '训练日志')\n"
    '        layout.addWidget(self.right_tabs)\n'
    '\n'
    '    def _set_running_state(self, running, message):\n'
    '        """同步主操作、停止按钮、进度和状态文字。"""\n'
    '        if running:\n'
    '            self.right_tabs.setCurrentIndex(self.log_tab_index)\n'
    '        locked_controls = [\n'
    '            self.import_btn, self.import_dir_btn, self.import_json_btn,\n'
    '            self.delete_btn, self.import_list,\n'
    '            self.rnn_btn, self.gru_btn, self.lstm_btn,\n'
    '            self.xgboost_btn, self.rf_btn,\n'
    '            self.load_model_btn, self.save_model_btn,\n'
    '            self.unload_model_btn, self.tcp_btn,\n'
    '            self.save_chart_btn, self.export_btn,\n'
    '        ]\n'
    '        locked_controls.extend(\n'
    "            widget for _, widget, _ in getattr(self, '_param_rows', []))\n"
    '        locked_controls.extend([\n'
    '            self.adapter_combo, self.cc_step_input, self.cv_step_input,\n'
    '            self.discharge_step_input,\n'
    '        ])\n'
    '        for control in locked_controls:\n'
    '            control.setEnabled(not running)\n'
    '        if not running:\n'
    '            self.save_model_btn.setEnabled(self.final_trained_model is not None)\n'
    '            self.unload_model_btn.setEnabled(self.loaded_model is not None)\n'
    '            self.tcp_btn.setEnabled(self.loaded_model is not None)\n'
    "            self.export_btn.setEnabled(bool(getattr(self, '_last_detail', None)))\n"
    '            self._on_adapter_changed()\n'
    '        self.start_btn.setEnabled(not running)\n'
    '        self.pause_btn.setEnabled(running)\n'
    '        self.progress_bar.setVisible(running)\n'
    '        self.run_status_label.setText(message)\n'
    "        self.run_status_label.setProperty('state', 'running' if running else 'idle')\n"
    '        self.run_status_label.style().unpolish(self.run_status_label)\n'
    '        self.run_status_label.style().polish(self.run_status_label)\n'
    "        self.run_status_dot.setProperty('state', 'running' if running else 'idle')\n"
    '        self.run_status_dot.style().unpolish(self.run_status_dot)\n'
    '        self.run_status_dot.style().polish(self.run_status_dot)\n'
    "        if hasattr(self, 'status_bar'):\n"
    '            self.status_bar.showMessage(message)\n'
    '\n'
    '    def select_mode(self, selected_mode):\n'
    '        selected_mode = normalize_model_name(selected_mode)\n'
    '        self.current_mode = selected_mode\n'
    '        buttons = {\n'
    "            'RNN': self.rnn_btn, 'GRU': self.gru_btn, 'LSTM': self.lstm_btn,\n"
    "            'XGBoost': self.xgboost_btn, 'RF': self.rf_btn\n"
    '        }\n'
    '        for m, btn in buttons.items():\n'
    '            btn.set_active(m == selected_mode)\n'
    '        descriptions = {\n'
    "            'RNN': '循环神经网络 · 时序基线',\n"
    "            'GRU': '门控循环单元 · 轻量时序',\n"
    "            'LSTM': '长短期记忆网络 · 长程依赖',\n"
    "            'XGBoost': '梯度提升树 · 表格特征',\n"
    "            'RF': '随机森林 · 稳健集成',\n"
    '        }\n'
    '        self.model_hint_label.setText(descriptions[selected_mode])\n'
    '        self._update_param_panel(selected_mode)\n'
    '        if self._help_dialog is not None and self._help_dialog.isVisible():\n'
    '            self._help_dialog.set_content(selected_mode)\n'
    '\n'
    '    def _update_param_panel(self, mode):\n'
    '        for label, widget, modes in self._param_rows:\n'
    '            visible = mode in modes\n'
    '            label.setVisible(visible)\n'
    '            widget.setVisible(visible)\n'
    '\n'
    '    def _on_adapter_changed(self):\n'
    '        """切换数据源适配器时更新工步设置说明。"""\n'
    '        from core.adapters import ADAPTERS\n'
    '        adapter_name = self.adapter_combo.currentData()\n'
    '        adapter_cls = ADAPTERS.get(adapter_name)\n'
    '        if adapter_cls is None:\n'
    '            return\n'
    '        needs_steps = adapter_cls.needs_step_config()\n'
    '        tooltip = (\n'
    "            '留空表示“无”；请输入非负整数。当前数据格式将使用此工步设置'\n"
    '            if needs_steps else\n'
    "            '留空表示“无”；请输入非负整数。当前数据格式不读取工步，仍可提前自定义')\n"
    '        for step_input in (\n'
    '                self.cc_step_input, self.cv_step_input,\n'
    '                self.discharge_step_input):\n'
    '            step_input.setToolTip(tooltip)\n'
    '\n'
    '    def import_files(self):\n'
    '        from core.adapters import ADAPTERS\n'
    '        adapter_name = self.adapter_combo.currentData()\n'
    '        adapter_cls = ADAPTERS.get(adapter_name)\n'
    "        exts = adapter_cls.extensions() if adapter_cls else ('.xlsx', '.csv')\n"
    "        ext_filter = ' '.join(f'*{e}' for e in exts)\n"
    '        paths, _ = QFileDialog.getOpenFileNames(\n'
    "            self, '选择电池数据文件', '',\n"
    "            f'数据文件 ({ext_filter});;所有文件 (*.*)')\n"
    '        if not paths:\n'
    '            return\n'
    '        for path in paths:\n'
    '            if path in self.imported_paths:\n'
    '                continue\n'
    '            self.imported_paths.append(path)\n'
    '            display = os.path.basename(path)\n'
    '            self.import_list.addItem(display)\n'
    '        self._update_data_summary()\n'
    '\n'
    '    def import_folder(self):\n'
    "        dlg = QFileDialog(self, '选择电池数据文件夹')\n"
    '        dlg.setFileMode(QFileDialog.FileMode.Directory)\n'
    '        dlg.setOption(QFileDialog.Option.ShowDirsOnly, True)\n'
    '        dlg.setOption(QFileDialog.Option.DontUseNativeDialog, True)\n'
    '        _configure_folder_dialog(dlg)\n'
    '        for view in dlg.findChildren(QAbstractItemView):\n'
    '            view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)\n'
    '        if dlg.exec() != QFileDialog.DialogCode.Accepted:\n'
    '            return\n'
    '        folders = dlg.selectedFiles()\n'
    '        if not folders:\n'
    '            return\n'
    '        for folder in folders:\n'
    '            if folder in self.imported_paths:\n'
    '                continue\n'
    '            self.imported_paths.append(folder)\n'
    '            from core.adapters import ADAPTERS\n'
    '            adapter_name = self.adapter_combo.currentData()\n'
    '            adapter_cls = ADAPTERS.get(adapter_name)\n'
    "            exts = adapter_cls.extensions() if adapter_cls else ('.xlsx', '.csv')\n"
    '            total = 0\n'
    '            for ext in exts:\n'
    "                total += len(glob.glob(os.path.join(folder, f'*{ext}')))\n"
    "            folder_name = os.path.basename(folder.rstrip('/\\\\'))\n"
    "            display = f'{folder_name}（{total}）'\n"
    '            self.import_list.addItem(display)\n'
    '        self._update_data_summary()\n'
    '\n'
    '    def import_json_config(self):\n'
    "        file_path, _ = QFileDialog.getOpenFileName(self, '导入 JSON 配置文件', '', 'JSON 文件 (*.json)')\n"
    '        if not file_path:\n'
    '            return\n'
    '        try:\n'
    "            with open(file_path, 'r', encoding='utf-8') as f:\n"
    '                data = json.load(f)\n'
    '\n'
    '            imported_config = TrainConfig.from_dict(data)\n'
    '            self._apply_train_config(imported_config)\n'
    '\n'
    "            self.append_log(f'已从 {os.path.basename(file_path)} 加载JSON配置')\n"
    "            self.logger.info(f'已从 {file_path} 导入JSON配置')\n"
    '\n'
    "            if data.get('auto_start', False):\n"
    '                self.start_evaluation()\n'
    '\n'
    '        except Exception as e:\n'
    "            show_message(self, 'error', '错误', f'导入 JSON 文件失败：{e}')\n"
    "            self.logger.error(f'导入 JSON 配置失败：{e}')\n"
    '\n'
    '    def _apply_train_config(self, config):\n'
    '        """Apply a validated TrainConfig to every corresponding UI control."""\n'
    '        self.rated_capacity_spin.setValue(config.rated_capacity)\n'
    '        self.threshold_ratio_spin.setValue(config.threshold_ratio)\n'
    '        self.voltage_upper_spin.setValue(config.voltage_upper)\n'
    '        self.voltage_lower_spin.setValue(config.voltage_lower)\n'
    '        self.feature_size_spin.setValue(config.window_size)\n'
    '        self.epochs_spin.setValue(config.epochs)\n'
    '        self.hidden_dim_spin.setValue(config.hidden_dim)\n'
    '        self.seed_spin.setValue(config.seed)\n'
    '        self.n_seeds_spin.setValue(config.n_seeds)\n'
    '\n'
    '        metric_text = {\n'
    "            'rmse': 'RMSE', 'mae': 'MAE', 'r2': 'R²',\n"
    "            'pearson': 'Pearson', 're': 'RE', 'all': '全部',\n"
    '        }[config.metric]\n'
    '        norm_text = {\n'
    "            'rated': '额定容量归一化',\n"
    "            'minmax': 'MinMax',\n"
    "            'zscore': 'ZScore',\n"
    '        }[config.norm_method]\n'
    '        self.metric_combo.setCurrentText(metric_text)\n'
    '        self.norm_combo.setCurrentText(norm_text)\n'
    '        self.device_combo.setCurrentText(\n'
    "            'GPU (CUDA)' if config.device == 'cuda' else 'CPU')\n"
    '\n'
    '        self.xgb_n_estimators_spin.setValue(config.n_estimators)\n'
    '        self.xgb_learning_rate_spin.setValue(config.learning_rate)\n'
    '        self.xgb_max_depth_spin.setValue(config.max_depth)\n'
    '        self.xgb_subsample_spin.setValue(config.subsample)\n'
    '        self.xgb_colsample_bytree_spin.setValue(config.colsample_bytree)\n'
    '        self.xgb_patience_spin.setValue(config.patience)\n'
    '\n'
    '        self.rf_n_estimators_spin.setValue(config.n_estimators)\n'
    '        self.rf_max_depth_spin.setValue(config.max_depth)\n'
    '        self.rf_min_samples_leaf_spin.setValue(config.min_samples_leaf)\n'
    '        self.rf_max_features_spin.setValue(config.max_features)\n'
    '        self.rf_patience_spin.setValue(config.patience)\n'
    '\n'
    '        adapter_index = self.adapter_combo.findData(config.adapter_type)\n'
    '        if adapter_index < 0:\n'
    "            raise ValueError(f'不支持的数据适配器: {config.adapter_type}')\n"
    '        self.adapter_combo.setCurrentIndex(adapter_index)\n'
    '        _set_step_input(self.cc_step_input, config.cc_step)\n'
    '        _set_step_input(self.cv_step_input, config.cv_step)\n'
    '        _set_step_input(self.discharge_step_input, config.discharge_step)\n'
    '        self.select_mode(config.mode)\n'
    '\n'
    '    def import_list_key_press(self, event):\n'
    '        if event.key() == Qt.Key.Key_Delete:\n'
    '            self.delete_selected_items()\n'
    '        else:\n'
    '            QListWidget.keyPressEvent(self.import_list, event)\n'
    '\n'
    '    def delete_selected_items(self):\n'
    '        rows = sorted([idx.row() for idx in self.import_list.selectedIndexes()], reverse=True)\n'
    '        if not rows:\n'
    "            show_message(self, 'info', '提示', '请先在列表中选中要删除的项目。')\n"
    '            return\n'
    '        for row in rows:\n'
    '            self.import_list.takeItem(row)\n'
    '            if row < len(self.imported_paths):\n'
    '                del self.imported_paths[row]\n'
    '        self._update_data_summary()\n'
    '\n'
    '    def _update_data_summary(self):\n'
    '        """同步数据队列摘要，不在狭窄列表中重复堆叠状态信息。"""\n'
    '        count = len(self.imported_paths)\n'
    '        if count:\n'
    "            self.data_summary_label.setText(f'已载入 {count} 项数据 · 队列待评估')\n"
    '        else:\n'
    "            self.data_summary_label.setText('尚未导入数据 · 等待建立评估队列')\n"
    '        self.data_summary_label.setProperty(\n'
    "            'state', 'ready' if count else 'empty')\n"
    '        self.data_summary_count.setText(str(count))\n'
    "        self.data_summary_count.setAccessibleName(f'已导入 {count} 项数据')\n"
    '        for widget in (self.data_summary_label, self.data_summary_count):\n'
    '            widget.style().unpolish(widget)\n'
    '            widget.style().polish(widget)\n'
    '\n'
    '    def append_log(self, text):\n'
    '        cursor = self.log_text.textCursor()\n'
    '        cursor.movePosition(QTextCursor.MoveOperation.End)\n'
    '        cursor.insertText(str(text))\n'
    '        cursor.insertBlock()\n'
    '        self.logger.info(str(text))\n'
    '\n'
    '    def _build_config(self):\n'
    "        norm_map = {'额定容量归一化': 'rated', 'MinMax': 'minmax', 'ZScore': 'zscore'}\n"
    "        metric_map = {'RMSE': 'rmse', 'MAE': 'mae', 'R²': 'r2', 'Pearson': 'pearson', 'RE': 're', '全部': 'all'}\n"
    '        device_text = self.device_combo.currentText()\n'
    "        target_device = 'cpu'\n"
    "        if device_text == 'GPU (CUDA)' and torch.cuda.is_available():\n"
    "            target_device = 'cuda'\n"
    '\n'
    '        config = TrainConfig(\n'
    '            rated_capacity=self.rated_capacity_spin.value(),\n'
    '            threshold_ratio=self.threshold_ratio_spin.value(),\n'
    '            voltage_upper=self.voltage_upper_spin.value(),\n'
    '            voltage_lower=self.voltage_lower_spin.value(),\n'
    '            window_size=self.feature_size_spin.value(),\n'
    '            hidden_dim=self.hidden_dim_spin.value(),\n'
    '            epochs=self.epochs_spin.value(),\n'
    '            mode=self.current_mode,\n'
    '            metric=metric_map[self.metric_combo.currentText()],\n'
    '            device=target_device,\n'
    '            norm_method=norm_map[self.norm_combo.currentText()],\n'
    '            adapter_type=self.adapter_combo.currentData(),\n'
    '            cc_step=_step_input_value(self.cc_step_input),\n'
    '            cv_step=_step_input_value(self.cv_step_input),\n'
    '            discharge_step=_step_input_value(self.discharge_step_input),\n'
    '        )\n'
    '\n'
    '        config.seed = self.seed_spin.value()\n'
    '        config.n_seeds = self.n_seeds_spin.value()\n'
    '        config.patience = self.xgb_patience_spin.value()\n'
    '\n'
    "        if self.current_mode == 'XGBoost':\n"
    '            config.n_estimators = self.xgb_n_estimators_spin.value()\n'
    '            config.learning_rate = self.xgb_learning_rate_spin.value()\n'
    '            config.max_depth = self.xgb_max_depth_spin.value()\n'
    '            config.subsample = self.xgb_subsample_spin.value()\n'
    '            config.colsample_bytree = self.xgb_colsample_bytree_spin.value()\n'
    '            config.patience = self.xgb_patience_spin.value()\n'
    "        elif self.current_mode == 'RF':\n"
    '            config.n_estimators = self.rf_n_estimators_spin.value()\n'
    '            config.max_depth = self.rf_max_depth_spin.value()\n'
    '            config.min_samples_leaf = self.rf_min_samples_leaf_spin.value()\n'
    '            config.max_features = self.rf_max_features_spin.value()\n'
    '            config.patience = self.rf_patience_spin.value()\n'
    '\n'
    '        return config\n'
    '\n'
    '    def start_evaluation(self):\n'
    '        if self.worker is not None:\n'
    '            show_message(\n'
    "                self, 'info', '任务仍在收尾',\n"
    "                '当前训练或预测任务尚未完全结束。请等待状态恢复为“准备就绪”后再开始新的任务。')\n"
    '            return\n'
    '        if len(self.imported_paths) == 0:\n'
    "            show_message(self, 'warning', '提示', '请先导入文件或文件夹。')\n"
    '            return\n'
    '        config = self._build_config()\n'
    '        from core.validation import validate_training_config\n'
    '        errors = validate_training_config(config)\n'
    '        if errors:\n'
    '            visible_errors = errors[:10]\n'
    '            suffix = (\n'
    "                f'\\n……另有 {len(errors) - 10} 项错误'\n"
    "                if len(errors) > 10 else '')\n"
    '            show_message(\n'
    "                self, 'warning', '数据校验未通过',\n"
    "                '\\n'.join(f'• {error}' for error in visible_errors) + suffix)\n"
    '            return\n'
    '\n'
    '        if self.loaded_model is not None:\n'
    '            self._run_prediction(config)\n'
    '            return\n'
    '\n'
    "        destination = 'current'\n"
    '        if self._has_completed_training_run:\n'
    '            destination = self._ask_training_destination()\n'
    "        if destination == 'current':\n"
    '            self._run_training(config)\n'
    "        elif destination == 'new':\n"
    '            self._launch_training_window(config)\n'
    '\n'
    '    def _ask_training_destination(self):\n'
    '        dialog = QMessageBox(self)\n'
    "        dialog.setWindowTitle('开始新的模型训练')\n"
    "        dialog.setWindowIcon(get_dialog_icon('chart'))\n"
    '        dialog.setIcon(QMessageBox.Icon.Question)\n'
    "        dialog.setText('当前窗口已经保留了一次模型训练结果。')\n"
    '        dialog.setInformativeText(\n'
    "            '请选择在当前窗口继续，或复制当前数据与参数到新的完整窗口中训练。'\n"
    "            '在当前窗口训练会清空旧日志，但不会删除已有结果批次。')\n"
    '        current_button = dialog.addButton(\n'
    "            '在此窗口训练', QMessageBox.ButtonRole.AcceptRole)\n"
    '        new_button = dialog.addButton(\n'
    "            '在新窗口训练', QMessageBox.ButtonRole.ActionRole)\n"
    '        cancel_button = dialog.addButton(\n'
    "            '取消', QMessageBox.ButtonRole.RejectRole)\n"
    '        dialog.setDefaultButton(cancel_button)\n'
    '        dialog.setEscapeButton(cancel_button)\n'
    '        _apply_windows_paper_caption(dialog)\n'
    '        dialog.exec()\n'
    '        clicked = dialog.clickedButton()\n'
    '        if clicked is current_button:\n'
    "            return 'current'\n"
    '        if clicked is new_button:\n'
    "            return 'new'\n"
    '        return None\n'
    '\n'
    '    def _launch_training_window(self, config):\n'
    '        child = MainWindow()\n'
    '        child_config = TrainConfig.from_dict(config.to_dict())\n'
    '        child._apply_train_config(child_config)\n'
    '        child.imported_paths = list(self.imported_paths)\n'
    '        child.import_list.clear()\n'
    '        for index, path in enumerate(child.imported_paths):\n'
    '            if index < self.import_list.count():\n'
    '                display = self.import_list.item(index).text()\n'
    '            else:\n'
    "                display = os.path.basename(path.rstrip('/\\\\')) or path\n"
    '            child.import_list.addItem(display)\n'
    '        child._update_data_summary()\n'
    '\n'
    '        self._child_training_windows.append(child)\n'
    '        MainWindow._independent_windows.append(child)\n'
    '        child.destroyed.connect(\n'
    '            lambda _object=None, window=child:\n'
    '            self._forget_training_window(window))\n'
    '        child.show()\n'
    '        child.raise_()\n'
    '        child.activateWindow()\n'
    '        child._run_training(child_config)\n'
    '        return child\n'
    '\n'
    '    def _forget_training_window(self, window):\n'
    '        if window in self._child_training_windows:\n'
    '            self._child_training_windows.remove(window)\n'
    '        if window in MainWindow._independent_windows:\n'
    '            MainWindow._independent_windows.remove(window)\n'
    '\n'
    '    def _run_training(self, config):\n'
    "        self._active_run_kind = 'training'\n"
    "        self._finish_status_message = '准备就绪'\n"
    '        self._active_run_snapshot = RunSnapshot.capture(\n'
    '            config, self.imported_paths)\n'
    '        config = TrainConfig.from_dict(\n'
    '            self._active_run_snapshot.config_dict())\n'
    '        imported_paths = self._active_run_snapshot.imported_paths\n'
    '        self._eval_rated_capacity = config.rated_capacity\n'
    '        self._eval_threshold_ratio = config.threshold_ratio\n'
    '\n'
    '        self.log_text.clear()\n'
    '        if not self._result_batches:\n'
    '            self._show_result_state(\n'
    "                '正在分析电池数据',\n"
    "                '训练日志会持续更新。可随时点击“停止”结束当前任务。')\n"
    "        self._set_running_state(True, '正在训练模型')\n"
    "        self.logger.info(f'开始评估，配置：{config}')\n"
    '\n'
    '        self.worker = EvalWorker(config, imported_paths, parent=self)\n'
    '        self.worker.log_signal.connect(self.append_log)\n'
    '        self.worker.error_signal.connect(self.on_error)\n'
    '        self.worker.result_signal.connect(self.on_result)\n'
    '        self.worker.progress_signal.connect(self.on_progress)\n'
    '        self.worker.finished_signal.connect(self.on_finished)\n'
    '        self.worker.finished.connect(self.on_finished)\n'
    '        self.worker.finished.connect(self.worker.deleteLater)\n'
    '        self.worker.final_model_signal.connect(self.on_final_model_ready)\n'
    '        self.worker.start()\n'
    '\n'
    '    def _run_prediction(self, config):\n'
    "        self._active_run_kind = 'prediction'\n"
    "        self._finish_status_message = '准备就绪'\n"
    "        config.window_size = self.loaded_metadata['window_size']\n"
    "        if 'rated_capacity' in self.loaded_metadata:\n"
    "            config.rated_capacity = self.loaded_metadata['rated_capacity']\n"
    "        if 'threshold_ratio' in self.loaded_metadata:\n"
    "            config.threshold_ratio = self.loaded_metadata['threshold_ratio']\n"
    '        self._active_run_snapshot = RunSnapshot.capture(\n'
    '            config, self.imported_paths)\n'
    '        config = TrainConfig.from_dict(\n'
    '            self._active_run_snapshot.config_dict())\n'
    '        imported_paths = self._active_run_snapshot.imported_paths\n'
    '        self._eval_rated_capacity = config.rated_capacity\n'
    '        self._eval_threshold_ratio = config.threshold_ratio\n'
    '\n'
    '        self.log_text.clear()\n'
    '        if not self._result_batches:\n'
    '            self._show_result_state(\n'
    "                '正在分析电池数据',\n"
    "                '正在使用已加载模型生成预测结果。')\n"
    "        self._set_running_state(True, '正在生成预测')\n"
    '\n'
    '        from ui.predict_worker import PredictWorker\n'
    '        self.worker = PredictWorker(\n'
    '            self.loaded_model, self.loaded_metadata,\n'
    '            imported_paths, config, parent=self\n'
    '        )\n'
    '        self.worker.log_signal.connect(self.append_log)\n'
    '        self.worker.error_signal.connect(self.on_error)\n'
    '        self.worker.result_signal.connect(self.on_result)\n'
    '        self.worker.progress_signal.connect(self.on_progress)\n'
    '        self.worker.finished_signal.connect(self.on_finished)\n'
    '        self.worker.finished.connect(self.on_finished)\n'
    '        self.worker.finished.connect(self.worker.deleteLater)\n'
    '        self.worker.start()\n'
    '\n'
    '    def pause_evaluation(self):\n'
    '        if self.worker is not None and self.worker.isRunning():\n'
    '            self.pause_btn.setEnabled(False)\n'
    "            self.run_status_label.setText('正在安全停止，请稍候…')\n"
    '            if self._request_worker_stop(timeout_ms=3000):\n'
    "                self.append_log('评估已在安全检查点停止。')\n"
    "                self._set_running_state(False, '评估已停止')\n"
    '                if self._result_batches:\n'
    '                    self.right_tabs.setCurrentIndex(self.result_tab_index)\n'
    '                else:\n'
    '                    self._show_result_state(\n'
    "                        '评估已停止', '参数和导入数据均已保留，可调整后重新开始。')\n"
    '            else:\n'
    '                show_message(\n'
    "                    self, 'warning', '仍在安全停止',\n"
    "                    '当前计算尚未到达安全检查点。系统不会强制终止，请稍候；停止完成前不能开始新任务或导出报告。')\n"
    '\n'
    '    def _request_worker_stop(self, timeout_ms, closing=False):\n'
    '        worker = self.worker\n'
    '        if worker is None or not worker.isRunning():\n'
    '            self.worker = None\n'
    '            return True\n'
    '        worker.request_stop()\n'
    '        worker.requestInterruption()\n'
    '        if worker.wait(timeout_ms):\n'
    '            self.on_finished(worker)\n'
    '            return True\n'
    '        if not closing:\n'
    "            self._set_running_state(True, '正在安全停止，请稍候…')\n"
    '            self.pause_btn.setEnabled(False)\n'
    '        return False\n'
    '\n'
    '    def save_model(self):\n'
    '        if self.final_trained_model is None:\n'
    "            show_message(self, 'warning', '提示', '请先完成训练后再保存模型。')\n"
    '            return\n'
    "        default_ext = '.pt' if self.current_mode in ('RNN', 'GRU', 'LSTM') else '.joblib'\n"
    '        filepath, _ = QFileDialog.getSaveFileName(\n'
    "            self, '保存模型',\n"
    "            os.fspath(MODEL_DIR / f'model{default_ext}'),\n"
    "            '模型文件 (*.pt *.pth *.joblib);;所有文件 (*.*)')\n"
    '        if not filepath:\n'
    '            return\n'
    '        try:\n'
    '            from core.model_persistence import save_model\n'
    '            save_model(self.final_trained_model, self.final_trained_metadata, filepath)\n'
    "            self.append_log(f'模型已保存至 {filepath}')\n"
    '        except Exception as e:\n'
    "            show_message(self, 'error', '错误', f'保存模型失败：{e}')\n"
    '\n'
    '    def load_model(self):\n'
    '        filepath, _ = QFileDialog.getOpenFileName(\n'
    "            self, '加载模型', os.fspath(OUTPUTS_DIR),\n"
    "            '模型文件 (*.pt *.pth *.joblib);;所有文件 (*.*)')\n"
    '        if not filepath:\n'
    '            return\n'
    '        allow_unsafe_joblib = False\n'
    "        if os.path.splitext(filepath)[1].lower() == '.joblib':\n"
    '            answer = show_message(\n'
    "                self, 'warning', '安全提醒',\n"
    "                'joblib 模型在加载时可能执行代码。仅当文件由本系统生成、来源可信且哈希清单未被替换时继续。是否加载？',\n"
    '                buttons=(QMessageBox.StandardButton.Yes |\n'
    '                         QMessageBox.StandardButton.No),\n'
    '                default=QMessageBox.StandardButton.No)\n'
    '            if answer != QMessageBox.StandardButton.Yes:\n'
    '                return\n'
    '            allow_unsafe_joblib = True\n'
    '        try:\n'
    '            self.load_model_from_path(\n'
    '                filepath, allow_unsafe_joblib=allow_unsafe_joblib)\n'
    '        except Exception as e:\n'
    "            show_message(self, 'error', '错误', f'加载模型失败：{e}')\n"
    '\n'
    '    def load_model_from_path(self, filepath, allow_unsafe_joblib=False):\n'
    '        """Validate a new model completely, then atomically replace the session."""\n'
    '        from core.model_persistence import load_model\n'
    '        new_model, new_metadata = load_model(\n'
    '            filepath, allow_unsafe_joblib=allow_unsafe_joblib)\n'
    "        mode = normalize_model_name(new_metadata['mode'])\n"
    '        self.select_mode(mode)\n'
    '\n'
    '        self.loaded_model, self.loaded_metadata = new_model, new_metadata\n'
    '        self.unload_model_btn.setEnabled(True)\n'
    '        self.tcp_btn.setEnabled(True)\n'
    "        self.append_log(f'已加载 {mode} 模型：{os.path.basename(filepath)}')\n"
    '        self.append_log(\n'
    '            f\'  窗口大小={new_metadata["window_size"]}，\'\n'
    '            f\'额定容量={new_metadata.get("rated_capacity", "-")}\')\n'
    '        self.status_bar.showMessage(\n'
    "            f'已加载 {mode} 模型，导入数据后点击启动即可预测')\n"
    '        return new_model, new_metadata\n'
    '\n'
    '    def unload_model(self):\n'
    '        """Unload the imported model so the main action trains a new model again."""\n'
    '        if self.tcp_running:\n'
    "            show_message(self, 'warning', '提示', '请先停止数据接入，再卸载模型。')\n"
    '            return False\n'
    '        self.loaded_model, self.loaded_metadata = None, None\n'
    '        self.unload_model_btn.setEnabled(False)\n'
    '        self.tcp_btn.setEnabled(False)\n'
    "        self.append_log('已卸载模型，开始评估时将重新训练。')\n"
    "        self.status_bar.showMessage('已切回训练模式')\n"
    '        return True\n'
    '\n'
    '    def on_final_model_ready(self, model, metadata):\n'
    '        self.final_trained_model = model\n'
    '        self.final_trained_metadata = metadata\n'
    '        self.save_model_btn.setEnabled(True)\n'
    '        self.append_log(\'最终模型（全数据训练）已就绪，可点击"保存模型"导出。\')\n'
    '\n'
    '    def toggle_tcp_server(self):\n'
    '        if self.tcp_running:\n'
    '            self._stop_tcp_server()\n'
    '        else:\n'
    '            self._start_tcp_server()\n'
    '\n'
    '    def _start_tcp_server(self):\n'
    '        if self.loaded_model is None:\n'
    "            show_message(self, 'warning', '提示', '请先加载模型后再启动数据接入。')\n"
    '            return\n'
    '        config = self._build_config()\n'
    "        config.window_size = self.loaded_metadata['window_size']\n"
    '        self._eval_rated_capacity = config.rated_capacity\n'
    '        self._eval_threshold_ratio = config.threshold_ratio\n'
    '\n'
    '        from ui.tcp_server import TCPServerWorker\n'
    '        from ui.tcp_display import TcpDisplayWindow\n'
    '\n'
    '        self._tcp_window = TcpDisplayWindow(self)\n'
    '        self._tcp_window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)\n'
    '        self._tcp_window.show()\n'
    '\n'
    '        # A10：默认只监听本机；开放局域网必须在界面里显式勾选，\n'
    '        # 并自动生成 token 供客户端握手。\n'
    '        allow_lan = False\n'
    "        if hasattr(self, 'tcp_lan_check') and self.tcp_lan_check.isChecked():\n"
    '            allow_lan = True\n'
    '        self.tcp_server = TCPServerWorker(\n'
    '            self.loaded_model, self.loaded_metadata, config, port=8888,\n'
    '            allow_lan=allow_lan,\n'
    '        )\n'
    '        self.tcp_server.status_signal.connect(self.append_log)\n'
    '        self.tcp_server.error_signal.connect(self.on_error)\n'
    '        self.tcp_server.data_received_signal.connect(\n'
    '            self._tcp_window.update_status)\n'
    '        self.tcp_server.soh_update_signal.connect(self._tcp_window.update_soh)\n'
    '        self.tcp_server.rul_update_signal.connect(self._tcp_window.update_rul)\n'
    '        self.tcp_server.prediction_signal.connect(\n'
    '            lambda m, p: self._tcp_window.update_chart(\n'
    '                m, p, self._eval_rated_capacity, self._eval_threshold_ratio))\n'
    '        self.tcp_server.start()\n'
    '        self.tcp_running = True\n'
    "        self.tcp_btn.setText('断开数据')\n"
    "        self.tcp_btn._role = 'danger'\n"
    "        self.tcp_btn.setProperty('role', 'danger')\n"
    '        self.tcp_btn.style().unpolish(self.tcp_btn)\n'
    '        self.tcp_btn.style().polish(self.tcp_btn)\n'
    '        if allow_lan:\n'
    '            self.append_log(\n'
    "                f'TCP 数据接入服务已启动（局域网模式，端口 8888）；'\n"
    "                f'客户端首条消息需带 token：{self.tcp_server.auth_token}')\n"
    '        else:\n'
    '            self.append_log(\n'
    "                'TCP 数据接入服务已启动，仅监听本机 127.0.0.1:8888...')\n"
    '\n'
    '    def _stop_tcp_server(self):\n'
    '        if self.tcp_server is not None:\n'
    '            self.tcp_server.request_stop()\n'
    '            self.tcp_server.wait(3000)\n'
    '        self.tcp_running = False\n'
    "        self.tcp_btn.setText('接入数据')\n"
    "        self.tcp_btn._role = 'primary'\n"
    "        self.tcp_btn.setProperty('role', 'primary')\n"
    '        self.tcp_btn.style().unpolish(self.tcp_btn)\n'
    '        self.tcp_btn.style().polish(self.tcp_btn)\n'
    '        if self._tcp_window is not None:\n'
    '            self._tcp_window.close()\n'
    '            self._tcp_window = None\n'
    "        self.append_log('TCP 数据接入服务已停止。')\n"
    '\n'
    '    def on_tcp_data(self, capacity, soh):\n'
    "        self.status_bar.showMessage(f'实时数据 | 容量: {capacity:.6f} Ah | SOH: {soh:.1f}%')\n"
    '\n'
    '    def on_soh_update(self, soh_info):\n'
    '        """A10：SOH 阶段表按「距最新已观测循环」的口径展示。"""\n'
    '        rows = [\'<table border="1" cellpadding="3" cellspacing="0">\',\n'
    "                '<tr><th>SOH (%)</th><th>距最新循环</th><th>状态</th></tr>']\n"
    '        for pct in (100, 95, 90, 85, 80):\n'
    '            info = soh_info.get(pct, {}) or {}\n'
    "            offset = info.get('cycle_offset')\n"
    '            if offset is None:\n'
    "                state = '预测期内未到达'\n"
    "            elif info.get('reached'):\n"
    "                state = '✓ 已到达'\n"
    '            else:\n'
    "                state = '预测中'\n"
    '            rows.append(\n'
    "                f'<tr><td>{pct}%</td>'\n"
    '                f\'<td>{"—" if offset is None else f"{offset:+d}"}</td>\'\n'
    "                f'<td>{state}</td></tr>')\n"
    "        rows.append('</table>')\n"
    "        self.soh_table_label.setText(''.join(rows))\n"
    '\n'
    '    def on_rul_update(self, rul_info):\n'
    '        """A10：RUL = 距最新已观测循环还有几个未来循环越过失效阈值。"""\n'
    "        rul = rul_info.get('rul')\n"
    '        if rul is None:\n'
    "            value = '预测期内不会越过失效阈值'\n"
    '        elif rul == 0:\n'
    "            value = '0 个循环（当前已低于失效阈值）'\n"
    '        else:\n'
    "            value = f'{int(rul)} 个循环'\n"
    '        rows = [\'<table border="1" cellpadding="3" cellspacing="0">\',\n'
    "                '<tr><th>剩余寿命 (RUL)</th><th>失效阈值</th></tr>',\n"
    "                f'<tr><td>{value}</td>'\n"
    '                f\'<td>{rul_info.get("threshold", 0):.4f} Ah</td></tr>\',\n'
    "                '</table>']\n"
    "        self.rul_table_label.setText(''.join(rows))\n"
    '\n'
    '    def on_tcp_prediction(self, measured, predicted):\n'
    '        self.canvas.plot_tcp_predictions(measured, predicted,\n'
    '                                         self._eval_rated_capacity,\n'
    '                                         self._eval_threshold_ratio)\n'
    '\n'
    '    def save_chart(self):\n'
    '        file_path, _ = QFileDialog.getSaveFileName(\n'
    "            self, '保存图表', os.fspath(FIGURE_DIR),\n"
    "            'PNG 图片 (*.png);;JPG 图片 (*.jpg);;PDF 文件 (*.pdf)')\n"
    '        if not file_path:\n'
    '            return\n'
    '        if os.path.exists(file_path):\n'
    '            answer = QMessageBox.question(\n'
    "                self, '确认覆盖',\n"
    "                f'文件已存在：\\n{file_path}\\n\\n是否覆盖？',\n"
    '                QMessageBox.StandardButton.Yes\n'
    '                | QMessageBox.StandardButton.No,\n'
    '                QMessageBox.StandardButton.No,\n'
    '            )\n'
    '            if answer != QMessageBox.StandardButton.Yes:\n'
    '                return\n'
    '        try:\n'
    '            atomic_save_figure(self.canvas, file_path)\n'
    '        except ReportExportError as error:\n'
    "            show_message(self, 'error', '图表保存失败', str(error))\n"
    '            return\n'
    "        show_message(self, 'success', '提示', '图表已保存。',\n"
    '                     buttons=QMessageBox.StandardButton.Ok,\n'
    '                     default=QMessageBox.StandardButton.Ok)\n'
    '\n'
    '\n'
    '    def export_report(self):\n'
    '        snapshot = self._last_run_snapshot\n'
    '        if snapshot is None or not snapshot.results:\n'
    "            show_message(self, 'warning', '提示', '请先完成一次训练评估。')\n"
    '            return\n'
    '\n'
    '        def confirm_overwrite(paths):\n'
    "            path_text = '\\n'.join(str(path) for path in paths)\n"
    '            answer = QMessageBox.question(\n'
    "                self, '确认覆盖已有报告',\n"
    "                f'以下文件已存在：\\n{path_text}\\n\\n是否覆盖？',\n"
    '                QMessageBox.StandardButton.Yes\n'
    '                | QMessageBox.StandardButton.No,\n'
    '                QMessageBox.StandardButton.No,\n'
    '            )\n'
    '            return answer == QMessageBox.StandardButton.Yes\n'
    '\n'
    '        try:\n'
    '            artifacts = export_run_report(\n'
    '                snapshot,\n'
    '                self.canvas,\n'
    '                confirm_overwrite=confirm_overwrite,\n'
    '            )\n'
    '        except ExportCancelled:\n'
    "            show_message(self, 'info', '已取消', '未覆盖已有报告。')\n"
    '            return\n'
    '        except ReportExportError as error:\n'
    "            show_message(self, 'error', '报告导出失败', str(error))\n"
    '            return\n'
    '\n'
    '        show_message(\n'
    "            self, 'success', '提示',\n"
    '            f\'报告已导出至：\\n{artifacts["run_directory"]}\\n\\n\'\n'
    "            '- report.json（运行快照、参数与结果）\\n'\n"
    "            '- 评估结果.xlsx（评估指标）\\n'\n"
    "            '- 评估结果.png（预测图表）',\n"
    '            buttons=QMessageBox.StandardButton.Ok,\n'
    '            default=QMessageBox.StandardButton.Ok)\n'
    '\n'
    '    def _install_sup_sub_shortcuts(self):\n'
    '        """安装全局上下标快捷键 (Ctrl+= 上标, Ctrl+Shift+= 下标) 与主题切换 (Ctrl+T)"""\n'
    "        sup_sc = QShortcut(QKeySequence('Ctrl+='), self)\n"
    '        sup_sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)\n'
    "        sup_sc.activated.connect(lambda: apply_sup_sub('^'))\n"
    "        sub_sc = QShortcut(QKeySequence('Ctrl+Shift+='), self)\n"
    '        sub_sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)\n'
    "        sub_sc.activated.connect(lambda: apply_sup_sub('_'))\n"
    "        theme_sc = QShortcut(QKeySequence('Ctrl+T'), self)\n"
    '        theme_sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)\n'
    '        theme_sc.activated.connect(self.toggle_theme)\n'
    '        self._sup_sub_shortcuts = [sup_sc, sub_sc, theme_sc]\n'
    '\n'
    '    _HELP_CONTENT = {\n'
    "        'RNN': (\n"
    "            '<h2>RNN - 简单循环网络</h2>'\n"
    '            \'<p>逐个处理容量序列中的每个值，靠"记忆"捕捉退化趋势。结构最简单、训练最快，适合容量持续下降、波动平稳的数据。</p>\'\n'
    "            '<hr>'\n"
    "            '<h3>通用参数</h3>'\n"
    "            '<p><b>额定容量 (Ah)：</b>电池出厂标称容量，用于将容量值缩放到相近范围以便训练，输出时自动还原。默认 1.1，适用 0.5~5.0。</p>'\n"
    '            \'<p><b>失效阈值比例：</b>容量低于"额定容量 × 此比例"时判定电池报废，行业常用 0.7~0.8，锂离子电池一般取 0.8。</p>\'\n'
    "            '<p><b>SOH上/下电压 (V)：</b>计算SOH健康指标所用的两个电压点。放电过程中分别找到电压最接近这两个设定值的时刻，以两点之间的放电容量差作为SOH指标。三元锂电池(NCM/NCA/LCO)推荐 3.8/3.4V，磷酸铁锂(LFP)推荐 3.4/3.0V，钛酸锂(LTO)推荐 2.3/1.8V。上电压必须大于下电压。</p>'\n"
    "            '<p><b>窗口大小：</b>用前 N 个循环的容量值预测下一个循环的容量值。越大参考的历史越多，但训练数据越少。默认 64，推荐 32~128。</p>'\n"
    '            \'<p><b>评估指标：</b>RMSE=均方根误差（Ah），日常首选，越小越准；MAE=平均绝对误差，对异常值不敏感；R²=决定系数，越接近1越好；Pearson=相关系数，衡量预测与真实值的线性相关性，越接近1越好；RE=寿命预测误差，衡量预测"何时报废"的准确度。</p>\'\n'
    "            '<p><b>随机种子：</b>固定随机数序列的起点，同一参数下每次结果一致。改种子可验证模型是否稳定。</p>'\n"
    "            '<p><b>多种子数(置信区间)：</b>使用多个不同随机种子重复训练，计算各指标的均值±标准差和95%置信区间，评估模型稳定性。值越大统计越可靠但耗时越长。默认5，推荐3~10。</p>'\n"
    "            '<hr>'\n"
    "            '<h3>深度学习参数</h3>'\n"
    '            \'<p><b>隐藏层维度：</b>网络"记忆"的容量。越大能记更多规律，但也容易"过拟合"，对训练数据记得太死，遇到新数据反而预测不准。默认 64，推荐 16~256。</p>\'\n'
    '            \'<p><b>训练轮数：</b>最大训练轮数。每 10 轮评估一次，若连续 20 轮指标不再改善则自动"早停"，提前结束训练，防止过拟合且节省时间。默认 100，推荐 50~200。</p>\'\n'
    "            '<p><b>归一化方式：</b>把容量值缩放到网络擅长的范围。额定容量归一化（除以额定值）最常用；MinMax 压缩到 0~1；ZScore 转为均值 0 标准差 1 的分布。</p>'\n"
    "            '<p><b>计算设备：</b>CPU 通用；GPU 需 NVIDIA 显卡，无 GPU 时自动退回 CPU。</p>'\n"
    '        ),\n'
    "        'GRU': (\n"
    "            '<h2>GRU - 门控循环网络</h2>'\n"
    '            \'<p>RNN 的升级版，增加了"门"来控制哪些信息该记住、哪些该忘掉，能更好处理长期退化趋势。速度与效果平衡，推荐首选。</p>\'\n'
    "            '<hr>'\n"
    "            '<h3>通用参数</h3>'\n"
    "            '<p><b>额定容量 (Ah)：</b>电池出厂标称容量，训练时缩放、输出时还原。默认 1.1，适用 0.5~5.0。</p>'\n"
    '            \'<p><b>失效阈值比例：</b>容量低于"额定容量 × 此比例"时判定失效，行业常用 0.7~0.8。默认 0.8。</p>\'\n'
    "            '<p><b>SOH上/下电压 (V)：</b>计算SOH健康指标所用的两个电压点。放电过程中分别找到电压最接近这两个设定值的时刻，以两点之间的放电容量差作为SOH指标。三元锂电池(NCM/NCA/LCO)推荐 3.8/3.4V，磷酸铁锂(LFP)推荐 3.4/3.0V，钛酸锂(LTO)推荐 2.3/1.8V。上电压必须大于下电压。</p>'\n"
    "            '<p><b>窗口大小：</b>用前 N 个循环的容量值预测下一个循环的容量值。越大参考的历史越多，但训练数据越少。默认 64，推荐 32~128。</p>'\n"
    '            \'<p><b>评估指标：</b>RMSE=均方根误差（Ah），日常首选，越小越准；MAE=平均绝对误差，对异常值不敏感；R²=决定系数，越接近1越好；Pearson=相关系数，衡量预测与真实值的线性相关性，越接近1越好；RE=寿命预测误差，衡量预测"何时报废"的准确度。</p>\'\n'
    "            '<p><b>随机种子：</b>固定随机序列起点，确保结果可复现。</p>'\n"
    "            '<p><b>多种子数(置信区间)：</b>使用多个不同随机种子重复训练，计算各指标的均值±标准差和95%置信区间，评估模型稳定性。值越大统计越可靠但耗时越长。默认5，推荐3~10。</p>'\n"
    "            '<hr>'\n"
    "            '<h3>深度学习参数</h3>'\n"
    "            '<p><b>隐藏层维度：</b>网络记忆容量，越大能学更多规律但可能过拟合。默认 64，推荐 16~256。</p>'\n"
    '            \'<p><b>训练轮数：</b>最大训练轮数。每 10 轮评估一次，若连续 20 轮指标不再改善则自动"早停"，提前结束训练，防止过拟合且节省时间。默认 100，推荐 50~200。</p>\'\n'
    "            '<p><b>归一化方式：</b>额定容量归一化（除以额定值，日常首选）；MinMax（缩放到 0~1）；ZScore（转为均值 0 标准差 1 的标准分布）。</p>'\n"
    "            '<p><b>计算设备：</b>CPU 或 GPU，无 GPU 时自动退回 CPU。</p>'\n"
    '        ),\n'
    "        'LSTM': (\n"
    "            '<h2>LSTM - 长短期记忆网络</h2>'\n"
    '            \'<p>GRU 的加强版，用三个"门"精细控制信息流动，擅长学习复杂的退化规律。参数量最多、训练最慢，适合容量波动较大、退化趋势不规则的数据。</p>\'\n'
    "            '<hr>'\n"
    "            '<h3>通用参数</h3>'\n"
    "            '<p><b>额定容量 (Ah)：</b>电池出厂标称容量，训练时缩放、输出时还原。默认 1.1，适用 0.5~5.0。</p>'\n"
    '            \'<p><b>失效阈值比例：</b>容量低于"额定容量 × 此比例"时判定失效，行业常用 0.7~0.8。默认 0.8。</p>\'\n'
    "            '<p><b>SOH上/下电压 (V)：</b>计算SOH健康指标所用的两个电压点。放电过程中分别找到电压最接近这两个设定值的时刻，以两点之间的放电容量差作为SOH指标。三元锂电池(NCM/NCA/LCO)推荐 3.8/3.4V，磷酸铁锂(LFP)推荐 3.4/3.0V，钛酸锂(LTO)推荐 2.3/1.8V。上电压必须大于下电压。</p>'\n"
    "            '<p><b>窗口大小：</b>用前 N 个循环的容量值预测下一个循环的容量值。越大参考的历史越多，但训练数据越少。默认 64，推荐 32~128。</p>'\n"
    '            \'<p><b>评估指标：</b>RMSE=均方根误差（Ah），日常首选，越小越准；MAE=平均绝对误差，对异常值不敏感；R²=决定系数，越接近1越好；Pearson=相关系数，衡量预测与真实值的线性相关性，越接近1越好；RE=寿命预测误差，衡量预测"何时报废"的准确度。</p>\'\n'
    "            '<p><b>随机种子：</b>固定随机序列起点，确保结果可复现。</p>'\n"
    "            '<p><b>多种子数(置信区间)：</b>使用多个不同随机种子重复训练，计算各指标的均值±标准差和95%置信区间，评估模型稳定性。值越大统计越可靠但耗时越长。默认5，推荐3~10。</p>'\n"
    "            '<hr>'\n"
    "            '<h3>深度学习参数</h3>'\n"
    "            '<p><b>隐藏层维度：</b>网络记忆容量，越大能学更多规律但可能过拟合。默认 64，推荐 16~256。</p>'\n"
    '            \'<p><b>训练轮数：</b>最大训练轮数。每 10 轮评估一次，若连续 20 轮指标不再改善则自动"早停"，提前结束训练，防止过拟合且节省时间。默认 100，推荐 50~200。</p>\'\n'
    "            '<p><b>归一化方式：</b>额定容量归一化（除以额定值，日常首选）；MinMax（缩放到 0~1）；ZScore（转为均值 0 标准差 1 的标准分布）。</p>'\n"
    "            '<p><b>计算设备：</b>CPU 或 GPU，无 GPU 时自动退回 CPU。</p>'\n"
    '        ),\n'
    "        'XGBoost': (\n"
    "            '<h2>XGBoost - 梯度提升树</h2>'\n"
    "            '<p>用多棵决策树接力预测：第一棵粗略估计，后面每棵修正前一棵的误差。无需归一化，训练快、不易过拟合，适合小样本数据。</p>'\n"
    "            '<hr>'\n"
    "            '<h3>通用参数</h3>'\n"
    "            '<p><b>额定容量 (Ah)：</b>仅用于计算失效阈值和展示结果。默认 1.1，适用 0.5~5.0。</p>'\n"
    '            \'<p><b>失效阈值比例：</b>容量低于"额定容量 × 此比例"时判定失效，行业常用 0.7~0.8。默认 0.8。</p>\'\n'
    "            '<p><b>SOH上/下电压 (V)：</b>计算SOH健康指标所用的两个电压点。三元锂电池(NCM/NCA/LCO)推荐 3.8/3.4V，磷酸铁锂(LFP)推荐 3.4/3.0V，钛酸锂(LTO)推荐 2.3/1.8V。上电压必须大于下电压。</p>'\n"
    "            '<p><b>窗口大小：</b>用前 N 个循环预测下一个。默认 64，推荐 32~128。</p>'\n"
    '            \'<p><b>评估指标：</b>RMSE=均方根误差（Ah），日常首选，越小越准；MAE=平均绝对误差，对异常值不敏感；R²=决定系数，越接近1越好；Pearson=相关系数，衡量预测与真实值的线性相关性，越接近1越好；RE=寿命预测误差，衡量预测"何时报废"的准确度。</p>\'\n'
    "            '<p><b>随机种子：</b>固定随机序列起点，确保结果可复现。</p>'\n"
    "            '<p><b>多种子数(置信区间)：</b>使用多个不同随机种子重复训练，计算各指标的均值±标准差和95%置信区间，评估模型稳定性。值越大统计越可靠但耗时越长。默认5，推荐3~10。</p>'\n"
    "            '<hr>'\n"
    "            '<h3>XGBoost 专用参数</h3>'\n"
    "            '<p><b>树的数量：</b>总共用多少棵树。越多拟合越充分，但太多会过拟合且训练变慢。默认 100，推荐 50~500。</p>'\n"
    "            '<p><b>学习率：</b>每棵树对最终结果的贡献比例。越小结果越稳健但需要更多树。默认 0.05，推荐 0.01~0.3。</p>'\n"
    "            '<p><b>树的最大深度：</b>每棵树最多分多少层。越深规律越精细，但容易过拟合。训练数据较少时（如几十个循环）建议不超过 6。默认 6，推荐 3~10。</p>'\n"
    "            '<p><b>样本采样比例：</b>每棵树随机抽取多少比例的数据来训练。小于 1 可增加多样性、减少过拟合。默认 1.0，推荐 0.6~1.0。</p>'\n"
    "            '<p><b>特征采样比例：</b>每棵树随机使用多少比例的特征。原理同上。默认 1.0，推荐 0.6~1.0。</p>'\n"
    "            '<p><b>早停批次数：</b>连续多少轮不改善就自动停止，防止过拟合、节省训练时间。默认 20，推荐 10~50。</p>'\n"
    '        ),\n'
    "        'RF': (\n"
    "            '<h2>RF - 随机森林</h2>'\n"
    "            '<p>同时训练多棵决策树，每棵树在随机抽取的数据和特征上学习，最后取所有树的平均值作为结果。天然抗过拟合、不怕异常值，无需归一化。</p>'\n"
    "            '<hr>'\n"
    "            '<h3>通用参数</h3>'\n"
    "            '<p><b>额定容量 (Ah)：</b>仅用于计算失效阈值和展示结果。默认 1.1，适用 0.5~5.0。</p>'\n"
    '            \'<p><b>失效阈值比例：</b>容量低于"额定容量 × 此比例"时判定失效，行业常用 0.7~0.8。默认 0.8。</p>\'\n'
    "            '<p><b>SOH上/下电压 (V)：</b>计算SOH健康指标所用的两个电压点。三元锂电池(NCM/NCA/LCO)推荐 3.8/3.4V，磷酸铁锂(LFP)推荐 3.4/3.0V，钛酸锂(LTO)推荐 2.3/1.8V。上电压必须大于下电压。</p>'\n"
    "            '<p><b>窗口大小：</b>用前 N 个循环预测下一个。默认 64，推荐 32~128。</p>'\n"
    '            \'<p><b>评估指标：</b>RMSE=均方根误差（Ah），日常首选，越小越准；MAE=平均绝对误差，对异常值不敏感；R²=决定系数，越接近1越好；Pearson=相关系数，衡量预测与真实值的线性相关性，越接近1越好；RE=寿命预测误差，衡量预测"何时报废"的准确度。</p>\'\n'
    "            '<p><b>随机种子：</b>固定随机序列起点，确保结果可复现。</p>'\n"
    "            '<p><b>多种子数(置信区间)：</b>使用多个不同随机种子重复训练，计算各指标的均值±标准差和95%置信区间，评估模型稳定性。值越大统计越可靠但耗时越长。默认5，推荐3~10。</p>'\n"
    "            '<hr>'\n"
    "            '<h3>RF 专用参数</h3>'\n"
    "            '<p><b>树的数量：</b>森林中树的总数。越多预测越准但越慢。默认 100，推荐 50~500。</p>'\n"
    "            '<p><b>树的最大深度：</b>每棵树最多几层分支，控制复杂度。训练数据较少（如几十个循环）时宜浅。默认 10，推荐 5~30。</p>'\n"
    '            \'<p><b>叶节点最小样本数：</b>每个叶子最少装几个样本。越大防过拟合越强，但太大容易"欠拟合"，模型过于简单，连训练数据也预测不准。默认 1，推荐 1~10。</p>\'\n'
    "            '<p><b>最大特征比例：</b>每棵树随机使用多少比例的特征，防止所有树长得太像。默认 1.0，推荐 0.5~1.0。</p>'\n"
    "            '<p><b>早停批次数：</b>连续多少批树的指标不改善就自动停止，防止过拟合、节省训练时间。默认 20，推荐 10~50。</p>'\n"
    '        ),\n'
    '    }\n'
    '\n'
    '    def show_help(self):\n'
    '        if self._help_dialog is None or not self._help_dialog.isVisible():\n'
    '            self._help_dialog = _HelpDialog(self, self.current_mode)\n'
    '            self._help_dialog.show()\n'
    '\n'
    '    def on_progress(self, event):\n'
    "        total = max(0, int(event.get('total', 0)))\n"
    "        current = max(0, int(event.get('current', 0)))\n"
    '        if total > 0:\n'
    '            self.progress_bar.setRange(0, total)\n'
    '            self.progress_bar.setValue(min(current, total))\n'
    '            self.progress_bar.setTextVisible(True)\n'
    '        else:\n'
    '            self.progress_bar.setRange(0, 0)\n'
    '            self.progress_bar.setTextVisible(False)\n'
    '\n'
    '        phase_name = {\n'
    "            'loading': '加载数据',\n"
    "            'evaluation': '跨电池评估',\n"
    "            'battery': '处理电池',\n"
    "            'seed': '多种子评估',\n"
    "            'rnn_epoch': '循环模型训练',\n"
    "            'rf_trees': '随机森林训练',\n"
    "            'xgboost_tree': 'XGBoost 训练',\n"
    "            'final_training': '最终模型训练',\n"
    "            'prediction': '批量预测',\n"
    "            'complete': '运行完成',\n"
    "        }.get(event.get('phase'), str(event.get('phase', '运行中')))\n"
    '        parts = [phase_name]\n'
    "        if event.get('battery'):\n"
    "            parts.append(str(event['battery']))\n"
    "        if event.get('seed') is not None:\n"
    '            parts.append(f\'seed={event["seed"]}\')\n'
    "        if event.get('epoch') is not None:\n"
    '            parts.append(f\'epoch={event["epoch"]}\')\n'
    '        if total > 0:\n'
    "            parts.append(f'{current}/{total}')\n"
    '        parts.append(f\'{float(event.get("elapsed_seconds", 0.0)):.1f}s\')\n'
    "        message = ' · '.join(parts)\n"
    '        self.run_status_label.setText(message)\n'
    "        if hasattr(self, 'status_bar'):\n"
    '            self.status_bar.showMessage(message)\n'
    '\n'
    '    def on_error(self, msg):\n'
    '        full_message = str(msg)\n'
    '        concise = next(\n'
    '            (line.strip() for line in full_message.splitlines()\n'
    '             if line.strip()),\n'
    "            '发生未知错误',\n"
    '        )[:500]\n'
    "        show_message(self, 'error', '错误', concise)\n"
    "        self.append_log('错误：' + concise)\n"
    '        self.logger.error(full_message)\n'
    "        self._finish_status_message = '评估遇到错误'\n"
    '        self._active_run_snapshot = None\n'
    '        self._active_run_kind = None\n'
    '        if self._result_batches:\n'
    '            self.right_tabs.setCurrentIndex(self.log_tab_index)\n'
    '        else:\n'
    '            self._show_result_state(\n'
    "                '评估未完成', '请根据弹窗或训练日志中的提示检查数据和参数。')\n"
    '\n'
    '    def show_error_toast(self, message):\n'
    '        """A1：把任何线程里未捕获的异常变成一条**非阻塞**提示。\n'
    '\n'
    '        由 ``utils.crash_guard.bridge.error`` 信号驱动；不在子线程里直接\n'
    '        创建 QMessageBox，也不会中断用户正在做的事。\n'
    '        """\n'
    '        text = str(message)\n'
    "        self.append_log(f'未处理的异常：{text}')\n"
    '        try:\n'
    "            self.status_bar.showMessage(f'未处理的异常：{text}', 15000)\n"
    '        except AttributeError:\n'
    '            pass\n'
    '        if self._error_toast is None:\n'
    '            self._error_toast = QLabel(self)\n'
    "            self._error_toast.setProperty('role', 'dangerText')\n"
    '            self._error_toast.setStyleSheet(\n'
    "                'padding: 6px 10px; border-radius: 4px;')\n"
    '            self._error_toast.setWordWrap(True)\n'
    '            self._error_toast.setVisible(False)\n'
    "        self._error_toast.setText(f'✕ 未处理的异常：{text}')\n"
    '        self._error_toast.setVisible(True)\n'
    '        QTimer.singleShot(15000, lambda: self._error_toast.setVisible(False))\n'
    '\n'
    '    def on_finished(self, worker=None):\n'
    '        signal_worker = self.sender()\n'
    "        if worker is None and hasattr(signal_worker, 'isRunning'):\n"
    '            worker = signal_worker\n'
    '        worker = worker or self.worker\n'
    '        if worker is None or self.worker is not worker:\n'
    '            return\n'
    '        if worker.isRunning():\n'
    '            # 自定义 finished_signal 在 run() 返回前发出；真正解锁必须等\n'
    '            # QThread.finished，避免旧线程仍存活时被新任务覆盖。\n'
    '            return\n'
    '        self.worker = None\n'
    '        message = self._finish_status_message\n'
    "        self._finish_status_message = '准备就绪'\n"
    '        if not self.start_btn.isEnabled():\n'
    '            self._set_running_state(False, message)\n'
    '\n'
    '    def on_result(self, results, elapsed):\n'
    '        if self._active_run_snapshot is None:\n'
    "            raise RuntimeError('评估结果缺少对应的运行快照')\n"
    '\n'
    '        threshold = self._eval_rated_capacity * self._eval_threshold_ratio\n'
    '        for name, result in results.items():\n'
    "            item = result['detail']\n"
    "            pred = result['prediction']\n"
    '            battery_data = self.worker.battery_dict.get(name, {})\n'
    '            measured = np.asarray(\n'
    "                battery_data.get('capacity', pred), dtype=np.float64)\n"
    '            # A4：失效语义基于滚动起点的递归预测（而不是一步预测）\n'
    "            recursive = item.get('recursive_prediction')\n"
    "            forecast = item.get('forecast')\n"
    '            if forecast:\n'
    '                failure_prediction = forecast\n'
    '                prediction_start = int(\n'
    "                    item.get('forecast_start', len(measured) - len(forecast)))\n"
    "                item['failure_cycle_protocol'] = 'rolling_origin'\n"
    '            elif recursive is not None:\n'
    '                failure_prediction = recursive\n'
    '                prediction_start = len(measured) - len(recursive)\n'
    "                item['failure_cycle_protocol'] = 'recursive_future'\n"
    '            else:\n'
    '                failure_prediction = pred\n'
    '                prediction_start = 0\n'
    "                item['failure_cycle_protocol'] = 'legacy_prediction'\n"
    '            cycle_ids = battery_data.get(\n'
    "                'cycle', np.arange(1, len(measured) + 1))\n"
    '            semantics = analyze_failure_cycles(\n'
    '                cycle_ids, measured, failure_prediction, threshold,\n'
    '                prediction_start=prediction_start)\n'
    '            item.update(semantics)\n'
    "            item['failure_cycle'] = semantics[\n"
    "                'predicted_failure_cycle']\n"
    "            item['threshold'] = threshold\n"
    '\n'
    '        completed_snapshot = self._active_run_snapshot.with_results(\n'
    '            results, elapsed_seconds=elapsed)\n'
    '        self._active_run_snapshot = None\n'
    '        completed_results = completed_snapshot.results_dict()\n'
    '        predictions = {\n'
    "            name: result['prediction'] for name, result in results.items()\n"
    '        }\n'
    '        detail_list = [\n'
    "            result['detail'] for result in completed_results.values()\n"
    '        ]\n'
    '        battery_names = list(completed_results)\n'
    '        chart_battery_data = {\n'
    '            name: {\n'
    "                'capacity': np.asarray(\n"
    "                    self.worker.battery_dict[name]['capacity'],\n"
    '                    dtype=np.float64,\n'
    '                ).copy()\n'
    '            }\n'
    '            for name in battery_names\n'
    '            if name in self.worker.battery_dict\n'
    '        }\n'
    "        run_kind = self._active_run_kind or 'training'\n"
    "        kind_label = '训练评估' if run_kind == 'training' else '模型预测'\n"
    "        mode = completed_snapshot.config_dict().get('mode', self.current_mode)\n"
    '        batch_number = len(self._result_batches) + 1\n'
    '        batch = {\n'
    "            'label': f'第 {batch_number} 次 · {kind_label} · {mode}',\n"
    "            'snapshot': completed_snapshot,\n"
    "            'results': completed_results,\n"
    "            'detail': detail_list,\n"
    "            'predictions': predictions,\n"
    "            'battery_names': battery_names,\n"
    "            'battery_data': chart_battery_data,\n"
    "            'elapsed': float(elapsed),\n"
    "            'rated_capacity': self._eval_rated_capacity,\n"
    "            'threshold_ratio': self._eval_threshold_ratio,\n"
    "            'selected_metric': self.metric_combo.currentText(),\n"
    "            'run_kind': run_kind,\n"
    '        }\n'
    '        self._append_result_batch(batch)\n'
    "        if run_kind == 'training':\n"
    '            self._has_completed_training_run = True\n'
    '        self._active_run_kind = None\n'
    "        self._finish_status_message = f'评估完成，耗时 {elapsed:.2f}s'\n"
    '\n'
    '    def _append_result_batch(self, batch):\n'
    '        self._result_batches.append(batch)\n'
    '        index = len(self._result_batches) - 1\n'
    '        blocker = QSignalBlocker(self.result_batch_combo)\n'
    "        self.result_batch_combo.addItem(batch['label'])\n"
    '        self.result_batch_combo.setCurrentIndex(index)\n'
    '        del blocker\n'
    '        self.result_batch_bar.setVisible(True)\n'
    '        self._display_result_batch(index)\n'
    '\n'
    '    def _display_result_batch(self, index):\n'
    '        if index < 0 or index >= len(self._result_batches):\n'
    '            return\n'
    '        batch = self._result_batches[index]\n'
    "        self._last_run_snapshot = batch['snapshot']\n"
    "        self._last_results = batch['results']\n"
    '        self._last_score = [\n'
    "            [result['score']] for result in batch['results'].values()\n"
    '        ]\n'
    "        self._last_pred = batch['predictions']\n"
    "        self._last_detail = batch['detail']\n"
    "        self._last_elapsed = batch['elapsed']\n"
    "        self.battery_list = list(batch['battery_names'])\n"
    "        self.battery_dict = batch['battery_data']\n"
    "        self._eval_rated_capacity = batch['rated_capacity']\n"
    "        self._eval_threshold_ratio = batch['threshold_ratio']\n"
    '\n'
    '        self.update_result_table(\n'
    '            self._last_detail,\n'
    '            self._last_elapsed,\n'
    "            selected_metric=batch['selected_metric'],\n"
    '        )\n'
    '        detail_map = {\n'
    "            item.get('battery'): item for item in self._last_detail\n"
    '            if isinstance(item, dict)\n'
    '        }\n'
    '        # U2：把滚动起点的 detail（预测起点 / 递归预测 / 区间 / EOL）交给图表；\n'
    '        # 老版画布不认识 details 参数时回退到位置参数，保证不崩。\n'
    '        try:\n'
    '            self.canvas.plot_results(\n'
    '                self.battery_list,\n'
    '                self.battery_dict,\n'
    '                self._last_pred,\n'
    '                self._eval_rated_capacity,\n'
    '                self._eval_threshold_ratio,\n'
    '                details=detail_map,\n'
    '            )\n'
    '        except TypeError:\n'
    '            self.canvas.plot_results(\n'
    '                self.battery_list,\n'
    '                self.battery_dict,\n'
    '                self._last_pred,\n'
    '                self._eval_rated_capacity,\n'
    '                self._eval_threshold_ratio,\n'
    '            )\n'
    '        self.export_btn.setEnabled(True)\n'
    '        self.right_tabs.setCurrentIndex(self.result_tab_index)\n'
    '\n'
    '    def _show_result_state(self, title, detail):\n'
    '        """在结果区呈现空、加载、停止或错误状态。\n'
    '\n'
    '        结果表现在是**常驻控件**，所以这里只清空它的数据、隐藏工具行，\n'
    '        不再销毁它（旧实现会把整块区域 rebuild 一遍）。\n'
    '        """\n'
    "        if hasattr(self, 'result_summary'):\n"
    '            self.result_summary.setVisible(False)\n'
    "        if (not title.startswith('正在') and\n"
    "                hasattr(self, 'result_tab_index')):\n"
    '            self.right_tabs.setCurrentIndex(self.result_tab_index)\n'
    '        self._last_detail_list = []\n'
    "        if hasattr(self, 'result_model'):\n"
    '            self.result_model.set_rows([])\n'
    '        # 先移除之前的状态横幅，避免多条叠在一起\n'
    '        for index in range(self.result_container_layout.count() - 1, -1, -1):\n'
    '            widget = self.result_container_layout.itemAt(index).widget()\n'
    "            if widget is not None and widget.objectName() == 'resultStateBanner':\n"
    '                self.result_container_layout.takeAt(index)\n'
    '                widget.setParent(None)\n'
    '                widget.deleteLater()\n'
    "        for name in ('result_view', 'result_notes'):\n"
    '            widget = getattr(self, name, None)\n'
    '            if widget is not None:\n'
    '                widget.setVisible(False)\n'
    "        for name in ('copy_table_btn', 'csv_btn', 'start_frac_combo'):\n"
    '            widget = getattr(self, name, None)\n'
    '            if widget is not None:\n'
    '                widget.setVisible(False)\n'
    '        state = QFrame()\n'
    "        state.setProperty('role', 'resultState')\n"
    "        state.setObjectName('resultStateBanner')\n"
    '        state_layout = QVBoxLayout(state)\n'
    '        state_layout.setContentsMargins(20, 24, 20, 22)\n'
    '        state_layout.setSpacing(8)\n'
    '\n'
    '        mark = QWidget()\n'
    '        mark.setFixedSize(56, 40)\n'
    '        battery = QFrame(mark)\n'
    "        battery.setProperty('role', 'resultStateBattery')\n"
    '        battery.setGeometry(3, 5, 44, 30)\n'
    '        battery_fill = QFrame(battery)\n'
    "        battery_fill.setProperty('role', 'resultStateBatteryFill')\n"
    '        battery_fill.setGeometry(4, 4, 27, 20)\n'
    '        battery_terminal = QFrame(mark)\n'
    "        battery_terminal.setProperty('role', 'resultStateBatteryTerminal')\n"
    '        battery_terminal.setGeometry(47, 14, 6, 12)\n'
    '        state_layout.addWidget(mark, 0, Qt.AlignmentFlag.AlignHCenter)\n'
    '\n'
    '        title_label = QLabel(title)\n'
    "        title_label.setProperty('role', 'resultStateTitle')\n"
    '        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)\n'
    '        title_label.setWordWrap(True)\n'
    '        detail_label = QLabel(detail)\n'
    "        detail_label.setProperty('role', 'resultStateDetail')\n"
    '        detail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)\n'
    '        detail_label.setWordWrap(True)\n'
    '        guide_text = (\n'
    "            '读取数据 · 训练模型 · 生成指标'\n"
    "            if title.startswith('正在')\n"
    "            else '导入数据 · 校准参数 · 开始评估'\n"
    '        )\n'
    '        guide_label = QLabel(guide_text)\n'
    "        guide_label.setProperty('role', 'resultStateGuide')\n"
    '        guide_label.setAlignment(Qt.AlignmentFlag.AlignCenter)\n'
    '\n'
    '        state_layout.addWidget(title_label)\n'
    '        state_layout.addWidget(detail_label)\n'
    '        state_layout.addSpacing(3)\n'
    '        state_layout.addWidget(guide_label)\n'
    "        state.setAccessibleName(f'{title}。{detail}')\n"
    '        self.result_container_layout.addWidget(state)\n'
    '\n'
    '    def clear_result_display(self):\n'
    '        """移除状态横幅，并恢复结果表工具行（不动常驻的结果表本身）。"""\n'
    '        for index in range(self.result_container_layout.count() - 1, -1, -1):\n'
    '            widget = self.result_container_layout.itemAt(index).widget()\n'
    "            if widget is not None and widget.objectName() == 'resultStateBanner':\n"
    '                self.result_container_layout.takeAt(index)\n'
    '                widget.setParent(None)\n'
    '                widget.deleteLater()\n'
    "        for name in ('result_view', 'result_notes', 'copy_table_btn',\n"
    "                     'csv_btn', 'start_frac_combo'):\n"
    '            widget = getattr(self, name, None)\n'
    '            if widget is not None:\n'
    '                widget.setVisible(True)\n'
    '\n'
    '    def update_result_table(self, detail_list, elapsed, selected_metric=None):\n'
    '        """U1：把结果渲染成可排序表格 + 跨电池汇总行 + 基线行。\n'
    '\n'
    '        旧的卡片堆（N 个 QGroupBox、5 段复制粘贴的指标代码、6 位小数）已经\n'
    '        被 QTableView + QAbstractTableModel + QSortFilterProxyModel 取代。\n'
    '        """\n'
    '        self._last_detail_list = list(detail_list or [])\n'
    '        # 恢复被状态横幅隐藏的结果表与工具行\n'
    '        self.clear_result_display()\n'
    '        self._refresh_start_frac_options(self._last_detail_list)\n'
    '        self._rebuild_result_rows()\n'
    '        self._update_result_summary(\n'
    '            self._last_detail_list, elapsed,\n'
    '            selected_metric or self.metric_combo.currentText())\n'
    '\n'
    '    def _refresh_start_frac_options(self, detail_list):\n'
    '        """按当前结果里实际存在的滚动起点填充下拉框。"""\n'
    '        fracs = set()\n'
    '        for item in detail_list or []:\n'
    "            rolling = (item or {}).get('rolling') or {}\n"
    "            fracs.update(rolling.get('per_start') or {})\n"
    '        options = sorted(float(f) for f in fracs)\n'
    "        combo = getattr(self, 'start_frac_combo', None)\n"
    '        if combo is None:\n'
    '            return\n'
    '        blocker = QSignalBlocker(combo)\n'
    '        combo.clear()\n'
    '        for frac in options:\n'
    "            combo.addItem(f'{frac:.0%}', frac)\n"
    '        primary = next(\n'
    "            (item.get('primary_start_frac') for item in detail_list\n"
    "             if item.get('primary_start_frac') is not None), None)\n"
    '        if primary is not None:\n'
    '            index = combo.findData(float(primary))\n'
    '            if index >= 0:\n'
    '                combo.setCurrentIndex(index)\n'
    '        del blocker\n'
    '\n'
    '    def _current_start_frac(self):\n'
    "        combo = getattr(self, 'start_frac_combo', None)\n"
    '        if combo is None or combo.count() == 0:\n'
    '            return None\n'
    '        data = combo.currentData()\n'
    '        return None if data is None else float(data)\n'
    '\n'
    '    def _baseline_rows(self, detail_list):\n'
    '        """收集基线（平推 / 线性外推 / 双指数）用于并排展示（A9）。"""\n'
    '        baselines = {}\n'
    '        for item in detail_list or []:\n'
    "            for name, entry in ((item or {}).get('baselines') or {}).items():\n"
    "                value = entry.get('rmse')\n"
    '                if value is None:\n'
    '                    continue\n'
    '                baselines.setdefault(name, []).append(float(value))\n'
    '        return {\n'
    "            name: {'rmse': float(np.mean(values))}\n"
    '            for name, values in baselines.items() if values\n'
    '        }\n'
    '\n'
    '    def _rebuild_result_rows(self):\n'
    "        detail_list = getattr(self, '_last_detail_list', [])\n"
    '        if not detail_list:\n'
    '            return\n'
    '        rows = rows_from_details(\n'
    '            detail_list,\n'
    '            start_frac=self._current_start_frac(),\n'
    '            baselines=self._baseline_rows(detail_list),\n'
    '        )\n'
    '        self.result_model.set_tokens(theme_tokens(self._theme_mode))\n'
    '        self.result_model.set_rows(rows)\n'
    '        # 列宽在 build_right_panel 里显式设定；这里不再 resizeColumnsToContents，\n'
    '        # 否则汇总行的长文本会把列撑宽、把前排的指标挤出可视区。\n'
    '\n'
    '        summary = summary_row(rows)\n'
    '        notes = []\n'
    '        if summary is not None:\n'
    '            # 汇总行的单元格只放均值（窄面板里不被截断），\n'
    '            # 完整的 mean ± std 与 bootstrap 区间写在这里。\n'
    '            stats = []\n'
    "            for key, label, fmt in (('rmse', 'RMSE', '{:.4f}'),\n"
    "                                    ('mae', 'MAE', '{:.4f}'),\n"
    "                                    ('skill', '技能分', '{:+.3f}')):\n"
    "                mean, std = summary.get(key), summary.get(f'{key}_std')\n"
    '                if mean is None:\n'
    '                    continue\n'
    '                # 单块电池时 std 恒为 0，不显示无意义的「± 0.0000」\n'
    '                if std:\n'
    "                    stats.append(f'{label} {fmt.format(mean)}'\n"
    '                                 f\' ± {fmt.format(std).lstrip("+")}\')\n'
    '                else:\n'
    "                    stats.append(f'{label} {fmt.format(mean)}')\n"
    '            if stats:\n'
    '                notes.append(\n'
    '                    f\'跨电池汇总（n={summary["n_batteries"]} 块电池）：\'\n'
    "                    + '，'.join(stats))\n"
    "            mean, lo, hi = bootstrap_summary(rows, 'rmse')\n"
    '            if np.isfinite(lo) and np.isfinite(hi) and lo != hi:\n'
    '                notes.append(\n'
    "                    f'RMSE 的 bootstrap 95% 区间：[{lo:.4f}, {hi:.4f}] Ah'\n"
    "                    '（n = 电池数才是泛化不确定性的来源，不是随机种子）')\n"
    '        alpha_values = [\n'
    "            item.get('persistence_blend') for item in detail_list\n"
    "            if item.get('persistence_blend') is not None\n"
    '        ]\n'
    '        if alpha_values and min(alpha_values) < 0.05:\n'
    '            notes.append(\n'
    "                '⚠ 有电池的持久性混合系数 α < 0.05：模型未超越平推基线，'\n"
    "                '递归预测已退化为水平线。')\n"
    '        # 置信区间口径说明：它只是同一留一折内的随机种子波动\n'
    "        if any(int(item.get('n_seeds', 1)) > 1 for item in detail_list):\n"
    '            notes.append(\n'
    "                '置信区间仅表示同一留一折内的随机种子波动，'\n"
    "                '不代表跨电池总体不确定性。')\n"
    '        if notes:\n'
    "            self.result_notes.setText('\\n'.join(notes))\n"
    '            self.result_notes.setVisible(True)\n'
    '        else:\n'
    '            self.result_notes.setVisible(False)\n'
    '\n'
    '    def _on_start_frac_changed(self, _index):\n'
    "        if getattr(self, '_last_detail_list', None):\n"
    '            self._rebuild_result_rows()\n'
    '\n'
    '    def _copy_result_table(self):\n'
    '        """把当前结果表复制到剪贴板（Tab 分隔，可直接粘进 Excel）。"""\n'
    '        rows = self.result_model.display_rows()\n'
    '        if not rows:\n'
    "            show_message(self, 'info', '暂无结果', '当前没有可复制的结果。')\n"
    '            return\n'
    '        header = [column[0] for column in COLUMNS]\n'
    "        lines = ['\\t'.join(header)]\n"
    '        for row in rows:\n'
    "            lines.append('\\t'.join(\n"
    '                ResultTableModel._display_text(\n'
    '                    row, column[1],\n'
    '                    ResultTableModel._cell_value(row, column[1]),\n'
    '                    column[2])\n'
    '                for column in COLUMNS))\n'
    "        QApplication.clipboard().setText('\\n'.join(lines))\n"
    "        self.append_log('结果表已复制到剪贴板。')\n"
    '\n'
    '    def _export_result_csv(self):\n'
    '        """导出结果表 CSV（U1.6）。"""\n'
    '        rows = self.result_model.display_rows()\n'
    '        if not rows:\n'
    "            show_message(self, 'info', '暂无结果', '当前没有可导出的结果。')\n"
    '            return\n'
    '        file_path, _ = QFileDialog.getSaveFileName(\n'
    "            self, '导出结果表', os.fspath(OUTPUTS_DIR / '评估结果.csv'),\n"
    "            'CSV 文件 (*.csv)')\n"
    '        if not file_path:\n'
    '            return\n'
    '        try:\n'
    "            with open(file_path, 'w', encoding='utf-8-sig', newline='') as stream:\n"
    '                stream.write(to_csv(rows))\n'
    '        except OSError as error:\n'
    "            show_message(self, 'error', '导出失败', f'无法写入文件：{error}')\n"
    '            return\n'
    "        self.append_log(f'结果表已导出：{file_path}')\n"
    '\n'
    '    def _update_result_summary(self, detail_list, elapsed, selected_metric):\n'
    '        metric_map = {\n'
    "            'RMSE': 'rmse',\n"
    "            'MAE': 'mae',\n"
    "            'R²': 'r2',\n"
    "            'Pearson': 'pearson',\n"
    "            'RE': 're',\n"
    "            '全部': 'rmse',\n"
    '        }\n'
    "        metric_label = 'RMSE' if selected_metric == '全部' else selected_metric\n"
    '        metric_key = metric_map[selected_metric]\n'
    '        values = [\n'
    '            float(item[metric_key])\n'
    '            for item in detail_list\n'
    '            if item.get(metric_key) is not None and\n'
    '            np.isfinite(item.get(metric_key))\n'
    '        ]\n'
    "        models = sorted({str(item.get('model', '未知模型'))\n"
    '                         for item in detail_list})\n'
    "        model_text = models[0] if len(models) == 1 else '多模型'\n"
    '        count = len(detail_list)\n'
    '        value_text = (\n'
    "            f'{float(np.mean(values)):.6f}' if values else 'N/A（截尾）')\n"
    '        seed_count = max(\n'
    "            (int(item.get('n_seeds', 1)) for item in detail_list),\n"
    '            default=1,\n'
    '        )\n'
    '\n'
    "        self.result_summary_title.setText(f'{count} 块电池 · {model_text}')\n"
    '        self.result_summary_metric.setText(\n'
    "            f'平均 {metric_label} {value_text}')\n"
    '        self.result_summary_meta.setText(\n'
    "            f'耗时 {elapsed:.2f} 秒 · {seed_count} 次随机种子')\n"
    '        self.result_summary.setAccessibleName(\n'
    "            f'{self.result_summary_title.text()}，'\n"
    "            f'{self.result_summary_metric.text()}，'\n"
    "            f'{self.result_summary_meta.text()}')\n"
    '        self.result_summary.setVisible(True)\n'
    '        self.right_tabs.setCurrentIndex(self.result_tab_index)\n'
)

# ---- utils/__init__.py ----
_MODULE_SOURCES['utils'] = (
    'from .config import TrainConfig\n'
    'from .logger import setup_logger\n'
)

# ---- core/__init__.py ----
_MODULE_SOURCES['core'] = (
    'from .preprocess import drop_outlier, build_instances, get_train_test, normalize_data\n'
    'from .evaluate import relative_error, evaluation\n'
    'from .dataload import load_battery_from_paths\n'
    'from .validation import normalize_column_names, validate_imported_item, COLUMN_NAME_MAP\n'
    'from .train import train\n'
)

# ---- models/__init__.py ----
_MODULE_SOURCES['models'] = (
    'from .rnn_model import Net\n'
    'from .XGBoost import train_xgboost\n'
    'from .RF import train_rf\n'
)

# ---- ui/__init__.py ----
_MODULE_SOURCES['ui'] = (
    'from .main_window import MainWindow\n'
    'from .chart_show import MplCanvas\n'
    'from .worker import EvalWorker\n'
)

# ---- battery_soh_app.py（应用入口） ----
_BOOTSTRAP_SOURCE = (
    'import os\n'
    'import sys\n'
    'import time\n'
    'import traceback\n'
    '\n'
    '# _StartupSplash 类依赖的 PyQt6 组件必须在类定义前导入\n'
    'from PyQt6.QtWidgets import (\n'
    '    QWidget, QProgressBar, QLabel, QApplication,\n'
    '    QFrame, QHBoxLayout, QVBoxLayout,\n'
    ')\n'
    'from PyQt6.QtGui import QPainter, QColor, QIcon, QLinearGradient, QPen\n'
    'from PyQt6.QtCore import Qt, QRectF, QSettings\n'
    '\n'
    '# theme_tokens 是纯字典 + 纯函数，不 import 任何第三方库，\n'
    '# 因此闪屏可以在 torch / matplotlib 加载之前就拿到颜色（U7③）。\n'
    'from theme_tokens import DEFAULT_THEME, THEMES, THEME_SETTINGS_KEY\n'
    '\n'
    '\n'
    'def concise_startup_error(error):\n'
    '    """Return one safe line for a startup dialog; traceback stays in logs."""\n'
    '    first_line = next(\n'
    '        (line.strip() for line in str(error).splitlines() if line.strip()),\n'
    '        error.__class__.__name__,\n'
    '    )\n'
    "    return f'加载核心模块失败：{first_line[:500]}'\n"
    '\n'
    '\n'
    'def _saved_theme_mode():\n'
    '    """读取已保存的主题；QSettings 很轻，可以在闪屏之前用。\n'
    '\n'
    '    默认 **深色（墨夜）**——与 ``theme_tokens.DEFAULT_THEME`` 保持一致，\n'
    '    否则闪屏会用浅色画一遍、主窗口再切成深色，启动瞬间闪一下白。\n'
    '    """\n'
    "    value = QSettings('BatterySOH', 'AssessmentSystem').value(\n"
    '        THEME_SETTINGS_KEY, DEFAULT_THEME)\n'
    '    mode = str(value).strip().lower() if value else DEFAULT_THEME\n'
    '    return mode if mode in THEMES else DEFAULT_THEME\n'
    '\n'
    '\n'
    'def _get_icon():\n'
    '    """加载 SOH.ico 作为应用图标（不导入 utils，避免提前触发 torch 导入）。"""\n'
    "    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))\n"
    "    ico_path = os.path.join(base_path, 'SOH.ico')\n"
    '    if os.path.exists(ico_path):\n'
    '        return QIcon(ico_path)\n'
    '    return QIcon()\n'
    '\n'
    '\n'
    'class _StartupSplash(QWidget):\n'
    '    """自定义启动闪屏：背景图 + 动态进度条 + 原生窗口控制按钮。\n'
    '\n'
    '    U7 的改动：\n'
    '    - 进度条文字移到条外（条内文字压在填充块上只有 2.01:1，读不清）；\n'
    '    - 颜色全部来自 ``theme_tokens``，深色主题下不会再闪一块浅色窗口；\n'
    '    - 字号用 pt（跟随系统字号设置）；\n'
    '    - 去掉最大化按钮（固定尺寸下它是纯视觉噪声）；\n'
    '    - 用户点关闭时设置取消标志，让主流程在下一个检查点干净退出，\n'
    '      而不是在某次 ``processEvents()`` 里直接 ``sys.exit(0)``。\n'
    '    """\n'
    '\n'
    '    def __init__(self, parent=None):\n'
    '        super().__init__(parent)\n'
    "        self.setObjectName('startupSplash')\n"
    "        self.setProperty('visualWorld', 'paperInk')\n"
    '\n'
    '        # 标记：是否为程序代码主动关闭（区别于用户点击标题栏关闭按钮）\n'
    '        self._programmatic_close = False\n'
    '        # 用户请求取消启动\n'
    '        self.cancelled = False\n'
    '\n'
    '        self.T = THEMES[_saved_theme_mode()]\n'
    '\n'
    '        # 窗口属性：置顶、保留标题栏以获得原生 最小化/关闭 按钮\n'
    '        self.setWindowFlags(\n'
    '            Qt.WindowType.WindowStaysOnTopHint |\n'
    '            Qt.WindowType.CustomizeWindowHint |\n'
    '            Qt.WindowType.WindowTitleHint |\n'
    '            Qt.WindowType.WindowMinimizeButtonHint |\n'
    '            Qt.WindowType.WindowCloseButtonHint\n'
    '        )\n'
    '        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)\n'
    '        self.setFixedSize(620, 400)\n'
    "        self.setWindowTitle('电池 SOH 评估系统')\n"
    '\n'
    '        T = self.T\n'
    "        self.setStyleSheet(f'''\n"
    '            QLabel[role="splashTitle"] {{\n'
    "                color: {T['primary_d']};\n"
    '                background: transparent;\n'
    '                font-family: "STZhongsong", "FangSong", "Microsoft YaHei UI";\n'
    '                font-size: 19pt;\n'
    '                font-weight: 700;\n'
    '                letter-spacing: 1px;\n'
    '            }}\n'
    '            QLabel[role="splashSubtitle"] {{\n'
    "                color: {T['text_muted']};\n"
    '                background: transparent;\n'
    '                font-family: "Microsoft YaHei UI";\n'
    '                font-size: 9pt;\n'
    '                letter-spacing: 1px;\n'
    '            }}\n'
    '            QFrame[role="splashBattery"] {{\n'
    '                background: rgba(0, 0, 0, 0);\n'
    "                border: 2px solid {T['primary']};\n"
    '                border-radius: 7px;\n'
    '            }}\n'
    '            QFrame[role="splashBatteryTerminal"] {{\n'
    "                background: {T['primary']};\n"
    '                border: none;\n'
    '                border-radius: 2px;\n'
    '            }}\n'
    '            QFrame[role="splashBatteryLine"] {{\n'
    "                background: {T['primary']};\n"
    '                border: none;\n'
    '            }}\n'
    "        ''')\n"
    '\n'
    '        self._identity_widget = QWidget(self)\n'
    "        self._identity_widget.setObjectName('splashIdentity')\n"
    '        self._identity_widget.setGeometry(70, 78, 480, 108)\n'
    '        identity_layout = QHBoxLayout(self._identity_widget)\n'
    '        identity_layout.setContentsMargins(0, 0, 0, 0)\n'
    '        identity_layout.setSpacing(16)\n'
    '        identity_layout.addStretch(1)\n'
    '\n'
    '        battery_mark = QWidget()\n'
    '        battery_mark.setFixedSize(58, 72)\n'
    '        battery = QFrame(battery_mark)\n'
    "        battery.setProperty('role', 'splashBattery')\n"
    '        battery.setGeometry(4, 8, 46, 58)\n'
    '        terminal = QFrame(battery_mark)\n'
    "        terminal.setProperty('role', 'splashBatteryTerminal')\n"
    '        terminal.setGeometry(17, 2, 20, 7)\n'
    '        for width, y in ((22, 22), (27, 33), (19, 44)):\n'
    '            line = QFrame(battery)\n'
    "            line.setProperty('role', 'splashBatteryLine')\n"
    '            line.setGeometry(11, y, width, 2)\n'
    '        identity_layout.addWidget(battery_mark)\n'
    '\n'
    '        text_layout = QVBoxLayout()\n'
    '        text_layout.setContentsMargins(0, 0, 0, 0)\n'
    '        text_layout.setSpacing(1)\n'
    "        self._title_label = QLabel('电池 SOH 评估系统')\n"
    "        self._title_label.setProperty('role', 'splashTitle')\n"
    '        self._title_label.setAlignment(\n'
    '            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)\n'
    '        self._subtitle_label = QLabel(\n'
    "            'Battery State of Health Assessment Workspace')\n"
    "        self._subtitle_label.setProperty('role', 'splashSubtitle')\n"
    '        text_layout.addWidget(self._title_label)\n'
    '        text_layout.addWidget(self._subtitle_label)\n'
    '        identity_layout.addLayout(text_layout)\n'
    '        identity_layout.addStretch(1)\n'
    '\n'
    '        # ── 加载状态与百分比进度 ──\n'
    '        # 状态文字区域缩窄，把右侧留给条外的百分比（避免重叠与截断）\n'
    "        self._status_label = QLabel('正在准备启动…', self)\n"
    '        self._status_label.setGeometry(48, 302, 452, 24)\n'
    '        self._status_label.setAlignment(\n'
    '            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)\n'
    "        self._status_label.setAccessibleName('当前加载阶段')\n"
    '        self._status_label.setWordWrap(False)\n'
    "        self._status_label.setStyleSheet(f'''\n"
    '            QLabel {{\n'
    "                color: {T['text_muted']};\n"
    '                font-family: "Microsoft YaHei UI";\n'
    '                font-size: 9pt;\n'
    '                font-weight: 500;\n'
    '                background: transparent;\n'
    '            }}\n'
    "        ''')\n"
    '\n'
    "        self._percent_label = QLabel('0%', self)\n"
    '        self._percent_label.setGeometry(508, 302, 64, 24)\n'
    '        self._percent_label.setAlignment(\n'
    '            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)\n'
    "        self._percent_label.setAccessibleName('应用启动百分比')\n"
    "        self._percent_label.setStyleSheet(f'''\n"
    '            QLabel {{\n'
    "                color: {T['text']};\n"
    '                font-family: "Microsoft YaHei UI";\n'
    '                font-size: 9pt;\n'
    '                font-weight: 700;\n'
    '                background: transparent;\n'
    '            }}\n'
    "        ''')\n"
    '\n'
    '        self._progress = QProgressBar(self)\n'
    '        self._progress.setGeometry(48, 337, 524, 22)\n'
    '        # U7②：关掉条内文字，百分比放到状态行右侧（对比度从 2.01:1 提升到达标）\n'
    '        self._progress.setTextVisible(False)\n'
    "        self._progress.setAccessibleName('应用启动进度')\n"
    '        self._progress.setMinimum(0)\n'
    '        self._progress.setMaximum(100)\n'
    '        self._progress.setValue(0)\n'
    "        self._progress.setStyleSheet(f'''\n"
    '            QProgressBar {{\n'
    "                border: 1px solid {T['border']};\n"
    '                border-radius: 6px;\n'
    "                background-color: {T['bg_surface']};\n"
    '            }}\n'
    '            QProgressBar::chunk {{\n'
    '                border-radius: 5px;\n'
    "                background: {T['primary']};\n"
    '            }}\n'
    "        ''')\n"
    '\n'
    '        # 居中显示\n'
    '        screen = QApplication.primaryScreen()\n'
    '        if screen:\n'
    '            geo = screen.availableGeometry()\n'
    '            x = (geo.width() - self.width()) // 2 + geo.x()\n'
    '            y = (geo.height() - self.height()) // 2 + geo.y()\n'
    '            self.move(x, y)\n'
    '\n'
    '    def paintEvent(self, event):\n'
    '        T = self.T\n'
    '        painter = QPainter(self)\n'
    '        painter.setRenderHint(QPainter.RenderHint.Antialiasing)\n'
    '\n'
    '        paper = QLinearGradient(0, 0, self.width(), self.height())\n'
    "        paper.setColorAt(0.0, QColor(T['bg_surface']))\n"
    "        paper.setColorAt(0.58, QColor(T['bg_base']))\n"
    "        paper.setColorAt(1.0, QColor(T['bg_deep']))\n"
    '        painter.fillRect(self.rect(), paper)\n'
    '\n'
    "        glow = QColor(T['primary'])\n"
    '        glow.setAlpha(14)\n'
    '        painter.setPen(QPen(glow, 1))\n'
    '        for offset in range(-120, 660, 28):\n'
    '            painter.drawLine(offset, 0, offset + 180, self.height())\n'
    '\n'
    "        edge = QColor(T['border'])\n"
    '        edge.setAlpha(100)\n'
    '        painter.setPen(QPen(edge, 1))\n'
    '        painter.drawLine(48, 220, 572, 220)\n'
    '\n'
    "        edge = QColor(T['border'])\n"
    '        edge.setAlpha(120)\n'
    '        painter.setPen(QPen(edge, 1))\n'
    '        painter.drawRoundedRect(QRectF(18, 18, 584, 364), 10, 10)\n'
    '        painter.end()\n'
    '\n'
    '    def set_progress(self, value, status):\n'
    '        """更新真实启动阶段、百分比和窗口标题。"""\n'
    '        progress = max(0, min(100, int(value)))\n'
    '        self._progress.setValue(progress)\n'
    "        self._percent_label.setText(f'{progress}%')\n"
    '        self._status_label.setText(str(status))\n'
    '        self._status_label.setToolTip(str(status))\n'
    "        self.setWindowTitle(f'电池 SOH 评估系统 · {progress}%')\n"
    '        QApplication.processEvents()\n'
    '\n'
    '    def closeEvent(self, event):\n'
    '        """\n'
    '        区分两种关闭场景：\n'
    '        - 用户点击标题栏关闭按钮 → 只设置取消标志，让主流程干净退出\n'
    '        - 主程序加载完成后主动关闭闪屏 → 仅关闭窗口，不退出进程\n'
    '        """\n'
    '        if self._programmatic_close:\n'
    '            super().closeEvent(event)\n'
    '            return\n'
    '        # 不在 processEvents() 中途 sys.exit(0)（那会绕过清理逻辑）\n'
    '        self.cancelled = True\n'
    '        event.ignore()\n'
    '\n'
    '\n'
    '#: 需要预导入的重库及其进度区间。逐个导入可以让每一段等待都有说明，\n'
    '#: 而不是从 15% 直接跳到 75% 且进度条冻结（U7①）。\n'
    'HEAVY_IMPORTS = (\n'
    "    ('PyTorch', 'torch', 15, 45),\n"
    "    ('Matplotlib', 'matplotlib.pyplot', 45, 55),\n"
    "    ('Pandas', 'pandas', 55, 62),\n"
    "    ('XGBoost', 'xgboost', 62, 68),\n"
    "    ('PyQt 界面组件', 'PyQt6.QtWidgets', 68, 72),\n"
    ')\n'
    '\n'
    '\n'
    'def _preload_heavy_modules(splash):\n'
    '    """预导入重库，返回是否被用户取消。"""\n'
    '    import importlib\n'
    '\n'
    '    for label, module, start, _end in HEAVY_IMPORTS:\n'
    '        if splash.cancelled:\n'
    '            return True\n'
    "        splash.set_progress(start, f'正在加载 {label}…')\n"
    '        try:\n'
    '            importlib.import_module(module)\n'
    '        except ImportError as error:\n'
    '            # 可选依赖缺失不应阻止启动（例如没有 xgboost 也能用 RNN）\n'
    "            splash.set_progress(start, f'{label} 不可用，已跳过（{error}）')\n"
    '    return splash.cancelled\n'
    '\n'
    '\n'
    'def fail_startup(splash, stage, error):\n'
    '    """统一的启动失败出口：日志 + 简短对话框 + 退出码 1。"""\n'
    '    traceback.print_exc()\n'
    '    splash._programmatic_close = True\n'
    '    splash.close()\n'
    '    try:\n'
    '        from utils.logger import setup_logger\n'
    "        setup_logger().exception('启动失败：%s', stage)\n"
    '    except Exception:\n'
    '        traceback.print_exc()\n'
    '    try:\n'
    '        from PyQt6.QtWidgets import QMessageBox\n'
    "        QMessageBox.critical(None, '启动失败', concise_startup_error(error))\n"
    '    except Exception:\n'
    '        traceback.print_exc()\n'
    '    sys.exit(1)\n'
    '\n'
    '\n'
    "if __name__ == '__main__':\n"
    '    # ── 阶段 1：立即创建 QApplication 并显示闪屏（目标 < 3 秒）──\n'
    '    # 注意：不在此处导入 utils/torch 等重模块，确保闪屏秒开\n'
    '    app = QApplication(sys.argv)\n'
    "    app.setApplicationDisplayName('Battery SOH Assessment System')\n"
    '    app.setWindowIcon(_get_icon())\n'
    '\n'
    '    # 字体引导：必须早于任何控件创建。PyQt6 的 offscreen/minimal 平台插件\n'
    '    # 不使用 Windows 字体引擎，QFontDatabase 可能为空 → 中文全变方框。\n'
    '    # install_fonts 会显式注册系统中文字体（见 ui/fonts.py）。\n'
    '    from ui.fonts import install_fonts\n'
    '    install_fonts(app)\n'
    '\n'
    '    # A1：安装全局异常钩子，把「闪退」变成「日志 + 一条非阻塞提示」。\n'
    '    # crash_guard 只依赖 PyQt6.QtCore，很轻，可以在这里导入。\n'
    '    from utils.crash_guard import bridge, install_excepthooks\n'
    '    install_excepthooks()\n'
    '\n'
    '    # 立即显示启动闪屏\n'
    '    qt_splash = _StartupSplash()\n'
    '    qt_splash.show()\n'
    "    qt_splash.set_progress(5, '正在准备应用界面…')\n"
    '    app.processEvents()\n'
    '\n'
    '    # ── 阶段 2：加载核心模块（进度 15% → 72%，最耗时）──\n'
    '    try:\n'
    '        if _preload_heavy_modules(qt_splash):\n'
    '            sys.exit(0)\n'
    "        qt_splash.set_progress(72, '正在加载界面模块…')\n"
    '        from ui.main_window import MainWindow\n'
    '    except Exception as startup_error:\n'
    "        fail_startup(qt_splash, '加载核心模块', startup_error)\n"
    '\n'
    "    qt_splash.set_progress(75, '核心组件加载完成')\n"
    '    app.processEvents()\n'
    '\n'
    '    # ── 阶段 3：初始化主窗口（进度 82% → 98%）──\n'
    '    # U7⑤：这一段此前在 try 保护之外，构造主窗口时出任何异常都会\n'
    '    # 「闪屏一闪就没了」；现在纳入同一个保护。\n'
    '    try:\n'
    "        qt_splash.set_progress(82, '正在初始化主窗口…')\n"
    '        app.processEvents()\n'
    '        window = MainWindow()\n'
    '        # A1：任何线程里未捕获的异常 → 非阻塞提示\n'
    '        bridge.error.connect(window.show_error_toast)\n'
    "        qt_splash.set_progress(92, '正在恢复配置与界面状态…')\n"
    '        app.processEvents()\n'
    '        window.show()\n'
    '    except Exception as startup_error:\n'
    "        fail_startup(qt_splash, '初始化主窗口', startup_error)\n"
    '\n'
    "    qt_splash.set_progress(98, '正在呈现主界面…')\n"
    '    app.processEvents()\n'
    '\n'
    '    # ── 关闭闪屏（进度 100%）──\n'
    '    # 标记为程序主动关闭，避免 closeEvent 中 sys.exit(0) 导致整个应用退出\n'
    "    qt_splash.set_progress(100, '启动完成')\n"
    '    qt_splash._programmatic_close = True\n'
    '    qt_splash.close()\n'
    '    qt_splash.deleteLater()\n'
    '\n'
    '    sys.exit(app.exec())\n'
)

# ---------------------------------------------------------------------------
# 启动序列（原 battery_soh_app.py 的 __main__ 块）
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    if '--check' in _sys.argv:
        _run_self_check()
        raise SystemExit(0)

    import traceback as _traceback
    from PyQt6.QtWidgets import QApplication as _QApplication

    _bootstrap = _register_module('battery_soh_app', _BOOTSTRAP_SOURCE)

    # ── 阶段 1：立即创建 QApplication 并显示闪屏 ──
    app = _QApplication(_sys.argv)
    app.setApplicationDisplayName('Battery SOH Assessment System')
    app.setWindowIcon(_bootstrap._get_icon())

    qt_splash = _bootstrap._StartupSplash()
    qt_splash.show()
    qt_splash.set_progress(5, '正在准备应用界面…')
    app.processEvents()

    # ── 阶段 2：加载核心模块 ──
    qt_splash.set_progress(15, '正在加载计算与绘图组件…')
    app.processEvents()

    try:
        _load_all_modules()
        from ui.main_window import MainWindow
    except Exception as startup_error:
        _traceback.print_exc()
        qt_splash._programmatic_close = True
        qt_splash.close()
        try:
            from utils.logger import setup_logger
            setup_logger().exception('加载核心模块失败')
        except Exception:
            _traceback.print_exc()
        try:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                None, '启动失败', _bootstrap.concise_startup_error(startup_error))
        except Exception:
            _traceback.print_exc()
        _sys.exit(1)

    qt_splash.set_progress(75, '核心组件加载完成')
    app.processEvents()

    # ── 阶段 3：初始化主窗口 ──
    qt_splash.set_progress(82, '正在初始化主窗口…')
    app.processEvents()

    window = MainWindow()
    qt_splash.set_progress(92, '正在恢复配置与界面状态…')
    app.processEvents()

    window.show()
    qt_splash.set_progress(98, '正在呈现主界面…')
    app.processEvents()

    qt_splash.set_progress(100, '启动完成')
    qt_splash._programmatic_close = True
    qt_splash.close()
    qt_splash.deleteLater()

    _sys.exit(app.exec())
