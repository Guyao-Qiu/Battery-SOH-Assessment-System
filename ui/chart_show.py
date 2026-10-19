import numpy as np
import matplotlib
matplotlib.use('QtAgg')
import matplotlib as mpl
import matplotlib.pyplot as plt
# C6：中文字体回退链来自唯一真相来源，不再在本文件里另写一份字体名单。
from theme_tokens import (
    CJK_FONTS, DARK, LIGHT, get_theme, series_style, usable_colors,
)
plt.rcParams['font.sans-serif'] = list(CJK_FONTS)
plt.rcParams['axes.unicode_minus'] = False
# 不再需要 mathtext.fontset，改用 Unicode 原生上下标字符

from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT,
)
# U9：刻度密度 —— 刻度用显式数组下发，标签按步长格式化。
# 刻意不使用 MultipleLocator / AutoMinorLocator：它们是有状态的 locator，
# 会在每次绘制时重新查询轴对象，与本环境的 PyQt6 + offscreen matplotlib
# 组合一起会触发原生访问违例（详见 _apply_ticks）。
from matplotlib.ticker import FuncFormatter

#: 图例字号相对默认字号的缩放（要求「缩小三分之一」→ 保留 2/3）。
LEGEND_FONT_SCALE = 2.0 / 3.0

#: 数据线默认宽度（与参考图表的细线风格一致）：实测线、预测线、阈值线。
MEASURED_LINE_WIDTH = 1.0
FORECAST_LINE_WIDTH = 1.5
THRESHOLD_LINE_WIDTH = 1.2

from PyQt6.QtCore import Qt, QSize, QPoint, QTimer, QEvent, QObject
from PyQt6.QtGui import (
    QIcon, QPixmap, QPainter, QColor, QPen, QBrush, QAction, QFont,
    QShortcut, QKeySequence,
)
from PyQt6.QtWidgets import (
    QPushButton, QToolTip, QApplication, QToolButton,
    QGroupBox, QLabel, QDialog, QDialogButtonBox, QTabWidget,
    QComboBox, QLineEdit, QCheckBox, QSpinBox, QMessageBox,
    QInputDialog, QColorDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QListWidget, QListWidgetItem, QAbstractItemView, QSplitter,
    QGridLayout, QScrollArea, QWidget, QFrame, QMenu,
)
from utils.icon_generator import get_dialog_icon, show_message, input_get_item

# ── 图标绘制 ──────────────────────────────────────────────
# 淡墨工具图标，与宣纸背景保持稳定对比。
# C1：写成 RGB 整数而不是颜色字面量——图标是固定装饰，不随主题切换，
# 但色值同样不该以 #RRGGBB 的形式散落在源码里。
_ICON_COLOR = QColor(70, 80, 74)  # 淡墨：接近中性墨色
_ICON_STROKE = 1.6
_ICON_SIZE = QSize(24, 24)


def _paint_icon(draw_func):
    pix = QPixmap(_ICON_SIZE)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(_ICON_COLOR, _ICON_STROKE))
    p.setBrush(Qt.BrushStyle.NoBrush)
    draw_func(p, _ICON_SIZE)
    p.end()
    return QIcon(pix)


def _home_draw(p, sz):
    """主页图标：现代感房屋"""
    w, h = sz.width(), sz.height()
    # 屋顶
    p.drawPolyline([QPoint(4, 11), QPoint(12, 4), QPoint(20, 11)])
    # 房屋主体
    p.drawRect(6, 11, 12, 9)
    # 门
    p.drawRect(10, 15, 4, 5)


def _arrow_left(p, sz):
    """返回上一个视图：向左箭头"""
    w, h = sz.width(), sz.height()
    # 主线
    p.drawLine(18, 12, 6, 12)
    # 箭头
    p.drawPolyline([QPoint(11, 7), QPoint(6, 12), QPoint(11, 17)])


def _arrow_right(p, sz):
    """前进到下一个视图：向右箭头"""
    w, h = sz.width(), sz.height()
    # 主线
    p.drawLine(6, 12, 18, 12)
    # 箭头
    p.drawPolyline([QPoint(13, 7), QPoint(18, 12), QPoint(13, 17)])


def _pan_draw(p, sz):
    """平移画布：十字方向箭头"""
    w, h = sz.width(), sz.height()
    c = 12
    # 垂直线与上下箭头
    p.drawLine(c, 4, c, 20)
    p.drawPolyline([QPoint(9, 7), QPoint(c, 4), QPoint(15, 7)])
    p.drawPolyline([QPoint(9, 17), QPoint(c, 20), QPoint(15, 17)])
    # 水平线与左右箭头
    p.drawLine(4, c, 20, c)
    p.drawPolyline([QPoint(7, 9), QPoint(4, c), QPoint(7, 15)])
    p.drawPolyline([QPoint(17, 9), QPoint(20, c), QPoint(17, 15)])


def _zoom_draw(p, sz):
    """矩形缩放：放大镜与虚线选框"""
    w, h = sz.width(), sz.height()
    # 放大镜圆圈与手柄
    p.drawEllipse(QPoint(10, 10), 5, 5)
    p.drawLine(14, 14, 19, 19)

    # 外层虚线框 (提示矩形框选)
    p.save()
    pen = p.pen()
    pen.setStyle(Qt.PenStyle.DashLine)
    pen.setWidthF(1.2)
    p.setPen(pen)
    p.drawRect(3, 3, 18, 18)
    p.restore()


def _subplots_draw(p, sz):
    """配置子图参数：网格布局（田字格）"""
    w, h = sz.width(), sz.height()
    # 整体大边框
    p.drawRect(4, 4, 16, 16)
    # 内部十字分隔线
    p.drawLine(4, 12, 20, 12)
    p.drawLine(12, 4, 12, 20)


def _customize_draw(p, sz):
    """编辑参数：调节滑块"""
    w, h = sz.width(), sz.height()
    # 上轨道和滑块
    p.drawLine(4, 8, 20, 8)
    p.drawEllipse(QPoint(16, 8), 2, 2)
    # 下轨道和滑块
    p.drawLine(4, 16, 20, 16)
    p.drawEllipse(QPoint(8, 16), 2, 2)


def _save_draw(p, sz):
    """保存当前图表：经典软盘"""
    w, h = sz.width(), sz.height()
    # 软盘轮廓带右上角折角
    p.drawPolyline([
        QPoint(4, 4), QPoint(16, 4), QPoint(20, 8),
        QPoint(20, 20), QPoint(4, 20), QPoint(4, 4)
    ])
    # 顶部标签槽
    p.drawRect(8, 4, 8, 5)
    # 底部读写金属片
    p.drawRect(6, 14, 12, 6)


