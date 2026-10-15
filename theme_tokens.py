"""唯一的"颜色真相来源"（浅色 宣纸 / 深色 墨夜）。

放在工程根目录，**不要**放进 ``ui/`` 或 ``utils/``：这两个包的 ``__init__.py``
会连带导入 matplotlib / torch，而启动闪屏需要在重库加载**之前**就拿到颜色，
否则「闪屏秒开」就被破坏了。

本模块只依赖标准库（纯字典 + 纯函数），不 import 任何第三方库。

设计语言：宣纸水墨
- 事实用中性墨色，模型输出用黛青强调，失效用朱砂；
- 任何状态都要有**非颜色**的冗余（图标 / 文字），见 ``ui/style.py`` 的 QSS。
"""

# ── 浅色：宣纸 ────────────────────────────────────────────────
LIGHT = {
    # 背景层级
    'bg_deep': '#E8E0D1', 'bg_base': '#F3EDE0', 'bg_surface': '#FAF6EC',
    'bg_elevated': '#E1D8C8', 'bg_hover': '#D6CDBC', 'bg_focus': '#FFFDF7',
    # 描边
    'border': '#7C8179', 'border_soft': '#C5BBAA',
    # 文字
    'text': '#202724', 'text_muted': '#4F5953', 'text_dim': '#6B726C',
    # 主强调：黛青
    'primary': '#315B5A', 'primary_d': '#244743', 'primary_l': '#52766E',
    'on_accent': '#FFF9ED',
    # 语义状态
    'success': '#4F6B4F', 'success_d': '#3C533C', 'success_l': '#3F6045',
    'warning': '#7A4E22', 'danger': '#9E3D2F', 'danger_d': '#7F2F26',
    'on_danger': '#FFF9ED',
    # 兼容旧 token（ui/style.py 的 COLORS 键名）
    'paper': '#F3EDE0', 'ink': '#202724', 'cinnabar': '#9E3D2F',
    'spin_selection': '#76563A', 'on_selection': '#FFF9ED',
    'shadow': 'rgba(32, 39, 36, 0.14)',
    # 图表专用
    'chart_bg': '#F7F1E5', 'chart_measured': '#202724',
    'chart_forecast': '#2B7A75', 'chart_threshold': '#9E3D2F',
    'chart_grid': '#C5BBAA', 'chart_spine': '#7C8179',
    'chart_band_alpha': 0.18,
    # 多电池叠加分类色：对图表底 ≥ 3.57:1，最小两两 ΔE 28.5（含色觉缺陷模拟）
    'chart_series': ['#1F4E9E', '#C04F00', '#00805A', '#0F8C99', '#202724'],
}

# ── 深色：墨夜（不是简单反色，底偏冷青灰，与宣纸呼应） ──────────
DARK = {
    'bg_deep': '#101415', 'bg_base': '#151B1C', 'bg_surface': '#1B2224',
    'bg_elevated': '#232C2E', 'bg_hover': '#2B3638', 'bg_focus': '#202829',
    'border': '#687776', 'border_soft': '#323E3F',
    'text': '#E9E4D8', 'text_muted': '#A9B2AD', 'text_dim': '#7C8682',
    'primary': '#6FB3A8', 'primary_d': '#4C8F85', 'primary_l': '#8CC7BD',
    'on_accent': '#0F1A19',
    'success': '#86B58B', 'success_d': '#6FA076', 'success_l': '#86B58B',
    'warning': '#D9A441', 'danger': '#E07A68', 'danger_d': '#C7634F',
    'on_danger': '#0F1A19',
    'paper': '#151B1C', 'ink': '#E9E4D8', 'cinnabar': '#E07A68',
    'spin_selection': '#C9A87C', 'on_selection': '#0F1A19',
    'shadow': 'rgba(0, 0, 0, 0.45)',
    'chart_bg': '#151B1C', 'chart_measured': '#E9E4D8',
    'chart_forecast': '#6FB3A8', 'chart_threshold': '#E07A68',
    'chart_grid': '#2B3638', 'chart_spine': '#687776',
    'chart_band_alpha': 0.28,
    'chart_series': ['#8FA8F0', '#FF7A66', '#F2D16B', '#D894B8', '#E9E4D8'],
}

THEMES = {'light': LIGHT, 'dark': DARK}
#: 产品默认外观 = 深色（墨夜）；浅色（宣纸）可选，切换后由 QSettings 记住。
DEFAULT_THEME = 'dark'

#: QSettings 里保存主题用的键名。
#: 带版本号是**有意的迁移**：旧版本每次启动都会把当时的默认值（浅色）写进
#: ``theme``，于是「改成深色为默认」对老用户不会生效。换用新键后，新默认值
#: 能真正落到每个人身上；此后用户自己的选择照常被记住。
THEME_SETTINGS_KEY = 'theme_v2'

# 图表中文字体回退链：Windows → macOS → Linux。
# 注意 matplotlib 对 .ttc 字体登记的家族名可能与系统不同（例如某些环境里
# Noto Sans CJK 只登记成 'Noto Sans CJK JP'），所以把几种写法都列上。
CJK_FONTS = [
    'Microsoft YaHei', 'PingFang SC', 'Noto Sans CJK SC', 'Noto Sans CJK JP',
    'Source Han Sans SC', 'WenQuanYi Micro Hei', 'SimHei', 'DejaVu Sans',
]

LINESTYLES = ['-', '--', '-.', ':']
MARKERS = ['o', 's', '^', 'D', 'v']


def get_theme(mode):
    """按名称取 token；未知名称回退默认主题。"""
    return THEMES.get(str(mode).strip().lower(), THEMES[DEFAULT_THEME])


def rgba(hex_color, alpha):
    """``'#315B5A', 0.08`` -> ``'rgba(49, 91, 90, 0.08)'``。

    QSS 里所有半透明色都用它，不再手写 ``rgba(49, 91, 90, ...)``。
    """
    h = str(hex_color).lstrip('#')
    if len(h) == 3:
        h = ''.join(ch * 2 for ch in h)
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f'rgba({r}, {g}, {b}, {alpha})'


def _lin(c):
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hex_color):
    """WCAG 2.1 相对亮度。"""
    h = str(hex_color).lstrip('#')
    if len(h) == 3:
        h = ''.join(ch * 2 for ch in h)
    r, g, b = (_lin(int(h[i:i + 2], 16)) for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(fg, bg):
    """WCAG 2.1 对比度（1.0–21.0）。"""
    hi, lo = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def usable_colors(palette, bg, minimum=3.0):
    """图形对象（线条 / 标记）按 WCAG 需要 ≥ 3:1；只保留满足要求的颜色。"""
    return [c for c in palette if contrast(c, bg) >= minimum]


def series_style(index, tokens):
    """前 5 条线靠颜色区分；更多条时轮换线型 / 标记，色觉缺陷下也能分辨。"""
    colors = tokens['chart_series']
    return {
        'color': colors[index % len(colors)],
        'linestyle': LINESTYLES[(index // len(colors)) % len(LINESTYLES)],
        'marker': MARKERS[index % len(MARKERS)],
        'markersize': 3,
    }
