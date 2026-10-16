import os
import sys
import ctypes
import json
import glob

import torch
import numpy as np

from PyQt6.QtCore import (
    Qt, QTimer, QSignalBlocker, QSettings, QSize,
    QSortFilterProxyModel,
)
from PyQt6.QtWidgets import (
    QApplication, QWidget, QMainWindow, QFileDialog, QLabel, QListWidget,
    QTextEdit, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QDoubleSpinBox,
    QSpinBox, QComboBox, QLineEdit, QMessageBox, QSizePolicy,
    QSplitter, QScrollArea, QAbstractSpinBox, QAbstractItemView, QProgressBar, QStatusBar,
    QDialog, QFrame, QToolButton, QTabWidget, QTableView, QHeaderView,
    QPushButton, QCheckBox, QStackedWidget, QButtonGroup,
)
from PyQt6.QtGui import (
    QTextCursor, QShortcut, QKeySequence, QFontMetrics, QIntValidator,
)
from ui.chart_show import MplCanvas, CustomToolbar, apply_sup_sub
from ui.worker import EvalWorker
from ui.animated_button import AnimatedButton
from ui.floating_theme_button import FloatingThemeButton
from ui.style import apply_theme, theme_tokens
from ui.result_model import (
    COLUMNS,
    COLUMN_WIDTHS,
    ResultTableModel,
    bootstrap_summary,
    rows_from_details,
    summary_row,
    to_csv,
)
from utils.config import (
    DEVICE_UI,
    FEATURE_LABELS,
    FEATURE_OPTIONS,
    NORM_UI,
    THEME_UI,
    TrainConfig,
    from_ui,
    load_config,
    normalize_device,
    normalize_model_name,
    save_config,
    to_ui,
)
from utils.logger import setup_logger
from utils.paths import FIGURE_DIR, MODEL_DIR, OUTPUTS_DIR
from utils.icon_generator import get_app_icon, get_dialog_icon, show_message
from core.adapters import get_adapter_list
from core.result_semantics import analyze_failure_cycles
from core.report_export import (
    ExportCancelled,
    ReportExportError,
    atomic_save_figure,
    export_run_report,
)
from core.run_snapshot import RunSnapshot
from theme_tokens import DEFAULT_THEME, THEMES, THEME_SETTINGS_KEY
# ── JSON 配置导入映射 ──────────────────────────────────────

#: 主题与窗口几何的持久化设置（U4 / C5）
SETTINGS_ORG = 'BatterySOH'
SETTINGS_APP = 'AssessmentSystem'

#: 侧边栏页面定义：(键, 轨道按钮文案, 图标 kind)，顺序即页面顺序。
#: 左右两栏合并成一个图标导航侧边栏后，数据/参数/结果/日志在此登记。
SIDEBAR_PAGES = (
    ('data', '数据', 'folder'),
    ('params', '参数', 'settings'),
    ('result', '结果', 'chart'),
    ('log', '日志', 'log'),
)

#: 帮助面板正文字号（pt）的持久化键。
HELP_FONT_SIZE_KEY = 'help_font_size'


def _settings():
    return QSettings(SETTINGS_ORG, SETTINGS_APP)


def restore_or_default_geometry(window):
    """恢复上次的窗口几何；没有记录时按可用屏幕自适应（U4）。

    旧实现固定 ``resize(1600, 900)``，在 1366×768 的笔记本上起始尺寸就超出屏幕。
    """
    settings = _settings()
    geometry = settings.value('geometry')
    if geometry is not None and window.restoreGeometry(geometry):
        return False
    screen = window.screen()
    if screen is not None:
        available = screen.availableGeometry()
        window.resize(
            min(1600, int(available.width() * 0.9)),
            min(900, int(available.height() * 0.9)))
    else:
        window.resize(1280, 800)
    return True


def save_geometry(window):
    _settings().setValue('geometry', window.saveGeometry())


def saved_theme_mode():
    """读取已保存的主题模式（供启动闪屏在重库加载前使用）。

    默认 **深色（墨夜）**：这是产品默认外观，浅色（宣纸）为可选。
    用户选择会被 QSettings 记住，下次启动沿用。
    """
    value = _settings().value(THEME_SETTINGS_KEY, DEFAULT_THEME)
    return str(value).strip().lower() if value else DEFAULT_THEME


def _map_metric(val):
    m = str(val).lower()
    return {'rmse': 'RMSE', 'mae': 'MAE', 'r2': 'R²', 'pearson': 'Pearson',
            're': 'RE', 'all': '全部'}.get(m, 'RMSE')

def _map_norm(val):
    """规范键 -> 界面文本（同时兼容旧的界面文本输入）。"""
    return to_ui(NORM_UI, from_ui(NORM_UI, val))

def _map_device(val):
    return to_ui(DEVICE_UI, normalize_device(val))


def format_metric_value(value):
    if value is None or not np.isfinite(value):
        return 'N/A（截尾）'
    return f'{value:.6f}'

_JSON_CONFIG_MAP = [
    (('rated_capacity',),           'rated_capacity_spin',      float),
    (('threshold_ratio', 'THRESHOLD_RATIO'), 'threshold_ratio_spin', float),
    (('voltage_upper',),                     'voltage_upper_spin',       float),
    (('voltage_lower',),                     'voltage_lower_spin',       float),
    (('window_size', 'Feature Size'),        'feature_size_spin',     int),
    (('metric',),                            'metric_combo',          _map_metric),
    (('seed', 'random_seed'),                'seed_spin',             int),
    (('hidden_dim',),                'hidden_dim_spin',         int),
    (('epochs', 'num_epochs'),       'epochs_spin',             int),
    (('norm_method', 'normalization'), 'norm_combo',            _map_norm),
    (('device',),                     'device_combo',           _map_device),
    (('n_estimators', 'xgb_n_estimators'),      'xgb_n_estimators_spin',      int),
    (('xgb_learning_rate',),                    'xgb_learning_rate_spin',     float),
    (('max_depth', 'xgb_max_depth'),            'xgb_max_depth_spin',         int),
    (('subsample', 'xgb_subsample'),            'xgb_subsample_spin',         float),
    (('colsample_bytree', 'xgb_colsample_bytree'), 'xgb_colsample_bytree_spin', float),
    (('patience', 'early_stopping_rounds'),     'xgb_patience_spin',          int),
    (('rf_n_estimators',),            'rf_n_estimators_spin',       int),
    (('rf_max_depth',),               'rf_max_depth_spin',          int),
    (('min_samples_leaf', 'rf_min_samples_leaf'), 'rf_min_samples_leaf_spin', int),
    (('max_features', 'rf_max_features'), 'rf_max_features_spin',       float),
    (('rf_patience',),                'rf_patience_spin',           int),
]

_FOLDER_DIALOG_TOOLTIPS = {
    'backButton': '后退',
    'forwardButton': '前进',
    'toParentButton': '返回上一级',
    'newFolderButton': '新建文件夹',
    'listModeButton': '列表视图',
    'detailModeButton': '详细信息视图',
}


def _hex_to_colorref(hex_color):
    """``'#RRGGBB'`` -> Windows COLORREF（``0x00BBGGRR``）。"""
    value = str(hex_color).lstrip('#')
    if len(value) == 3:
        value = ''.join(char * 2 for char in value)
    red, green, blue = (int(value[index:index + 2], 16)
                        for index in (0, 2, 4))
    return (blue << 16) | (green << 8) | red


def _apply_windows_paper_caption(dlg):
    """在 Windows 11 上让此对话框的原生标题栏匹配当前主题。"""
    if sys.platform != 'win32':
        return
    try:
        hwnd = int(dlg.winId())
        dwm = ctypes.windll.dwmapi
        tokens = theme_tokens()
        dark_mode = ctypes.c_int(1 if tokens is THEMES['dark'] else 0)
        dwm.DwmSetWindowAttribute(
            hwnd, 20, ctypes.byref(dark_mode), ctypes.sizeof(dark_mode))

        DWMWA_BORDER_COLOR = 34
        DWMWA_CAPTION_COLOR = 35
        DWMWA_TEXT_COLOR = 36
        # 颜色全部来自主题 token，深色主题下标题栏也会跟着变
        for attribute, token_name in (
                (DWMWA_BORDER_COLOR, 'border'),
                (DWMWA_CAPTION_COLOR, 'bg_deep'),
                (DWMWA_TEXT_COLOR, 'text')):
            value = ctypes.c_uint(_hex_to_colorref(tokens[token_name]))
            dwm.DwmSetWindowAttribute(
                hwnd, attribute, ctypes.byref(value), ctypes.sizeof(value))
    except (AttributeError, OSError, TypeError, KeyError):
        # 旧版 Windows 不支持标题栏颜色属性时，内容区主题仍正常生效。
        pass


def _configure_folder_dialog(dlg):
    """汉化文件夹对话框标签、工具提示和无障碍名称。"""
    dlg.setLabelText(QFileDialog.DialogLabel.LookIn, '查找范围：')
    dlg.setLabelText(QFileDialog.DialogLabel.FileName, '文件夹：')
    dlg.setLabelText(QFileDialog.DialogLabel.FileType, '文件类型：')
    dlg.setLabelText(QFileDialog.DialogLabel.Accept, '选择文件夹')
    dlg.setLabelText(QFileDialog.DialogLabel.Reject, '取消')
    for button in dlg.findChildren(QToolButton):
        tooltip = _FOLDER_DIALOG_TOOLTIPS.get(button.objectName())
        if tooltip:
            button.setToolTip(tooltip)
            button.setAccessibleName(tooltip)
    _apply_windows_paper_caption(dlg)


def _configure_button_row(layout, buttons, spacing=8):
    """统一按钮行的尺寸策略，让控件等宽伸展且不会相互覆盖。"""
    layout.setSpacing(spacing)
    layout.setContentsMargins(0, 0, 0, 0)
    for button in buttons:
        text_width = QFontMetrics(button.font()).horizontalAdvance(button.text())
        button.setMinimumWidth(max(72, text_width + 28))
        button.setMinimumHeight(36)
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(button, 1)


def _create_step_input(accessible_name):
    step_input = QLineEdit()
    step_input.setAccessibleName(accessible_name)
    step_input.setPlaceholderText('无')
    step_input.setValidator(QIntValidator(0, 2_147_483_647, step_input))
    step_input.setClearButtonEnabled(True)
    step_input.setInputMethodHints(Qt.InputMethodHint.ImhDigitsOnly)
    return step_input


def _set_step_input(step_input, value):
    step_input.setText('' if value is None else str(value))


def _step_input_value(step_input):
    text = step_input.text().strip()
    if not text:
        return None
    state, _, _ = step_input.validator().validate(text, len(text))
    return int(text) if state == QIntValidator.State.Acceptable else None


class _HelpDialog(QDialog):
    """模型参数帮助对话框（非模态，随模型切换实时更新）。

    顶部提供字号设置（默认 12pt），改动后**立即**应用到当前内容，
    并记住用户的选择，下次打开沿用。
    """

    #: 帮助正文字号（pt）；默认 12
    DEFAULT_FONT_SIZE = 12
    FONT_SIZE_RANGE = (8, 24)

    def __init__(self, parent, mode):
        super().__init__(parent)
        self.setWindowTitle('参数设置帮助')
        self.setWindowIcon(get_dialog_icon('help'))
        self.resize(620, 640)
        self.setMinimumSize(450, 400)

        self._mode = mode
        self._font_size = int(_settings().value(
            HELP_FONT_SIZE_KEY, self.DEFAULT_FONT_SIZE) or self.DEFAULT_FONT_SIZE)

        layout = QVBoxLayout(self)

        # ── 字号工具行 ──
        tools = QHBoxLayout()
        tools.addWidget(QLabel('字号：'))
        self._font_spin = QSpinBox()
        self._font_spin.setRange(*self.FONT_SIZE_RANGE)
        self._font_spin.setValue(self._font_size)
        self._font_spin.setSuffix(' pt')
        self._font_spin.setAccessibleName('帮助正文字号')
        self._font_spin.setToolTip('调整帮助文档字号，立即生效并记住选择')
        self._font_spin.valueChanged.connect(self._on_font_size_changed)
        tools.addWidget(self._font_spin)
        tools.addStretch(1)
        layout.addLayout(tools)

        self._text = QTextEdit()
        self._text.setReadOnly(True)
        layout.addWidget(self._text)

        self.set_content(mode)

    def _on_font_size_changed(self, size):
        self._font_size = int(size)
        _settings().setValue(HELP_FONT_SIZE_KEY, self._font_size)
        self._render()

    def set_content(self, mode):
        self._mode = mode
        self._render()

    def _render(self):
        """把正文按当前字号渲染（即时生效）。"""
        content = MainWindow._HELP_CONTENT.get(
            self._mode, '<p>暂无该模型的帮助信息。</p>')
        self._text.document().setDefaultStyleSheet(
            f'body {{ font-size: {self._font_size}pt; }}'
            f'h2 {{ font-size: {self._font_size + 5}pt; }}'
            f'h3 {{ font-size: {self._font_size + 2}pt; }}')
        self._text.setHtml(content)
        # 让控件自身的默认字号也跟着走，标题之外的段落同样受控
        font = self._text.font()
        font.setPointSize(self._font_size)
        self._text.setFont(font)


class _GuideDialog(QDialog):
    """系统使用指南：完整介绍工作流程、数据格式与常见问题。

    与 F1 的参数帮助分开：这里讲“怎么用这个系统”，
    F1 讲“当前模型的每个参数是什么意思”。
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle('使用指南')
        self.setWindowIcon(get_dialog_icon('book'))
        self.resize(700, 680)
        self.setMinimumSize(480, 420)

        layout = QVBoxLayout(self)
        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setHtml(self.guide_html())
        layout.addWidget(self._text)

    @staticmethod
    def guide_html():
        """使用指南正文（纯静态内容）。"""
        adapters = '、'.join(
            f'{display}（{name}）' for name, display in get_adapter_list())
        return f"""
<h2>电池 SOH 评估系统 · 使用指南</h2>

<h3>一、这个系统能做什么</h3>
<p>导入电池循环数据后，系统用循环神经网络（RNN / GRU / LSTM）或树模型
（XGBoost / RF）学习容量退化趋势，输出：</p>
<ul>
  <li><b>容量预测曲线</b>：实测容量与模型预测容量对比；</li>
  <li><b>失效循环与剩余寿命（RUL）</b>：容量跌破失效阈值时的循环序号与还剩多少个循环；</li>
  <li><b>评估指标</b>：RMSE、MAE、R²、Pearson、RE，以及跨电池汇总；</li>
  <li><b>可导出的报告</b>：report.json、评估结果.xlsx、评估结果.png。</li>
</ul>

<h3>二、标准工作流程</h3>
<ol>
  <li><b>导入数据</b>（左栏「数据」页）：点「导入文件」选 .xlsx/.csv，或
      「导入文件夹」批量导入整个目录。导入后队列会显示条目数。</li>
  <li><b>选数据源格式</b>：根据数据来源选择适配器（{adapters}）。
      CALCE 格式需要填写工步编号（可留空表示"无"）。</li>
  <li><b>设置参数</b>（左栏「参数」页）：
      <ul>
        <li><b>电池容量与失效判据</b>：额定容量、失效阈值比例、SOH 上下电压；</li>
        <li><b>评估与验证</b>：窗口大小、评估指标、输入特征、随机种子、多种子数；</li>
        <li><b>模型高级参数</b>：隐藏层维度、训练轮数、归一化、计算设备（默认折叠）。</li>
      </ul>
      不确定某个参数含义时，按 <b>F1</b> 或点「帮助」查看当前模型的参数说明。</li>
  <li><b>选择模型</b>（中间顶部）：RNN / GRU / LSTM / XGBoost / RF。
      不确定时推荐先用 <b>GRU</b>（速度与效果平衡）。</li>
  <li><b>开始评估</b>：点绿色大按钮或按 <b>Ctrl+Enter</b>。
      训练期间可随时按「停止」在安全检查点中断，参数与数据都会保留。</li>
  <li><b>查看结果</b>（左栏「结果」页）：可排序表格 + 跨电池汇总行 + 图表。
      用「预测起点」下拉框切换不同的滚动起点，用「复制表格 / 导出 CSV」带走数据。</li>
  <li><b>保存与导出</b>：训练完成后可「保存模型」；点「导出报告」生成完整报告包。</li>
