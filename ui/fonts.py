"""Qt 字体引导：保证中文在任何平台插件下都能正确渲染。

## 为什么需要这个模块

PyQt6 的 **offscreen / minimal 平台插件不使用 Windows 字体引擎**，只认
``PyQt6/Qt6/lib/fonts`` 目录。该目录在多数 pip / conda 安装里是缺失的，于是：

* ``QFontDatabase.families()`` 返回**空列表**；
* QSS 里的 ``font-family`` 一个都解析不到；
* 所有 Qt 文字渲染成方框（豆腐块），而 matplotlib 图表不受影响——它自己
  解析 ``theme_tokens.CJK_FONTS``。

实测（本仓库目标环境）：

* ``platform = windows`` → 570 个字体族，中文正常；
* ``platform = offscreen`` → **0 个字体族**，中文全部变成方框。

因此本模块显式把系统中文字体注册进 Qt 并设为应用字体，做到：

1. 真实窗口环境（``windows`` / ``cocoa`` / ``xcb``）本来就能枚举字体，
   这里只是幂等地挑出最合适的字体族；
2. offscreen 环境（README 截图、CI 冒烟）下补齐字体，截图不再出现方框；
3. 用户机器上 Qt 字体库损坏时也能自愈。
"""

from __future__ import annotations

import os
import sys

_FONT_DIRS = (
    os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts'),
    os.path.expanduser('~/.fonts'),
    '/usr/share/fonts',
    '/usr/local/share/fonts',
    '/System/Library/Fonts',
    '/Library/Fonts',
)

#: 需要注册的字体文件，按「中文 UI → Latin UI → 等宽 → 标题 → 兜底」排列。
#: ``.ttc`` 是字体集合，一个文件里可能注册出多个家族（如 msyh.ttc →
#: ``Microsoft YaHei`` 与 ``Microsoft YaHei UI``）。
_FONT_FILES = (
    'msyh.ttc', 'msyhbd.ttc', 'msyhl.ttc',       # 微软雅黑（中文 UI 首选）
    'msjh.ttc',                                   # 微软正黑（繁体环境兜底）
    'segoeui.ttf', 'segoeuib.ttf', 'segoeuil.ttf',  # Latin UI
    'consola.ttf', 'consolab.ttf',                # 等宽（数值 / 日志）
    'stzhongs.ttf', 'stkaiti.ttf', 'stxihei.ttf', 'stsong.ttf',  # 中文字体
    'simhei.ttf', 'simsun.ttc', 'deng.ttf',       # 兜底中文
    'NotoSansCJK-Regular.ttc', 'NotoSansCJKsc-Regular.otf',
    'wqy-microhei.ttc', 'DejaVuSans.ttf',         # Linux 兜底
)

#: UI 字体回退链。第一项是目标族，其余是不同平台 / 不同字体包的写法。
UI_FONT_FAMILIES = (
    'Microsoft YaHei UI', 'Microsoft YaHei', 'PingFang SC',
    'Noto Sans CJK SC', 'Noto Sans CJK JP', 'Source Han Sans SC',
    'WenQuanYi Micro Hei', 'Segoe UI', 'SimHei', 'DengXian', 'SimSun',
)

#: 标题 / 展示用字体回退链（中文衬线优先，更有「宣纸」气质）。
DISPLAY_FONT_FAMILIES = (
    'STZhongsong', 'STKaiti', 'STXihei', 'FangSong', 'KaiTi',
    'Microsoft YaHei', 'SimSun',
)

#: 等宽字体回退链（数值、日志、坐标读数）。
MONO_FONT_FAMILIES = (
    'Consolas', 'JetBrains Mono', 'Cascadia Mono', 'Cascadia Code',
    'DejaVu Sans Mono', 'Courier New',
)

_INSTALLED = False
_REGISTERED = False
_RESOLVED = {'ui': None, 'display': None, 'mono': None, 'registered': ()}
#: 已经配置过的 QApplication（按 id 记录）与当时设置的字体族。
#: ``setFont`` 会触发**所有现存控件**的样式重算，因此在长生命周期进程里
#: 反复调用既浪费又危险（实测在连续创建/销毁大量窗口的测试进程中会段错误）。
_CONFIGURED_APPS = {}


def _font_path(name):
    """在候选目录里找字体文件，返回第一个存在的绝对路径。"""
    for directory in _FONT_DIRS:
        candidate = os.path.join(directory, name)
        if os.path.isfile(candidate):
            return candidate
    return None


