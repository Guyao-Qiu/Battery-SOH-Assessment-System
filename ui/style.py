"""
统一主题样式 - Battery SOH Assessment System
设计语言：宣纸水墨（专业评估仪器）
- 暖宣纸基底 + 墨色层级 + 单一黛青主强调
- 朱砂仅用于危险/失效，竹青与赭石用于语义状态
- 统一细描边、清晰焦点、克制墨晕反馈

颜色不再写在本文件里：唯一真相来源是工程根目录的 ``theme_tokens.py``
（纯字典 + 纯函数，不 import 第三方库，因此启动闪屏可以在重库加载前就用它）。
本模块只负责把这些 token 渲染成 QSS。
"""

from pathlib import Path

from theme_tokens import (
    DEFAULT_THEME,
    THEMES,
    get_theme,
    rgba,
)
from ui.fonts import (
    DISPLAY_FONT_FAMILIES,
    MONO_FONT_FAMILIES,
    UI_FONT_FAMILIES,
    font_fallbacks_css,
)


DESIGN_LANGUAGE = '宣纸水墨'

#: 兼容旧引用：``COLORS`` 是当前浅色主题的 token 别名。
#: 新代码请直接用 ``build_qss(tokens)`` / ``get_theme(mode)``。
COLORS = THEMES[DEFAULT_THEME]

#: 当前生效的主题模式（由 :func:`apply_theme` 更新）
_current_mode = DEFAULT_THEME

COMBO_DOWN_ARROW_URL = (
    Path(__file__).resolve().parents[1] / 'assets' / 'icons' /
    'combo-down-arrow.svg'
).as_posix()


# ── 字体族 ──────────────────────────────────────────────────
# 候选链写在 ui/fonts.py 里；这里把它渲染成 QSS 的 font-family 列表。
# 之所以不再硬写死一个族名：PyQt6 的 offscreen 平台插件下 QFontDatabase
# 可能是空的（见 ui/fonts.py 的模块说明），必须由 install_fonts() 显式
# 注册系统字体后，这些族名才解析得到。
FONT_FAMILY = font_fallbacks_css(UI_FONT_FAMILIES)
FONT_DISPLAY = font_fallbacks_css(DISPLAY_FONT_FAMILIES)
FONT_MONO = font_fallbacks_css(MONO_FONT_FAMILIES)


def _font(size=10, weight='normal', mono=False):
    family = FONT_MONO if mono else FONT_FAMILY
    return f'font-family: {family}; font-size: {size}pt; font-weight: {weight};'


def _display_font(size=10, weight='normal'):
    return f'font-family: {FONT_DISPLAY}; font-size: {size}pt; font-weight: {weight};'