def _subplots_draw(p, sz):
    """子图图标：2x2 网格"""
    w, h = sz.width(), sz.height()
    m = 4
    gap = 4
    # 四个矩形
    for i in range(2):
        for j in range(2):
            x = m + i * (w // 2 - m)
            y = m + j * (h // 2 - m)
            p.drawLine(x, y, x + w // 2 - gap, y)
            p.drawLine(x + w // 2 - gap, y, x + w // 2 - gap, y + h // 2 - gap)
            p.drawLine(x + w // 2 - gap, y + h // 2 - gap, x, y + h // 2 - gap)
            p.drawLine(x, y + h // 2 - gap, x, y)

def _customize_draw(p, sz):
    """自定义图标：滑块"""
    w, h = sz.width(), sz.height()
    m = 5
    # 滑轨竖线
    p.drawLine(w // 2, m, w // 2, h - m)
    # 底部横条
    p.drawLine(m, h - m, w - m, h - m)
    # 滑块圆形
    cy = h // 2 - 2
    p.drawEllipse(QPoint(w // 2, cy), 4, 4)


def _save_draw(p, sz):
    """保存图标：磁盘"""
    w, h = sz.width(), sz.height()
    m = 4
    # 外框
    p.drawLine(m, m, m, h - m)
    p.drawLine(m, h - m, w - m, h - m)
    p.drawLine(w - m, m, w - m, h - m)
    p.drawLine(m, m, w - m, m)
    # 标签缺口
    p.drawLine(w - m - 6, m, w - m - 6, m + 5)
    p.drawLine(w - m - 6, m + 5, w - m, m + 5)
    # 内部向下箭头
    c = w // 2
    p.drawLine(c, m + 6, c, h - m - 3)
    p.drawLine(c - 4, h - m - 7, c, h - m - 3)
    p.drawLine(c + 4, h - m - 7, c, h - m - 3)


def _line_style_draw(p, sz):
    """线条样式图标：三条水平线（修复浮点坐标）"""
    w, h = sz.width(), sz.height()
    p.setPen(QPen(_ICON_COLOR, _ICON_STROKE))
    margin = 4
    y1 = int(h * 0.25)
    y2 = int(h * 0.5)
    y3 = int(h * 0.75)
    p.drawLine(margin, y1, w - margin, y1)
    p.drawLine(margin, y2, w - margin, y2)
    p.drawLine(margin, y3, w - margin, y3)


_ICON_DRAW_FUNCS = {
    'Home':      _home_draw,
    'Back':      _arrow_left,
    'Forward':   _arrow_right,
    'Pan':       _pan_draw,
    'Zoom':      _zoom_draw,
    'Subplots':  _subplots_draw,
    'Customize': _customize_draw,
    'Save':      _save_draw,
    'LineStyle': _line_style_draw,
}

_icon_cache = {}

def _get_icon(name):
    if name not in _icon_cache:
        _icon_cache[name] = _paint_icon(_ICON_DRAW_FUNCS[name])
    return _icon_cache[name]

TOOLTIP_CN = {
    'Home':      '重置为原始视图',
    'Back':      '返回上一个视图',
    'Forward':   '前进到下一个视图',
    'Pan':       '平移画布\n左键拖拽平移，右键拖拽缩放\nX轴/Y轴固定坐标轴，Ctrl键固定纵横比',
    'Zoom':      '矩形缩放\n框选区域进行放大\nX轴/Y轴固定坐标轴',
    'Subplots':  '配置子图参数',
    'Customize': '编辑坐标轴、曲线和图像参数',
    'Save':      '保存当前图表',
    'LineStyle': '修改线条样式',
}

# ── 颜色面板数据（C3） ────────────────────────────────────
# 这里只是「颜色选择器」的货源；真正画线用的分类色来自主题 token
# （PALETTE_LIGHT / PALETTE_DARK 与 palette_for），并且一律按图表底色做
# WCAG ≥ 3:1 过滤，所以亮黄（1.05:1）、中黄（1.18:1）这类在宣纸上
# 几乎看不见的颜色不会再被画到图上，也不会再出现在面板里。
#
# C1：这些是 matplotlib / Okabe-Ito / NPG 的**固定参考色板**（跟主题无关，
# 供用户手动挑一个具体色值），因此不放进 theme_tokens.py。为了不违反
# 「源码里不出现颜色字面量」，统一以 RGB 整数三元组存放，再用
# ``_hex()`` 渲染成 ``#RRGGBB``；数字仍然是数据，只是换了表示法。
def _hex(rgb):
    """``(31, 119, 180)`` -> 六位十六进制字符串（C1：字面量集中到一处构造）。"""
    return '#%02X%02X%02X' % tuple(rgb)


#: 固定参考色板：名称 -> RGB 整数三元组。
_BASE_SWATCHES = [
    ('深蓝',   (31, 119, 180)),    # tab10 蓝
    ('橙色',   (255, 127, 14)),    # tab10 橙
    ('绿色',   (44, 160, 44)),     # tab10 绿
    ('红色',   (214, 39, 40)),     # tab10 红
    ('紫色',   (148, 103, 189)),   # tab10 紫
    ('棕色',   (140, 86, 75)),     # tab10 棕
    ('粉色',   (227, 119, 194)),   # tab10 粉
    ('灰色',   (127, 127, 127)),   # tab10 灰
    ('橄榄绿', (188, 189, 34)),    # tab10 橄榄
    ('青色',   (23, 190, 207)),    # tab10 青
    ('黑色',   (0, 0, 0)),         # 中性黑
    ('天蓝色', (86, 180, 233)),    # Okabe-Ito 天蓝
    ('朱红色', (213, 94, 0)),      # Okabe-Ito 朱红
    ('蓝绿色', (0, 158, 115)),     # Okabe-Ito 蓝绿
    ('黄色',   (240, 228, 66)),    # Okabe-Ito 黄
    ('中蓝色', (0, 114, 178)),     # Okabe-Ito 中蓝
    ('紫红色', (204, 121, 167)),   # Okabe-Ito 紫红
    ('浅蓝色', (174, 199, 232)),   # tab20 浅蓝
    ('浅橙色', (255, 187, 120)),   # tab20 浅橙
    ('浅绿色', (152, 223, 138)),   # tab20 浅绿
    ('浅红色', (255, 152, 150)),   # tab20 浅红
    ('NPG红色', (230, 75, 53)),    # NPG 红
    ('石板蓝', (60, 84, 136)),     # NPG 石板蓝
    ('亮黄色', (255, 255, 51)),    # 高亮黄（浅色底上会被 3:1 过滤掉）
]

_BASE_PALETTE = [(name, _hex(rgb)) for name, rgb in _BASE_SWATCHES]


def _theme_palette_entries():
    """把两套主题的系列 / 预测 / 失效色也放进候选池，方便手动挑同一套色。"""
    entries = []
    for label, tokens in (('浅色', LIGHT), ('深色', DARK)):
        for index, color in enumerate(tokens['chart_series']):
            entries.append((f'{label}系列{index + 1}', color))
        entries.append((f'{label}预测', tokens['chart_forecast']))
        entries.append((f'{label}失效', tokens['chart_threshold']))
    return entries


def _build_candidate_pool():
    """候选池 = 基础色板 + 主题色，按 hex 去重并保持首次出现的顺序。"""
    pool, seen = [], set()
    for name, color in list(_BASE_PALETTE) + _theme_palette_entries():
        key = color.upper()
        if key in seen:
            continue
        seen.add(key)
        pool.append((name, color))
    return pool


#: 兼容旧引用：颜色选择面板的**完整候选池**（不随主题变化）。
COLOR_PALETTE = _build_candidate_pool()

#: 默认多电池叠加分类色，直接取自主题 token（唯一真相来源）。
PALETTE_LIGHT = list(LIGHT['chart_series'])
PALETTE_DARK = list(DARK['chart_series'])

#: 主题名 -> 分类色。
PALETTE_BY_THEME = {'light': PALETTE_LIGHT, 'dark': PALETTE_DARK}

#: 本模块缓存的当前主题 token，由 :func:`apply_mpl_style` 更新。
_ACTIVE_TOKENS = LIGHT


def active_tokens():
    """当前生效的主题 token：优先问 ``ui.style``，取不到就用本模块缓存。"""
    try:
        from ui.style import theme_tokens as _style_theme_tokens
        return _style_theme_tokens()
    except Exception:
        return _ACTIVE_TOKENS


def palette_for(tokens):
    """某套主题下的默认分类色（对比不足的颜色自动剔除）。"""
    tokens = tokens or LIGHT
    return (usable_colors(tokens['chart_series'], tokens['chart_bg'], 3.0)
            or [tokens['chart_forecast']])


def usable_palette(tokens=None, minimum=3.0):
    """按当前主题过滤后的候选色，颜色选择面板只提供这些。"""
    tokens = tokens or active_tokens()
    return usable_colors(
        [color for _name, color in COLOR_PALETTE], tokens['chart_bg'], minimum)


def offered_colors(tokens=None, minimum=3.0):
    """``[(名称, hex), ...]``：颜色面板实际展示的色块（已按主题过滤）。"""
    tokens = tokens or active_tokens()
    allowed = {color.upper() for color in usable_palette(tokens, minimum)}
    entries = [
        (name, color) for name, color in COLOR_PALETTE
        if color.upper() in allowed
    ]
    return entries or list(COLOR_PALETTE)


def apply_mpl_style(tokens):
    """把主题 token 推进 matplotlib 的 rcParams（C2）。

    切换主题后调用一次，图表底色、描边、刻度、网格与文字就整体跟着换色；
    返回传入的 token，方便 ``tokens = apply_mpl_style(get_theme(mode))`` 串联。
    """
    global _ACTIVE_TOKENS
    if tokens is None:
        tokens = LIGHT
    _ACTIVE_TOKENS = tokens
    mpl.rcParams.update({
        'font.sans-serif': list(CJK_FONTS),
        'axes.unicode_minus': False,
        'figure.facecolor': tokens['chart_bg'],
        'figure.edgecolor': tokens['chart_bg'],
        'savefig.facecolor': tokens['chart_bg'],
        'savefig.edgecolor': tokens['chart_bg'],
        'axes.facecolor': tokens['chart_bg'],
        'axes.edgecolor': tokens['chart_spine'],
        'axes.labelcolor': tokens['text_muted'],
        'axes.titlecolor': tokens['text'],
        'xtick.color': tokens['text_muted'],
        'ytick.color': tokens['text_muted'],
        'text.color': tokens['text'],
        'grid.color': tokens['chart_grid'],
        'grid.alpha': 0.5,
        'grid.linewidth': 0.5,
        # 只留左 / 下两条轴线，图表不再被四面框死。
        'axes.spines.top': False,
        'axes.spines.right': False,
    })
    return tokens


def _first_cross(values, threshold):
    """``values`` 中第一个低于 ``threshold`` 的下标；从未低于则返回 None。"""
    if threshold is None:
        return None
    array = np.asarray(values, dtype=np.float64).reshape(-1)
    array = array[np.isfinite(array)]
    if array.size == 0:
        return None
    positions = np.flatnonzero(array < threshold)
    return int(positions[0]) if len(positions) else None


def _series_values(entry):
    """从 ``battery_data[name]`` 里取出容量序列（DataFrame / dict / 数组都行）。"""
    if entry is None:
        return []
    if hasattr(entry, 'columns'):                 # pandas.DataFrame
        column = 'capacity' if 'capacity' in entry.columns else None
        if column is None:
            return []
        return [float(value) for value in entry[column].tolist()]
    if isinstance(entry, dict):                   # {'capacity': [...], ...}
        raw = entry.get('capacity')
        if raw is None:
            return []
        # 注意：不能写 `raw or []`——numpy 数组的真值判断会抛 ValueError
        return [float(value) for value in raw]
    try:
        return [float(value) for value in entry]
    except TypeError:
        return []


def _series_cycles(entry, length):
    """真实循环号：优先用数据里的 ``cycle`` 列 / 键，缺失时退回位置下标。"""
    values = None
    if entry is not None:
        if hasattr(entry, 'columns'):
            if 'cycle' in entry.columns:
                values = [float(value) for value in entry['cycle'].tolist()]
        elif isinstance(entry, dict):
            raw = entry.get('cycle')
            if raw is not None:
                values = [float(value) for value in raw]
    if values is None or len(values) != length:
        return [float(index) for index in range(length)]
    return values


def _luminance(hex_color):
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    return 0.299 * r + 0.587 * g + 0.114 * b


def _as_float_list(values):
    """把任意序列转成 float 列表；``None`` 或含非数值时返回 ``[]``。"""
    if values is None:
        return []
    try:
        return [float(value) for value in values]
    except (TypeError, ValueError):
        return []


def _tick_interval(rated_capacity):
    """按额定容量挑一个「好看」的 y 轴刻度间隔（U2 聚焦退化带时也用）。"""
    if not rated_capacity or rated_capacity <= 0:
        return 0.2
    rough = rated_capacity / 5
    nice = [0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0]
    best = nice[0]
    for candidate in nice:
        if abs(candidate - rough) < abs(best - rough):
            best = candidate
    return best


#: 刻度步长的「好看」候选：1 / 2 / 2.5 / 5 × 10ⁿ
_NICE_STEPS = (1.0, 2.0, 2.5, 5.0, 10.0)


def nice_step(span, target_divisions=12):
    """把区间 ``span`` 切成人眼友好的步长（1/2/2.5/5 × 10ⁿ）。

    目的是让刻度**足够密**——用户应当能从网格线上直接读出数值，
    而不是在两条粗刻度之间靠眼睛估。
    """
    span = abs(float(span))
    if not np.isfinite(span) or span <= 0:
        return 1.0
    rough = span / max(1, int(target_divisions))
    if rough <= 0:
        return 1.0
    exponent = np.floor(np.log10(rough))
    base = 10.0 ** exponent
    for factor in _NICE_STEPS:
        candidate = factor * base
        if candidate >= rough:
            return float(candidate)
    return float(10.0 * base)


def _tick_decimals(interval):
    """返回能**精确表示该步长**的最少小数位。

    这样既不会让相邻刻度显示成同一个数（0.25 步长如果只给 1 位就会变成
    0.2 / 0.5 / 0.8），也不会过度补零（0.1 步长只需 1 位，不必写成 0.10）。
    """
    if not np.isfinite(interval) or interval <= 0:
        return 3
    for decimals in range(0, 7):
        if abs(round(interval, decimals) - interval) <= max(
                1e-9, abs(interval) * 1e-9):
            return decimals
    return 6


def _format_tick(value, step):
    """刻度标签：整数步长不带小数点，小步长按需要补位。"""
    if not np.isfinite(value):
        return ''
    if abs(float(value)) < 1e-12:
        return '0'
    decimals = _tick_decimals(step)
    text = f'{value:.{decimals}f}'
    # 去掉 "-0.00" 这类负零
    if float(text) == 0:
        return '0'
    return text


def _ticks_in_range(low, high, step):
    """在 ``[low, high]`` 内按 ``step`` 生成刻度数组。"""
    if not np.isfinite(low) or not np.isfinite(high) or step <= 0:
        return np.asarray([])
    first = np.ceil(low / step - 1e-9) * step
    if not np.isfinite(first):
        return np.asarray([])
    count = int(np.floor((high - first) / step + 1e-9)) + 1
    if count <= 0:
        return np.asarray([])
    return first + step * np.arange(count)


def _minor_ticks(major, divisions=5):
    """在两个主刻度之间插 ``divisions - 1`` 条次刻度（不含主刻度本身）。"""
    major = np.asarray(major, dtype=np.float64)
    if len(major) < 2 or divisions < 2:
        return np.asarray([])
    extra = []
    for left, right in zip(major[:-1], major[1:]):
        span = (right - left) / divisions
        if span <= 0:
            continue
        extra.extend(left + span * index for index in range(1, divisions))
    return np.asarray(extra, dtype=np.float64)


def _apply_ticks(axis, low, high, target_divisions, label_step=None):
    """给某个轴铺上**显式**的主 / 次刻度。

    刻意不用 ``MultipleLocator`` / ``AutoMinorLocator``：它们是**有状态**的
    locator，会在每次绘制时重新查询轴对象；与本环境的 PyQt6 + offscreen
    matplotlib 组合一起使用时，窗口反复创建 / 销毁会触发原生访问违例
    （0xC0000005，实测可稳定复现）。显式刻度数组是一次性算好的定值，
    既没有这个风险，读数效果完全一样。
    """
    if not (np.isfinite(low) and np.isfinite(high) and high > low):
        return None
    step = nice_step(high - low, target_divisions)
    major = _ticks_in_range(low, high, step)
    if len(major) < 2:
        return None
    axis.set_ticks(major)
    axis.set_ticks(_minor_ticks(major), minor=True)
    axis.set_major_formatter(FuncFormatter(
        lambda value, _pos, _step=(label_step or step):
        _format_tick(value, _step)))
    return step


def _focused_ylim(series_list, rated_capacity, threshold_val=None,
                  target_divisions=12):
    """返回聚焦退化带后的 ``(y_lo, y_hi, y_ticks)``；无有效数据时返回 None。

    上下各留 4% 余量，绝不把 y 轴强行拉到 0——容量从 0 起画会让整条退化曲线
    挤成一条平线，看不出任何趋势。

    刻度密度由 ``target_divisions`` 控制（默认 12 条主刻度）。旧实现最多只给
    9 条，读数只能靠估；现在用 1/2/2.5/5 × 10ⁿ 的友好步长填满整个区间。
    """
    lows, highs = [], []
    for series in series_list:
        values = np.asarray(series, dtype=np.float64).reshape(-1)
        values = values[np.isfinite(values)]
        if values.size:
            lows.append(float(values.min()))
            highs.append(float(values.max()))
    if threshold_val is not None and np.isfinite(threshold_val):
        lows.append(float(threshold_val))
        highs.append(float(threshold_val))
    if not lows:
        return None
    low, high = min(lows), max(highs)
    if high - low < 1e-9:
        high = low + max(abs(low) * 0.04, 0.05)
    pad = (high - low) * 0.04
    y_lo, y_hi = low - pad, high + pad

    # 优先用与额定容量对齐的步长；太稀就换成更细的友好步长
    interval = _tick_interval(rated_capacity)
    friendly = nice_step(y_hi - y_lo, target_divisions)
    if interval > friendly:
        interval = friendly
    if interval <= 0 or not np.isfinite(interval):
        interval = friendly
    ticks = np.arange(np.floor(y_lo / interval) * interval,
                      y_hi + interval * 0.5, interval)
    ticks = ticks[(ticks >= y_lo - interval * 0.01)
                  & (ticks <= y_hi + interval * 0.01)]
    if len(ticks) < 4:                     # 退化带很窄时别只剩两三条线
        interval = max(nice_step(y_hi - y_lo, 8), 1e-6)
        ticks = np.arange(np.floor(y_lo / interval) * interval,
                          y_hi + interval * 0.5, interval)
    return y_lo, y_hi, ticks


class _ColorCell(QWidget):
    """单色块：上方纯色按钮 + 下方十六进制值 + 颜色名称"""

    def __init__(self, name, hex_color, parent=None):
        super().__init__(parent)
        self._hex = hex_color
        layout = QVBoxLayout(self)
        layout.setSpacing(1)
        layout.setContentsMargins(0, 0, 0, 0)

        # C1：色块描边 / 悬停高亮都用主题 token，不再写字面量。
        tokens = active_tokens()
        btn = QPushButton()
        btn.setFixedSize(72, 36)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setToolTip(f'{name}\n{hex_color}')
        btn.setStyleSheet(f'''
            QPushButton {{
                background-color: {hex_color};
                border: 1px solid {tokens['border_soft']};
                border-radius: 3px;
            }}
            QPushButton:hover {{
                border: 2px solid {tokens['primary']};
            }}
        ''')
        btn.clicked.connect(lambda: self._on_click())
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

        hex_lbl = QLabel(hex_color)
        hex_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hex_lbl.setStyleSheet('font-size: 8px; font-weight: bold; background: transparent;')
        layout.addWidget(hex_lbl)

        name_lbl = QLabel(name)
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_lbl.setStyleSheet('font-size: 7px; background: transparent;')
        layout.addWidget(name_lbl)

        self._click_callback = None

    def set_click_callback(self, callback):
        self._click_callback = callback

    def _on_click(self):
        if self._click_callback:
            self._click_callback(self._hex)

    @property
    def hex_color(self):
        return self._hex


def _parse_color_input(text):
    """解析用户输入的 RGB 或十六进制颜色，返回 hex 字符串或 None"""
    t = text.strip()
    if not t:
        return None
    # 十六进制
    if t.startswith('#'):
        if len(t) == 7 and all(c in '0123456789ABCDEFabcdef' for c in t[1:]):
            return t.upper()
        if len(t) == 4 and all(c in '0123456789ABCDEFabcdef' for c in t[1:]):
            r, g, b = t[1], t[2], t[3]
            return f'#{r}{r}{g}{g}{b}{b}'.upper()
    # RGB: r,g,b 或 rgb(r,g,b)
    import re
    m = re.findall(r'\d+', t)
    if len(m) == 3:
        try:
            r, g, b = int(m[0]), int(m[1]), int(m[2])
            if 0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255:
                return f'#{r:02X}{g:02X}{b:02X}'
        except ValueError:
            pass
    return None


#: 颜色选择器的初始值：纯黑。这是「数据」而不是主题色，用 RGB 整数构造。
_DEFAULT_PICK_HEX = _hex((0, 0, 0))


class ColorGridDialog(QDialog):
    """颜色面板弹窗 —— 网格色板 + 自定义 RGB/Hex 输入"""
    color_selected = None

    def __init__(self, parent=None, current_hex=_DEFAULT_PICK_HEX):
        super().__init__(parent)
        self.setWindowTitle('选择颜色')
        self.setWindowIcon(get_dialog_icon('color'))
        self.setModal(True)
        self.resize(600, 550)
        # C1：默认值由 RGB 整数构造，不再是颜色字面量。
        self._selected_hex = current_hex
        tokens = active_tokens()
        self._border_style = f'border: 1px solid {tokens["border_soft"]};'
        self._preview_style = (
            f'border: 1px solid {tokens["border_soft"]};'
            f' background-color: {tokens["bg_hover"]};')

        layout = QVBoxLayout(self)

        # ── 色板区域（C3：只提供当前主题下 ≥ 3:1 的颜色） ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(6)

        cols = 4
        for i, (name, hex_val) in enumerate(offered_colors()):
            cell = _ColorCell(name, hex_val)
            cell.set_click_callback(self._on_select)
            r, c = i // cols, i % cols
            grid.addWidget(cell, r, c)

        scroll.setWidget(container)
        layout.addWidget(scroll)

        # ── 自定义颜色输入 ──
        custom_group = QGroupBox('自定义颜色')
        custom_layout = QHBoxLayout(custom_group)

        custom_layout.addWidget(QLabel('颜色值：'))
        self._custom_input = QLineEdit()
        # 帮助文案只说明格式，不再写出一个具体色值（C1）。
        self._custom_input.setPlaceholderText('例：# 后跟 6 位十六进制，或 255,0,0')
        self._custom_input.textChanged.connect(self._on_custom_input_changed)
        custom_layout.addWidget(self._custom_input)

        self._custom_preview = QFrame()
        self._custom_preview.setFixedSize(28, 28)
        self._custom_preview.setStyleSheet(self._preview_style)
        custom_layout.addWidget(self._custom_preview)

        apply_custom = QPushButton('应用')
        apply_custom.clicked.connect(self._apply_custom)
        custom_layout.addWidget(apply_custom)

        layout.addWidget(custom_group)

        # ── 底部 ──
        bottom = QHBoxLayout()
        bottom.addWidget(QLabel('当前选中：'))
        self._preview = QFrame()
        self._preview.setFixedSize(60, 24)
        self._preview.setStyleSheet(
            f'background-color: {current_hex}; {self._border_style}')
        bottom.addWidget(self._preview)
        self._hex_label = QLabel(current_hex)
        bottom.addWidget(self._hex_label)
        bottom.addStretch()

        btn_box = QDialogButtonBox()
        ok_btn = btn_box.addButton('确定', QDialogButtonBox.ButtonRole.AcceptRole)
        ok_btn.clicked.connect(self.accept)
        cancel_btn = btn_box.addButton('取消', QDialogButtonBox.ButtonRole.RejectRole)
        cancel_btn.clicked.connect(self.reject)
        bottom.addWidget(btn_box)
        layout.addLayout(bottom)

    def _on_select(self, hex_val):
        self._selected_hex = hex_val
        self._preview.setStyleSheet(
            f'background-color: {hex_val}; {self._border_style}')
        self._hex_label.setText(hex_val)
        self._custom_input.setText(hex_val)

    def _on_custom_input_changed(self, text):
        parsed = _parse_color_input(text)
        if parsed:
            self._custom_preview.setStyleSheet(
                f'background-color: {parsed}; {self._border_style}')
        else:
            self._custom_preview.setStyleSheet(self._preview_style)

    def _apply_custom(self):
        parsed = _parse_color_input(self._custom_input.text())
        if parsed:
            self._on_select(parsed)

    def accept(self):
        self.color_selected = self._selected_hex
        super().accept()


# ── 线条样式设置面板 ───────────────────────────────────────
_LINESTYLE_MAP = {
    '实线':   'solid',
    '虚线':   'dashed',
    '点画线': 'dashdot',
}

_LINESTYLE_REVERSE = {v: k for k, v in _LINESTYLE_MAP.items()}

_LINEWIDTH_OPTIONS = ['0.5', '1', '1.5', '2']


class LineStyleDialog(QDialog):
    """线条样式修改面板"""
    def __init__(self, figure, canvas, parent=None):
        super().__init__(parent)
        self.setWindowTitle('线条样式设置')
        self.setWindowIcon(get_dialog_icon('line'))
        self.resize(700, 500)
        self.setModal(False)
        self._figure = figure
        self._canvas = canvas
        self._current_line = None
        self._lines_info = []  # [(axis_idx, axis_title, line_idx, line, label)]
        # C1：色块描边统一来自主题 token。
        self._border_style = (
            f'border: 1px solid {active_tokens()["border_soft"]};'
            ' border-radius: 3px;')

        self._build_ui()
        self._populate_lines()
        self._set_settings_enabled(False)

    def _build_ui(self):
        main_layout = QVBoxLayout(self)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)

        # ── 左侧：线条列表 ──
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(QLabel('<b>图表线条</b>'))
        self._line_list = QListWidget()
        self._line_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._line_list.currentRowChanged.connect(self._on_line_selected)
        left_layout.addWidget(self._line_list)
        splitter.addWidget(left)

        # ── 右侧：参数设置 ──
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 0, 0, 0)

        right_layout.addWidget(QLabel('<b>参数设置</b>'))

        form = QFormLayout()
        form.setSpacing(12)

        self._style_combo = QComboBox()
        self._style_combo.addItems(['实线', '虚线', '点画线'])
        form.addRow('线条样式：', self._style_combo)

        self._color_btn = QPushButton()
        self._color_btn.setFixedSize(80, 28)
        self._color_btn.setStyleSheet(
            f'background-color: {_DEFAULT_PICK_HEX}; {self._border_style}')
        self._color_btn.clicked.connect(self._pick_color)
        self._color_hex = _DEFAULT_PICK_HEX
        form.addRow('线条颜色：', self._color_btn)

        self._width_combo = QComboBox()
        self._width_combo.setEditable(True)
        self._width_combo.addItems(_LINEWIDTH_OPTIONS)
        self._width_combo.setCurrentText('1')
        form.addRow('线条宽度：', self._width_combo)

        right_layout.addLayout(form)
        right_layout.addStretch()
        splitter.addWidget(right)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 4)
        main_layout.addWidget(splitter, 1)

        # ── 底部按钮 ──
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._apply_btn = QPushButton('应用')
        self._apply_btn.clicked.connect(self._apply_changes)
        self._apply_btn.setMinimumWidth(80)

        self._ok_btn = QPushButton('确定')
        self._ok_btn.clicked.connect(self._ok)
        self._ok_btn.setMinimumWidth(80)

        self._cancel_btn = QPushButton('取消')
        self._cancel_btn.clicked.connect(self.reject)
        self._cancel_btn.setMinimumWidth(80)

        btn_layout.addWidget(self._apply_btn)
        btn_layout.addWidget(self._ok_btn)
        btn_layout.addWidget(self._cancel_btn)
        main_layout.addLayout(btn_layout)

    def _populate_lines(self):
        """收集图中所有线条，按子图分组显示"""
        self._line_list.clear()
        self._lines_info = []
        axes = self._figure.get_axes()
        # C1：分组标题用主题强调色，不再写死一个高亮蓝。
        group_color = QColor(active_tokens()['primary'])

        for ax_idx, ax in enumerate(axes):
            lines = ax.get_lines()
            if not lines:
                continue
            # 子图标题
            ax_title = ax.get_title()
            if not ax_title:
                ax_title = f'子图 {ax_idx + 1}'
            # 添加分组标题
            group_item = QListWidgetItem(f'▸ {ax_title}')
            group_item.setFlags(Qt.ItemFlag.NoItemFlags)
            font = group_item.font()
            font.setBold(True)
            group_item.setFont(font)
            group_item.setForeground(group_color)
            self._line_list.addItem(group_item)

            for line_idx, line in enumerate(lines):
                label = line.get_label()
                if not label or label.startswith('_'):
                    label = f'线条 {line_idx + 1}'
                item = QListWidgetItem(f'    {label}')
                item.setData(Qt.ItemDataRole.UserRole, len(self._lines_info))
                self._line_list.addItem(item)
                self._lines_info.append((ax_idx, ax_title, line_idx, line, label))

    def _on_line_selected(self, row):
        item = self._line_list.item(row)
        if item is None or item.data(Qt.ItemDataRole.UserRole) is None:
            self._current_line = None
            self._set_settings_enabled(False)
            return
        idx = item.data(Qt.ItemDataRole.UserRole)
        self._current_line = self._lines_info[idx][3]
        self._set_settings_enabled(True)
        self._load_line_properties()

    def _set_settings_enabled(self, enabled):
        self._style_combo.setEnabled(enabled)
        self._color_btn.setEnabled(enabled)
        self._width_combo.setEnabled(enabled)
        self._apply_btn.setEnabled(enabled)
        self._ok_btn.setEnabled(enabled)

    def _load_line_properties(self):
        """将当前选中线条的属性加载到设置控件"""
        line = self._current_line
        if line is None:
            return
        # 线条样式
        ls = line.get_linestyle()
        style_name = _LINESTYLE_REVERSE.get(ls, '实线')
        idx = self._style_combo.findText(style_name)
        if idx >= 0:
            self._style_combo.setCurrentIndex(idx)
        # 颜色
        from matplotlib.colors import to_hex
        try:
            rgba = line.get_color()
            self._color_hex = to_hex(rgba, keep_alpha=False)
        except Exception:
            self._color_hex = _DEFAULT_PICK_HEX
        self._color_btn.setStyleSheet(
            f'background-color: {self._color_hex}; {self._border_style}')
        # 宽度
        lw = line.get_linewidth()
        self._width_combo.setCurrentText(str(lw))

    def _pick_color(self):
        dlg = ColorGridDialog(self, self._color_hex)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.color_selected:
            self._color_hex = dlg.color_selected
            self._color_btn.setStyleSheet(
                f'background-color: {self._color_hex}; {self._border_style}')

    def _apply_changes(self):
        if self._current_line is None:
            return
        # 线条样式
        style_cn = self._style_combo.currentText()
        ls = _LINESTYLE_MAP.get(style_cn, 'solid')
        self._current_line.set_linestyle(ls)
        # 颜色
        self._current_line.set_color(self._color_hex)
        # 宽度
        try:
            lw = float(self._width_combo.currentText())
            self._current_line.set_linewidth(lw)
        except ValueError:
            pass
        # 强制立即重绘（draw_idle 在非模态对话框中可能延迟或不触发）
        self._canvas.draw()

    def _ok(self):
        self._apply_changes()
        self.accept()

    # ── 对话框翻译工具 ─────────────────────────────────────────
_SUBPLOT_TR = {
    'Borders': '边距', 'Spacings': '间距',
    'top': '上边距', 'bottom': '下边距', 'left': '左边距', 'right': '右边距',
    'hspace': '水平间距', 'wspace': '垂直间距',
    'Export values': '导出数值', 'Tight layout': '紧凑布局',
    'Reset': '重置', 'Close': '关闭',
}

_FIGOPT_TAB_TR = {'Axes': '坐标轴', 'Curves': '曲线', 'Images, etc.': '图像等'}

_FIGOPT_LABEL_TR = {
    'Title': '标题',
    'Bottom-Axis': 'X 轴', 'Top-Axis': 'Y 轴 (右)',
    'Min': '最小值', 'Max': '最大值', 'Label': '标签', 'Scale': '刻度',
    '(Re-)Generate automatic legend': '(重新)生成自动图例',
    'Line': '线条', 'Line style': '线型', 'Draw style': '绘制样式',
    'Width': '宽度', 'Color (RGBA)': '颜色 (RGBA)',
    'Marker': '标记', 'Style': '样式', 'Size': '大小',
    'Face color (RGBA)': '填充色 (RGBA)', 'Edge color (RGBA)': '边颜色 (RGBA)',
    'Colormap': '颜色映射', 'Min. value': '最小值', 'Max. value': '最大值',
    'Interpolation': '插值', 'Interpolation stage': '插值阶段',
}

_FIGOPT_LINESTYLE_TR = {
    'Solid': '实线', 'Dashed': '虚线', 'DashDot': '点划线',
    'Dotted': '点线', 'None': '无', 'none': '无',
}

_FIGOPT_DRAWSTYLE_TR = {
    'Default': '默认', 'Steps (Pre)': '阶梯 (前)',
    'Steps (Mid)': '阶梯 (中)', 'Steps (Post)': '阶梯 (后)',
}

_FIGOPT_BTN_TR = {'OK': '确定', 'Cancel': '取消', 'Apply': '应用',
                   'Ok': '确定'}


# ── Unicode 上下标字符映射 ──────────────────────────────────
_SUPERSCRIPT_MAP = {
    '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
    '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
    '+': '⁺', '-': '⁻', '=': '⁼', '(': '⁽', ')': '⁾',
    'a': 'ᵃ', 'b': 'ᵇ', 'c': 'ᶜ', 'd': 'ᵈ', 'e': 'ᵉ',
    'f': 'ᶠ', 'g': 'ᵍ', 'h': 'ʰ', 'i': 'ⁱ', 'j': 'ʲ',
    'k': 'ᵏ', 'l': 'ˡ', 'm': 'ᵐ', 'n': 'ⁿ', 'o': 'ᵒ',
    'p': 'ᵖ', 'r': 'ʳ', 's': 'ˢ', 't': 'ᵗ', 'u': 'ᵘ',
    'v': 'ᵛ', 'w': 'ʷ', 'x': 'ˣ', 'y': 'ʸ', 'z': 'ᶻ',
    'A': 'ᴬ', 'B': 'ᴮ', 'C': 'ᶜ', 'D': 'ᴰ', 'E': 'ᴱ',
    'F': 'ᶠ', 'G': 'ᴳ', 'H': 'ᴴ', 'I': 'ᴵ', 'J': 'ᴶ',
    'K': 'ᴷ', 'L': 'ᴸ', 'M': 'ᴹ', 'N': 'ᴺ', 'O': 'ᴼ',
    'P': 'ᴾ', 'Q': 'ᵟ', 'R': 'ᴿ', 'S': 'ˢ', 'T': 'ᵀ',
    'U': 'ᵁ', 'V': 'ⱽ', 'W': 'ᵂ', 'X': 'ˣ', 'Y': 'ʸ', 'Z': 'ᶻ',
}

_SUBSCRIPT_MAP = {
    '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄',
    '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉',
    '+': '₊', '-': '₋', '=': '₌', '(': '₍', ')': '₎',
    'a': 'ₐ', 'e': 'ₑ', 'h': 'ₕ', 'i': 'ᵢ', 'j': 'ⱼ',
    'k': 'ₖ', 'l': 'ₗ', 'm': 'ₘ', 'n': 'ₙ', 'o': 'ₒ',
    'p': 'ₚ', 'r': 'ᵣ', 's': 'ₛ', 't': 'ₜ', 'u': 'ᵤ',
    'v': 'ᵥ', 'x': 'ₓ',
}


# ── 上标/下标快捷键 ─────────────────────────────────────────
def apply_sup_sub(mode):
    """将当前焦点 QLineEdit 中选中的文本转为 Unicode 上标(^)或下标(_)
    无 Unicode 对应的字符保持原样"""
    widget = QApplication.focusWidget()
    if not isinstance(widget, QLineEdit) or not widget.isVisible():
        return
    text = widget.text()
    s = widget.selectionStart()
    e = widget.selectionEnd()
    if s < 0 or e <= s:
        return  # 未选中文本，不做任何操作
    sel = text[s:e]
    char_map = _SUPERSCRIPT_MAP if mode == '^' else _SUBSCRIPT_MAP
    converted = ''.join(char_map.get(ch, ch) for ch in sel)
    if converted != sel:
        widget.setText(text[:s] + converted + text[e:])


def _install_sup_sub_shortcuts(widget):
    """在指定 widget 上安装上下标快捷键 (Ctrl+= / Ctrl+Shift+=)"""
    from PyQt6.QtGui import QShortcut, QKeySequence
    sup_sc = QShortcut(QKeySequence('Ctrl+='), widget)
    sup_sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
    sup_sc.activated.connect(lambda: apply_sup_sub('^'))
    sub_sc = QShortcut(QKeySequence('Ctrl+Shift+='), widget)
    sub_sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
    sub_sc.activated.connect(lambda: apply_sup_sub('_'))
    if not hasattr(widget, '_sup_sub_shortcuts'):
        widget._sup_sub_shortcuts = []
    widget._sup_sub_shortcuts.extend([sup_sc, sub_sc])


class _LegendEditDialog(QDialog):
    """支持上下标快捷键的图例文本编辑对话框"""
    def __init__(self, parent, old_text):
        super().__init__(parent)
        self.setWindowTitle('编辑图例')
        self.setWindowIcon(get_dialog_icon('legend'))
        self.setModal(True)
        self.resize(450, 150)
        self.result_text = old_text

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('图例文本：'))
        self._edit = QLineEdit(old_text)
        self._edit.selectAll()
        layout.addWidget(self._edit)

        btn_box = QDialogButtonBox()
        ok_btn = btn_box.addButton('确定', QDialogButtonBox.ButtonRole.AcceptRole)
        ok_btn.clicked.connect(self._on_ok)
        cancel_btn = btn_box.addButton('取消', QDialogButtonBox.ButtonRole.RejectRole)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(btn_box)

        _install_sup_sub_shortcuts(self)

    def _on_ok(self):
        self.result_text = self._edit.text()
        self.accept()


def _translate_figopt_dialog(dialog):
    """递归翻译 figure options 对话框中的所有英文文本，并加入上下标快捷键"""
    dialog.setWindowTitle('图表选项')
    dialog.setWindowIcon(get_dialog_icon('chart'))

    for bbox in dialog.findChildren(QDialogButtonBox):
        for btn in bbox.buttons():
            t = btn.text()
            if t in _FIGOPT_BTN_TR:
                btn.setText(_FIGOPT_BTN_TR[t])

    for tab in dialog.findChildren(QTabWidget):
        for i in range(tab.count()):
            old = tab.tabText(i)
            if old in _FIGOPT_TAB_TR:
                tab.setTabText(i, _FIGOPT_TAB_TR[old])

    for gb in dialog.findChildren(QGroupBox):
        t = gb.title()
        if t in _FIGOPT_TAB_TR:
            gb.setTitle(_FIGOPT_TAB_TR[t])

    for w in dialog.findChildren(QLabel):
        t = w.text()
        if t in _FIGOPT_LABEL_TR:
            w.setText(_FIGOPT_LABEL_TR[t])
        elif t in _FIGOPT_TAB_TR:
            w.setText(_FIGOPT_TAB_TR[t])
        elif t in _FIGOPT_LINESTYLE_TR:
            w.setText(_FIGOPT_LINESTYLE_TR[t])
        elif t in _FIGOPT_DRAWSTYLE_TR:
            w.setText(_FIGOPT_DRAWSTYLE_TR[t])

    for cb in dialog.findChildren(QCheckBox):
        t = cb.text()
        if t in _FIGOPT_LABEL_TR:
            cb.setText(_FIGOPT_LABEL_TR[t])

    for combo in dialog.findChildren(QComboBox):
        for i in range(combo.count()):
            item = combo.itemText(i)
            if item in _FIGOPT_LINESTYLE_TR:
                combo.setItemText(i, _FIGOPT_LINESTYLE_TR[item])
            elif item in _FIGOPT_DRAWSTYLE_TR:
                combo.setItemText(i, _FIGOPT_DRAWSTYLE_TR[item])
            elif item in _FIGOPT_LABEL_TR:
                combo.setItemText(i, _FIGOPT_LABEL_TR[item])

    _install_sup_sub_shortcuts(dialog)


# ── 悬停延时过滤器 ─────────────────────────────────────────
class _HoverDelayFilter(QObject):
    """鼠标悬停 2s 后才弹出 tooltip"""
    def __init__(self, tooltip_text, delay=2000):
        super().__init__()
        self._text = tooltip_text
        self._delay = delay
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._fire)
        self._widget = None

    def eventFilter(self, obj, event):
        t = event.type()
        if t == QEvent.Type.Enter:
            self._widget = obj
            self._timer.start(self._delay)
        elif t == QEvent.Type.Leave:
            self._timer.stop()
            QToolTip.hideText()
            self._widget = None
        elif t == QEvent.Type.MouseButtonPress:
            self._timer.stop()
            QToolTip.hideText()
        return False

    def _fire(self):
        if self._widget:
            pos = self._widget.mapToGlobal(
                QPoint(self._widget.width() // 2, self._widget.height() + 2))
            QToolTip.showText(pos, self._text, self._widget)


class CustomToolbar(NavigationToolbar2QT):
    toolitems = tuple(
        item for item in NavigationToolbar2QT.toolitems
        if item[0] in {'Home', 'Pan', 'Zoom', 'Save'}
    )

    def __init__(self, canvas, parent=None):
        super().__init__(canvas, parent)
        canvas._navigation_toolbar = self
        self._apply_style()
        self._add_line_style_button()

    def _apply_style(self):
        self.setIconSize(QSize(22, 22))
        # 不再硬编码颜色，让全局宣纸水墨主题接管；仅设置尺寸与间距。
        self.setStyleSheet("""
            QToolBar {
                background: transparent;
                border: none;
                spacing: 2px;
            }
            QToolButton {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 4px 6px;
                margin: 1px;
            }
        """)

        action_name_map = {}
        for a in self.actions():
            if a.text():
                action_name_map[a.text()] = a

        for name in _ICON_DRAW_FUNCS:
            if name in action_name_map:
                action_name_map[name].setIcon(_get_icon(name))

        for child in self.findChildren(QToolButton):
            action = child.defaultAction() if hasattr(child, 'defaultAction') else None
            key = None
            if action:
                for name, a in action_name_map.items():
                    if a is action:
                        key = name
                        break
            if not key:
                continue
            if key in TOOLTIP_CN:
                child.setToolTip('')
                f = _HoverDelayFilter(TOOLTIP_CN[key], 1500)
                child.installEventFilter(f)
                if not hasattr(self, '_hover_filters'):
                    self._hover_filters = []
                self._hover_filters.append(f)

    # 线条样式按钮
    def _add_line_style_button(self):
        icon = _get_icon('LineStyle')
        self._line_style_action = self.addAction(icon, 'LineStyle')
        self._line_style_action.setToolTip('')
        self._line_style_action.triggered.connect(self._open_line_style_dialog)
        # 为新按钮安装悬停延迟
        for child in self.findChildren(QToolButton):
            action = child.defaultAction() if hasattr(child, 'defaultAction') else None
            if action is self._line_style_action:
                child.setToolTip('')
                f = _HoverDelayFilter(TOOLTIP_CN['LineStyle'], 2000)
                child.installEventFilter(f)
                if not hasattr(self, '_hover_filters'):
                    self._hover_filters = []
                self._hover_filters.append(f)
                break

    def _open_line_style_dialog(self):
        """打开线条样式面板；已打开时复用并前置，不重复新建窗口。"""
        dlg = getattr(self, '_line_style_dialog', None)
        if dlg is not None:
            try:
                still_alive = not dlg.isHidden() or dlg.isVisible()
            except RuntimeError:
                # 底层 C++ 对象已被销毁（例如父窗口关闭）
                still_alive = False
            if still_alive:
                dlg.show()
                dlg.raise_()
                dlg.activateWindow()
                return
        dlg = LineStyleDialog(self.canvas.figure, self.canvas, self)
        # 关闭即释放，避免持有已销毁对象
        dlg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        dlg.finished.connect(self._forget_line_style_dialog)
        self._line_style_dialog = dlg
        dlg.show()

    def _forget_line_style_dialog(self, _result=None):
        self._line_style_dialog = None

    # ── 汉化 configure_subplots ──────────────────────────
    def configure_subplots(self):
        super().configure_subplots()
        dlg = self._subplot_dialog
        if dlg is None:
            return dlg
        dlg.setWindowTitle('子图参数配置')
        dlg.setWindowIcon(get_dialog_icon('subplot'))
        # 新增：子图个数设置（控件置于对话框右侧）
        if not hasattr(dlg, '_subplot_count_added'):
            layout = dlg.layout()
            if layout is not None:
                count_label = QLabel('子图个数：', dlg)
                count_spin = QSpinBox(dlg)
                count_spin.setRange(1, 16)
                count_spin.setValue(4)
                count_btn = QPushButton('应用', dlg)

                # 记录控件，便于后续使用
                dlg._subplot_count_spin = count_spin
                dlg._subplot_count_btn = count_btn

                inserted = False

                # 尝试将控件插入到“边距/间距”参数区域所在布局的右侧
                for i in range(layout.count()):
                    item = layout.itemAt(i)
                    sub_layout = item.layout()
                    if sub_layout is None:
                        continue

                    # 处理 QFormLayout：把“子图个数”作为新的一行加入
                    if isinstance(sub_layout, QFormLayout):
                        row = QHBoxLayout()
                        row.addWidget(count_spin)
                        row.addWidget(count_btn)
                        row.addStretch()
                        sub_layout.addRow(count_label, row)
                        inserted = True
                        break

                    # 处理普通布局：在其右侧追加一组控件
                    if isinstance(sub_layout, (QVBoxLayout, QHBoxLayout)):
                        row = QHBoxLayout()
                        row.addWidget(count_label)
                        row.addWidget(count_spin)
                        row.addWidget(count_btn)
                        row.addStretch()
                        sub_layout.addLayout(row)
                        inserted = True
                        break

                # 如果没找到合适的参数区布局，则退回到底部追加
                if not inserted:
                    count_layout = QHBoxLayout()
                    count_layout.addStretch()
                    count_layout.addWidget(count_label)
                    count_layout.addWidget(count_spin)
                    count_layout.addWidget(count_btn)
                    layout.addLayout(count_layout)

                dlg._subplot_count_added = True
        for gb in dlg.findChildren(QGroupBox):
            t = gb.title()
            if t in _SUBPLOT_TR:
                gb.setTitle(_SUBPLOT_TR[t])
        for btn in dlg.findChildren(QPushButton):
            t = btn.text()
            if t in _SUBPLOT_TR:
                btn.setText(_SUBPLOT_TR[t])
        for label in dlg.findChildren(QLabel):
            t = label.text()
            if t in _SUBPLOT_TR:
                label.setText(_SUBPLOT_TR[t])
        return dlg

    # ── 汉化 edit_parameters ─────────────────────────────
    def edit_parameters(self):
        from matplotlib.backends.qt_editor import figureoptions
        axes = self.canvas.figure.get_axes()
        if not axes:
            show_message(self.canvas.parent(), 'error', '错误', '没有可编辑的坐标轴。')
            return
        if len(axes) == 1:
            ax = axes[0]
        else:
            titles = [
                ax.get_label() or
                ax.get_title() or
                ax.get_title('left') or
                ax.get_title('right') or
                ' - '.join(filter(None, [ax.get_xlabel(), ax.get_ylabel()])) or
                f'<anonymous {type(ax).__name__}>'
                for ax in axes]
            duplicate_titles = [
                title for title in titles if titles.count(title) > 1]
            for i, ax in enumerate(axes):
                if titles[i] in duplicate_titles:
                    titles[i] += f' (id: {id(ax):#x})'
            item, ok = input_get_item(
                self.canvas.parent(),
                '自定义', '选择坐标轴：', titles, 0, False, icon_kind='axis')
            if not ok:
                return
            ax = axes[titles.index(item)]
        figureoptions.figure_edit(ax, self)
        if hasattr(self, '_fedit_dialog') and self._fedit_dialog is not None:
            _translate_figopt_dialog(self._fedit_dialog)


class LivePlot:
    """U5：TCP 实时图的增量更新器。

    坐标轴和两条线在构造时**只建一次**；之后每条消息只做 ``push``（存下最新
    数据）+ ``flush``（``set_data`` / ``relim`` / ``autoscale_view`` /
    ``draw_idle``），因此不再整图 ``clear`` 重建，也不会丢掉用户的缩放与图例。
    """

    def __init__(self, ax, tokens):
        self.ax = ax
        self.tokens = tokens
        self._history = []
        self._forecast = []
        self._threshold = None
        self._rated_capacity = None
        self._threshold_ratio = None
        self._soh_axis = None
        # 事实 = 中性墨色实线 + 小圆点；模型输出 = 强调色虚线。
        self.observed_line, = ax.plot(
            [], [], color=tokens['chart_measured'], marker='o', markersize=3,
            linewidth=MEASURED_LINE_WIDTH, label='实测容量', zorder=3)
        self.forecast_line, = ax.plot(
            [], [], color=tokens['chart_forecast'],
            linewidth=FORECAST_LINE_WIDTH,
            linestyle='--', label='预测容量', zorder=4)
        self.threshold_line = ax.axhline(
            y=0.0, color=tokens['chart_threshold'], linestyle='--',
            linewidth=THRESHOLD_LINE_WIDTH, label='失效阈值线', zorder=5)

    def set_threshold(self, threshold, rated_capacity=None, threshold_ratio=None):
        """更新失效阈值线（额定容量 / 比例变了也不重建坐标轴）。"""
        self._threshold = None if threshold is None else float(threshold)
        if rated_capacity is not None:
            self._rated_capacity = float(rated_capacity)
        if threshold_ratio is not None:
            self._threshold_ratio = float(threshold_ratio)
        if self._threshold is None:
            return
        self.threshold_line.set_ydata([self._threshold, self._threshold])
        if self._threshold_ratio is not None:
            self.threshold_line.set_label(
                f'失效阈值 {self._threshold:.3f} Ah'
                f'（{self._threshold_ratio:.0%} 额定）')

    def attach_soh_axis(self, soh_axis):
        """记录右侧 SOH% 副轴，便于主题切换时重新着色。"""
        self._soh_axis = soh_axis

    def push(self, history, forecast):
        """只存下最新的一帧数据，不做任何绘图。"""
        self._history = _as_float_list(history)
        self._forecast = _as_float_list(forecast)

    def flush(self, canvas):
        """把最新数据刷进已存在的线条，然后只重算数据范围并重绘。"""
        history, forecast = self._history, self._forecast
        self.observed_line.set_data(list(range(len(history))), history)
        if forecast:
            start = max(0, len(history) - 1)
            self.forecast_line.set_data(
                list(range(start, start + len(forecast))), forecast)
        else:
            self.forecast_line.set_data([], [])
        self._autoscale_y(history, forecast)
        self.ax.relim()
        self.ax.autoscale_view(scalex=True, scaley=False)
        canvas.draw_idle()

    def _autoscale_y(self, history, forecast):
        """U2 的同一套 y 轴策略：聚焦退化带，不强制从 0 起。"""
        focused = _focused_ylim(
            [history, forecast], self._rated_capacity, self._threshold)
        if focused is None:
            return
        y_lo, y_hi, ticks = focused
        self.ax.set_ylim(y_lo, y_hi)
        self.ax.set_yticks(ticks)


class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, allow_fullscreen=True,
                 interactive_navigation=False):
        # 主题 token 决定图表底色；默认跟随当前生效主题（C2）。
        self._tokens = active_tokens()
        apply_mpl_style(self._tokens)
        self.fig, self.ax = plt.subplots(1, 1, figsize=(8, 6))
        self.fig.patch.set_facecolor(self._tokens['chart_bg'])
        self.ax.set_facecolor(self._tokens['chart_bg'])
        super().__init__(self.fig)
        self.setParent(parent)
        self._allow_fullscreen = allow_fullscreen
        self._interactive_navigation = interactive_navigation
        self._last_plot_kind = None
        self._last_plot_payload = None
        self._fullscreen_dialog = None
        self._fullscreen_subplot_key = None
        self._hover_annot = None
        self._hover_cid = None
        self._subplot_keys_by_axis = {}
        self._pan_state = None
        self._navigation_toolbar = None
        # U5：实时 TCP 图只建一次坐标轴，之后只更新数据。
        self._live_ax = None
        self._live_plot = None
        if self._interactive_navigation:
            self.mpl_connect('scroll_event', self._on_scroll_zoom)
            self.mpl_connect('button_press_event', self._on_pan_press)
            self.mpl_connect('motion_notify_event', self._on_pan_motion)
            self.mpl_connect('button_release_event', self._on_pan_release)
        self._show_placeholder()

    def apply_theme_tokens(self, tokens):
        """C5/C2：主题切换后重设画布底色并刷新 matplotlib 全局样式。"""
        self._tokens = apply_mpl_style(tokens)
        self.fig.patch.set_facecolor(self._tokens['chart_bg'])
        for axis in self.fig.axes:
            axis.set_facecolor(self._tokens['chart_bg'])
        if self._last_plot_kind is not None and self._last_plot_payload:
            self.replay_last_plot(self)
        else:
            self._show_placeholder()
        return self._tokens

    def _show_placeholder(self):
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        for spine in self.ax.spines.values():
            spine.set_visible(False)
        self.ax.text(0.5, 0.5, '导入数据并点击“开始评估”\n曲线与失效阈值将在这里显示',
                     transform=self.ax.transAxes, ha='center', va='center',
                     fontsize=12, color=self._tokens['text_dim'], linespacing=1.6)
        self.draw()

    def mouseDoubleClickEvent(self, event):
        """双击主图进入全屏；在全屏图中双击则返回。"""
        if event.button() == Qt.MouseButton.LeftButton:
            if self._allow_fullscreen:
                self.open_fullscreen()
            else:
                self.window().close()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        """右键提供当前子图与全部子图两种全屏入口。"""
        if not self._allow_fullscreen or self._last_plot_kind is None:
            super().contextMenuEvent(event)
            return
        subplot_key = self._subplot_key_at(event.pos())
        menu = self._build_fullscreen_menu(subplot_key)
        menu.exec(event.globalPos())
        event.accept()

    def _subplot_key_at(self, position):
        if not self._subplot_keys_by_axis or self.width() <= 0 or self.height() <= 0:
            return None
        figure_x = float(position.x()) / self.width() * self.fig.bbox.width
        figure_y = (
            1.0 - float(position.y()) / self.height()
        ) * self.fig.bbox.height
        for axis, subplot_key in self._subplot_keys_by_axis.items():
            if axis.get_visible() and axis.bbox.contains(figure_x, figure_y):
                return subplot_key
        return None

    def _build_fullscreen_menu(self, subplot_key):
        menu = QMenu(self)
        current_action = menu.addAction('全屏查看当前子图')
        current_action.setEnabled(subplot_key is not None)
        current_action.triggered.connect(
            lambda _checked=False, key=subplot_key: self.open_fullscreen(key))
        all_action = menu.addAction('全屏查看全部子图')
        all_action.triggered.connect(
            lambda _checked=False: self.open_fullscreen(None))
        return menu

    def open_fullscreen(self, subplot_key=None):
        """打开独立全屏图表，不移动或破坏主窗口中的原图。"""
        if self._fullscreen_dialog is not None and self._fullscreen_dialog.isVisible():
            if self._fullscreen_subplot_key == subplot_key:
                self._fullscreen_dialog.raise_()
                self._fullscreen_dialog.activateWindow()
                return
            self._fullscreen_dialog.close()
        dialog = ChartFullscreenDialog(
            self, self.window(), subplot_key=subplot_key)
        self._fullscreen_dialog = dialog
        self._fullscreen_subplot_key = subplot_key

        def _forget_dialog(_result):
            if self._fullscreen_dialog is dialog:
                self._fullscreen_dialog = None
                self._fullscreen_subplot_key = None

        dialog.finished.connect(_forget_dialog)
        dialog.showFullScreen()

    def replay_last_plot(self, target_canvas, subplot_key=None):
        """把当前图表数据重绘到独立画布，保留缩放和平移能力。"""
        if self._last_plot_kind == 'results':
            payload = self._last_plot_payload
            battery_names = list(payload[0])
            if subplot_key is not None:
                if subplot_key not in battery_names:
                    raise ValueError(f'找不到子图：{subplot_key}')
                battery_names = [subplot_key]
            target_canvas.plot_results(battery_names, *payload[1:])
        elif self._last_plot_kind == 'tcp':
            target_canvas.plot_tcp_predictions(*self._last_plot_payload)

    def _toolbar_navigation_is_active(self):
        toolbar = self._navigation_toolbar
        return toolbar is not None and bool(getattr(toolbar, 'mode', ''))

    def _on_scroll_zoom(self, event):
        if (not self._interactive_navigation or event.inaxes is None or
                event.xdata is None or event.ydata is None):
            return
        if event.button == 'up':
            scale = 1.0 / 1.2
        elif event.button == 'down':
            scale = 1.2
        else:
            return

        axis = event.inaxes
        x_min, x_max = axis.get_xlim()
        y_min, y_max = axis.get_ylim()
        axis.set_xlim(
            event.xdata - (event.xdata - x_min) * scale,
            event.xdata + (x_max - event.xdata) * scale,
        )
        axis.set_ylim(
            event.ydata - (event.ydata - y_min) * scale,
            event.ydata + (y_max - event.ydata) * scale,
        )
        self.draw_idle()

    def _on_pan_press(self, event):
        if (not self._interactive_navigation or event.button != 1 or
                event.inaxes is None or self._toolbar_navigation_is_active()):
            return
        self._pan_state = {
            'axis': event.inaxes,
            'x': float(event.x),
            'y': float(event.y),
            'xlim': event.inaxes.get_xlim(),
            'ylim': event.inaxes.get_ylim(),
        }

    def _on_pan_motion(self, event):
        if self._pan_state is None:
            return
        axis = self._pan_state['axis']
        if axis.bbox.width <= 0 or axis.bbox.height <= 0:
            return
        x_min, x_max = self._pan_state['xlim']
        y_min, y_max = self._pan_state['ylim']
        delta_x = (
            float(event.x) - self._pan_state['x']
        ) * (x_max - x_min) / axis.bbox.width
        delta_y = (
            float(event.y) - self._pan_state['y']
        ) * (y_max - y_min) / axis.bbox.height
        axis.set_xlim(x_min - delta_x, x_max - delta_x)
        axis.set_ylim(y_min - delta_y, y_max - delta_y)
        self.draw_idle()

    def _on_pan_release(self, event):
        if event.button == 1:
            self._pan_state = None

    def _calc_tick_interval(self, rated_capacity):
        return _tick_interval(rated_capacity)

    def _install_hover(self, xlabel='放电循环', ylabel='容量 (Ah)'):
        """为当前图表安装数据点悬停提示"""
        if self._hover_cid is not None:
            self.fig.canvas.mpl_disconnect(self._hover_cid)
        self._hover_annot = None
        self._hover_xlabel = xlabel
        self._hover_ylabel = ylabel
        self._hover_cid = self.fig.canvas.mpl_connect(
            'motion_notify_event', self._on_hover)

    def _on_hover(self, event):
        if event.inaxes is None or event.xdata is None or event.ydata is None:
            if self._hover_annot:
                self._hover_annot.set_visible(False)
                self.draw_idle()
            return

        # 在当前坐标轴中找最近的数据点
        min_dist = float('inf')
        nearest = None

        for line in event.inaxes.get_lines():
            if not line.get_visible():
                continue
            xdata, ydata = line.get_xdata(), line.get_ydata()
            if len(xdata) == 0:
                continue
            # 将数据点转为像素坐标
            x_px, y_px = event.inaxes.transData.transform(
                np.column_stack([xdata, ydata])).T
            mx, my = event.x, event.y
            dist = np.sqrt((x_px - mx) ** 2 + (y_px - my) ** 2)
            idx = np.argmin(dist)
            d = dist[idx]
            if d < min_dist:
                min_dist = d
                nearest = (xdata[idx], ydata[idx], line.get_label())

        # 15 像素以内才显示提示
        if nearest is not None and min_dist < 15:
            x_val, y_val, label = nearest
            text = f'{self._hover_xlabel}: {int(x_val)}\n' \
                   f'{self._hover_ylabel}: {y_val:.2f}'
            if label and not label.startswith('_'):
                text = f'{label}\n{text}'

            # 在画布像素坐标下定位提示框，确保实时跟随鼠标
            # 偏移：鼠标右下方 14 像素
            OFFSET_X, OFFSET_Y = 14, -14
            tx_px = event.x + OFFSET_X
            ty_px = event.y + OFFSET_Y

            # 限制在画布范围内
            canvas_w = self.fig.canvas.get_width_height()[0]
            canvas_h = self.fig.canvas.get_width_height()[1]
            # 假设提示框宽 120 高 50 像素，避免溢出
            tw, th = 130, 56
            if tx_px + tw > canvas_w:
                tx_px = event.x - OFFSET_X - tw
            if ty_px - th < 0:
                ty_px = event.y + abs(OFFSET_Y) + th

            # 转 figure 归一化坐标
            inv = self.fig.transFigure.inverted()
            fx, fy = inv.transform((tx_px, ty_px))

            tokens = self._tokens
            if self._hover_annot is None:
                self._hover_annot = self.fig.text(
                    fx, fy, text,
                    transform=self.fig.transFigure,
                    ha='left', va='top',
                    bbox=dict(boxstyle='round,pad=0.4',
                              facecolor=tokens['bg_surface'],
                              edgecolor=tokens['chart_forecast'],
                              alpha=0.95, linewidth=1.2),
                    fontsize=9, color=tokens['text'], zorder=1000)
            else:
                self._hover_annot.set_position((fx, fy))
                self._hover_annot.set_text(text)
                self._hover_annot.set_visible(True)
            self.draw_idle()
        else:
            if self._hover_annot:
                self._hover_annot.set_visible(False)
                self.draw_idle()

    def _make_legend_interactive(self, ax):
        """设置图例可拖动、可编辑、无边框；字号取默认的 2/3。"""
        legend = ax.legend()
        legend.set_draggable(True)
        legend.set_frame_on(False)
        texts = legend.get_texts()
        base_size = (texts[0].get_fontsize() if texts
                     else mpl.rcParams.get('font.size', 10))
        try:
            legend_size = float(base_size) * LEGEND_FONT_SCALE
        except (TypeError, ValueError):
            legend_size = 10.0 * LEGEND_FONT_SCALE
        for text in texts:
            text.set_color(self._tokens['text'])
            text.set_fontsize(legend_size)
            text.set_picker(True)

    def _on_legend_pick(self, event):
        """单击图例文本触发编辑"""
        artist = event.artist
        if not hasattr(artist, 'get_text'):
            return
        ax = artist.axes
        legend = ax.get_legend()
        if legend is not None:
            legend.set_draggable(False)
        old_text = artist.get_text()
        parent = self.parent() if self.parent() else self

        dlg = _LegendEditDialog(parent, old_text)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.result_text != old_text:
            new_text = dlg.result_text
            for line in ax.get_lines():
                if line.get_label() == old_text:
                    line.set_label(new_text)
                    break
            self._make_legend_interactive(ax)
            self.draw()
        elif legend is not None:
            legend.set_draggable(True)

    # ── U2：主结果图的数据装配 ─────────────────────────────
    @staticmethod
    def _resolve_detail(details, battery_name):
        """从 ``details`` 里取出某块电池的 detail（dict 按名字 / list 按 battery）。"""
        if not details:
            return {}
        if isinstance(details, dict):
            found = details.get(battery_name)
            return found if isinstance(found, dict) else {}
        for item in details:
            if isinstance(item, dict) and item.get('battery') == battery_name:
                return item
        return {}

    @staticmethod
    def _primary_rolling_row(detail):
        """主预测起点的滚动行：先对齐 forecast_start，再退回 0.5 起点 / 首个有效行。

        最初样式的评估不再产出 ``rolling_rows``，此时返回 None，调用方自行回退。
        """
        rows = detail.get('rolling_rows') or []
        if not rows:
            return None
        start = detail.get('forecast_start')
        if start is not None:
            for row in rows:
                if row.get('start') == start:
                    return row
        primary_frac = detail.get('primary_start_frac')
        if primary_frac is not None:
            for row in rows:
                try:
                    if abs(float(row.get('start_frac', -1)) -
                           float(primary_frac)) < 1e-9:
                        return row
                except (TypeError, ValueError):
                    continue
        for row in rows:
            if row.get('status') == 'ok':
                return row
        return rows[0]

    def _eol_positions(self, detail, measured, forecast, threshold_val):
        """返回 ``(真实 EOL 下标, 预测 EOL 下标)``；判不出来时该位为 None。

        先用结果里已算好的失效位置（``measured_failure_position`` /
        ``predicted_failure_position``），缺失时才退回用 :func:`_first_cross`
        在实测 / 预测序列上找第一次跌破阈值的位置。
        """
        true_index = detail.get('measured_failure_position')
        pred_index = detail.get('predicted_failure_position')
        if true_index is None:
            true_index = _first_cross(measured, threshold_val)
        if pred_index is None:
            recursive = _as_float_list(detail.get('recursive_prediction'))
            if recursive:
                offset = _first_cross(recursive, threshold_val)
                if offset is not None:
                    pred_index = int(offset)
            elif forecast:
                offset = _first_cross(forecast, threshold_val)
                if offset is not None:
                    start = detail.get('forecast_start')
                    base = (start if start is not None
                            else max(0, len(measured) - len(forecast)))
                    pred_index = int(base) + int(offset)
        if pred_index is None:
            pred_index = true_index
        return true_index, pred_index

    @staticmethod
    def _index_to_cycle(cycles, index):
        """把序列下标换算成真实循环号；越界时按最后一个循环步长外推。"""
        if index is None:
            return None
        index = int(index)
        if index < 0:
            return None
        if not len(cycles):
            return float(index)
        if index < len(cycles):
            return float(cycles[index])
        step = float(cycles[-1] - cycles[-2]) if len(cycles) > 1 else 1.0
        return float(cycles[-1]) + step * (index - len(cycles) + 1)

    def _style_axis(self, ax, tokens, target_divisions=12):
        """把主题 token 落到单个坐标轴：描边、刻度、网格（C2）。

        U9：刻度要**密到能直接读数**。主刻度按 1/2/2.5/5 × 10ⁿ 的友好步长铺满，
        中间再插 4 条次刻度（只画短刻度线、不写标签），这样既看得清数值，
        又不会让标签互相压住。

        刻度用**显式数组**下发（见 :func:`_apply_ticks` 的说明），不使用
        有状态的 locator。
        """
        for name, spine in ax.spines.items():
            spine.set_visible(name in ('left', 'bottom'))
            spine.set_color(tokens['chart_spine'])
            spine.set_linewidth(1.0)
        ax.tick_params(axis='both', which='major', direction='in',
                       length=6, width=1, colors=tokens['text_muted'],
                       labelsize=9, labelcolor=tokens['text'])
        ax.tick_params(axis='both', which='minor', direction='in',
                       length=3, width=0.8, colors=tokens['text_dim'])
        ax.grid(True, which='major', color=tokens['chart_grid'],
                linewidth=0.5, alpha=0.5, zorder=0)
        ax.grid(True, which='minor', color=tokens['chart_grid'],
                linewidth=0.3, alpha=0.25, zorder=0)
        ax.set_axisbelow(True)

        x_lo, x_hi = sorted(ax.get_xlim())
        _apply_ticks(ax.xaxis, x_lo, x_hi, target_divisions)
        y_lo, y_hi = sorted(ax.get_ylim())
        _apply_ticks(ax.yaxis, y_lo, y_hi, target_divisions)

    def _attach_soh_axis(self, ax, rated_capacity, tokens):
        """右侧 SOH% 副轴：容量 / 额定容量 × 100。

        U9：SOH 刻度对齐到整数百分比步长，这样左右两轴都能读出准确数值
        （左轴 Ah，右轴 %），不必在两条线之间目测换算。
        """
        if not rated_capacity or rated_capacity <= 0:
            return None
        secondary = ax.secondary_yaxis(
            'right',
            functions=(lambda y: y / rated_capacity * 100.0,
                       lambda s: s * rated_capacity / 100.0))
        secondary.set_ylabel('SOH (%)', fontsize=10, color=tokens['text_muted'])
        secondary.tick_params(axis='y', which='major', direction='in',
                              colors=tokens['text_muted'], labelsize=9,
                              length=6, width=1,
                              labelcolor=tokens['text'])
        secondary.tick_params(axis='y', which='minor', direction='in',
                              colors=tokens['text_dim'], length=3, width=0.8)
        for name, spine in secondary.spines.items():
            spine.set_visible(name == 'right')
            spine.set_color(tokens['chart_spine'])

        # 用当前容量范围换算出 SOH% 范围，再铺上整数百分比的显式刻度
        y_lo, y_hi = sorted(ax.get_ylim())
        if np.isfinite(y_lo) and np.isfinite(y_hi) and y_hi > y_lo:
            soh_lo = y_lo / rated_capacity * 100.0
            soh_hi = y_hi / rated_capacity * 100.0
            # 百分比轴上 2.5% 这类步长显得别扭，优先 1/2/5/10/20/25/50
            allowed = (0.5, 1.0, 2.0, 2.5, 5.0, 10.0, 20.0, 25.0, 50.0)
            step = nice_step(soh_hi - soh_lo, 10)
            step = min(allowed, key=lambda candidate: abs(candidate - step))
            _apply_ticks(secondary.yaxis, soh_lo, soh_hi, 10,
                         label_step=step)
        return secondary

    def _focus_y(self, ax, series_list, rated_capacity, threshold_val=None):
        """U2：y 轴不再从 0 起，而是聚焦退化带（上下各留 4% 余量）。"""
        focused = _focused_ylim(series_list, rated_capacity, threshold_val)
        if focused is None:
            return
        y_lo, y_hi, ticks = focused
        ax.set_ylim(y_lo, y_hi)
        ax.set_yticks(ticks)

    def _annotate_persistence_note(self, ax, tokens):
        """U2：α≈0 时在图例旁标注「模型未超越平推」。"""
        text = '模型未超越平推（α≈0）'
        legend = ax.get_legend()
        if legend is not None:
            try:
                ax.annotate(
                    text, xy=(0.5, 0.0), xycoords=legend,
                    xytext=(0, -6), textcoords='offset points',
                    ha='center', va='top', fontsize=8.5,
                    color=tokens['chart_threshold'],
                    annotation_clip=False, zorder=10)
                return
            except (TypeError, ValueError):
                pass
        ax.text(0.99, 0.02, text, transform=ax.transAxes, ha='right',
                va='bottom', fontsize=8.5, color=tokens['chart_threshold'])

    def plot_results(self, battery_names, battery_data,
                     prediction_by_battery, rated_capacity, threshold_ratio,
                     details=None):
        """主结果图（C2 + U2）：事实用墨色、模型输出用强调色、失效用朱砂。

        ``details`` 可选，形如 ``{电池名: detail}`` 或 ``[detail, ...]``；认识的键：
        ``forecast`` / ``forecast_start`` / ``forecast_band`` / ``rolling_rows`` /
        ``primary_start_frac`` / ``persistence_blend``。缺任何一个都能正常出图。
        """
        self._last_plot_kind = 'results'
        # 把 details 一并存进 payload：全屏重绘时 U2 的预测起点 / 区间 / EOL
        # 标注不会丢（``replay_last_plot`` 用 ``*payload[1:]`` 原样转发）。
        self._last_plot_payload = (
            battery_names, battery_data, prediction_by_battery,
            rated_capacity, threshold_ratio, details)
        self.fig.clear()
        self._subplot_keys_by_axis = {}
        self._pan_state = None
        # 重新走一次「首帧」路径：清掉旧坐标轴引用，LivePlot 会随新轴重建。
        self._live_ax = None
        self._live_plot = None
        if hasattr(self, '_pick_cid'):
            self.fig.canvas.mpl_disconnect(self._pick_cid)
            self._pick_cid = None

        tokens = apply_mpl_style(getattr(self, '_tokens', None) or active_tokens())
        self._tokens = tokens
        bg_color = tokens['chart_bg']
        self.fig.patch.set_facecolor(bg_color)

        valid_names = [
            name for name in battery_names
            if name in battery_data and name in prediction_by_battery
        ]
        total = len(valid_names)
        if total == 0:
            self.ax = self.fig.add_subplot(111)
            self.ax.axis('off')
            self.ax.set_facecolor(bg_color)
            self.draw()
            return

        cols = 2 if total > 1 else 1
        rows = (total + 1) // 2
        axes = self.fig.subplots(rows, cols, squeeze=False)
        axes = np.array(axes).flatten()

        threshold_val = rated_capacity * threshold_ratio
        threshold_label = (
            f'失效阈值 {threshold_val:.3f} Ah（{threshold_ratio:.0%} 额定）')

        for idx in range(total):
            ax = axes[idx]
            ax.set_facecolor(bg_color)
            battery_name = valid_names[idx]
            self._subplot_keys_by_axis[ax] = battery_name
            detail = self._resolve_detail(details, battery_name)

            entry = battery_data[battery_name]
            measured = np.asarray(_series_values(entry), dtype=np.float64)
            cycles = _series_cycles(entry, len(measured))
            forecast = _as_float_list(detail.get('forecast'))
            band = detail.get('forecast_band')

            # ── 事实：实测容量 = 中性墨色细线 + 小圆点 ──
            # 单电池时严格用墨色；多电池叠加时用主题分类色区分不同电池，
            # 但仍保持实线（事实是实线、模型输出是虚线）。
            if total > 1:
                style = series_style(idx, tokens)
                measured_color = style['color']
            else:
                measured_color = tokens['chart_measured']
            if len(measured):
                marker_step = max(1, len(cycles) // 24)
                ax.plot(cycles, measured, color=measured_color,
                        linewidth=MEASURED_LINE_WIDTH,
                        marker='o', markersize=3, markevery=marker_step,
                        label='真实值', zorder=3)

            # ── 模型输出：递归预测（强调色虚线） ──
            if forecast:
                start = detail.get('forecast_start')
                base = (int(start) if start is not None
                        else max(0, len(measured) - len(forecast)))
                forecast_x = [self._index_to_cycle(cycles, base + i)
                              for i in range(len(forecast))]
                ax.plot(forecast_x, forecast, color=tokens['chart_forecast'],
                        linewidth=FORECAST_LINE_WIDTH, linestyle='--',
                        label='预测值', zorder=4)
                if band:
                    try:
                        band_lo, band_hi = band
                    except (TypeError, ValueError):
                        band_lo = band_hi = None
                    if (band_lo is not None and len(band_lo) == len(forecast)
                            and len(band_hi) == len(forecast)):
                        ax.fill_between(
                            forecast_x, band_lo, band_hi,
                            color=tokens['chart_forecast'],
                            alpha=tokens['chart_band_alpha'], lw=0,
                            label='预测区间(10–90%)', zorder=1)
                # 预测起点：竖向点线 + 小标签
                start_x = self._index_to_cycle(cycles, base)
                if start_x is not None:
                    ax.axvline(start_x, color=tokens['chart_forecast'],
                               linestyle=':', linewidth=1.1, alpha=0.85,
                               zorder=2)
                    ax.annotate(
                        '预测起点', xy=(start_x, 1.0),
                        xycoords=('data', 'axes fraction'),
                        xytext=(3, -4), textcoords='offset points',
                        fontsize=8.5, color=tokens['chart_forecast'],
                        ha='left', va='top', annotation_clip=False)
            else:
                # 没有 forecast 时退回老行为：一步预测序列 → 递归预测序列。
                series = _as_float_list(
                    prediction_by_battery.get(battery_name))
                if series and len(measured):
                    if len(series) < len(measured):
                        series = series + [np.nan] * (
                            len(measured) - len(series))
                    elif len(series) > len(measured):
                        series = series[:len(measured)]
                    ax.plot(cycles, series, color=tokens['chart_forecast'],
                            linewidth=FORECAST_LINE_WIDTH, linestyle='--',
                            label='预测值', zorder=4)
                else:
                    recursive = _as_float_list(
                        detail.get('recursive_prediction'))
                    if recursive:
                        base = max(0, len(measured) - len(recursive))
                        recursive_x = [
                            self._index_to_cycle(cycles, base + i)
                            for i in range(len(recursive))]
                        ax.plot(recursive_x, recursive,
                                color=tokens['chart_forecast'],
                                linewidth=FORECAST_LINE_WIDTH,
                                linestyle='--', label='预测值（递归）', zorder=4)

            # ── 失效：朱砂虚线 ──
            ax.axhline(y=threshold_val, color=tokens['chart_threshold'],
                       linestyle='--', linewidth=THRESHOLD_LINE_WIDTH,
                       label=threshold_label, zorder=5)

            # ── EOL 标记：菱形=真实，三角形=预测（形状冗余，不靠颜色） ──
            true_index, pred_index = self._eol_positions(
                detail, measured, forecast, threshold_val)
            for index, marker, label in ((true_index, 'D', '真实 EOL'),
                                         (pred_index, '^', '预测 EOL')):
                mark_x = self._index_to_cycle(cycles, index)
                if mark_x is None:
                    continue
                ax.plot([mark_x], [threshold_val], linestyle='none',
                        marker=marker, markersize=7,
                        color=tokens['chart_threshold'],
                        markeredgecolor=tokens['chart_bg'], zorder=6,
                        label=label)

            self._style_axis(ax, tokens)
            self._focus_y(ax, [measured, forecast], rated_capacity, threshold_val)
            self._attach_soh_axis(ax, rated_capacity, tokens)

            self._make_legend_interactive(ax)
            alpha = detail.get('persistence_blend')
            if alpha is not None and float(alpha) < 0.05:
                self._annotate_persistence_note(ax, tokens)
            ax.set_xlabel('放电循环', fontsize=10, color=tokens['text_muted'])
            ax.set_ylabel('容量 (Ah)', fontsize=10, color=tokens['text_muted'])
            ax.set_title(battery_name + ' 预测值与真实值对比',
                         fontsize=12, color=tokens['text'], fontweight='bold')

        for idx in range(total, len(axes)):
            axes[idx].axis('off')
            axes[idx].set_facecolor(bg_color)

        self.ax = axes[0]
        self.fig.tight_layout(rect=[0, 0, 1, 0.98])
        self._pick_cid = self.fig.canvas.mpl_connect('pick_event', self._on_legend_pick)
        self._install_hover('放电循环', '容量 (Ah)')
        self.draw()

    def plot_tcp_predictions(self, measured, predicted, rated_capacity, threshold_ratio):
        """实时 TCP 数据预测图：实测容量曲线 + 预测容量曲线 + 失效阈值线。

        U5：坐标轴与两条线**只建一次**，之后每条消息只更新数据（``LivePlot``），
        不再 ``fig.clear()`` 整图重建。方法签名保持不变。
        """
        self._last_plot_kind = 'tcp'
        self._last_plot_payload = (
            measured, predicted, rated_capacity, threshold_ratio)

        tokens = apply_mpl_style(getattr(self, '_tokens', None) or active_tokens())
        self._tokens = tokens
        self.fig.patch.set_facecolor(tokens['chart_bg'])

        first_time = self._live_plot is None or self._live_ax is None
        if first_time:
            self.fig.clear()
            self._subplot_keys_by_axis = {}
            self._pan_state = None
            if hasattr(self, '_pick_cid'):
                self.fig.canvas.mpl_disconnect(self._pick_cid)
                self._pick_cid = None
            self.ax = self.fig.add_subplot(111)
            self.ax.set_facecolor(tokens['chart_bg'])
            self._live_ax = self.ax
            self._live_plot = LivePlot(self.ax, tokens)
            self._live_plot.set_threshold(
                rated_capacity * threshold_ratio, rated_capacity, threshold_ratio)
            self._live_plot.attach_soh_axis(self._attach_soh_axis(
                self.ax, rated_capacity, tokens))
            self._style_axis(self.ax, tokens)
            self.ax.set_xlabel('循环次数', fontsize=10,
                               color=tokens['text_muted'])
            self.ax.set_ylabel('容量 (Ah)', fontsize=10,
                               color=tokens['text_muted'])
            self.ax.set_title('实时 SOH 预测', fontsize=12,
                              color=tokens['text'], fontweight='bold')
            self._make_legend_interactive(self.ax)
            self.fig.tight_layout()
            self._install_hover('循环次数', '容量 (Ah)')
        else:
            self.ax = self._live_ax
            self._live_plot.set_threshold(
                rated_capacity * threshold_ratio, rated_capacity, threshold_ratio)

        self._live_plot.push(measured, predicted)
        self._live_plot.flush(self)

    def save_figure(self, file_path):
        self.fig.savefig(file_path, dpi=300, bbox_inches='tight')


class ChartFullscreenDialog(QDialog):
    """可缩放、可平移的独立全屏训练结果视图。"""

    def __init__(self, source_canvas, parent=None, subplot_key=None):
        super().__init__(parent)
        title = subplot_key if subplot_key is not None else '全部子图'
        self.setWindowTitle(f'训练结果 · {title} · 全屏观察')
        self.setWindowIcon(get_dialog_icon('chart'))
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(6)

        hint = QLabel('滚轮缩放 · 按住鼠标左键拖动平移 · 双击图表或按 Esc 返回')
        hint.setProperty('role', 'subtitle')
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setAccessibleName('全屏图表操作提示')

        self.canvas = MplCanvas(
            self, allow_fullscreen=False, interactive_navigation=True)
        self.toolbar = CustomToolbar(self.canvas, self)
        layout.addWidget(hint)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas, 1)

        source_canvas.replay_last_plot(
            self.canvas, subplot_key=subplot_key)
        self._escape_shortcut = QShortcut(QKeySequence('Escape'), self)
        self._escape_shortcut.activated.connect(self.close)
