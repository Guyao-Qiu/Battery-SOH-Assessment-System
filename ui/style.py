"""
统一主题样式 - 电池 SOH 评估系统
设计语言：宣纸水墨（专业评估仪器）
- 暖宣纸基底 + 墨色层级 + 单一黛青主强调
- 朱砂仅用于危险/失效，竹青与赭石用于语义状态
- 统一细描边、清晰焦点、克制墨晕反馈
"""

from pathlib import Path

DESIGN_LANGUAGE = '宣纸水墨'

# ── 调色板 ──────────────────────────────────────────────────
COLORS = {
    'paper':       '#F3EDE0',   # 宣纸
    'ink':         '#202724',   # 浓墨
    'cinnabar':    '#9E3D2F',   # 朱砂
    'bg_deep':     '#E8E0D1',   # 窗口底纸
    'bg_base':     '#F3EDE0',   # 主宣纸
    'bg_surface':  '#FAF6EC',   # 提亮纸面
    'bg_elevated': '#E1D8C8',   # 次级纸面
    'bg_hover':    '#D6CDBC',   # 悬停墨洗
    'border':      '#898D84',   # 淡墨描边
    'border_soft': '#C5BBAA',   # 弱描边
    'text':        '#202724',   # 主墨
    'text_muted':  '#59635D',   # 次级墨（浅底 AA）
    'text_dim':    '#777D77',   # 禁用墨
    'primary':     '#315B5A',   # 单一主强调：黛青
    'primary_d':   '#244743',   # 深黛
    'primary_l':   '#52766E',   # 浅黛
    'on_accent':   '#FFF9ED',   # 黛青表面上的文字
    'spin_selection': '#76563A',  # 赭褐：数字滚轮选中态
    'on_selection': '#FFF9ED',    # 赭褐表面上的暖白文字
    'success':     '#4F6B4F',   # 竹青
    'success_l':   '#3F6045',
    'warning':     '#98652E',   # 赭石
    'danger':      '#9E3D2F',   # 朱砂危险
    'danger_d':    '#7F2F26',
    'on_danger':   '#FFF9ED',
    'shadow':      'rgba(32, 39, 36, 0.14)',
}

COMBO_DOWN_ARROW_URL = (
    Path(__file__).resolve().parents[1] / 'assets' / 'icons' /
    'combo-down-arrow.svg'
).as_posix()


# ── 字体族 ──────────────────────────────────────────────────
FONT_FAMILY = '"Segoe UI", "Microsoft YaHei", "PingFang SC", "Helvetica Neue", sans-serif'
FONT_MONO   = '"JetBrains Mono", "Cascadia Code", "Consolas", monospace'


def _font(size=10, weight='normal', mono=False):
    family = FONT_MONO if mono else FONT_FAMILY
    return f'font-family: {family}; font-size: {size}pt; font-weight: {weight};'


# ── 主题 QSS ────────────────────────────────────────────────
GLOBAL_QSS = f"""
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
    background: rgba(49, 91, 90, 0.10);
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

/* ── 分组框 ───────────────────────────────────── */
QGroupBox {{
    {_font(10, 'bold')}
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
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
    letter-spacing: 1px;
    background: transparent;
}}
QGroupBox[role="resultCard"] {{
    background: {COLORS['bg_base']};
    border-color: {COLORS['border_soft']};
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
    background: #3C533C;
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
    background: rgba(49, 91, 90, 0.08);
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
    background: rgba(49, 91, 90, 0.08);
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
    background: #FFFDF7;
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
    background: rgba(49, 91, 90, 0.08);
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

/* ── 滚动区 ───────────────────────────────────── */
QScrollArea {{
    background: transparent;
    border: none;
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
    background: {COLORS['bg_surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 4px;
    spacing: 4px;
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
    background: rgba(49, 91, 90, 0.10);
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
"""


def apply_theme(app):
    """应用全局主题样式到 QApplication"""
    app.setStyleSheet(GLOBAL_QSS)