</ol>

<h3>三、界面导航</h3>
<ul>
  <li>左侧窄轨道四个按钮对应四个页面：数据 / 参数 / 结果 / 日志，
      快捷键 <b>Ctrl+1 ~ Ctrl+4</b>；</li>
  <li><b>再次点击当前页按钮可收起侧边栏</b>，把空间让给图表；再点任意按钮展开；</li>
  <li>右上角圆形按钮切换深浅主题（<b>Ctrl+T</b>），按住可以拖到任意位置；</li>
  <li>图表支持右键或双击全屏查看，按 <b>Esc</b> 退出全屏。</li>
</ul>

<h3>四、加载已有模型做预测</h3>
<ol>
  <li>点「加载模型」选择之前保存的 .pt / .pth / .joblib 文件；</li>
  <li>导入新数据后点「开始评估」，此时执行的是<b>预测</b>而不是重新训练；</li>
  <li>点「卸载模型」可切回训练模式。</li>
</ol>

<h3>五、实时数据接入（实验功能）</h3>
<p>加载模型后点「接入数据」可开启 TCP 服务（默认只监听本机 127.0.0.1:8888），
外部程序推送容量数据即可实时得到 SOH / RUL 预测。需要局域网访问时，
必须显式勾选「允许局域网访问」，系统会自动生成访问 token。</p>

<h3>六、常见问题</h3>
<ul>
  <li><b>点了「开始评估」没反应？</b> 先确认已导入数据；参数不合规时系统会弹出
      校验提示并列出具体问题。</li>
  <li><b>结果指标不理想？</b> 检查窗口大小是否合适（数据循环数少时不要设太大）、
      失效阈值比例是否符合你的电池体系，并对比日志里的基线说明。</li>
  <li><b>想知道模型有没有超过简单基线？</b> 结果区会给出技能分与平推基线对比；
      技能分低于 0.05 时会明确警告。</li>
  <li><b>训练很慢？</b> 在「模型高级参数」里确认计算设备；没有 NVIDIA 显卡时
      会自动使用 CPU。</li>
  <li><b>置信区间怎么理解？</b> 它只表示同一留一折内随机种子的波动，
      <b>不代表</b>跨电池的总体不确定性（结果区有同样的说明）。</li>