def register_system_fonts(force=False):
    """把系统字体文件注册进 Qt；返回本次新注册的家族名元组。

    **每个进程只做一次**。``QFontDatabase.addApplicationFont`` 每次调用都会往
    Qt 内部的字体表里追加记录（即使文件相同），因此在「创建大量窗口」的进程里
    反复调用会不断膨胀内部状态，实测会让长时间运行的测试进程崩溃。
    字体是进程级资源，没有理由随窗口重复注册。

    ``force=True`` 可强制重新扫描（例如用户在运行中装了新字体）。
    """
    global _REGISTERED
    if _REGISTERED and not force:
        return _RESOLVED.get('registered') or ()

    try:
        from PyQt6.QtGui import QFontDatabase
    except ImportError:          # pragma: no cover - 无 PyQt6 时静默跳过
        return ()

    registered = []
    for name in _FONT_FILES:
        path = _font_path(name)
        if path is None:
            continue
        font_id = QFontDatabase.addApplicationFont(path)
        if font_id == -1:
            continue
        registered.extend(QFontDatabase.applicationFontFamilies(font_id))
    _REGISTERED = True
    return tuple(dict.fromkeys(registered))


def _pick_family(families, candidates):
    """在 ``families`` 里按 ``candidates`` 的顺序挑第一个可用的族名。"""
    available = set(families)
    for candidate in candidates:
        if candidate in available:
            return candidate
    return None


def resolve_families():
    """返回 ``{'ui':…, 'display':…, 'mono':…}`` 与实际注册到的家族列表。"""
    from PyQt6.QtGui import QFontDatabase

    registered = register_system_fonts()
    families = list(QFontDatabase.families())

    resolved = {
        'ui': _pick_family(families, UI_FONT_FAMILIES),
        'display': _pick_family(families, DISPLAY_FONT_FAMILIES),
        'mono': _pick_family(families, MONO_FONT_FAMILIES),
    }
    _RESOLVED.update(resolved)
    _RESOLVED['registered'] = registered
    return dict(_RESOLVED)


def install_fonts(app=None, point_size=10):
    """注册系统字体并把解析出的 UI 字体设为应用默认字体。

    应在创建 **任何控件之前** 调用（``battery_soh_app.py`` 在 QApplication
    构造后立刻调用；``MainWindow`` 也会兜底调用一次）。返回解析出的 UI 族名。

    幂等：字体注册总要跑（Qt 自己会去重），但 ``QApplication.setFont`` 对同一个
    QApplication 只做一次——它会让**所有现存控件**重算样式，重复调用没有收益，
    在窗口频繁创建销毁的长时间进程里还会踩到已析构的控件。

    返回值可能为 ``None``——表示这台机器上一个候选字体都没有，此时 Qt 自己
    的回退仍然生效，但我们不会假装已经修好。
    """
    global _INSTALLED

    from PyQt6.QtGui import QFont

    if app is None:
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance()

    families = resolve_families()
    ui_family = families.get('ui')
    key = id(app)

    if ui_family and _CONFIGURED_APPS.get(key) == ui_family:
        _INSTALLED = True
        return ui_family

    if ui_family:
        font = QFont(ui_family, point_size)
        font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        if app is not None:
            app.setFont(font)
            _CONFIGURED_APPS[key] = ui_family
        else:                                # pragma: no cover - 无 QApplication
            QFont.insertSubstitutions(ui_family, [ui_family])
    _INSTALLED = True
    return ui_family


def installed():
    """是否已调用过 :func:`install_fonts`。"""
    return _INSTALLED


def ui_font(point_size=10, weight=None, family=None):
    """构造 UI 字体（未安装时给出安全的族名回退）。"""
    from PyQt6.QtGui import QFont

    name = family or _RESOLVED.get('ui') or UI_FONT_FAMILIES[0]
    font = QFont(name, point_size)
    if weight is not None:
        font.setWeight(weight)
    return font


def font_fallbacks_css(candidates=UI_FONT_FAMILIES):
    """QSS 用的回退链字符串，例如 ``"Microsoft YaHei", "Segoe UI", sans-serif``。"""
    quoted = ', '.join(f'"{name}"' for name in candidates)
    return f'{quoted}, sans-serif'


def diagnostics():
    """诊断信息：字体目录、已注册家族、解析结果。供启动日志与排查使用。"""
    try:
        from PyQt6.QtGui import QFontDatabase
    except ImportError:          # pragma: no cover
        return {'error': 'PyQt6 不可用'}

    available = list(QFontDatabase.families())
    return {
        'platform': (os.environ.get('QT_QPA_PLATFORM') or 'default'),
        'family_count': len(available),
        'registered': list(_RESOLVED.get('registered') or ()),
        'resolved': {key: _RESOLVED.get(key)
                     for key in ('ui', 'display', 'mono')},
        'font_dirs': [d for d in _FONT_DIRS if os.path.isdir(d)],
        'cjk_ok': bool(available) and _pick_family(
            available, UI_FONT_FAMILIES) is not None,
        'python': sys.version.split()[0],
    }
