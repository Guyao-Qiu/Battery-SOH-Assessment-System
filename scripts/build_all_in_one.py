#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把 Battery SOH 评估系统打包成单个可独立运行的 .py 文件。

用法：
    python scripts/build_all_in_one.py

产物：
    battery_soh_all_in_one.py（写在项目根目录）

原理：
    1. 读取 core / models / ui / utils 下全部模块源码，逐行以字符串字面量内嵌；
    2. 运行时按原名（core.xxx / ui.xxx / ...）创建模块对象并注册进 sys.modules，
       模块之间的 from/import（含 from .xxx 相对导入）行为与多文件版本完全一致；
    3. 静态资源（SOH.ico、assets/icons/*.svg）与初始 config.json 以 base64 内嵌，
       脚本同级目录若已有同名文件则优先使用本地文件，绝不覆盖。
"""

from __future__ import annotations

import base64
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'battery_soh_all_in_one.py'

PACKAGE_NAMES = ('core', 'models', 'ui', 'utils')

# 按依赖从少到多排列，可减少运行时迭代加载的轮数
MODULE_FILES = (
    # theme_tokens 是顶层模块（不在任何包里）：纯字典 + 纯函数，
    # 启动闪屏要在重库加载前拿到颜色，所以必须最先就绪。
    'theme_tokens.py',
    'utils/paths.py',
    'utils/logger.py',
    'utils/config.py',
    'utils/crash_guard.py',
    'utils/icon_generator.py',
    'core/progress.py',
    'core/cancellation.py',
    'core/batching.py',
    'core/evaluate.py',
    'core/preprocess.py',
    'core/prediction.py',
    'core/baselines.py',
    'core/protocol.py',
    'core/stream_protocol.py',
    'core/validation.py',
    'core/adapters.py',
    'core/dataload.py',
    'core/result_semantics.py',
    'core/run_snapshot.py',
    'core/report_export.py',
    'models/rnn_model.py',
    'models/XGBoost.py',
    'models/RF.py',
    'core/model_factory.py',
    'core/train.py',
    'core/model_persistence.py',
    # ui.fonts 必须在 ui.style 之前：style 会 import 它来渲染 font-family 回退链
    'ui/fonts.py',
    'ui/style.py',
    'ui/animated_button.py',
    'ui/result_model.py',
    'ui/chart_show.py',
    'ui/worker.py',
    'ui/predict_worker.py',
    'ui/tcp_server.py',
    'ui/tcp_display.py',
    'ui/main_window.py',
    'utils/__init__.py',
    'core/__init__.py',
    'models/__init__.py',
    'ui/__init__.py',
)

# 以 base64 内嵌的静态资源（相对项目根）
STATIC_ASSET_FILES = (
    'SOH.ico',
    'assets/icons/combo-down-arrow.svg',
)

CONFIG_REL = 'config.json'
BOOTSTRAP_REL = 'battery_soh_app.py'

# 这些模块用 __file__ 反推资源位置，必须把 __file__ 指向资源根而非项目根
ASSET_ROOT_MODULES = {
    'ui.style': 'ui/style.py',
    'utils.icon_generator': 'utils/icon_generator.py',
    'battery_soh_app': 'battery_soh_app.py',
}

_CODING_COOKIE = re.compile(r'^[ \t\f]*#.*?coding[:=][ \t]*[-\w.]+')

# ---------------------------------------------------------------------------
# 生成器工具
# ---------------------------------------------------------------------------


def module_name(rel_path: str) -> str:
    """'utils/paths.py' -> 'utils.paths'；'core/__init__.py' -> 'core'。"""
    parts = rel_path[:-3].split('/')
    if parts[-1] == '__init__':
        parts = parts[:-1]
    return '.'.join(parts)


def read_source(rel_path: str) -> str:
    """读取源码；顺手注释掉编码声明行（str 源码里的 cookie 跨版本易踩坑）。"""
    text = (ROOT / rel_path).read_text(encoding='utf-8-sig')
    lines = text.split('\n')
    for index in range(min(2, len(lines))):
        if _CODING_COOKIE.match(lines[index]):
            lines[index] = '# (coding 声明已由单文件统一处理)'
    return '\n'.join(lines)


def emit_source(source: str, indent: str = '    ') -> str:
    """把源码逐行转成相邻拼接的字符串字面量，保持文件可读、行长可控。"""
    lines = source.split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    return '\n'.join(indent + repr(line + '\n') for line in lines)


def emit_base64(payload: str, indent: str = '        ', width: int = 76) -> str:
    chunks = [payload[i:i + width] for i in range(0, len(payload), width)]
    return '\n'.join(indent + repr(chunk) for chunk in chunks)


# ---------------------------------------------------------------------------
# 单文件模板
# ---------------------------------------------------------------------------

HEADER = '''# -*- coding: utf-8 -*-
# ===========================================================================
#  Battery SOH Assessment System —— 单文件整合版 (All-in-One)
# ===========================================================================
#  本文件由 scripts/build_all_in_one.py 自动生成，请勿手工编辑。
#  生成时间: __TIMESTAMP__
#  内嵌模块: __MODULE_COUNT__ 个（原 core/ models/ ui/ utils/ 全部源码）
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
        '本程序需要 Python 3.10 或更高版本，当前为 %s\\n' % _sys.version.split()[0])
    raise SystemExit(1)

_BASE_DIR = _Path(_os.path.dirname(_os.path.abspath(__file__)))
_PACKAGE_NAMES = ('core', 'models', 'ui', 'utils')

# ---------------------------------------------------------------------------
# 内嵌静态资源（base64）
# ---------------------------------------------------------------------------
_EMBEDDED_STATIC = {
'''

STATIC_TAIL = '''}

'''

RUNTIME_BLOCK = '''# ---------------------------------------------------------------------------
# 运行时装配：把内嵌源码还原成模块并注册进 sys.modules
# ---------------------------------------------------------------------------
_ASSET_ROOT_MODULES = __ASSET_ROOT_MODULES__

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


'''

MAIN_BLOCK = '''# ---------------------------------------------------------------------------
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
'''


# ---------------------------------------------------------------------------
# 组装
# ---------------------------------------------------------------------------


def build() -> str:
    required = list(MODULE_FILES) + list(STATIC_ASSET_FILES) + [CONFIG_REL, BOOTSTRAP_REL]
    missing = [rel for rel in required if not (ROOT / rel).is_file()]
    if missing:
        raise SystemExit('缺少源文件: ' + ', '.join(missing))

    parts = [
        HEADER.replace('__TIMESTAMP__', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
              .replace('__MODULE_COUNT__', str(len(MODULE_FILES))),
    ]

    for rel in STATIC_ASSET_FILES:
        payload = base64.b64encode((ROOT / rel).read_bytes()).decode('ascii')
        parts.append('    %r: (\n%s\n    ),\n' % (rel, emit_base64(payload)))

    parts.append(STATIC_TAIL)

    config_payload = base64.b64encode((ROOT / CONFIG_REL).read_bytes()).decode('ascii')
    parts.append('_EMBEDDED_CONFIG = (\n%s\n)\n\n' % emit_base64(config_payload))

    asset_map = '{\n' + ''.join(
        '    %r: %r,\n' % (key, value) for key, value in ASSET_ROOT_MODULES.items()
    ) + '}'
    parts.append(RUNTIME_BLOCK.replace('__ASSET_ROOT_MODULES__', asset_map))
    parts.append('\n')

    parts.append('# ---------------------------------------------------------------------------\n')
    parts.append('# 内嵌模块源码\n')
    parts.append('# ---------------------------------------------------------------------------\n')
    parts.append('_MODULE_SOURCES = {}\n\n')

    for rel in MODULE_FILES:
        source = read_source(rel)
        parts.append('# ---- %s ----\n' % rel)
        parts.append('_MODULE_SOURCES[%r] = (\n%s\n)\n\n' % (module_name(rel), emit_source(source)))

    parts.append('# ---- %s（应用入口） ----\n' % BOOTSTRAP_REL)
    parts.append('_BOOTSTRAP_SOURCE = (\n%s\n)\n\n' % emit_source(read_source(BOOTSTRAP_REL)))

    parts.append(MAIN_BLOCK)
    return ''.join(parts)


def main():
    text = build()
    OUTPUT.write_text(text, encoding='utf-8')
    line_count = text.count('\n') + 1
    size_kb = OUTPUT.stat().st_size / 1024
    print('已生成: %s' % OUTPUT)
    print('行数: %d  大小: %.1f KB  内嵌模块: %d 个' % (line_count, size_kb, len(MODULE_FILES)))


if __name__ == '__main__':
    main()