</ul>
"""


class CollapsibleSection(QFrame):
    """紧凑参数分区，可按需展开高级设置。"""

    def __init__(self, title, expanded=True, parent=None):
        super().__init__(parent)
        self.setProperty('role', 'parameterSection')

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 6)
        layout.setSpacing(2)

        self.toggle = QToolButton()
        self.toggle.setText(title)
        self.toggle.setProperty('role', 'sectionToggle')
        self.toggle.setCheckable(True)
        self.toggle.setChecked(expanded)
        self.toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.toggle.setAccessibleName(f'{title}，按空格展开或收起')
        self.toggle.toggled.connect(self._set_expanded)
        layout.addWidget(self.toggle)

        self.content = QWidget()
        self.form_layout = QFormLayout(self.content)
        self.form_layout.setContentsMargins(10, 4, 10, 8)
        self.form_layout.setHorizontalSpacing(12)
        self.form_layout.setVerticalSpacing(7)
        self.form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        layout.addWidget(self.content)

        self._set_expanded(expanded)

    def _set_expanded(self, expanded):
        self.content.setVisible(expanded)
        arrow = Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow
        self.toggle.setArrowType(arrow)


class MainWindow(QMainWindow):
    _independent_windows = []

    def __init__(self):
        super().__init__()
        # 字体在**进程启动时**装好（battery_soh_app.py 在 QApplication 之后、
        # 任何控件之前调用 ui.fonts.install_fonts）。这里刻意**不**碰
        # QFontDatabase：在控件已存在之后再调用它的静态方法，会让本环境里
        # 字体库缺失的 PyQt6（Qt6/lib/fonts 不存在）在后续绘制时段错误
        # （0xC0000005，实测可稳定复现）。窗口只负责画界面，不负责装字体。
        self.setWindowTitle('Battery SOH Assessment System')
        self.setWindowIcon(get_app_icon())
        self.setMinimumSize(1180, 700)
        # U4：恢复上次几何；没有记录时按可用屏幕自适应，而不是硬编码 1600×900
        restore_or_default_geometry(self)

        self.imported_paths = []
        self.current_mode = 'RNN'
        self.worker = None
        self._active_run_kind = None
        self._finish_status_message = '准备就绪'
        self._eval_rated_capacity = 1.1
        self._eval_threshold_ratio = 0.8
        self.battery_dict = {}
        self.battery_list = []
        self._active_run_snapshot = None
        self._last_run_snapshot = None
        self._result_batches = []
        self._has_completed_training_run = False
        self._child_training_windows = []
        self._error_toast = None
        self._theme_mode = saved_theme_mode()

        self.loaded_model = None
        self.loaded_metadata = None
        self.final_trained_model = None
        self.final_trained_metadata = None
        self.tcp_server = None
        self.tcp_running = False
        self._tcp_window = None

        self.logger = setup_logger()
        self.init_ui()
        self._install_sup_sub_shortcuts()
        self._load_persisted_config()

    def apply_theme(self, mode=None):
        """应用全局宣纸水墨主题样式；``mode`` 为 ``'light'`` / ``'dark'``。"""
        if mode is not None:
            self._theme_mode = str(mode).strip().lower()
        tokens = apply_theme(QApplication.instance(), self._theme_mode)
        _settings().setValue(THEME_SETTINGS_KEY, self._theme_mode)
        # 让结果表与图表跟着换色
        if getattr(self, 'result_model', None) is not None:
            self.result_model.set_tokens(tokens)
        if getattr(self, 'canvas', None) is not None:
            try:
                self.canvas.apply_theme_tokens(tokens)
            except AttributeError:
                pass
        self._sync_theme_button()
        return tokens

    def toggle_theme(self):
        """浅色 / 深色主题切换（C5）。"""
        self.apply_theme('light' if self._theme_mode == 'dark' else 'dark')
        self.append_log(
            f'主题已切换为：{THEME_UI.get(self._theme_mode, self._theme_mode)}')

    def _load_persisted_config(self):
        cfg = load_config()
        if not cfg:
            return
        widget_map = {
            'rated_capacity': self.rated_capacity_spin,
            'threshold_ratio': self.threshold_ratio_spin,
            'voltage_upper': self.voltage_upper_spin,
            'voltage_lower': self.voltage_lower_spin,
            'window_size': self.feature_size_spin,
            'epochs': self.epochs_spin,
            'hidden_dim': self.hidden_dim_spin,
            'seed': self.seed_spin,
            'n_seeds': self.n_seeds_spin,
            'n_estimators': self.xgb_n_estimators_spin,
            'learning_rate': self.xgb_learning_rate_spin,
            'max_depth': self.xgb_max_depth_spin,
            'subsample': self.xgb_subsample_spin,
            'colsample_bytree': self.xgb_colsample_bytree_spin,
            'min_samples_leaf': self.rf_min_samples_leaf_spin,
            'max_features': self.rf_max_features_spin,
            'patience': self.xgb_patience_spin,
        }
        for key, widget in widget_map.items():
            if key in cfg:
                try:
                    widget.setValue(cfg[key])
                except (TypeError, ValueError):
                    pass
        if 'mode' in cfg:
            try:
                self.select_mode(normalize_model_name(cfg['mode']))
            except ValueError:
                pass
        if 'metric' in cfg and hasattr(self, 'metric_combo'):
            idx = self.metric_combo.findText(cfg['metric'])
            if idx >= 0:
                self.metric_combo.setCurrentIndex(idx)
        # A11：配置里存的是规范键（'cuda'），界面显示的是 'GPU (CUDA)'。
        # 旧配置文件可能存了界面文本，from_ui 两种都接受。
        if 'device' in cfg and hasattr(self, 'device_combo'):
            idx = self.device_combo.findText(to_ui(DEVICE_UI, cfg['device']))
            if idx >= 0:
                self.device_combo.setCurrentIndex(idx)
        if 'norm_method' in cfg and hasattr(self, 'norm_combo'):
            idx = self.norm_combo.findText(
                to_ui(NORM_UI, from_ui(NORM_UI, cfg['norm_method'])))
            if idx >= 0:
                self.norm_combo.setCurrentIndex(idx)
        if 'feature_columns' in cfg and hasattr(self, 'feature_checks'):
            selected = set(cfg['feature_columns'] or ['capacity'])
            for name, checkbox in self.feature_checks.items():
                checkbox.setChecked(name in selected)
            self.feature_checks['capacity'].setChecked(True)
        # 数据源配置
        if 'adapter_type' in cfg and hasattr(self, 'adapter_combo'):
            idx = self.adapter_combo.findData(cfg['adapter_type'])
            if idx >= 0:
                self.adapter_combo.setCurrentIndex(idx)
        if 'cc_step' in cfg and hasattr(self, 'cc_step_input'):
            _set_step_input(self.cc_step_input, cfg['cc_step'])
        if 'cv_step' in cfg and hasattr(self, 'cv_step_input'):
            _set_step_input(self.cv_step_input, cfg['cv_step'])
        if 'discharge_step' in cfg and hasattr(self, 'discharge_step_input'):
            _set_step_input(
                self.discharge_step_input, cfg['discharge_step'])
        # 触发适配器切换以更新控件状态
        if hasattr(self, '_on_adapter_changed'):
            self._on_adapter_changed()

    def _save_persisted_config(self):
        # A11：配置里只存"规范键"（'cuda' / 'rated' / 'NASA'），
        # 界面文本只在界面层转换。旧版本把 'GPU (CUDA)' 直接写进 JSON，
        # 导致导入自己保存的配置时 GPU 被静默切回 CPU。
        cfg = {
            'rated_capacity': self.rated_capacity_spin.value(),
            'threshold_ratio': self.threshold_ratio_spin.value(),
            'voltage_upper': self.voltage_upper_spin.value(),
            'voltage_lower': self.voltage_lower_spin.value(),
            'window_size': self.feature_size_spin.value(),
            'epochs': self.epochs_spin.value(),
            'hidden_dim': self.hidden_dim_spin.value(),
            'seed': self.seed_spin.value(),
            'n_seeds': self.n_seeds_spin.value(),
            'mode': self.current_mode,
            'metric': from_ui(
                {'rmse': 'RMSE', 'mae': 'MAE', 'r2': 'R²',
                 'pearson': 'Pearson', 're': 'RE', 'all': '全部'},
                self.metric_combo.currentText(), 'rmse'),
            'device': normalize_device(self.device_combo.currentText()),
            'norm_method': from_ui(
                NORM_UI, self.norm_combo.currentText(), 'rated'),
            'feature_columns': self._selected_features(),
            'n_estimators': self.xgb_n_estimators_spin.value(),
            'learning_rate': self.xgb_learning_rate_spin.value(),
            'max_depth': self.xgb_max_depth_spin.value(),
            'subsample': self.xgb_subsample_spin.value(),
            'colsample_bytree': self.xgb_colsample_bytree_spin.value(),
            'min_samples_leaf': self.rf_min_samples_leaf_spin.value(),
            'max_features': self.rf_max_features_spin.value(),
            'patience': self.xgb_patience_spin.value(),
            'adapter_type': self.adapter_combo.currentData(),
            'cc_step': _step_input_value(self.cc_step_input),
            'cv_step': _step_input_value(self.cv_step_input),
            'discharge_step': _step_input_value(self.discharge_step_input),
        }
        try:
            save_config(cfg)
        except OSError as error:
            self.logger.error(f'配置保存失败：{error}')
            show_message(
                self, 'error', '配置保存失败',
                '无法保存当前配置。请检查 config.json 是否被占用，'
                '以及项目目录是否具有写入权限。')
            return False
        return True

    def _selected_features(self):
        """当前勾选的多特征列（容量必选且排第一）。"""
        if not hasattr(self, 'feature_checks'):
            return ['capacity']
        names = [
            name for name, checkbox in self.feature_checks.items()
            if checkbox.isChecked()
        ]
        if 'capacity' not in names:
            names.insert(0, 'capacity')
        return names

    def closeEvent(self, event):
        if not self._request_worker_stop(timeout_ms=5000, closing=True):
            show_message(
                self, 'warning', '仍在安全停止',
                '训练线程尚未到达安全检查点，窗口暂不关闭。请稍候后再次关闭，避免损坏模型或报告。')
            event.ignore()
            return
        self._save_persisted_config()
        save_geometry(self)          # U4：记住窗口几何
        super().closeEvent(event)

    def build_theme_button(self, parent):
        """右上角悬浮的圆形主题切换按钮（可拖动，替代原顶部条）。

        原来它和标题一起占了一整行顶栏（图二），现在只保留一个圆形图标按钮，
        悬浮在内容之上、可自由拖动，位置按窗口比例记住。
        """
        self.theme_btn = FloatingThemeButton(parent)
        self.theme_btn.clicked.connect(self.toggle_theme)
        # 按钮拖过图表时，让画布整体重绘：matplotlib 画布是 WA_OpaquePaintEvent
        # 的不透明控件，只做局部重绘会在它上面留下竖线状残影。
        self.theme_btn.moved.connect(self._repaint_canvas)
        self._sync_theme_button()
        return self.theme_btn

    def _repaint_canvas(self):
        """强制图表画布全量重绘（悬浮按钮拖动后清除残影）。"""
        canvas = getattr(self, 'canvas', None)
        if canvas is not None:
            canvas.update()

    def _sync_theme_button(self):
        """让按钮图标反映**点击后**会切到的主题（当前深色→显示太阳）。"""
        button = getattr(self, 'theme_btn', None)
        if button is None:
            return
        button.sync_to_theme(self._theme_mode)

    def _reposition_theme_button(self):
        """窗口尺寸变化时，按保存的比例重新贴合悬浮按钮。"""
        button = getattr(self, 'theme_btn', None)
        if button is None:
            return
        button.restore_or_default_position()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_theme_button()

    def init_ui(self):
        # 先应用主题（必须在控件创建前）
        self.apply_theme()

        central = QWidget()
        self.setCentralWidget(central)
        central.setObjectName('central')

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 8)
        main_layout.setSpacing(8)
        central.setLayout(main_layout)

        # 图标导航侧边栏（数据/参数/结果/日志）+ 中央图表工作区
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)

        sidebar_widget = QWidget()
        center_widget = QWidget()

        self.main_splitter.addWidget(sidebar_widget)
        self.main_splitter.addWidget(center_widget)

        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)
        # 侧栏宽度受「最小窗口下图表仍占主导」的约束（见
        # tests/test_ui_polish_layout.py::test_minimum_workspace_keeps_chart_column_dominant），
        # 结果表在窄面板里靠横向滚动 + 省略号 + 工具提示呈现完整信息。
        # 侧栏收起时只剩 64px 轨道；展开时页面栈保证 300px 可用宽度
        self.main_splitter.setSizes([430, 790])
        self.main_splitter.setHandleWidth(2)
        sidebar_widget.setMinimumWidth(76)
        center_widget.setMinimumWidth(500)

        main_layout.addWidget(self.main_splitter, 1)

        self.build_sidebar(sidebar_widget)
        self.build_center_panel(center_widget)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self._set_running_state(False, '准备就绪')

        # 悬浮主题按钮挂在中央控件上（可拖动，随窗口缩放重新贴合）
        self.build_theme_button(central)
        self.theme_btn.raise_()
        self._reposition_theme_button()

    def build_sidebar(self, parent):
        """图标导航侧边栏：窄轨道 + 页面栈（数据/参数/结果/日志）。

        左右两栏合并而来：轨道按钮负责切换页面，中央图表区不再与
        结果/日志分享横向空间。Ctrl+1~4 为页面快捷键。
        """
        layout = QHBoxLayout(parent)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        rail = QFrame()
        rail.setObjectName('navRail')
        rail.setProperty('role', 'navRail')
        rail.setFixedWidth(64)
        rail_layout = QVBoxLayout(rail)
        rail_layout.setContentsMargins(4, 8, 4, 8)
        rail_layout.setSpacing(4)

        self.sidebar_stack = QStackedWidget()
        self.sidebar_stack.setObjectName('sidebarPages')
        self.sidebar_stack.setAccessibleName('侧边栏页面')
        self.sidebar_stack.setMinimumWidth(300)

        self._nav_group = QButtonGroup(self)
        self._nav_group.setExclusive(True)
        self._sidebar_page_index = {}
        self._sidebar_expanded = True
        self._sidebar_expanded_width = 430
        self._nav_shortcuts = []
        for position, (key, label, icon_kind) in enumerate(SIDEBAR_PAGES):
            page = QWidget()
            if key == 'data':
                self.build_data_page(page)
            elif key == 'params':
                self.build_params_page(page)
            elif key == 'result':
                self.build_result_page(page)
            else:
                self.build_log_page(page)
            index = self.sidebar_stack.addWidget(page)
            self._sidebar_page_index[key] = index

            nav_button = QToolButton()
            nav_button.setText(label)
            nav_button.setIcon(get_dialog_icon(icon_kind))
            nav_button.setIconSize(QSize(24, 24))
            nav_button.setToolButtonStyle(
                Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            nav_button.setCheckable(True)
            nav_button.setAutoRaise(True)
            nav_button.setProperty('role', 'navRailButton')
            nav_button.setToolTip(
                f'「{label}」页 (Ctrl+{position + 1})；再次点击当前页可收起侧边栏')
            nav_button.setAccessibleName(f'{label}页导航')
            self._nav_group.addButton(nav_button, index)
            rail_layout.addWidget(nav_button)

            shortcut = QShortcut(QKeySequence(f'Ctrl+{position + 1}'), self)
            shortcut.activated.connect(
                lambda idx=index: self._set_sidebar_index(idx))
            self._nav_shortcuts.append(shortcut)

        rail_layout.addStretch(1)

        # ── 底部：使用指南（详细介绍整个系统的用法） ──
        self.guide_btn = QToolButton()
        self.guide_btn.setText('指南')
        self.guide_btn.setIcon(get_dialog_icon('book'))
        self.guide_btn.setIconSize(QSize(24, 24))
        self.guide_btn.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.guide_btn.setAutoRaise(True)
        self.guide_btn.setProperty('role', 'navRailButton')
        self.guide_btn.setToolTip('打开使用指南（系统用法、数据格式与常见问题）')
        self.guide_btn.setAccessibleName('使用指南')
        self.guide_btn.clicked.connect(self.show_guide)
        rail_layout.addWidget(self.guide_btn)

        self._nav_group.idClicked.connect(self._on_nav_clicked)
        self.sidebar_stack.currentChanged.connect(self._sync_nav_buttons)
        self._nav_group.button(0).setChecked(True)

        layout.addWidget(rail)
        layout.addWidget(self.sidebar_stack, 1)

    def _on_nav_clicked(self, index):
        """点击轨道按钮：已展开时点当前页收起、点其他页切换；收起时展开。"""
        if not self._sidebar_expanded:
            self._set_sidebar_index(index)
        elif self.sidebar_stack.currentIndex() == index:
            self._collapse_sidebar()
        else:
            self.sidebar_stack.setCurrentIndex(index)

    def _collapse_sidebar(self):
        """收起页面栈，只留 64px 轨道；空出的宽度交给图表区。"""
        self._sidebar_expanded = False
        sizes = self.main_splitter.sizes()
        if sizes:
            self._sidebar_expanded_width = max(
                sizes[0], self.sidebar_stack.minimumWidth())
        self.sidebar_stack.setVisible(False)
        total = sum(sizes) or (self.width() - 40)
        rail_width = 76
        self.main_splitter.setSizes(
            [rail_width, max(total - rail_width, 500)])

    def _set_sidebar_index(self, index):
        was_collapsed = not self._sidebar_expanded
        self._sidebar_expanded = True
        self.sidebar_stack.setVisible(True)
        self.sidebar_stack.setCurrentIndex(index)
        if was_collapsed:
            sizes = self.main_splitter.sizes()
            total = sum(sizes) or (self.width() - 40)
            width = getattr(self, '_sidebar_expanded_width', 430)
            self.main_splitter.setSizes(
                [width, max(total - width, 500)])

    def _sync_nav_buttons(self, index):
        button = self._nav_group.button(index)
        if button is not None:
            button.setChecked(True)

    def _show_sidebar_page(self, key):
        index = self._sidebar_page_index.get(key)
        if index is not None:
            self._set_sidebar_index(index)

    def build_data_page(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        file_group = QGroupBox('文件导入')
        file_layout = QVBoxLayout()

        btn_row = QHBoxLayout()
        self.import_btn = AnimatedButton('导入文件', 'default')
        self.import_btn.setShortcut(QKeySequence('Ctrl+O'))
        self.import_btn.setToolTip('导入电池数据文件 (Ctrl+O)')
        self.import_btn.clicked.connect(self.import_files)
        self.import_dir_btn = AnimatedButton('导入文件夹', 'default')
        self.import_dir_btn.setShortcut(QKeySequence('Ctrl+Shift+O'))
        self.import_dir_btn.setToolTip('批量导入电池数据文件夹 (Ctrl+Shift+O)')
        self.import_dir_btn.clicked.connect(self.import_folder)
        self.import_json_btn = AnimatedButton('导入JSON', 'default')
        self.import_json_btn.setShortcut(QKeySequence('Ctrl+Alt+O'))
        self.import_json_btn.setToolTip(
            '从 JSON 配置文件导入全部参数，适用于团队共享配置或复现实验 (Ctrl+Alt+O)')
        self.import_json_btn.clicked.connect(self.import_json_config)
        _configure_button_row(btn_row, (self.import_btn, self.import_dir_btn))

        file_layout.addLayout(btn_row)

        data_summary = QFrame()
        data_summary.setProperty('role', 'dataSummary')
        data_summary_layout = QHBoxLayout(data_summary)
        data_summary_layout.setContentsMargins(10, 7, 10, 7)
        data_summary_layout.setSpacing(8)
        self.data_summary_label = QLabel()
        self.data_summary_label.setProperty('role', 'dataSummaryText')
        self.data_summary_label.setWordWrap(True)
        self.data_summary_count = QLabel('0')
        self.data_summary_count.setProperty('role', 'dataSummaryCount')
        self.data_summary_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        data_summary_layout.addWidget(self.data_summary_label, 1)
        data_summary_layout.addWidget(self.data_summary_count)
        file_layout.addWidget(data_summary)
        self._update_data_summary()

        self.import_list = QListWidget()
        self.import_list.setAccessibleName('已导入的数据文件和文件夹')
        self.import_list.setToolTip('选择项目后按 Delete 可移除')
        self.import_list.keyPressEvent = self.import_list_key_press
        file_layout.addWidget(self.import_list)

        self.delete_btn = AnimatedButton('删除选中', 'danger')
        self.delete_btn.clicked.connect(self.delete_selected_items)
        file_action_row = QHBoxLayout()
        _configure_button_row(
            file_action_row, (self.import_json_btn, self.delete_btn))
        file_layout.addLayout(file_action_row)
        file_group.setLayout(file_layout)

        # ── 数据源配置 ──
        source_group = QGroupBox('数据源')
        source_layout = QFormLayout()

        self.adapter_combo = QComboBox()
        for adapter_name, adapter_display in get_adapter_list():
            self.adapter_combo.addItem(adapter_display, adapter_name)
        self.adapter_combo.currentIndexChanged.connect(self._on_adapter_changed)
        source_layout.addRow('数据格式:', self.adapter_combo)

        source_group.setLayout(source_layout)

        layout.addWidget(source_group, 0, Qt.AlignmentFlag.AlignTop)
        layout.addWidget(file_group, 1)

    def build_params_page(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        param_group = QGroupBox('参数设置')
        param_layout = QVBoxLayout()
        param_layout.setContentsMargins(8, 10, 8, 8)
        param_layout.setSpacing(8)

        self.step_section = CollapsibleSection('设置工步', expanded=False)
        self.cc_step_input = _create_step_input('恒流充电工步')
        self.cv_step_input = _create_step_input('恒压充电工步')
        self.discharge_step_input = _create_step_input('放电工步')
        self.step_section.form_layout.addRow(
            '恒流充电工步:', self.cc_step_input)
        self.step_section.form_layout.addRow(
            '恒压充电工步:', self.cv_step_input)
        self.step_section.form_layout.addRow(
            '放电工步:', self.discharge_step_input)

        battery_section = CollapsibleSection('电池容量与失效判据')
        evaluation_section = CollapsibleSection('评估与验证')
        advanced_section = CollapsibleSection('模型高级参数', expanded=False)
        param_layout.addWidget(self.step_section)
        param_layout.addWidget(battery_section)
        param_layout.addWidget(evaluation_section)
        param_layout.addWidget(advanced_section)
        self._param_rows = []

        def _add_row(section, label_text, widget, modes):
            label = QLabel(label_text)
            # 标签可能带数学符号的富文本标记（斜体变量 / 下标）
            label.setTextFormat(Qt.TextFormat.RichText)
            section.form_layout.addRow(label, widget)
            self._param_rows.append((label, widget, modes))

        self.rated_capacity_spin = QDoubleSpinBox()
        self.rated_capacity_spin.setDecimals(2)
        self.rated_capacity_spin.setRange(0.01, 1000)
        self.rated_capacity_spin.setValue(1.1)
        self.rated_capacity_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        _add_row(battery_section, '额定容量 (Ah)', self.rated_capacity_spin,
                 ['RNN', 'GRU', 'LSTM', 'XGBoost', 'RF'])

        self.threshold_ratio_spin = QDoubleSpinBox()
        self.threshold_ratio_spin.setDecimals(2)
        self.threshold_ratio_spin.setRange(0.01, 1.0)
        self.threshold_ratio_spin.setValue(0.8)
        self.threshold_ratio_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        _add_row(battery_section, '失效阈值比例', self.threshold_ratio_spin,
                 ['RNN', 'GRU', 'LSTM', 'XGBoost', 'RF'])

        self.voltage_upper_spin = QDoubleSpinBox()
        self.voltage_upper_spin.setDecimals(2)
        self.voltage_upper_spin.setRange(1.0, 5.0)
        self.voltage_upper_spin.setSingleStep(0.05)
        self.voltage_upper_spin.setValue(3.8)
        self.voltage_upper_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        _add_row(battery_section, '<i>SOH</i> 上电压 (V)', self.voltage_upper_spin,
                 ['RNN', 'GRU', 'LSTM', 'XGBoost', 'RF'])

        self.voltage_lower_spin = QDoubleSpinBox()
        self.voltage_lower_spin.setDecimals(2)
        self.voltage_lower_spin.setRange(0.5, 5.0)
        self.voltage_lower_spin.setSingleStep(0.05)
        self.voltage_lower_spin.setValue(3.4)
        self.voltage_lower_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        _add_row(battery_section, '<i>SOH</i> 下电压 (V)', self.voltage_lower_spin,
                 ['RNN', 'GRU', 'LSTM', 'XGBoost', 'RF'])

        self.feature_size_spin = QSpinBox()
        self.feature_size_spin.setRange(1, 10000)
        self.feature_size_spin.setValue(64)
        self.feature_size_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        _add_row(evaluation_section, '窗口大小', self.feature_size_spin,
                 ['RNN', 'GRU', 'LSTM', 'XGBoost', 'RF'])

        self.metric_combo = QComboBox()
        self.metric_combo.addItems(['RMSE', 'MAE', 'R²', 'Pearson', 'RE', '全部'])
        _add_row(evaluation_section, '评估指标', self.metric_combo,
                 ['RNN', 'GRU', 'LSTM', 'XGBoost', 'RF'])

        # ---- 多特征输入（A5）：默认只用容量，勾选后启用 HI 特征 ----
        # 标题与说明占通栏一行，说明紧贴“输入特征”字样下方，复选框另起一行
        feature_header = QWidget()
        header_layout = QVBoxLayout(feature_header)
        header_layout.setContentsMargins(0, 0, 0, 2)
        header_layout.setSpacing(2)
        header_layout.addWidget(QLabel('输入特征'))
        self._feature_hint = QLabel(
            '默认只用容量（纯自回归）。勾选 <i>dq</i><sub>v</sub> / '
            '<i>CCCT</i> / <i>CVCT</i> / 内阻后启用多特征输入；'
            '<i>dq</i><sub>v</sub> 是电压窗口内的放电容量（健康指标 '
            '<i>HI</i>），不是 <i>SOH</i>。')
        self._feature_hint.setTextFormat(Qt.TextFormat.RichText)
        self._feature_hint.setProperty('role', 'muted')
        self._feature_hint.setWordWrap(True)
        header_layout.addWidget(self._feature_hint)
        evaluation_section.form_layout.addRow(feature_header)

        feature_widget = QWidget()
        feature_layout = QVBoxLayout(feature_widget)
        feature_layout.setContentsMargins(0, 0, 0, 0)
        feature_layout.setSpacing(2)
        self.feature_checks = {}
        for name, label in FEATURE_OPTIONS.items():
            # QCheckBox 不渲染富文本：复选框只放中文说明，数学符号用
            # 旁边的富文本 QLabel 承载（斜体变量 + 下标，数学排版习惯）。
            text, math_html = FEATURE_LABELS.get(name, (label, ''))
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(4)

            checkbox = QCheckBox(text)
            checkbox.setAccessibleName(label)
            if name == 'capacity':
                checkbox.setChecked(True)
                checkbox.setEnabled(False)      # 容量是预测目标，必选
                checkbox.setToolTip('容量是预测目标，始终参与输入')
            else:
                checkbox.setToolTip(
                    '勾选后模型除容量外还使用该健康指标（HI）。'
                    '注意：递归预测时非容量通道保持窗口末值。')
            row_layout.addWidget(checkbox)
            if math_html:
                math_label = QLabel(math_html)
                math_label.setTextFormat(Qt.TextFormat.RichText)
                math_label.setProperty('role', 'muted')
                math_label.setToolTip(label)
                row_layout.addWidget(math_label)
            row_layout.addStretch(1)
            self.feature_checks[name] = checkbox
            feature_layout.addWidget(row)
        feature_label = QLabel()
        evaluation_section.form_layout.addRow(feature_label, feature_widget)
        all_modes = ['RNN', 'GRU', 'LSTM', 'XGBoost', 'RF']
        self._param_rows.append((feature_header, feature_widget, all_modes))
        self._param_rows.append((feature_label, feature_widget, all_modes))

        # ---- RNN/LSTM/GRU 专用 ----
        self.hidden_dim_spin = QSpinBox()
        self.hidden_dim_spin.setRange(1, 2048)
        self.hidden_dim_spin.setValue(64)
        self.hidden_dim_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        _add_row(advanced_section, '隐藏层维度', self.hidden_dim_spin, ['RNN', 'GRU', 'LSTM'])

        self.epochs_spin = QSpinBox()
        self.epochs_spin.setRange(10, 100000)
        self.epochs_spin.setSingleStep(10)
        self.epochs_spin.setValue(100)
        _add_row(advanced_section, '训练轮数', self.epochs_spin, ['RNN', 'GRU', 'LSTM'])

        self.norm_combo = QComboBox()
        self.norm_combo.addItems(['额定容量归一化', 'MinMax', 'ZScore'])
        _add_row(advanced_section, '归一化方式', self.norm_combo,
                 ['RNN', 'GRU', 'LSTM', 'XGBoost', 'RF'])

        self.device_combo = QComboBox()
        self.device_combo.addItems(['CPU', 'GPU (CUDA)'])
        _add_row(advanced_section, '计算设备', self.device_combo, ['RNN', 'GRU', 'LSTM'])

        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(0, 9999)
        self.seed_spin.setValue(2)
        self.seed_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        _add_row(evaluation_section, '随机种子', self.seed_spin,
                 ['RNN', 'GRU', 'LSTM', 'XGBoost', 'RF'])

        self.n_seeds_spin = QSpinBox()
        self.n_seeds_spin.setRange(1, 20)
        self.n_seeds_spin.setValue(5)
        self.n_seeds_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        # “置信区间”作为第二行小字放在标签下方，标签列更窄、排版更紧凑
        n_seeds_label = QWidget()
        n_seeds_label_layout = QVBoxLayout(n_seeds_label)
        n_seeds_label_layout.setContentsMargins(0, 0, 0, 0)
        n_seeds_label_layout.setSpacing(0)
        n_seeds_label_layout.addWidget(QLabel('多种子数'))
        n_seeds_sub_label = QLabel('置信区间')
        n_seeds_sub_label.setProperty('role', 'muted')
        n_seeds_label_layout.addWidget(n_seeds_sub_label)
        evaluation_section.form_layout.addRow(n_seeds_label, self.n_seeds_spin)
        self._param_rows.append((n_seeds_label, self.n_seeds_spin,
                                 ['RNN', 'GRU', 'LSTM', 'XGBoost', 'RF']))

        # ---- XGBoost 专用 ----
        self.xgb_n_estimators_spin = QSpinBox()
        self.xgb_n_estimators_spin.setRange(10, 10000)
        self.xgb_n_estimators_spin.setValue(100)
        self.xgb_n_estimators_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        _add_row(advanced_section, '树的数量', self.xgb_n_estimators_spin, ['XGBoost'])

        self.xgb_learning_rate_spin = QDoubleSpinBox()
        self.xgb_learning_rate_spin.setDecimals(2)
        self.xgb_learning_rate_spin.setRange(0.01, 1.0)
        self.xgb_learning_rate_spin.setSingleStep(0.01)
        self.xgb_learning_rate_spin.setValue(0.05)
        _add_row(advanced_section, '学习率', self.xgb_learning_rate_spin, ['XGBoost'])

        self.xgb_max_depth_spin = QSpinBox()
        self.xgb_max_depth_spin.setRange(1, 100)
        self.xgb_max_depth_spin.setValue(6)
        _add_row(advanced_section, '树的最大深度', self.xgb_max_depth_spin, ['XGBoost'])

        self.xgb_subsample_spin = QDoubleSpinBox()
        self.xgb_subsample_spin.setDecimals(1)
        self.xgb_subsample_spin.setRange(0.1, 1.0)
        self.xgb_subsample_spin.setSingleStep(0.1)
        self.xgb_subsample_spin.setValue(1.0)
        _add_row(advanced_section, '样本采样比例', self.xgb_subsample_spin, ['XGBoost'])

        self.xgb_colsample_bytree_spin = QDoubleSpinBox()
        self.xgb_colsample_bytree_spin.setDecimals(1)
        self.xgb_colsample_bytree_spin.setRange(0.1, 1.0)
        self.xgb_colsample_bytree_spin.setSingleStep(0.1)
        self.xgb_colsample_bytree_spin.setValue(1.0)
        _add_row(advanced_section, '特征采样比例', self.xgb_colsample_bytree_spin,
                 ['XGBoost'])

        self.xgb_patience_spin = QSpinBox()
        self.xgb_patience_spin.setRange(1, 500)
        self.xgb_patience_spin.setSingleStep(10)
        self.xgb_patience_spin.setValue(20)
        _add_row(advanced_section, '早停批次数', self.xgb_patience_spin, ['XGBoost'])

        # ---- RF 专用 ----
        self.rf_n_estimators_spin = QSpinBox()
        self.rf_n_estimators_spin.setRange(10, 5000)
        self.rf_n_estimators_spin.setValue(100)
        self.rf_n_estimators_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        _add_row(advanced_section, '树的数量', self.rf_n_estimators_spin, ['RF'])

        self.rf_max_depth_spin = QSpinBox()
        self.rf_max_depth_spin.setRange(1, 200)
        self.rf_max_depth_spin.setValue(10)
        _add_row(advanced_section, '树的最大深度', self.rf_max_depth_spin, ['RF'])

        self.rf_min_samples_leaf_spin = QSpinBox()
        self.rf_min_samples_leaf_spin.setRange(1, 100)
        self.rf_min_samples_leaf_spin.setValue(1)
        _add_row(advanced_section, '叶节点最小样本数', self.rf_min_samples_leaf_spin, ['RF'])

        self.rf_max_features_spin = QDoubleSpinBox()
        self.rf_max_features_spin.setDecimals(1)
        self.rf_max_features_spin.setRange(0.1, 1.0)
        self.rf_max_features_spin.setSingleStep(0.1)
        self.rf_max_features_spin.setValue(1.0)
        _add_row(advanced_section, '最大特征比例', self.rf_max_features_spin, ['RF'])

        self.rf_patience_spin = QSpinBox()
        self.rf_patience_spin.setRange(1, 500)
        self.rf_patience_spin.setSingleStep(10)
        self.rf_patience_spin.setValue(20)
        _add_row(advanced_section, '早停批次数', self.rf_patience_spin, ['RF'])

        param_group.setLayout(param_layout)

        # 把“参数设置”放入可滚动区域，避免窗口高度不足时控件被压缩
        param_scroll = QScrollArea()
        param_scroll.setWidgetResizable(True)
        param_scroll.setFrameShape(QFrame.Shape.NoFrame)
        param_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        param_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        param_scroll.setWidget(param_group)

        layout.addWidget(param_scroll, 1)

        self.help_btn = AnimatedButton('帮助', 'ghost')
        self.help_btn.setShortcut(QKeySequence('F1'))
        self.help_btn.setToolTip('查看当前模型参数说明 (F1)')
        self.help_btn.clicked.connect(self.show_help)
        self.help_btn.setMaximumWidth(80)
        layout.addWidget(self.help_btn, 0, Qt.AlignmentFlag.AlignLeft)

        self._help_dialog = None
        self._guide_dialog = None
        self._update_param_panel('RNN')

    def build_center_panel(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(6, 0, 6, 0)
        layout.setSpacing(8)

        model_shelf = QFrame()
        model_shelf.setProperty('role', 'modelShelf')
        model_shelf_layout = QVBoxLayout(model_shelf)
        model_shelf_layout.setContentsMargins(10, 7, 10, 9)
        model_shelf_layout.setSpacing(6)

        model_header_layout = QHBoxLayout()
        model_label = QLabel('选择评估模型')
        model_label.setProperty('role', 'sectionTitle')
        self.model_hint_label = QLabel()
        self.model_hint_label.setProperty('role', 'modelHint')
        self.model_hint_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        model_header_layout.addWidget(model_label)
        model_header_layout.addStretch(1)
        model_header_layout.addWidget(self.model_hint_label)
        model_shelf_layout.addLayout(model_header_layout)

        btn_layout = QHBoxLayout()
        self.rnn_btn = AnimatedButton('RNN', 'model')
        self.gru_btn = AnimatedButton('GRU', 'model')
        self.lstm_btn = AnimatedButton('LSTM', 'model')
        self.xgboost_btn = AnimatedButton('XGBoost', 'model')
        self.rf_btn = AnimatedButton('RF', 'model')

        self.rnn_btn.clicked.connect(lambda: self.select_mode('RNN'))
        self.gru_btn.clicked.connect(lambda: self.select_mode('GRU'))
        self.lstm_btn.clicked.connect(lambda: self.select_mode('LSTM'))
        self.xgboost_btn.clicked.connect(lambda: self.select_mode('XGBoost'))
        self.rf_btn.clicked.connect(lambda: self.select_mode('RF'))

        _configure_button_row(
            btn_layout,
            (self.rnn_btn, self.gru_btn, self.lstm_btn,
             self.xgboost_btn, self.rf_btn),
            spacing=6)
        model_shelf_layout.addLayout(btn_layout)

        action_layout = QHBoxLayout()

        io_layout = QHBoxLayout()
        self.save_model_btn = AnimatedButton('保存模型', 'default')
        self.load_model_btn = AnimatedButton('加载模型', 'default')
        self.unload_model_btn = AnimatedButton('卸载模型', 'default')
        self.tcp_btn = AnimatedButton('接入数据', 'default')

        self.save_model_btn.clicked.connect(self.save_model)
        self.load_model_btn.clicked.connect(self.load_model)
        self.unload_model_btn.clicked.connect(self.unload_model)
        self.load_model_btn.setShortcut(QKeySequence('Ctrl+L'))
        self.load_model_btn.setToolTip('加载已有模型 (Ctrl+L)')
        self.unload_model_btn.setToolTip('卸载当前模型并切回训练模式')
        self.tcp_btn.clicked.connect(self.toggle_tcp_server)
        self.tcp_btn.setToolTip('接入实时容量数据（实验功能，默认仅监听本机）')

        # A10：默认只监听 127.0.0.1；开放局域网必须显式勾选
        self.tcp_lan_check = QCheckBox('允许局域网访问')
        self.tcp_lan_check.setToolTip(
            '勾选后服务将监听 0.0.0.0 并自动生成访问 token；'
            '仅在可信网络中临时启用。')
        self.tcp_lan_check.setAccessibleName('允许局域网访问 TCP 服务')

        self.save_model_btn.setEnabled(False)
        self.unload_model_btn.setEnabled(False)
        self.tcp_btn.setEnabled(False)

        _configure_button_row(
            io_layout, (self.save_model_btn, self.load_model_btn,
                        self.unload_model_btn, self.tcp_btn))
        io_layout.addWidget(self.tcp_lan_check)

        self.start_btn = AnimatedButton('开始评估', 'hero')
        self.start_btn.setShortcut(QKeySequence('Ctrl+Return'))
        self.start_btn.setToolTip('使用当前数据和参数开始评估 (Ctrl+Enter)')
        self.start_btn.clicked.connect(self.start_evaluation)
        self.start_btn.setMinimumHeight(48)

        action_layout.addWidget(self.start_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setVisible(False)

        self.run_status_label = QLabel('准备就绪')
        self.run_status_label.setProperty('role', 'runStatus')
        self.run_status_label.setProperty('state', 'idle')
        self.run_status_label.setAccessibleName('评估运行状态')

        run_status_strip = QFrame()
        run_status_strip.setProperty('role', 'runStatusStrip')
        run_status_layout = QHBoxLayout(run_status_strip)
        run_status_layout.setContentsMargins(10, 5, 10, 5)
        run_status_layout.setSpacing(8)
        self.run_status_dot = QFrame()
        self.run_status_dot.setProperty('role', 'runStatusDot')
        self.run_status_dot.setProperty('state', 'idle')
        self.run_status_dot.setFixedSize(10, 10)
        self.run_status_dot.setAccessibleName('评估状态指示')
        run_status_layout.addWidget(self.run_status_dot)
        run_status_layout.addWidget(self.run_status_label, 1)

        context_label = QLabel('当前模型与参数仅在本地运行')
        context_label.setProperty('role', 'runContext')
        run_status_layout.addWidget(context_label)

        self.canvas = MplCanvas()
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.canvas.setToolTip(
            '右键图表可选择全屏查看当前子图或全部子图；按 Esc 退出全屏')

        self.toolbar = CustomToolbar(self.canvas, self)

        layout.addWidget(model_shelf)
        layout.addLayout(io_layout)
        layout.addLayout(action_layout)
        layout.addWidget(run_status_strip)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas, 1)

        self.select_mode('RNN')

    def build_result_page(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        title = QLabel('评估结果')
        title.setProperty('role', 'pageTitle')
        layout.addWidget(title)

        self.result_batch_bar = QFrame()
        self.result_batch_bar.setProperty('role', 'resultBatchBar')
        batch_layout = QHBoxLayout(self.result_batch_bar)
        batch_layout.setContentsMargins(8, 5, 8, 5)
        batch_layout.setSpacing(8)
        batch_label = QLabel('结果批次')
        batch_label.setProperty('role', 'resultBatchLabel')
        self.result_batch_combo = QComboBox()
        self.result_batch_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.result_batch_combo.setMinimumContentsLength(18)
        self.result_batch_combo.setAccessibleName('选择要查看的训练或预测结果批次')
        self.result_batch_combo.currentIndexChanged.connect(
            self._display_result_batch)
        batch_layout.addWidget(batch_label)
        batch_layout.addWidget(self.result_batch_combo, 1)
        self.result_batch_bar.setVisible(False)
        layout.addWidget(self.result_batch_bar)

        self.result_summary = QFrame()
        self.result_summary.setProperty('role', 'resultSummary')
        summary_layout = QVBoxLayout(self.result_summary)
        summary_layout.setContentsMargins(12, 9, 12, 9)
        summary_layout.setSpacing(3)
        summary_top = QHBoxLayout()
        summary_top.setContentsMargins(0, 0, 0, 0)
        self.result_summary_title = QLabel()
        self.result_summary_title.setProperty('role', 'resultSummaryTitle')
        self.result_summary_metric = QLabel()
        self.result_summary_metric.setProperty('role', 'resultSummaryMetric')
        self.result_summary_metric.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        summary_top.addWidget(self.result_summary_title, 1)
        summary_top.addWidget(self.result_summary_metric)
        self.result_summary_meta = QLabel()
        self.result_summary_meta.setProperty('role', 'resultSummaryMeta')
        summary_layout.addLayout(summary_top)
        summary_layout.addWidget(self.result_summary_meta)
        self.result_summary.setVisible(False)
        layout.addWidget(self.result_summary)

        self.result_scroll = QScrollArea()
        self.result_scroll.setWidgetResizable(True)
        self.result_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.result_container = QWidget()
        self.result_container.setProperty('role', 'resultContainer')
        self.result_container_layout = QVBoxLayout(self.result_container)
        self.result_container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.result_container_layout.setSpacing(8)

        # ── U1：可排序结果表（取代 N 张卡片竖排） ──
        self.result_model = ResultTableModel(
            [], tokens=theme_tokens(self._theme_mode))
        self.result_proxy = QSortFilterProxyModel()
        self.result_proxy.setSourceModel(self.result_model)
        # 用 UserRole 里的原始值排序，而不是格式化后的字符串
        self.result_proxy.setSortRole(Qt.ItemDataRole.UserRole)
        self.result_view = QTableView()
        self.result_view.setModel(self.result_proxy)
        self.result_view.setSortingEnabled(True)
        self.result_view.setAlternatingRowColors(True)
        self.result_view.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self.result_view.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self.result_view.verticalHeader().setVisible(False)
        # U1：显式列宽（ResizeToContents 会被汇总行撑到 1200px 以上），
        # 超出部分省略号显示，完整值在工具提示里。
        header = self.result_view.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        header.setDefaultAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.result_view.setTextElideMode(Qt.TextElideMode.ElideRight)
        for index, column in enumerate(COLUMNS):
            self.result_view.setColumnWidth(
                index, COLUMN_WIDTHS.get(column[1], 74))
        self.result_view.setAccessibleName('评估结果表，点击列头可排序')
        self.result_view.setMinimumHeight(180)
        self.result_container_layout.addWidget(self.result_view)

        # 起点选择 + 导出 CSV（U1.6）
        result_tools = QHBoxLayout()
        result_tools.setContentsMargins(0, 0, 0, 0)
        result_tools.setSpacing(6)
        self.start_frac_combo = QComboBox()
        self.start_frac_combo.setAccessibleName('选择滚动预测起点')
        self.start_frac_combo.currentIndexChanged.connect(
            self._on_start_frac_changed)
        start_label = QLabel('预测起点')
        start_label.setProperty('role', 'muted')
        result_tools.addWidget(start_label)
        result_tools.addWidget(self.start_frac_combo)
        result_tools.addStretch(1)
        self.copy_table_btn = QPushButton('复制表格')
        self.copy_table_btn.setProperty('role', 'ghost')
        self.copy_table_btn.clicked.connect(self._copy_result_table)
        self.csv_btn = QPushButton('导出 CSV')
        self.csv_btn.setProperty('role', 'ghost')
        self.csv_btn.clicked.connect(self._export_result_csv)
        result_tools.addWidget(self.copy_table_btn)
        result_tools.addWidget(self.csv_btn)
        self.result_container_layout.addLayout(result_tools)

        # 基线与口径说明
        self.result_notes = QLabel()
        self.result_notes.setProperty('role', 'muted')
        self.result_notes.setWordWrap(True)
        self.result_notes.setVisible(False)
        self.result_container_layout.addWidget(self.result_notes)

        self.result_scroll.setWidget(self.result_container)
        self._show_result_state(
            '等待评估结果',
            '导入数据并开始评估后，这里会显示滚动起点的 RMSE、'
            'RUL 误差与相对平推的技能分。')

        layout.addWidget(self.result_scroll)

        op_layout = QHBoxLayout()
        self.pause_btn = AnimatedButton('停止', 'danger')
        self.pause_btn.setEnabled(False)
        self.pause_btn.setShortcut(QKeySequence('Esc'))
        self.pause_btn.setToolTip('停止当前评估 (Esc)')
        self.pause_btn.clicked.connect(self.pause_evaluation)

        self.save_chart_btn = AnimatedButton('保存图表', 'default')
        self.save_chart_btn.clicked.connect(self.save_chart)

        self.export_btn = AnimatedButton('导出报告', 'success')
        self.export_btn.clicked.connect(self.export_report)
        self.export_btn.setEnabled(False)

        _configure_button_row(
            op_layout, (self.pause_btn, self.save_chart_btn, self.export_btn))
        layout.addLayout(op_layout)

    def build_log_page(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        title = QLabel('训练日志')
        title.setProperty('role', 'pageTitle')
        layout.addWidget(title)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setAccessibleName('训练日志')
        layout.addWidget(self.log_text)

    def _set_running_state(self, running, message):
        """同步主操作、停止按钮、进度和状态文字。"""
        if running:
            self._show_sidebar_page('log')
        locked_controls = [
            self.import_btn, self.import_dir_btn, self.import_json_btn,
            self.delete_btn, self.import_list,
            self.rnn_btn, self.gru_btn, self.lstm_btn,
            self.xgboost_btn, self.rf_btn,
            self.load_model_btn, self.save_model_btn,
            self.unload_model_btn, self.tcp_btn,
            self.save_chart_btn, self.export_btn,
        ]
        locked_controls.extend(
            widget for _, widget, _ in getattr(self, '_param_rows', []))
        locked_controls.extend([
            self.adapter_combo, self.cc_step_input, self.cv_step_input,
            self.discharge_step_input,
        ])
        for control in locked_controls:
            control.setEnabled(not running)
        if not running:
            self.save_model_btn.setEnabled(self.final_trained_model is not None)
            self.unload_model_btn.setEnabled(self.loaded_model is not None)
            self.tcp_btn.setEnabled(self.loaded_model is not None)
            self.export_btn.setEnabled(bool(getattr(self, '_last_detail', None)))
            self._on_adapter_changed()
        self.start_btn.setEnabled(not running)
        self.pause_btn.setEnabled(running)
        self.progress_bar.setVisible(running)
        self.run_status_label.setText(message)
        self.run_status_label.setProperty('state', 'running' if running else 'idle')
        self.run_status_label.style().unpolish(self.run_status_label)
        self.run_status_label.style().polish(self.run_status_label)
        self.run_status_dot.setProperty('state', 'running' if running else 'idle')
        self.run_status_dot.style().unpolish(self.run_status_dot)
        self.run_status_dot.style().polish(self.run_status_dot)
        if hasattr(self, 'status_bar'):
            self.status_bar.showMessage(message)

    def select_mode(self, selected_mode):
        selected_mode = normalize_model_name(selected_mode)
        self.current_mode = selected_mode
        buttons = {
            'RNN': self.rnn_btn, 'GRU': self.gru_btn, 'LSTM': self.lstm_btn,
            'XGBoost': self.xgboost_btn, 'RF': self.rf_btn
        }
        for m, btn in buttons.items():
            btn.set_active(m == selected_mode)
        descriptions = {
            'RNN': '循环神经网络 · 时序基线',
            'GRU': '门控循环单元 · 轻量时序',
            'LSTM': '长短期记忆网络 · 长程依赖',
            'XGBoost': '梯度提升树 · 表格特征',
            'RF': '随机森林 · 稳健集成',
        }
        self.model_hint_label.setText(descriptions[selected_mode])
        self._update_param_panel(selected_mode)
        if self._help_dialog is not None and self._help_dialog.isVisible():
            self._help_dialog.set_content(selected_mode)

    def _update_param_panel(self, mode):
        for label, widget, modes in self._param_rows:
            visible = mode in modes
            label.setVisible(visible)
            widget.setVisible(visible)

    def _on_adapter_changed(self):
        """切换数据源适配器时更新工步设置说明。"""
        from core.adapters import ADAPTERS
        adapter_name = self.adapter_combo.currentData()
        adapter_cls = ADAPTERS.get(adapter_name)
        if adapter_cls is None:
            return
        needs_steps = adapter_cls.needs_step_config()
        tooltip = (
            '留空表示“无”；请输入非负整数。当前数据格式将使用此工步设置'
            if needs_steps else
            '留空表示“无”；请输入非负整数。当前数据格式不读取工步，仍可提前自定义')
        for step_input in (
                self.cc_step_input, self.cv_step_input,
                self.discharge_step_input):
            step_input.setToolTip(tooltip)

    def import_files(self):
        from core.adapters import ADAPTERS
        adapter_name = self.adapter_combo.currentData()
        adapter_cls = ADAPTERS.get(adapter_name)
        exts = adapter_cls.extensions() if adapter_cls else ('.xlsx', '.csv')
        ext_filter = ' '.join(f'*{e}' for e in exts)
        paths, _ = QFileDialog.getOpenFileNames(
            self, '选择电池数据文件', '',
            f'数据文件 ({ext_filter});;所有文件 (*.*)')
        if not paths:
            return
        for path in paths:
            if path in self.imported_paths:
                continue
            self.imported_paths.append(path)
            display = os.path.basename(path)
            self.import_list.addItem(display)
        self._update_data_summary()

    def import_folder(self):
        dlg = QFileDialog(self, '选择电池数据文件夹')
        dlg.setFileMode(QFileDialog.FileMode.Directory)
        dlg.setOption(QFileDialog.Option.ShowDirsOnly, True)
        dlg.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        _configure_folder_dialog(dlg)
        for view in dlg.findChildren(QAbstractItemView):
            view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        if dlg.exec() != QFileDialog.DialogCode.Accepted:
            return
        folders = dlg.selectedFiles()
        if not folders:
            return
        for folder in folders:
            if folder in self.imported_paths:
                continue
            self.imported_paths.append(folder)
            from core.adapters import ADAPTERS
            adapter_name = self.adapter_combo.currentData()
            adapter_cls = ADAPTERS.get(adapter_name)
            exts = adapter_cls.extensions() if adapter_cls else ('.xlsx', '.csv')
            total = 0
            for ext in exts:
                total += len(glob.glob(os.path.join(folder, f'*{ext}')))
            folder_name = os.path.basename(folder.rstrip('/\\'))
            display = f'{folder_name}（{total}）'
            self.import_list.addItem(display)
        self._update_data_summary()

    def import_json_config(self):
        file_path, _ = QFileDialog.getOpenFileName(self, '导入 JSON 配置文件', '', 'JSON 文件 (*.json)')
        if not file_path:
            return
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            imported_config = TrainConfig.from_dict(data)
            self._apply_train_config(imported_config)

            self.append_log(f'已从 {os.path.basename(file_path)} 加载JSON配置')
            self.logger.info(f'已从 {file_path} 导入JSON配置')

            if data.get('auto_start', False):
                self.start_evaluation()

        except Exception as e:
            show_message(self, 'error', '错误', f'导入 JSON 文件失败：{e}')
            self.logger.error(f'导入 JSON 配置失败：{e}')

    def _apply_train_config(self, config):
        """Apply a validated TrainConfig to every corresponding UI control."""
        self.rated_capacity_spin.setValue(config.rated_capacity)
        self.threshold_ratio_spin.setValue(config.threshold_ratio)
        self.voltage_upper_spin.setValue(config.voltage_upper)
        self.voltage_lower_spin.setValue(config.voltage_lower)
        self.feature_size_spin.setValue(config.window_size)
        self.epochs_spin.setValue(config.epochs)
        self.hidden_dim_spin.setValue(config.hidden_dim)
        self.seed_spin.setValue(config.seed)
        self.n_seeds_spin.setValue(config.n_seeds)

        metric_text = {
            'rmse': 'RMSE', 'mae': 'MAE', 'r2': 'R²',
            'pearson': 'Pearson', 're': 'RE', 'all': '全部',
        }[config.metric]
        norm_text = {
            'rated': '额定容量归一化',
            'minmax': 'MinMax',
            'zscore': 'ZScore',
        }[config.norm_method]
        self.metric_combo.setCurrentText(metric_text)
        self.norm_combo.setCurrentText(norm_text)
        self.device_combo.setCurrentText(
            'GPU (CUDA)' if config.device == 'cuda' else 'CPU')

        self.xgb_n_estimators_spin.setValue(config.n_estimators)
        self.xgb_learning_rate_spin.setValue(config.learning_rate)
        self.xgb_max_depth_spin.setValue(config.max_depth)
        self.xgb_subsample_spin.setValue(config.subsample)
        self.xgb_colsample_bytree_spin.setValue(config.colsample_bytree)
        self.xgb_patience_spin.setValue(config.patience)

        self.rf_n_estimators_spin.setValue(config.n_estimators)
        self.rf_max_depth_spin.setValue(config.max_depth)
        self.rf_min_samples_leaf_spin.setValue(config.min_samples_leaf)
        self.rf_max_features_spin.setValue(config.max_features)
        self.rf_patience_spin.setValue(config.patience)

        adapter_index = self.adapter_combo.findData(config.adapter_type)
        if adapter_index < 0:
            raise ValueError(f'不支持的数据适配器: {config.adapter_type}')
        self.adapter_combo.setCurrentIndex(adapter_index)
        _set_step_input(self.cc_step_input, config.cc_step)
        _set_step_input(self.cv_step_input, config.cv_step)
        _set_step_input(self.discharge_step_input, config.discharge_step)
        self.select_mode(config.mode)

    def import_list_key_press(self, event):
        if event.key() == Qt.Key.Key_Delete:
            self.delete_selected_items()
        else:
            QListWidget.keyPressEvent(self.import_list, event)

    def delete_selected_items(self):
        rows = sorted([idx.row() for idx in self.import_list.selectedIndexes()], reverse=True)
        if not rows:
            show_message(self, 'info', '提示', '请先在列表中选中要删除的项目。')
            return
        for row in rows:
            self.import_list.takeItem(row)
            if row < len(self.imported_paths):
                del self.imported_paths[row]
        self._update_data_summary()

    def _update_data_summary(self):
        """同步数据队列摘要，不在狭窄列表中重复堆叠状态信息。"""
        count = len(self.imported_paths)
        if count:
            self.data_summary_label.setText(f'已载入 {count} 项数据 · 队列待评估')
        else:
            self.data_summary_label.setText('尚未导入数据 · 等待建立评估队列')
        self.data_summary_label.setProperty(
            'state', 'ready' if count else 'empty')
        self.data_summary_count.setText(str(count))
        self.data_summary_count.setAccessibleName(f'已导入 {count} 项数据')
        for widget in (self.data_summary_label, self.data_summary_count):
            widget.style().unpolish(widget)
            widget.style().polish(widget)

    def append_log(self, text):
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(str(text))
        cursor.insertBlock()
        self.logger.info(str(text))

    def _build_config(self):
        norm_map = {'额定容量归一化': 'rated', 'MinMax': 'minmax', 'ZScore': 'zscore'}
        metric_map = {'RMSE': 'rmse', 'MAE': 'mae', 'R²': 'r2', 'Pearson': 'pearson', 'RE': 're', '全部': 'all'}
        device_text = self.device_combo.currentText()
        target_device = 'cpu'
        if device_text == 'GPU (CUDA)' and torch.cuda.is_available():
            target_device = 'cuda'

        config = TrainConfig(
            rated_capacity=self.rated_capacity_spin.value(),
            threshold_ratio=self.threshold_ratio_spin.value(),
            voltage_upper=self.voltage_upper_spin.value(),
            voltage_lower=self.voltage_lower_spin.value(),
            window_size=self.feature_size_spin.value(),
            hidden_dim=self.hidden_dim_spin.value(),
            epochs=self.epochs_spin.value(),
            mode=self.current_mode,
            metric=metric_map[self.metric_combo.currentText()],
            device=target_device,
            norm_method=norm_map[self.norm_combo.currentText()],
            adapter_type=self.adapter_combo.currentData(),
            cc_step=_step_input_value(self.cc_step_input),
            cv_step=_step_input_value(self.cv_step_input),
            discharge_step=_step_input_value(self.discharge_step_input),
        )

        config.seed = self.seed_spin.value()
        config.n_seeds = self.n_seeds_spin.value()
        config.patience = self.xgb_patience_spin.value()

        if self.current_mode == 'XGBoost':
            config.n_estimators = self.xgb_n_estimators_spin.value()
            config.learning_rate = self.xgb_learning_rate_spin.value()
            config.max_depth = self.xgb_max_depth_spin.value()
            config.subsample = self.xgb_subsample_spin.value()
            config.colsample_bytree = self.xgb_colsample_bytree_spin.value()
            config.patience = self.xgb_patience_spin.value()
        elif self.current_mode == 'RF':
            config.n_estimators = self.rf_n_estimators_spin.value()
            config.max_depth = self.rf_max_depth_spin.value()
            config.min_samples_leaf = self.rf_min_samples_leaf_spin.value()
            config.max_features = self.rf_max_features_spin.value()
            config.patience = self.rf_patience_spin.value()

        return config

    def start_evaluation(self):
        if self.worker is not None:
            show_message(
                self, 'info', '任务仍在收尾',
                '当前训练或预测任务尚未完全结束。请等待状态恢复为“准备就绪”后再开始新的任务。')
            return
        if len(self.imported_paths) == 0:
            show_message(self, 'warning', '提示', '请先导入文件或文件夹。')
            return
        config = self._build_config()
        from core.validation import validate_training_config
        errors = validate_training_config(config)
        if errors:
            visible_errors = errors[:10]
            suffix = (
                f'\n……另有 {len(errors) - 10} 项错误'
                if len(errors) > 10 else '')
            show_message(
                self, 'warning', '数据校验未通过',
                '\n'.join(f'• {error}' for error in visible_errors) + suffix)
            return

        if self.loaded_model is not None:
            self._run_prediction(config)
            return

        destination = 'current'
        if self._has_completed_training_run:
            destination = self._ask_training_destination()
        if destination == 'current':
            self._run_training(config)
        elif destination == 'new':
            self._launch_training_window(config)

    def _ask_training_destination(self):
        dialog = QMessageBox(self)
        dialog.setWindowTitle('开始新的模型训练')
        dialog.setWindowIcon(get_dialog_icon('chart'))
        dialog.setIcon(QMessageBox.Icon.Question)
        dialog.setText('当前窗口已经保留了一次模型训练结果。')
        dialog.setInformativeText(
            '请选择在当前窗口继续，或复制当前数据与参数到新的完整窗口中训练。'
            '在当前窗口训练会清空旧日志，但不会删除已有结果批次。')
        current_button = dialog.addButton(
            '在此窗口训练', QMessageBox.ButtonRole.AcceptRole)
        new_button = dialog.addButton(
            '在新窗口训练', QMessageBox.ButtonRole.ActionRole)
        cancel_button = dialog.addButton(
            '取消', QMessageBox.ButtonRole.RejectRole)
        dialog.setDefaultButton(cancel_button)
        dialog.setEscapeButton(cancel_button)
        _apply_windows_paper_caption(dialog)
        dialog.exec()
        clicked = dialog.clickedButton()
        if clicked is current_button:
            return 'current'
        if clicked is new_button:
            return 'new'
        return None

    def _launch_training_window(self, config):
        child = MainWindow()
        child_config = TrainConfig.from_dict(config.to_dict())
        child._apply_train_config(child_config)
        child.imported_paths = list(self.imported_paths)
        child.import_list.clear()
        for index, path in enumerate(child.imported_paths):
            if index < self.import_list.count():
                display = self.import_list.item(index).text()
            else:
                display = os.path.basename(path.rstrip('/\\')) or path
            child.import_list.addItem(display)
        child._update_data_summary()

        self._child_training_windows.append(child)
        MainWindow._independent_windows.append(child)
        child.destroyed.connect(
            lambda _object=None, window=child:
            self._forget_training_window(window))
        child.show()
        child.raise_()
        child.activateWindow()
        child._run_training(child_config)
        return child

    def _forget_training_window(self, window):
        if window in self._child_training_windows:
            self._child_training_windows.remove(window)
        if window in MainWindow._independent_windows:
            MainWindow._independent_windows.remove(window)

    def _run_training(self, config):
        self._active_run_kind = 'training'
        self._finish_status_message = '准备就绪'
        self._active_run_snapshot = RunSnapshot.capture(
            config, self.imported_paths)
        config = TrainConfig.from_dict(
            self._active_run_snapshot.config_dict())
        imported_paths = self._active_run_snapshot.imported_paths
        self._eval_rated_capacity = config.rated_capacity
        self._eval_threshold_ratio = config.threshold_ratio

        self.log_text.clear()
        if not self._result_batches:
            self._show_result_state(
                '正在分析电池数据',
                '训练日志会持续更新。可随时点击“停止”结束当前任务。')
        self._set_running_state(True, '正在训练模型')
        self.logger.info(f'开始评估，配置：{config}')

        self.worker = EvalWorker(config, imported_paths, parent=self)
        self.worker.log_signal.connect(self.append_log)
        self.worker.error_signal.connect(self.on_error)
        self.worker.result_signal.connect(self.on_result)
        self.worker.progress_signal.connect(self.on_progress)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.finished.connect(self.on_finished)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.final_model_signal.connect(self.on_final_model_ready)
        self.worker.start()

    def _run_prediction(self, config):
        self._active_run_kind = 'prediction'
        self._finish_status_message = '准备就绪'
        config.window_size = self.loaded_metadata['window_size']
        if 'rated_capacity' in self.loaded_metadata:
            config.rated_capacity = self.loaded_metadata['rated_capacity']
        if 'threshold_ratio' in self.loaded_metadata:
            config.threshold_ratio = self.loaded_metadata['threshold_ratio']
        self._active_run_snapshot = RunSnapshot.capture(
            config, self.imported_paths)
        config = TrainConfig.from_dict(
            self._active_run_snapshot.config_dict())
        imported_paths = self._active_run_snapshot.imported_paths
        self._eval_rated_capacity = config.rated_capacity
        self._eval_threshold_ratio = config.threshold_ratio

        self.log_text.clear()
        if not self._result_batches:
            self._show_result_state(
                '正在分析电池数据',
                '正在使用已加载模型生成预测结果。')
        self._set_running_state(True, '正在生成预测')

        from ui.predict_worker import PredictWorker
        self.worker = PredictWorker(
            self.loaded_model, self.loaded_metadata,
            imported_paths, config, parent=self
        )
        self.worker.log_signal.connect(self.append_log)
        self.worker.error_signal.connect(self.on_error)
        self.worker.result_signal.connect(self.on_result)
        self.worker.progress_signal.connect(self.on_progress)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.finished.connect(self.on_finished)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()

    def pause_evaluation(self):
        if self.worker is not None and self.worker.isRunning():
            self.pause_btn.setEnabled(False)
            self.run_status_label.setText('正在安全停止，请稍候…')
            if self._request_worker_stop(timeout_ms=3000):
                self.append_log('评估已在安全检查点停止。')
                self._set_running_state(False, '评估已停止')
                if self._result_batches:
                    self._show_sidebar_page('result')
                else:
                    self._show_result_state(
                        '评估已停止', '参数和导入数据均已保留，可调整后重新开始。')
            else:
                show_message(
                    self, 'warning', '仍在安全停止',
                    '当前计算尚未到达安全检查点。系统不会强制终止，请稍候；停止完成前不能开始新任务或导出报告。')

    def _request_worker_stop(self, timeout_ms, closing=False):
        worker = self.worker
        if worker is None or not worker.isRunning():
            self.worker = None
            return True
        worker.request_stop()
        worker.requestInterruption()
        if worker.wait(timeout_ms):
            self.on_finished(worker)
            return True
        if not closing:
            self._set_running_state(True, '正在安全停止，请稍候…')
            self.pause_btn.setEnabled(False)
        return False

    def save_model(self):
        if self.final_trained_model is None:
            show_message(self, 'warning', '提示', '请先完成训练后再保存模型。')
            return
        default_ext = '.pt' if self.current_mode in ('RNN', 'GRU', 'LSTM') else '.joblib'
        filepath, _ = QFileDialog.getSaveFileName(
            self, '保存模型',
            os.fspath(MODEL_DIR / f'model{default_ext}'),
            '模型文件 (*.pt *.pth *.joblib);;所有文件 (*.*)')
        if not filepath:
            return
        try:
            from core.model_persistence import save_model
            save_model(self.final_trained_model, self.final_trained_metadata, filepath)
            self.append_log(f'模型已保存至 {filepath}')
        except Exception as e:
            show_message(self, 'error', '错误', f'保存模型失败：{e}')

    def load_model(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, '加载模型', os.fspath(OUTPUTS_DIR),
            '模型文件 (*.pt *.pth *.joblib);;所有文件 (*.*)')
        if not filepath:
            return
        allow_unsafe_joblib = False
        if os.path.splitext(filepath)[1].lower() == '.joblib':
            answer = show_message(
                self, 'warning', '安全提醒',
                'joblib 模型在加载时可能执行代码。仅当文件由本系统生成、来源可信且哈希清单未被替换时继续。是否加载？',
                buttons=(QMessageBox.StandardButton.Yes |
                         QMessageBox.StandardButton.No),
                default=QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                return
            allow_unsafe_joblib = True
        try:
            self.load_model_from_path(
                filepath, allow_unsafe_joblib=allow_unsafe_joblib)
        except Exception as e:
            show_message(self, 'error', '错误', f'加载模型失败：{e}')

    def load_model_from_path(self, filepath, allow_unsafe_joblib=False):
        """Validate a new model completely, then atomically replace the session."""
        from core.model_persistence import load_model
        new_model, new_metadata = load_model(
            filepath, allow_unsafe_joblib=allow_unsafe_joblib)
        mode = normalize_model_name(new_metadata['mode'])
        self.select_mode(mode)

        self.loaded_model, self.loaded_metadata = new_model, new_metadata
        self.unload_model_btn.setEnabled(True)
        self.tcp_btn.setEnabled(True)
        self.append_log(f'已加载 {mode} 模型：{os.path.basename(filepath)}')
        self.append_log(
            f'  窗口大小={new_metadata["window_size"]}，'
            f'额定容量={new_metadata.get("rated_capacity", "-")}')
        self.status_bar.showMessage(
            f'已加载 {mode} 模型，导入数据后点击启动即可预测')
        return new_model, new_metadata

    def unload_model(self):
        """Unload the imported model so the main action trains a new model again."""
        if self.tcp_running:
            show_message(self, 'warning', '提示', '请先停止数据接入，再卸载模型。')
            return False
        self.loaded_model, self.loaded_metadata = None, None
        self.unload_model_btn.setEnabled(False)
        self.tcp_btn.setEnabled(False)
        self.append_log('已卸载模型，开始评估时将重新训练。')
        self.status_bar.showMessage('已切回训练模式')
        return True

    def on_final_model_ready(self, model, metadata):
        self.final_trained_model = model
        self.final_trained_metadata = metadata
        self.save_model_btn.setEnabled(True)
        self.append_log('最终模型（全数据训练）已就绪，可点击"保存模型"导出。')

    def toggle_tcp_server(self):
        if self.tcp_running:
            self._stop_tcp_server()
        else:
            self._start_tcp_server()

    def _start_tcp_server(self):
        if self.loaded_model is None:
            show_message(self, 'warning', '提示', '请先加载模型后再启动数据接入。')
            return
        config = self._build_config()
        config.window_size = self.loaded_metadata['window_size']
        self._eval_rated_capacity = config.rated_capacity
        self._eval_threshold_ratio = config.threshold_ratio

        from ui.tcp_server import TCPServerWorker
        from ui.tcp_display import TcpDisplayWindow

        self._tcp_window = TcpDisplayWindow(self)
        self._tcp_window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self._tcp_window.show()

        # A10：默认只监听本机；开放局域网必须在界面里显式勾选，
        # 并自动生成 token 供客户端握手。
        allow_lan = False
        if hasattr(self, 'tcp_lan_check') and self.tcp_lan_check.isChecked():
            allow_lan = True
        self.tcp_server = TCPServerWorker(
            self.loaded_model, self.loaded_metadata, config, port=8888,
            allow_lan=allow_lan,
        )
        self.tcp_server.status_signal.connect(self.append_log)
        self.tcp_server.error_signal.connect(self.on_error)
        self.tcp_server.data_received_signal.connect(
            self._tcp_window.update_status)
        self.tcp_server.soh_update_signal.connect(self._tcp_window.update_soh)
        self.tcp_server.rul_update_signal.connect(self._tcp_window.update_rul)
        self.tcp_server.prediction_signal.connect(
            lambda m, p: self._tcp_window.update_chart(
                m, p, self._eval_rated_capacity, self._eval_threshold_ratio))
        self.tcp_server.start()
        self.tcp_running = True
        self.tcp_btn.setText('断开数据')
        self.tcp_btn._role = 'danger'
        self.tcp_btn.setProperty('role', 'danger')
        self.tcp_btn.style().unpolish(self.tcp_btn)
        self.tcp_btn.style().polish(self.tcp_btn)
        if allow_lan:
            self.append_log(
                f'TCP 数据接入服务已启动（局域网模式，端口 8888）；'
                f'客户端首条消息需带 token：{self.tcp_server.auth_token}')
        else:
            self.append_log(
                'TCP 数据接入服务已启动，仅监听本机 127.0.0.1:8888...')

    def _stop_tcp_server(self):
        if self.tcp_server is not None:
            self.tcp_server.request_stop()
            self.tcp_server.wait(3000)
        self.tcp_running = False
        self.tcp_btn.setText('接入数据')
        self.tcp_btn._role = 'primary'
        self.tcp_btn.setProperty('role', 'primary')
        self.tcp_btn.style().unpolish(self.tcp_btn)
        self.tcp_btn.style().polish(self.tcp_btn)
        if self._tcp_window is not None:
            self._tcp_window.close()
            self._tcp_window = None
        self.append_log('TCP 数据接入服务已停止。')

    def on_tcp_data(self, capacity, soh):
        self.status_bar.showMessage(f'实时数据 | 容量: {capacity:.6f} Ah | SOH: {soh:.1f}%')

    def on_soh_update(self, soh_info):
        """A10：SOH 阶段表按「距最新已观测循环」的口径展示。"""
        rows = ['<table border="1" cellpadding="3" cellspacing="0">',
                '<tr><th>SOH (%)</th><th>距最新循环</th><th>状态</th></tr>']
        for pct in (100, 95, 90, 85, 80):
            info = soh_info.get(pct, {}) or {}
            offset = info.get('cycle_offset')
            if offset is None:
                state = '预测期内未到达'
            elif info.get('reached'):
                state = '✓ 已到达'
            else:
                state = '预测中'
            rows.append(
                f'<tr><td>{pct}%</td>'
                f'<td>{"—" if offset is None else f"{offset:+d}"}</td>'
                f'<td>{state}</td></tr>')
        rows.append('</table>')
        self.soh_table_label.setText(''.join(rows))

    def on_rul_update(self, rul_info):
        """A10：RUL = 距最新已观测循环还有几个未来循环越过失效阈值。"""
        rul = rul_info.get('rul')
        if rul is None:
            value = '预测期内不会越过失效阈值'
        elif rul == 0:
            value = '0 个循环（当前已低于失效阈值）'
        else:
            value = f'{int(rul)} 个循环'
        rows = ['<table border="1" cellpadding="3" cellspacing="0">',
                '<tr><th>剩余寿命 (RUL)</th><th>失效阈值</th></tr>',
                f'<tr><td>{value}</td>'
                f'<td>{rul_info.get("threshold", 0):.4f} Ah</td></tr>',
                '</table>']
        self.rul_table_label.setText(''.join(rows))

    def on_tcp_prediction(self, measured, predicted):
        self.canvas.plot_tcp_predictions(measured, predicted,
                                         self._eval_rated_capacity,
                                         self._eval_threshold_ratio)

    def save_chart(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, '保存图表', os.fspath(FIGURE_DIR),
            'PNG 图片 (*.png);;JPG 图片 (*.jpg);;PDF 文件 (*.pdf)')
        if not file_path:
            return
        if os.path.exists(file_path):
            answer = QMessageBox.question(
                self, '确认覆盖',
                f'文件已存在：\n{file_path}\n\n是否覆盖？',
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        try:
            atomic_save_figure(self.canvas, file_path)
        except ReportExportError as error:
            show_message(self, 'error', '图表保存失败', str(error))
            return
        show_message(self, 'success', '提示', '图表已保存。',
                     buttons=QMessageBox.StandardButton.Ok,
                     default=QMessageBox.StandardButton.Ok)


    def export_report(self):
        snapshot = self._last_run_snapshot
        if snapshot is None or not snapshot.results:
            show_message(self, 'warning', '提示', '请先完成一次训练评估。')
            return

        def confirm_overwrite(paths):
            path_text = '\n'.join(str(path) for path in paths)
            answer = QMessageBox.question(
                self, '确认覆盖已有报告',
                f'以下文件已存在：\n{path_text}\n\n是否覆盖？',
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            return answer == QMessageBox.StandardButton.Yes

        try:
            artifacts = export_run_report(
                snapshot,
                self.canvas,
                confirm_overwrite=confirm_overwrite,
            )
        except ExportCancelled:
            show_message(self, 'info', '已取消', '未覆盖已有报告。')
            return
        except ReportExportError as error:
            show_message(self, 'error', '报告导出失败', str(error))
            return

        show_message(
            self, 'success', '提示',
            f'报告已导出至：\n{artifacts["run_directory"]}\n\n'
            '- report.json（运行快照、参数与结果）\n'
            '- 评估结果.xlsx（评估指标）\n'
            '- 评估结果.png（预测图表）',
            buttons=QMessageBox.StandardButton.Ok,
            default=QMessageBox.StandardButton.Ok)

    def _install_sup_sub_shortcuts(self):
        """安装全局上下标快捷键 (Ctrl+= 上标, Ctrl+Shift+= 下标) 与主题切换 (Ctrl+T)"""
        sup_sc = QShortcut(QKeySequence('Ctrl+='), self)
        sup_sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        sup_sc.activated.connect(lambda: apply_sup_sub('^'))
        sub_sc = QShortcut(QKeySequence('Ctrl+Shift+='), self)
        sub_sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        sub_sc.activated.connect(lambda: apply_sup_sub('_'))
        theme_sc = QShortcut(QKeySequence('Ctrl+T'), self)
        theme_sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        theme_sc.activated.connect(self.toggle_theme)
        self._sup_sub_shortcuts = [sup_sc, sub_sc, theme_sc]

    _HELP_CONTENT = {
        'RNN': (
            '<h2>RNN - 简单循环网络</h2>'
            '<p>逐个处理容量序列中的每个值，靠"记忆"捕捉退化趋势。结构最简单、训练最快，适合容量持续下降、波动平稳的数据。</p>'
            '<hr>'
            '<h3>通用参数</h3>'
            '<p><b>额定容量 (Ah)：</b>电池出厂标称容量，用于将容量值缩放到相近范围以便训练，输出时自动还原。默认 1.1，适用 0.5~5.0。</p>'
            '<p><b>失效阈值比例：</b>容量低于"额定容量 × 此比例"时判定电池报废，行业常用 0.7~0.8，锂离子电池一般取 0.8。</p>'
            '<p><b>SOH上/下电压 (V)：</b>计算SOH健康指标所用的两个电压点。放电过程中分别找到电压最接近这两个设定值的时刻，以两点之间的放电容量差作为SOH指标。三元锂电池(NCM/NCA/LCO)推荐 3.8/3.4V，磷酸铁锂(LFP)推荐 3.4/3.0V，钛酸锂(LTO)推荐 2.3/1.8V。上电压必须大于下电压。</p>'
            '<p><b>窗口大小：</b>用前 N 个循环的容量值预测下一个循环的容量值。越大参考的历史越多，但训练数据越少。默认 64，推荐 32~128。</p>'
            '<p><b>评估指标：</b>RMSE=均方根误差（Ah），日常首选，越小越准；MAE=平均绝对误差，对异常值不敏感；R²=决定系数，越接近1越好；Pearson=相关系数，衡量预测与真实值的线性相关性，越接近1越好；RE=寿命预测误差，衡量预测"何时报废"的准确度。</p>'
            '<p><b>随机种子：</b>固定随机数序列的起点，同一参数下每次结果一致。改种子可验证模型是否稳定。</p>'
            '<p><b>多种子数(置信区间)：</b>使用多个不同随机种子重复训练，计算各指标的均值±标准差和95%置信区间，评估模型稳定性。值越大统计越可靠但耗时越长。默认5，推荐3~10。</p>'
            '<hr>'
            '<h3>深度学习参数</h3>'
            '<p><b>隐藏层维度：</b>网络"记忆"的容量。越大能记更多规律，但也容易"过拟合"，对训练数据记得太死，遇到新数据反而预测不准。默认 64，推荐 16~256。</p>'
            '<p><b>训练轮数：</b>最大训练轮数。每 10 轮评估一次，若连续 20 轮指标不再改善则自动"早停"，提前结束训练，防止过拟合且节省时间。默认 100，推荐 50~200。</p>'
            '<p><b>归一化方式：</b>把容量值缩放到网络擅长的范围。额定容量归一化（除以额定值）最常用；MinMax 压缩到 0~1；ZScore 转为均值 0 标准差 1 的分布。</p>'
            '<p><b>计算设备：</b>CPU 通用；GPU 需 NVIDIA 显卡，无 GPU 时自动退回 CPU。</p>'
        ),
        'GRU': (
            '<h2>GRU - 门控循环网络</h2>'
            '<p>RNN 的升级版，增加了"门"来控制哪些信息该记住、哪些该忘掉，能更好处理长期退化趋势。速度与效果平衡，推荐首选。</p>'
            '<hr>'
            '<h3>通用参数</h3>'
            '<p><b>额定容量 (Ah)：</b>电池出厂标称容量，训练时缩放、输出时还原。默认 1.1，适用 0.5~5.0。</p>'
            '<p><b>失效阈值比例：</b>容量低于"额定容量 × 此比例"时判定失效，行业常用 0.7~0.8。默认 0.8。</p>'
            '<p><b>SOH上/下电压 (V)：</b>计算SOH健康指标所用的两个电压点。放电过程中分别找到电压最接近这两个设定值的时刻，以两点之间的放电容量差作为SOH指标。三元锂电池(NCM/NCA/LCO)推荐 3.8/3.4V，磷酸铁锂(LFP)推荐 3.4/3.0V，钛酸锂(LTO)推荐 2.3/1.8V。上电压必须大于下电压。</p>'
            '<p><b>窗口大小：</b>用前 N 个循环的容量值预测下一个循环的容量值。越大参考的历史越多，但训练数据越少。默认 64，推荐 32~128。</p>'
            '<p><b>评估指标：</b>RMSE=均方根误差（Ah），日常首选，越小越准；MAE=平均绝对误差，对异常值不敏感；R²=决定系数，越接近1越好；Pearson=相关系数，衡量预测与真实值的线性相关性，越接近1越好；RE=寿命预测误差，衡量预测"何时报废"的准确度。</p>'
            '<p><b>随机种子：</b>固定随机序列起点，确保结果可复现。</p>'
            '<p><b>多种子数(置信区间)：</b>使用多个不同随机种子重复训练，计算各指标的均值±标准差和95%置信区间，评估模型稳定性。值越大统计越可靠但耗时越长。默认5，推荐3~10。</p>'
            '<hr>'
            '<h3>深度学习参数</h3>'
            '<p><b>隐藏层维度：</b>网络记忆容量，越大能学更多规律但可能过拟合。默认 64，推荐 16~256。</p>'
            '<p><b>训练轮数：</b>最大训练轮数。每 10 轮评估一次，若连续 20 轮指标不再改善则自动"早停"，提前结束训练，防止过拟合且节省时间。默认 100，推荐 50~200。</p>'
            '<p><b>归一化方式：</b>额定容量归一化（除以额定值，日常首选）；MinMax（缩放到 0~1）；ZScore（转为均值 0 标准差 1 的标准分布）。</p>'
            '<p><b>计算设备：</b>CPU 或 GPU，无 GPU 时自动退回 CPU。</p>'
        ),
        'LSTM': (
            '<h2>LSTM - 长短期记忆网络</h2>'
            '<p>GRU 的加强版，用三个"门"精细控制信息流动，擅长学习复杂的退化规律。参数量最多、训练最慢，适合容量波动较大、退化趋势不规则的数据。</p>'
            '<hr>'
            '<h3>通用参数</h3>'
            '<p><b>额定容量 (Ah)：</b>电池出厂标称容量，训练时缩放、输出时还原。默认 1.1，适用 0.5~5.0。</p>'
            '<p><b>失效阈值比例：</b>容量低于"额定容量 × 此比例"时判定失效，行业常用 0.7~0.8。默认 0.8。</p>'
            '<p><b>SOH上/下电压 (V)：</b>计算SOH健康指标所用的两个电压点。放电过程中分别找到电压最接近这两个设定值的时刻，以两点之间的放电容量差作为SOH指标。三元锂电池(NCM/NCA/LCO)推荐 3.8/3.4V，磷酸铁锂(LFP)推荐 3.4/3.0V，钛酸锂(LTO)推荐 2.3/1.8V。上电压必须大于下电压。</p>'
            '<p><b>窗口大小：</b>用前 N 个循环的容量值预测下一个循环的容量值。越大参考的历史越多，但训练数据越少。默认 64，推荐 32~128。</p>'
            '<p><b>评估指标：</b>RMSE=均方根误差（Ah），日常首选，越小越准；MAE=平均绝对误差，对异常值不敏感；R²=决定系数，越接近1越好；Pearson=相关系数，衡量预测与真实值的线性相关性，越接近1越好；RE=寿命预测误差，衡量预测"何时报废"的准确度。</p>'
            '<p><b>随机种子：</b>固定随机序列起点，确保结果可复现。</p>'
            '<p><b>多种子数(置信区间)：</b>使用多个不同随机种子重复训练，计算各指标的均值±标准差和95%置信区间，评估模型稳定性。值越大统计越可靠但耗时越长。默认5，推荐3~10。</p>'
            '<hr>'
            '<h3>深度学习参数</h3>'
            '<p><b>隐藏层维度：</b>网络记忆容量，越大能学更多规律但可能过拟合。默认 64，推荐 16~256。</p>'
            '<p><b>训练轮数：</b>最大训练轮数。每 10 轮评估一次，若连续 20 轮指标不再改善则自动"早停"，提前结束训练，防止过拟合且节省时间。默认 100，推荐 50~200。</p>'
            '<p><b>归一化方式：</b>额定容量归一化（除以额定值，日常首选）；MinMax（缩放到 0~1）；ZScore（转为均值 0 标准差 1 的标准分布）。</p>'
            '<p><b>计算设备：</b>CPU 或 GPU，无 GPU 时自动退回 CPU。</p>'
        ),
        'XGBoost': (
            '<h2>XGBoost - 梯度提升树</h2>'
            '<p>用多棵决策树接力预测：第一棵粗略估计，后面每棵修正前一棵的误差。无需归一化，训练快、不易过拟合，适合小样本数据。</p>'
            '<hr>'
            '<h3>通用参数</h3>'
            '<p><b>额定容量 (Ah)：</b>仅用于计算失效阈值和展示结果。默认 1.1，适用 0.5~5.0。</p>'
            '<p><b>失效阈值比例：</b>容量低于"额定容量 × 此比例"时判定失效，行业常用 0.7~0.8。默认 0.8。</p>'
            '<p><b>SOH上/下电压 (V)：</b>计算SOH健康指标所用的两个电压点。三元锂电池(NCM/NCA/LCO)推荐 3.8/3.4V，磷酸铁锂(LFP)推荐 3.4/3.0V，钛酸锂(LTO)推荐 2.3/1.8V。上电压必须大于下电压。</p>'
            '<p><b>窗口大小：</b>用前 N 个循环预测下一个。默认 64，推荐 32~128。</p>'
            '<p><b>评估指标：</b>RMSE=均方根误差（Ah），日常首选，越小越准；MAE=平均绝对误差，对异常值不敏感；R²=决定系数，越接近1越好；Pearson=相关系数，衡量预测与真实值的线性相关性，越接近1越好；RE=寿命预测误差，衡量预测"何时报废"的准确度。</p>'
            '<p><b>随机种子：</b>固定随机序列起点，确保结果可复现。</p>'
            '<p><b>多种子数(置信区间)：</b>使用多个不同随机种子重复训练，计算各指标的均值±标准差和95%置信区间，评估模型稳定性。值越大统计越可靠但耗时越长。默认5，推荐3~10。</p>'
            '<hr>'
            '<h3>XGBoost 专用参数</h3>'
            '<p><b>树的数量：</b>总共用多少棵树。越多拟合越充分，但太多会过拟合且训练变慢。默认 100，推荐 50~500。</p>'
            '<p><b>学习率：</b>每棵树对最终结果的贡献比例。越小结果越稳健但需要更多树。默认 0.05，推荐 0.01~0.3。</p>'
            '<p><b>树的最大深度：</b>每棵树最多分多少层。越深规律越精细，但容易过拟合。训练数据较少时（如几十个循环）建议不超过 6。默认 6，推荐 3~10。</p>'
            '<p><b>样本采样比例：</b>每棵树随机抽取多少比例的数据来训练。小于 1 可增加多样性、减少过拟合。默认 1.0，推荐 0.6~1.0。</p>'
            '<p><b>特征采样比例：</b>每棵树随机使用多少比例的特征。原理同上。默认 1.0，推荐 0.6~1.0。</p>'
            '<p><b>早停批次数：</b>连续多少轮不改善就自动停止，防止过拟合、节省训练时间。默认 20，推荐 10~50。</p>'
        ),
        'RF': (
            '<h2>RF - 随机森林</h2>'
            '<p>同时训练多棵决策树，每棵树在随机抽取的数据和特征上学习，最后取所有树的平均值作为结果。天然抗过拟合、不怕异常值，无需归一化。</p>'
            '<hr>'
            '<h3>通用参数</h3>'
            '<p><b>额定容量 (Ah)：</b>仅用于计算失效阈值和展示结果。默认 1.1，适用 0.5~5.0。</p>'
            '<p><b>失效阈值比例：</b>容量低于"额定容量 × 此比例"时判定失效，行业常用 0.7~0.8。默认 0.8。</p>'
            '<p><b>SOH上/下电压 (V)：</b>计算SOH健康指标所用的两个电压点。三元锂电池(NCM/NCA/LCO)推荐 3.8/3.4V，磷酸铁锂(LFP)推荐 3.4/3.0V，钛酸锂(LTO)推荐 2.3/1.8V。上电压必须大于下电压。</p>'
            '<p><b>窗口大小：</b>用前 N 个循环预测下一个。默认 64，推荐 32~128。</p>'
            '<p><b>评估指标：</b>RMSE=均方根误差（Ah），日常首选，越小越准；MAE=平均绝对误差，对异常值不敏感；R²=决定系数，越接近1越好；Pearson=相关系数，衡量预测与真实值的线性相关性，越接近1越好；RE=寿命预测误差，衡量预测"何时报废"的准确度。</p>'
            '<p><b>随机种子：</b>固定随机序列起点，确保结果可复现。</p>'
            '<p><b>多种子数(置信区间)：</b>使用多个不同随机种子重复训练，计算各指标的均值±标准差和95%置信区间，评估模型稳定性。值越大统计越可靠但耗时越长。默认5，推荐3~10。</p>'
            '<hr>'
            '<h3>RF 专用参数</h3>'
            '<p><b>树的数量：</b>森林中树的总数。越多预测越准但越慢。默认 100，推荐 50~500。</p>'
            '<p><b>树的最大深度：</b>每棵树最多几层分支，控制复杂度。训练数据较少（如几十个循环）时宜浅。默认 10，推荐 5~30。</p>'
            '<p><b>叶节点最小样本数：</b>每个叶子最少装几个样本。越大防过拟合越强，但太大容易"欠拟合"，模型过于简单，连训练数据也预测不准。默认 1，推荐 1~10。</p>'
            '<p><b>最大特征比例：</b>每棵树随机使用多少比例的特征，防止所有树长得太像。默认 1.0，推荐 0.5~1.0。</p>'
            '<p><b>早停批次数：</b>连续多少批树的指标不改善就自动停止，防止过拟合、节省训练时间。默认 20，推荐 10~50。</p>'
        ),
    }

    def show_help(self):
        if self._help_dialog is None or not self._help_dialog.isVisible():
            self._help_dialog = _HelpDialog(self, self.current_mode)
            self._help_dialog.show()

    def show_guide(self):
        """打开使用指南（非模态，重复点击复用同一窗口）。"""
        if self._guide_dialog is None or not self._guide_dialog.isVisible():
            self._guide_dialog = _GuideDialog(self)
            self._guide_dialog.show()
        else:
            self._guide_dialog.raise_()
            self._guide_dialog.activateWindow()

    def on_progress(self, event):
        total = max(0, int(event.get('total', 0)))
        current = max(0, int(event.get('current', 0)))
        if total > 0:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(min(current, total))
            self.progress_bar.setTextVisible(True)
        else:
            self.progress_bar.setRange(0, 0)
            self.progress_bar.setTextVisible(False)

        phase_name = {
            'loading': '加载数据',
            'evaluation': '跨电池评估',
            'battery': '处理电池',
            'seed': '多种子评估',
            'rnn_epoch': '循环模型训练',
            'rf_trees': '随机森林训练',
            'xgboost_tree': 'XGBoost 训练',
            'final_training': '最终模型训练',
            'prediction': '批量预测',
            'complete': '运行完成',
        }.get(event.get('phase'), str(event.get('phase', '运行中')))
        parts = [phase_name]
        if event.get('battery'):
            parts.append(str(event['battery']))
        if event.get('seed') is not None:
            parts.append(f'seed={event["seed"]}')
        if event.get('epoch') is not None:
            parts.append(f'epoch={event["epoch"]}')
        if total > 0:
            parts.append(f'{current}/{total}')
        parts.append(f'{float(event.get("elapsed_seconds", 0.0)):.1f}s')
        message = ' · '.join(parts)
        self.run_status_label.setText(message)
        if hasattr(self, 'status_bar'):
            self.status_bar.showMessage(message)

    def on_error(self, msg):
        full_message = str(msg)
        concise = next(
            (line.strip() for line in full_message.splitlines()
             if line.strip()),
            '发生未知错误',
        )[:500]
        show_message(self, 'error', '错误', concise)
        self.append_log('错误：' + concise)
        self.logger.error(full_message)
        self._finish_status_message = '评估遇到错误'
        self._active_run_snapshot = None
        self._active_run_kind = None
        if self._result_batches:
            self._show_sidebar_page('log')
        else:
            self._show_result_state(
                '评估未完成', '请根据弹窗或训练日志中的提示检查数据和参数。')

    def show_error_toast(self, message):
        """A1：把任何线程里未捕获的异常变成一条**非阻塞**提示。

        由 ``utils.crash_guard.bridge.error`` 信号驱动；不在子线程里直接
        创建 QMessageBox，也不会中断用户正在做的事。
        """
        text = str(message)
        self.append_log(f'未处理的异常：{text}')
        try:
            self.status_bar.showMessage(f'未处理的异常：{text}', 15000)
        except AttributeError:
            pass
        if self._error_toast is None:
            self._error_toast = QLabel(self)
            self._error_toast.setProperty('role', 'dangerText')
            self._error_toast.setStyleSheet(
                'padding: 6px 10px; border-radius: 4px;')
            self._error_toast.setWordWrap(True)
            self._error_toast.setVisible(False)
        self._error_toast.setText(f'✕ 未处理的异常：{text}')
        self._error_toast.setVisible(True)
        QTimer.singleShot(15000, lambda: self._error_toast.setVisible(False))

    def on_finished(self, worker=None):
        signal_worker = self.sender()
        if worker is None and hasattr(signal_worker, 'isRunning'):
            worker = signal_worker
        worker = worker or self.worker
        if worker is None or self.worker is not worker:
            return
        if worker.isRunning():
            # 自定义 finished_signal 在 run() 返回前发出；真正解锁必须等
            # QThread.finished，避免旧线程仍存活时被新任务覆盖。
            return
        self.worker = None
        message = self._finish_status_message
        self._finish_status_message = '准备就绪'
        if not self.start_btn.isEnabled():
            self._set_running_state(False, message)

    def on_result(self, results, elapsed):
        if self._active_run_snapshot is None:
            raise RuntimeError('评估结果缺少对应的运行快照')

        threshold = self._eval_rated_capacity * self._eval_threshold_ratio
        for name, result in results.items():
            item = result['detail']
            pred = result['prediction']
            battery_data = self.worker.battery_dict.get(name, {})
            measured = np.asarray(
                battery_data.get('capacity', pred), dtype=np.float64)
            # A4：失效语义基于滚动起点的递归预测（而不是一步预测）
            recursive = item.get('recursive_prediction')
            forecast = item.get('forecast')
            if forecast:
                failure_prediction = forecast
                prediction_start = int(
                    item.get('forecast_start', len(measured) - len(forecast)))
                item['failure_cycle_protocol'] = 'rolling_origin'
            elif recursive is not None:
                failure_prediction = recursive
                prediction_start = len(measured) - len(recursive)
                item['failure_cycle_protocol'] = 'recursive_future'
            else:
                failure_prediction = pred
                prediction_start = 0
                item['failure_cycle_protocol'] = 'legacy_prediction'
            cycle_ids = battery_data.get(
                'cycle', np.arange(1, len(measured) + 1))
            semantics = analyze_failure_cycles(
                cycle_ids, measured, failure_prediction, threshold,
                prediction_start=prediction_start)
            item.update(semantics)
            item['failure_cycle'] = semantics[
                'predicted_failure_cycle']
            item['threshold'] = threshold

        completed_snapshot = self._active_run_snapshot.with_results(
            results, elapsed_seconds=elapsed)
        self._active_run_snapshot = None
        completed_results = completed_snapshot.results_dict()
        predictions = {
            name: result['prediction'] for name, result in results.items()
        }
        detail_list = [
            result['detail'] for result in completed_results.values()
        ]
        battery_names = list(completed_results)
        chart_battery_data = {
            name: {
                'capacity': np.asarray(
                    self.worker.battery_dict[name]['capacity'],
                    dtype=np.float64,
                ).copy()
            }
            for name in battery_names
            if name in self.worker.battery_dict
        }
        run_kind = self._active_run_kind or 'training'
        kind_label = '训练评估' if run_kind == 'training' else '模型预测'
        mode = completed_snapshot.config_dict().get('mode', self.current_mode)
        batch_number = len(self._result_batches) + 1
        batch = {
            'label': f'第 {batch_number} 次 · {kind_label} · {mode}',
            'snapshot': completed_snapshot,
            'results': completed_results,
            'detail': detail_list,
            'predictions': predictions,
            'battery_names': battery_names,
            'battery_data': chart_battery_data,
            'elapsed': float(elapsed),
            'rated_capacity': self._eval_rated_capacity,
            'threshold_ratio': self._eval_threshold_ratio,
            'selected_metric': self.metric_combo.currentText(),
            'run_kind': run_kind,
        }
        self._append_result_batch(batch)
        if run_kind == 'training':
            self._has_completed_training_run = True
        self._active_run_kind = None
        self._finish_status_message = f'评估完成，耗时 {elapsed:.2f}s'

    def _append_result_batch(self, batch):
        self._result_batches.append(batch)
        index = len(self._result_batches) - 1
        blocker = QSignalBlocker(self.result_batch_combo)
        self.result_batch_combo.addItem(batch['label'])
        self.result_batch_combo.setCurrentIndex(index)
        del blocker
        self.result_batch_bar.setVisible(True)
        self._display_result_batch(index)

    def _display_result_batch(self, index):
        if index < 0 or index >= len(self._result_batches):
            return
        batch = self._result_batches[index]
        self._last_run_snapshot = batch['snapshot']
        self._last_results = batch['results']
        self._last_score = [
            [result['score']] for result in batch['results'].values()
        ]
        self._last_pred = batch['predictions']
        self._last_detail = batch['detail']
        self._last_elapsed = batch['elapsed']
        self.battery_list = list(batch['battery_names'])
        self.battery_dict = batch['battery_data']
        self._eval_rated_capacity = batch['rated_capacity']
        self._eval_threshold_ratio = batch['threshold_ratio']

        self.update_result_table(
            self._last_detail,
            self._last_elapsed,
            selected_metric=batch['selected_metric'],
        )
        detail_map = {
            item.get('battery'): item for item in self._last_detail
            if isinstance(item, dict)
        }
        # U2：把滚动起点的 detail（预测起点 / 递归预测 / 区间 / EOL）交给图表；
        # 老版画布不认识 details 参数时回退到位置参数，保证不崩。
        try:
            self.canvas.plot_results(
                self.battery_list,
                self.battery_dict,
                self._last_pred,
                self._eval_rated_capacity,
                self._eval_threshold_ratio,
                details=detail_map,
            )
        except TypeError:
            self.canvas.plot_results(
                self.battery_list,
                self.battery_dict,
                self._last_pred,
                self._eval_rated_capacity,
                self._eval_threshold_ratio,
            )
        self.export_btn.setEnabled(True)
        self._show_sidebar_page('result')

    def _show_result_state(self, title, detail):
        """在结果区呈现空、加载、停止或错误状态。

        结果表现在是**常驻控件**，所以这里只清空它的数据、隐藏工具行，
        不再销毁它（旧实现会把整块区域 rebuild 一遍）。
        """
        if hasattr(self, 'result_summary'):
            self.result_summary.setVisible(False)
        if (not title.startswith('正在') and
                hasattr(self, 'sidebar_stack')):
            self._show_sidebar_page('result')
        self._last_detail_list = []
        if hasattr(self, 'result_model'):
            self.result_model.set_rows([])
        # 先移除之前的状态横幅，避免多条叠在一起
        for index in range(self.result_container_layout.count() - 1, -1, -1):
            widget = self.result_container_layout.itemAt(index).widget()
            if widget is not None and widget.objectName() == 'resultStateBanner':
                self.result_container_layout.takeAt(index)
                widget.setParent(None)
                widget.deleteLater()
        for name in ('result_view', 'result_notes'):
            widget = getattr(self, name, None)
            if widget is not None:
                widget.setVisible(False)
        for name in ('copy_table_btn', 'csv_btn', 'start_frac_combo'):
            widget = getattr(self, name, None)
            if widget is not None:
                widget.setVisible(False)
        state = QFrame()
        state.setProperty('role', 'resultState')
        state.setObjectName('resultStateBanner')
        state_layout = QVBoxLayout(state)
        state_layout.setContentsMargins(20, 24, 20, 22)
        state_layout.setSpacing(8)

        mark = QWidget()
        mark.setFixedSize(56, 40)
        battery = QFrame(mark)
        battery.setProperty('role', 'resultStateBattery')
        battery.setGeometry(3, 5, 44, 30)
        battery_fill = QFrame(battery)
        battery_fill.setProperty('role', 'resultStateBatteryFill')
        battery_fill.setGeometry(4, 4, 27, 20)
        battery_terminal = QFrame(mark)
        battery_terminal.setProperty('role', 'resultStateBatteryTerminal')
        battery_terminal.setGeometry(47, 14, 6, 12)
        state_layout.addWidget(mark, 0, Qt.AlignmentFlag.AlignHCenter)

        title_label = QLabel(title)
        title_label.setProperty('role', 'resultStateTitle')
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setWordWrap(True)
        detail_label = QLabel(detail)
        detail_label.setProperty('role', 'resultStateDetail')
        detail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        detail_label.setWordWrap(True)
        guide_text = (
            '读取数据 · 训练模型 · 生成指标'
            if title.startswith('正在')
            else '导入数据 · 校准参数 · 开始评估'
        )
        guide_label = QLabel(guide_text)
        guide_label.setProperty('role', 'resultStateGuide')
        guide_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        state_layout.addWidget(title_label)
        state_layout.addWidget(detail_label)
        state_layout.addSpacing(3)
        state_layout.addWidget(guide_label)
        state.setAccessibleName(f'{title}。{detail}')
        self.result_container_layout.addWidget(state)

    def clear_result_display(self):
        """移除状态横幅，并恢复结果表工具行（不动常驻的结果表本身）。"""
        for index in range(self.result_container_layout.count() - 1, -1, -1):
            widget = self.result_container_layout.itemAt(index).widget()
            if widget is not None and widget.objectName() == 'resultStateBanner':
                self.result_container_layout.takeAt(index)
                widget.setParent(None)
                widget.deleteLater()
        for name in ('result_view', 'result_notes', 'copy_table_btn',
                     'csv_btn', 'start_frac_combo'):
            widget = getattr(self, name, None)
            if widget is not None:
                widget.setVisible(True)

    def update_result_table(self, detail_list, elapsed, selected_metric=None):
        """U1：把结果渲染成可排序表格 + 跨电池汇总行 + 基线行。

        旧的卡片堆（N 个 QGroupBox、5 段复制粘贴的指标代码、6 位小数）已经
        被 QTableView + QAbstractTableModel + QSortFilterProxyModel 取代。
        """
        self._last_detail_list = list(detail_list or [])
        # 恢复被状态横幅隐藏的结果表与工具行
        self.clear_result_display()
        self._refresh_start_frac_options(self._last_detail_list)
        self._rebuild_result_rows()
        self._update_result_summary(
            self._last_detail_list, elapsed,
            selected_metric or self.metric_combo.currentText())

    def _refresh_start_frac_options(self, detail_list):
        """按当前结果里实际存在的滚动起点填充下拉框。"""
        fracs = set()
        for item in detail_list or []:
            rolling = (item or {}).get('rolling') or {}
            fracs.update(rolling.get('per_start') or {})
        options = sorted(float(f) for f in fracs)
        combo = getattr(self, 'start_frac_combo', None)
        if combo is None:
            return
        blocker = QSignalBlocker(combo)
        combo.clear()
        for frac in options:
            combo.addItem(f'{frac:.0%}', frac)
        primary = next(
            (item.get('primary_start_frac') for item in detail_list
             if item.get('primary_start_frac') is not None), None)
        if primary is not None:
            index = combo.findData(float(primary))
            if index >= 0:
                combo.setCurrentIndex(index)
        del blocker

    def _current_start_frac(self):
        combo = getattr(self, 'start_frac_combo', None)
        if combo is None or combo.count() == 0:
            return None
        data = combo.currentData()
        return None if data is None else float(data)

    def _baseline_rows(self, detail_list):
        """收集基线（平推 / 线性外推 / 双指数）用于并排展示（A9）。"""
        baselines = {}
        for item in detail_list or []:
            for name, entry in ((item or {}).get('baselines') or {}).items():
                value = entry.get('rmse')
                if value is None:
                    continue
                baselines.setdefault(name, []).append(float(value))
        return {
            name: {'rmse': float(np.mean(values))}
            for name, values in baselines.items() if values
        }

    def _rebuild_result_rows(self):
        detail_list = getattr(self, '_last_detail_list', [])
        if not detail_list:
            return
        rows = rows_from_details(
            detail_list,
            start_frac=self._current_start_frac(),
            baselines=self._baseline_rows(detail_list),
        )
        self.result_model.set_tokens(theme_tokens(self._theme_mode))
        self.result_model.set_rows(rows)
        # 列宽在 build_result_page 里显式设定；这里不再 resizeColumnsToContents，
        # 否则汇总行的长文本会把列撑宽、把前排的指标挤出可视区。

        summary = summary_row(rows)
        notes = []
        if summary is not None:
            # 汇总行的单元格只放均值（窄面板里不被截断），
            # 完整的 mean ± std 与 bootstrap 区间写在这里。
            stats = []
            for key, label, fmt in (('rmse', 'RMSE', '{:.4f}'),
                                    ('mae', 'MAE', '{:.4f}'),
                                    ('skill', '技能分', '{:+.3f}')):
                mean, std = summary.get(key), summary.get(f'{key}_std')
                if mean is None:
                    continue
                # 单块电池时 std 恒为 0，不显示无意义的「± 0.0000」
                if std:
                    stats.append(f'{label} {fmt.format(mean)}'
                                 f' ± {fmt.format(std).lstrip("+")}')
                else:
                    stats.append(f'{label} {fmt.format(mean)}')
            if stats:
                notes.append(
                    f'跨电池汇总（n={summary["n_batteries"]} 块电池）：'
                    + '，'.join(stats))
            mean, lo, hi = bootstrap_summary(rows, 'rmse')
            if np.isfinite(lo) and np.isfinite(hi) and lo != hi:
                notes.append(
                    f'RMSE 的 bootstrap 95% 区间：[{lo:.4f}, {hi:.4f}] Ah'
                    '（n = 电池数才是泛化不确定性的来源，不是随机种子）')
        alpha_values = [
            item.get('persistence_blend') for item in detail_list
            if item.get('persistence_blend') is not None
        ]
        if alpha_values and min(alpha_values) < 0.05:
            notes.append(
                '⚠ 有电池的持久性混合系数 α < 0.05：模型未超越平推基线，'
                '递归预测已退化为水平线。')
        # 置信区间口径说明：它只是同一留一折内的随机种子波动
        if any(int(item.get('n_seeds', 1)) > 1 for item in detail_list):
            notes.append(
                '置信区间仅表示同一留一折内的随机种子波动，'
                '不代表跨电池总体不确定性。')
        if notes:
            self.result_notes.setText('\n'.join(notes))
            self.result_notes.setVisible(True)
        else:
            self.result_notes.setVisible(False)

    def _on_start_frac_changed(self, _index):
        if getattr(self, '_last_detail_list', None):
            self._rebuild_result_rows()

    def _copy_result_table(self):
        """把当前结果表复制到剪贴板（Tab 分隔，可直接粘进 Excel）。"""
        rows = self.result_model.display_rows()
        if not rows:
            show_message(self, 'info', '暂无结果', '当前没有可复制的结果。')
            return
        header = [column[0] for column in COLUMNS]
        lines = ['\t'.join(header)]
        for row in rows:
            lines.append('\t'.join(
                ResultTableModel._display_text(
                    row, column[1],
                    ResultTableModel._cell_value(row, column[1]),
                    column[2])
                for column in COLUMNS))
        QApplication.clipboard().setText('\n'.join(lines))
        self.append_log('结果表已复制到剪贴板。')

    def _export_result_csv(self):
        """导出结果表 CSV（U1.6）。"""
        rows = self.result_model.display_rows()
        if not rows:
            show_message(self, 'info', '暂无结果', '当前没有可导出的结果。')
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, '导出结果表', os.fspath(OUTPUTS_DIR / '评估结果.csv'),
            'CSV 文件 (*.csv)')
        if not file_path:
            return
        try:
            with open(file_path, 'w', encoding='utf-8-sig', newline='') as stream:
                stream.write(to_csv(rows))
        except OSError as error:
            show_message(self, 'error', '导出失败', f'无法写入文件：{error}')
            return
        self.append_log(f'结果表已导出：{file_path}')

    def _update_result_summary(self, detail_list, elapsed, selected_metric):
        metric_map = {
            'RMSE': 'rmse',
            'MAE': 'mae',
            'R²': 'r2',
            'Pearson': 'pearson',
            'RE': 're',
            '全部': 'rmse',
        }
        metric_label = 'RMSE' if selected_metric == '全部' else selected_metric
        metric_key = metric_map[selected_metric]
        values = [
            float(item[metric_key])
            for item in detail_list
            if item.get(metric_key) is not None and
            np.isfinite(item.get(metric_key))
        ]
        models = sorted({str(item.get('model', '未知模型'))
                         for item in detail_list})
        model_text = models[0] if len(models) == 1 else '多模型'
        count = len(detail_list)
        value_text = (
            f'{float(np.mean(values)):.6f}' if values else 'N/A（截尾）')
        seed_count = max(
            (int(item.get('n_seeds', 1)) for item in detail_list),
            default=1,
        )

        self.result_summary_title.setText(f'{count} 块电池 · {model_text}')
        self.result_summary_metric.setText(
            f'平均 {metric_label} {value_text}')
        self.result_summary_meta.setText(
            f'耗时 {elapsed:.2f} 秒 · {seed_count} 次随机种子')
        self.result_summary.setAccessibleName(
            f'{self.result_summary_title.text()}，'
            f'{self.result_summary_metric.text()}，'
            f'{self.result_summary_meta.text()}')
        self.result_summary.setVisible(True)
        self._show_sidebar_page('result')