def build_qss(COLORS):
    """把一套主题 token 渲染成全局 QSS。

    形参刻意命名为 ``COLORS``，这样函数体里原有的 ``COLORS['…']`` 引用
    一个字都不用改；手写的半透明色统一走 :func:`theme_tokens.rgba`。
    """
    return f"""
/* ── 全局 ───────────────────────────────────── */
* {{
    {_font(10)}
    color: {COLORS['text']};
}}

QMainWindow, QDialog, QWidget#central {{
    background: {COLORS['bg_deep']};
}}

/* ── 文本 ─────────────────────────────────────── */
QLabel {{
    color: {COLORS['text']};
    background: transparent;
    {_font(10)}
}}
QLabel[role="title"] {{
    {_font(14, 'bold')}
    color: {COLORS['text']};
    letter-spacing: 1px;
}}
QLabel[role="subtitle"] {{
    {_font(9)}
    color: {COLORS['text_muted']};
    letter-spacing: 0.5px;
}}

/* ── 顶部条（右上顶角主题切换） ────────────────── */
QFrame[role="topBar"] {{
    background: {COLORS['bg_elevated']};
    border: 1px solid {COLORS['border_soft']};
    border-radius: 6px;
}}
QLabel[role="topBarTitle"] {{
    {_font(11, 'bold')}
    color: {COLORS['text']};
    letter-spacing: 0.6px;
}}
QLabel[role="topBarSubtitle"] {{
    {_font(9)}
    color: {COLORS['text_dim']};
    letter-spacing: 0.4px;
}}
QPushButton#themeToggle {{
    {_font(9, 'bold')}
    color: {COLORS['text']};
    background: {COLORS['bg_surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 14px;
    padding: 5px 14px;
}}
QPushButton#themeToggle:hover {{
    background: {COLORS['bg_hover']};
    border-color: {COLORS['primary']};
}}
QPushButton#themeToggle:pressed {{
    background: {COLORS['primary']};
    color: {COLORS['on_accent']};
}}
QPushButton#themeToggle:focus {{
    border: 2px solid {COLORS['primary']};
}}
QLabel[role="metric"] {{
    {_font(20, 'bold')}
    color: {COLORS['primary']};
}}
QLabel[role="badge"] {{
    color: {COLORS['primary']};
    {_font(8, 'bold')}
    padding: 2px 8px;
    border: 1px solid {COLORS['primary_d']};
    border-radius: 8px;
    background: {rgba(COLORS['primary'], 0.10)};
}}
QLabel[role="sectionTitle"] {{
    {_font(11, 'bold')}
    color: {COLORS['text']};
    padding: 2px 0;
}}
QLabel[role="runStatus"] {{
    {_font(9, '600')}
    color: {COLORS['text_muted']};
    background: {COLORS['bg_surface']};
    border: 1px solid {COLORS['border_soft']};
    border-radius: 6px;
    padding: 7px 10px;
}}
QLabel[role="runStatus"][state="running"] {{
    color: {COLORS['primary']};
    border-color: {COLORS['primary_d']};
}}
QLabel[role="emptyState"] {{
    {_font(10)}
    color: {COLORS['text_muted']};
    background: {COLORS['bg_base']};
    border: 1px dashed {COLORS['border']};
    border-radius: 10px;
    padding: 24px 18px;
}}

QFrame[role="dataSummary"] {{
    background: {rgba(COLORS['primary'], 0.06)};
    border: 1px solid {COLORS['border_soft']};
    border-radius: 6px;
}}
QLabel[role="dataSummaryText"] {{
    {_font(8)}
    color: {COLORS['text_muted']};
}}
QLabel[role="dataSummaryText"][state="ready"] {{
    color: {COLORS['primary_d']};
}}
QLabel[role="dataSummaryCount"] {{
    {_font(11, 'bold', mono=True)}
    color: {COLORS['on_accent']};
    background: {COLORS['primary']};
    border: 1px solid {COLORS['primary_d']};
    border-radius: 11px;
    min-width: 22px;
    min-height: 22px;
}}

QFrame[role="modelShelf"] {{
    background: {COLORS['bg_base']};
    border: 1px solid {COLORS['border_soft']};
    border-radius: 7px;
}}
QLabel[role="modelHint"] {{
    {_font(8)}
    color: {COLORS['text_muted']};
}}

QFrame[role="runStatusStrip"] {{
    background: {COLORS['bg_surface']};
    border: 1px solid {COLORS['border_soft']};
    border-radius: 6px;
}}
QFrame[role="runStatusDot"] {{
    background: {COLORS['bg_elevated']};
    border: 1px solid {COLORS['border']};
    border-radius: 5px;
}}
QFrame[role="runStatusDot"][state="running"] {{
    background: {COLORS['primary']};
    border-color: {COLORS['primary_d']};
}}
QFrame[role="runStatusStrip"] QLabel[role="runStatus"] {{
    background: transparent;
    border: none;
    padding: 2px 0;
}}
QLabel[role="runContext"] {{
    {_font(9)}
    color: {COLORS['text_muted']};
}}

QFrame[role="resultBatchBar"] {{
    background: {COLORS['bg_elevated']};
    border: 1px solid {COLORS['border_soft']};
    border-radius: 4px;
}}
QLabel[role="resultBatchLabel"] {{
    {_font(9, '600')}
    color: {COLORS['text_muted']};
}}

QFrame[role="resultSummary"] {{
    background: {rgba(COLORS['primary'], 0.06)};
    border: 1px solid {COLORS['border_soft']};
    border-left: 3px solid {COLORS['primary']};
    border-radius: 5px;
}}
QLabel[role="resultSummaryTitle"] {{
    {_display_font(11, 'bold')}
    color: {COLORS['primary_d']};
}}
QLabel[role="resultSummaryMetric"] {{
    {_font(10, 'bold', mono=True)}
    color: {COLORS['primary_d']};
}}
QLabel[role="resultSummaryMeta"] {{
    {_font(9)}
    color: {COLORS['text_muted']};
}}

QFrame[role="resultState"] {{
    background: {COLORS['bg_base']};
    border: 1px dashed {COLORS['border']};
    border-radius: 10px;
}}
QFrame[role="resultStateBattery"] {{
    background: transparent;
    border: 1px solid {COLORS['primary']};
    border-radius: 5px;
}}
QFrame[role="resultStateBatteryFill"] {{
    background: {rgba(COLORS['primary'], 0.18)};
    border: 1px solid {COLORS['primary_l']};
    border-radius: 2px;
}}
QFrame[role="resultStateBatteryTerminal"] {{
    background: {COLORS['primary']};
    border: none;
    border-radius: 2px;
}}
QLabel[role="resultStateTitle"] {{
    {_display_font(12, 'bold')}
    color: {COLORS['primary_d']};
    letter-spacing: 0.5px;
}}
QLabel[role="resultStateDetail"] {{
    {_font(9)}
    color: {COLORS['text_muted']};
}}
QLabel[role="resultStateGuide"] {{
    {_font(9, '600')}
    color: {COLORS['warning']};
    background: rgba(122, 78, 34, 0.07);
    border: 1px solid {COLORS['border_soft']};
    border-radius: 8px;
    padding: 4px 9px;
}}

/* ── 分组框 ───────────────────────────────────── */
QGroupBox {{
    {_font(10, 'bold')}
    color: {COLORS['text']};
    border: 1px solid {COLORS['border_soft']};
    border-radius: 8px;
    margin-top: 14px;
    padding: 14px 10px 10px 10px;
    background: {COLORS['bg_surface']};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 12px;
    left: 12px;
    color: {COLORS['text']};
    background: transparent;
}}
QGroupBox[role="resultCard"] {{
    background: transparent;
    border: none;
    border-top: 1px solid {COLORS['border_soft']};
    border-radius: 0;
}}
QLabel[role="resultStatus"] {{
    {_font(10, 'bold')}
}}
QLabel[role="resultStatus"][state="success"] {{ color: {COLORS['success_l']}; }}
QLabel[role="resultStatus"][state="warning"] {{ color: {COLORS['warning']}; }}
QLabel[role="resultStatus"][state="danger"] {{ color: {COLORS['danger']}; }}

/* ── 按钮基础 (由 AnimatedButton 接管点击效果) ── */
QPushButton {{
    {_font(10, '500')}
    color: {COLORS['text']};
    background: {COLORS['bg_elevated']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    padding: 7px 14px;
    min-height: 18px;
    text-align: center;
}}
QPushButton:hover {{
    background: {COLORS['bg_hover']};
    border-color: {COLORS['primary']};
    color: {COLORS['primary_d']};
}}
QPushButton:pressed {{
    background: {COLORS['bg_surface']};
    padding-top: 8px;
    padding-bottom: 6px;
}}
QPushButton:focus {{
    border: 2px solid {COLORS['primary']};
}}
QPushButton:disabled {{
    color: {COLORS['text_dim']};
    background: {COLORS['bg_elevated']};
    border-color: {COLORS['border_soft']};
}}

/* ── 角色按钮（主色） ─────────────────────────── */
QPushButton[role="primary"] {{
    color: {COLORS['on_accent']};
    background: {COLORS['primary']};
    border: 1px solid {COLORS['primary']};
    {_font(10, 'bold')}
    letter-spacing: 1px;
}}
QPushButton[role="primary"]:hover {{
    background: {COLORS['primary_l']};
    color: {COLORS['on_accent']};
}}
QPushButton[role="primary"]:pressed {{
    background: {COLORS['primary_d']};
}}

QPushButton[role="success"] {{
    color: {COLORS['on_accent']};
    background: {COLORS['success']};
    border: 1px solid {COLORS['success']};
    {_font(10, 'bold')}
}}
QPushButton[role="success"]:hover {{
    background: {COLORS['success_d']};
}}

QPushButton[role="danger"] {{
    color: {COLORS['on_danger']};
    background: {COLORS['danger']};
    border: 1px solid {COLORS['danger']};
    {_font(10, 'bold')}
}}
QPushButton[role="danger"]:hover {{
    background: {COLORS['danger_d']};
}}

QPushButton[role="ghost"] {{
    background: transparent;
    border: 1px solid {COLORS['border']};
    color: {COLORS['text_muted']};
}}
QPushButton[role="ghost"]:hover {{
    background: {rgba(COLORS['primary'], 0.08)};
    border-color: {COLORS['primary']};
    color: {COLORS['primary_d']};
}}

/* ── 模型选择按钮（激活态） ───────────────────── */
QPushButton[role="model"] {{
    {_font(10, '600')}
    color: {COLORS['text_muted']};
    background: {COLORS['bg_surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    padding: 8px 4px;
    min-width: 64px;
    letter-spacing: 1px;
}}
QPushButton[role="model"]:hover {{
    color: {COLORS['text']};
    border-color: {COLORS['primary']};
    background: {rgba(COLORS['primary'], 0.08)};
}}
QPushButton[role="model"][active="true"] {{
    color: {COLORS['on_accent']};
    background: {COLORS['primary']};
    border: 1px solid {COLORS['primary_l']};
    {_font(10, 'bold')}
}}

/* ── 输入控件 ─────────────────────────────────── */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    {_font(10)}
    color: {COLORS['text']};
    background: {COLORS['bg_surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 3px;
    padding: 5px 8px;
    selection-background-color: {COLORS['primary_d']};
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border-color: {COLORS['primary']};
    background: {COLORS['bg_focus']};
}}
QSpinBox, QDoubleSpinBox {{
    selection-background-color: {COLORS['spin_selection']};
    selection-color: {COLORS['on_selection']};
}}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    width: 0; height: 0; border: 0;
}}
QComboBox::drop-down {{
    border: none;
    width: 22px;
}}
QComboBox QAbstractItemView {{
    {_font(10)}
    color: {COLORS['text']};
    background: {COLORS['bg_surface']};
    border: 1px solid {COLORS['border']};
    selection-background-color: {COLORS['primary_d']};
    selection-color: {COLORS['on_accent']};
    padding: 4px;
}}
QComboBox::down-arrow {{
    image: url("{COMBO_DOWN_ARROW_URL}");
    width: 12px;
    height: 8px;
    margin-right: 6px;
}}

QMenu {{
    {_font(10)}
    color: {COLORS['text']};
    background: {COLORS['bg_surface']};
    border: 1px solid {COLORS['border']};
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 24px 6px 10px;
    border-radius: 3px;
}}
QMenu::item:selected {{
    color: {COLORS['on_accent']};
    background: {COLORS['primary_d']};
}}
QMenu::item:disabled {{
    color: {COLORS['text_dim']};
    background: transparent;
}}

/* ── 文件夹选择对话框 ─────────────────────────── */
QFileDialog {{
    background: {COLORS['bg_deep']};
}}
QFileDialog QLabel {{
    color: {COLORS['text']};
    background: transparent;
}}
QFileDialog QSplitter {{
    background: {COLORS['bg_deep']};
}}
QFileDialog QLineEdit, QFileDialog QComboBox {{
    color: {COLORS['text']};
    background: {COLORS['bg_surface']};
    border: 1px solid {COLORS['border']};
    selection-background-color: {COLORS['primary']};
    selection-color: {COLORS['on_accent']};
}}
QFileDialog QToolButton {{
    color: {COLORS['text_muted']};
    background: {COLORS['bg_base']};
    border: 1px solid transparent;
    border-radius: 4px;
}}
QFileDialog QToolButton:hover {{
    color: {COLORS['primary_d']};
    background: {COLORS['bg_elevated']};
    border-color: {COLORS['border']};
}}
QFileDialog QToolButton:checked,
QFileDialog QToolButton:pressed {{
    color: {COLORS['on_accent']};
    background: {COLORS['primary']};
    border-color: {COLORS['primary_d']};
}}
QFileDialog QPushButton {{
    color: {COLORS['text']};
    background: {COLORS['bg_elevated']};
    border: 1px solid {COLORS['border']};
}}
QFileDialog QPushButton:hover {{
    color: {COLORS['primary_d']};
    background: {COLORS['bg_hover']};
    border-color: {COLORS['primary']};
}}
QFileDialog QTreeView, QFileDialog QListView {{
    color: {COLORS['text']};
    background: {COLORS['bg_surface']};
    alternate-background-color: {COLORS['bg_base']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    selection-background-color: {COLORS['primary']};
    selection-color: {COLORS['on_accent']};
}}
QFileDialog QTreeView::item, QFileDialog QListView::item {{
    color: {COLORS['text']};
    background: transparent;
    padding: 4px 6px;
}}
QFileDialog QTreeView::item:hover, QFileDialog QListView::item:hover {{
    color: {COLORS['primary_d']};
    background: {COLORS['bg_elevated']};
}}
QFileDialog QTreeView::item:selected, QFileDialog QListView::item:selected {{
    color: {COLORS['on_accent']};
    background: {COLORS['primary']};
}}
QFileDialog QHeaderView::section {{
    color: {COLORS['text']};
    background: {COLORS['bg_elevated']};
    border: none;
    border-right: 1px solid {COLORS['border_soft']};
    border-bottom: 1px solid {COLORS['border']};
    padding: 5px 8px;
}}

/* ── 列表 ─────────────────────────────────────── */
QListWidget {{
    {_font(10)}
    color: {COLORS['text']};
    background: {COLORS['bg_base']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 4px;
}}
QListWidget:focus {{
    border: 2px solid {COLORS['primary']};
}}
QListWidget::item {{
    padding: 6px 8px;
    border-radius: 4px;
    margin: 1px 0;
}}
QListWidget::item:hover {{
    background: {rgba(COLORS['primary'], 0.08)};
    color: {COLORS['primary_d']};
}}
QListWidget::item:selected {{
    background: {COLORS['primary_d']};
    color: {COLORS['on_accent']};
}}

/* ── 文本编辑 ─────────────────────────────────── */
QTextEdit, QPlainTextEdit {{
    {_font(9, 'normal', mono=True)}
    color: {COLORS['text']};
    background: {COLORS['bg_base']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 6px;
    selection-background-color: {COLORS['primary_d']};
}}
QTextEdit:focus, QPlainTextEdit:focus {{
    border: 2px solid {COLORS['primary']};
}}

/* ── 工作区页签 ───────────────────────────────── */
/* QTabWidget / QTabBar 都要显式给背景：只写 ::tab 的话，最后一个页签**右侧
   的空白区**由 QTabBar 自己绘制，会露出默认调色板（深色主题下看不出来，
   浅色主题下就是一块突兀的黑条）。 */
QTabWidget {{
    background: transparent;
}}
QTabWidget::pane {{
    background: {COLORS['bg_base']};
    border: 1px solid {COLORS['border_soft']};
    border-top: none;
}}
QTabWidget::tab-bar {{
    alignment: left;
    background: transparent;
}}
QTabBar {{
    background: transparent;
    /* 关掉 QTabBar 自己画的基线，否则会在页签下方留一条深色横线 */
    qproperty-drawBase: 0;
}}
QTabBar::tab {{
    {_font(9, '600')}
    color: {COLORS['text_muted']};
    background: {COLORS['bg_elevated']};
    border: 1px solid {COLORS['border_soft']};
    border-bottom: 1px solid {COLORS['border']};
    padding: 7px 14px;
    min-width: 78px;
}}
QTabBar::tab:selected {{
    color: {COLORS['primary_d']};
    background: {COLORS['bg_base']};
    border-bottom-color: {COLORS['bg_base']};
}}
QTabBar::tab:hover:!selected {{
    color: {COLORS['primary_d']};
    background: {COLORS['bg_hover']};
}}
QTabBar:focus {{
    border: 2px solid {COLORS['primary']};
}}
/* 页签过多时出现的滚动按钮，同样不能露出默认配色 */
QTabBar QToolButton {{
    background: {COLORS['bg_elevated']};
    border: 1px solid {COLORS['border_soft']};
    color: {COLORS['text']};
}}
QTabBar QToolButton:hover {{
    background: {COLORS['bg_hover']};
}}

/* ── 进度条 ───────────────────────────────────── */
QProgressBar {{
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    background: {COLORS['bg_base']};
    text-align: center;
    color: {COLORS['text']};
    height: 14px;
}}
QProgressBar::chunk {{
    background: {COLORS['primary']};
    border-radius: 5px;
}}

/* ── 状态栏 ───────────────────────────────────── */
QStatusBar {{
    background: {COLORS['bg_base']};
    color: {COLORS['text_muted']};
    border-top: 1px solid {COLORS['border']};
    {_font(9)}
    padding: 2px 8px;
}}
QStatusBar::item {{
    border: none;
}}

/* ── 分割器 ───────────────────────────────────── */
QSplitter::handle {{
    background: {COLORS['border']};
}}
QSplitter::handle:horizontal {{ width: 2px; }}
QSplitter::handle:vertical   {{ height: 2px; }}
QSplitter::handle:hover {{
    background: {COLORS['primary']};
}}
QSplitter#leftPanelSplitter::handle:vertical {{
    background: qlineargradient(
        x1: 0, y1: 0, x2: 0, y2: 1,
        stop: 0 transparent,
        stop: 0.39 transparent,
        stop: 0.40 {COLORS['border']},
        stop: 0.60 {COLORS['border']},
        stop: 0.61 transparent,
        stop: 1 transparent
    );
}}
QSplitter#leftPanelSplitter::handle:vertical:hover {{
    background: qlineargradient(
        x1: 0, y1: 0, x2: 0, y2: 1,
        stop: 0 transparent,
        stop: 0.39 transparent,
        stop: 0.40 {COLORS['primary']},
        stop: 0.60 {COLORS['primary']},
        stop: 0.61 transparent,
        stop: 1 transparent
    );
}}

/* ── 滚动区 ───────────────────────────────────── */
QScrollArea {{
    background: transparent;
    border: none;
}}
QWidget[role="resultContainer"] {{
    background: {COLORS['bg_base']};
}}
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {COLORS['border']};
    border-radius: 4px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background: {COLORS['primary']};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: {COLORS['border']};
    border-radius: 4px;
    min-width: 24px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {COLORS['primary']};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ── 工具栏 ───────────────────────────────────── */
QToolBar {{
    background: {COLORS['bg_base']};
    border: 1px solid {COLORS['border_soft']};
    border-radius: 4px;
    padding: 3px;
    spacing: 2px;
}}
QToolButton {{
    {_font(9)}
    color: {COLORS['text_muted']};
    background: transparent;
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 5px 8px;
    margin: 1px;
}}
QToolButton:hover {{
    background: {rgba(COLORS['primary'], 0.10)};
    border-color: {COLORS['primary']};
    color: {COLORS['primary_d']};
}}
QToolButton:pressed {{
    background: {COLORS['primary_d']};
    color: {COLORS['on_accent']};
}}
QToolButton:focus {{
    border: 2px solid {COLORS['primary']};
}}

/* ── 参数分区 ─────────────────────────────────── */
QFrame[role="parameterSection"] {{
    background: {COLORS['bg_base']};
    border: 1px solid {COLORS['border_soft']};
    border-radius: 8px;
}}
QToolButton[role="sectionToggle"] {{
    {_font(10, 'bold')}
    color: {COLORS['text']};
    background: transparent;
    border: none;
    border-radius: 6px;
    padding: 8px 10px;
    text-align: left;
}}
QToolButton[role="sectionToggle"]:hover {{
    color: {COLORS['primary_d']};
    background: {COLORS['bg_elevated']};
    border: none;
}}
QToolButton[role="sectionToggle"]:focus {{
    border: 2px solid {COLORS['primary']};
}}

/* ── 表单标签 ─────────────────────────────────── */
QFormLayout {{
    {_font(10)}
}}

/* ── 消息框 ───────────────────────────────────── */
QMessageBox {{
    background: {COLORS['bg_surface']};
    {_font(10)}
}}
QMessageBox QLabel {{
    color: {COLORS['text']};
    {_font(10)}
}}
QMessageBox QPushButton {{
    min-width: 70px;
}}

/* ── 滚动条覆盖 ───────────────────────────────── */
QToolTip {{
    {_font(9)}
    color: {COLORS['text']};
    background: {COLORS['bg_surface']};
    border: 1px solid {COLORS['primary']};
    border-radius: 4px;
    padding: 4px 8px;
}}

/* ── 启动大按钮 (主行动点) ────────────────────── */
QPushButton[role="hero"] {{
    color: {COLORS['on_accent']};
    background: {COLORS['primary']};
    border: 1px solid {COLORS['primary_d']};
    border-radius: 4px;
    {_font(12, 'bold')}
    letter-spacing: 2px;
    padding: 10px 24px;
}}
QPushButton[role="hero"]:hover {{
    color: {COLORS['on_accent']};
    background: {COLORS['primary_d']};
    border: 1px solid {COLORS['primary_d']};
}}
QPushButton[role="hero"]:pressed {{
    color: {COLORS['on_accent']};
    background: {COLORS['primary_d']};
    padding-top: 11px;
    padding-bottom: 9px;
}}
QPushButton[role="hero"]:disabled {{
    color: {COLORS['text_dim']};
    background: {COLORS['bg_surface']};
    border: 1px solid {COLORS['border_soft']};
    letter-spacing: 2px;
}}

/* 角色色不得覆盖禁用态，避免停止、保存等按钮看起来仍可操作。 */
QPushButton[role="primary"]:disabled,
QPushButton[role="success"]:disabled,
QPushButton[role="danger"]:disabled,
QPushButton[role="ghost"]:disabled,
QPushButton[role="model"]:disabled,
QPushButton[role="model"][active="true"]:disabled {{
    color: {COLORS['text_muted']};
    background: {COLORS['bg_surface']};
    border: 1px solid {COLORS['border_soft']};
}}

/* ── 动态属性样式（取代内联 setStyleSheet，见 C1） ── */
QLabel[role="muted"] {{
    {_font(9)}
    color: {COLORS['text_muted']};
    background: transparent;
}}
QLabel[role="mono"] {{
    {_font(10, 'bold', mono=True)}
    color: {COLORS['primary_d']};
    background: transparent;
}}
QLabel[role="warning"] {{
    {_font(9, '600')}
    color: {COLORS['warning']};
    background: transparent;
}}
QLabel[role="dangerText"] {{
    {_font(9, '600')}
    color: {COLORS['danger']};
    background: transparent;
}}
QLabel[role="successText"] {{
    {_font(9, '600')}
    color: {COLORS['success_d']};
    background: transparent;
}}
/* 状态色必须带非颜色冗余（图标 / 文字前缀），见 U6 */
QTableView {{
    {_font(9)}
    color: {COLORS['text']};
    background: {COLORS['bg_surface']};
    alternate-background-color: {COLORS['bg_base']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    gridline-color: {COLORS['border_soft']};
    selection-background-color: {COLORS['primary']};
    selection-color: {COLORS['on_accent']};
}}
QTableView::item {{
    /* U1：结果面板较窄，内边距压到最小以便更多列可见 */
    padding: 2px 5px;
}}
QTableView QHeaderView::section {{
    {_font(9, 'bold')}
    color: {COLORS['text']};
    background: {COLORS['bg_elevated']};
    border: none;
    border-right: 1px solid {COLORS['border_soft']};
    border-bottom: 1px solid {COLORS['border']};
    padding: 5px 6px;
}}
QTableView QTableCornerButton::section {{
    background: {COLORS['bg_elevated']};
    border: none;
}}
"""


def theme_tokens(mode=None):
    """取某套主题 token（默认当前生效的主题）。"""
    return get_theme(mode or _current_mode)


def apply_theme(app, mode=None):
    """应用全局主题样式到 QApplication；``mode`` 为 ``'light'`` 或 ``'dark'``。"""
    global _current_mode, COLORS
    if mode is not None:
        _current_mode = str(mode).strip().lower()
    tokens = get_theme(_current_mode)
    COLORS = tokens
    app.setStyleSheet(build_qss(tokens))
    # 让 Qt 原生控件（对话框、菜单、滚动条）也跟随明暗
    try:
        from PyQt6.QtCore import Qt
        from PyQt6.QtWidgets import QApplication
        style_hints = QApplication.styleHints()
        scheme = (Qt.ColorScheme.Dark if _current_mode == 'dark'
                  else Qt.ColorScheme.Light)
        style_hints.setColorScheme(scheme)
    except (ImportError, AttributeError):
        pass
    return tokens


def current_theme_mode():
    return _current_mode


#: 兼容旧引用：模块级 ``GLOBAL_QSS`` 现在是默认主题渲染出的静态样式表。
GLOBAL_QSS = build_qss(COLORS)
