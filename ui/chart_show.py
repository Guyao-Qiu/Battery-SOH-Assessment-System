import numpy as np
import matplotlib
matplotlib.use('QtAgg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial']
plt.rcParams['axes.unicode_minus'] = False
# 不再需要 mathtext.fontset，改用 Unicode 原生上下标字符

from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT,
)

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
    QGridLayout, QScrollArea, QWidget, QFrame,
)
from utils.icon_generator import get_dialog_icon, show_message, input_get_item

# ── 图标绘制 ──────────────────────────────────────────────
# 淡墨工具图标，与宣纸背景保持稳定对比。
_ICON_COLOR = QColor(70, 80, 74)  # #46504A
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

# ── 颜色面板数据 ──────────────────────────────────────────
COLOR_PALETTE = [
    ('深蓝',   '#1F77B4'),
    ('橙色',   '#FF7F0E'),
    ('绿色',   '#2CA02C'),
    ('红色',   '#D62728'),
    ('紫色',   '#9467BD'),
    ('棕色',   '#8C564B'),
    ('粉色',   '#E377C2'),
    ('灰色',   '#7F7F7F'),
    ('橄榄绿', '#BCBD22'),
    ('青色',   '#17BECF'),
    ('黑色',   '#000000'),
    ('天蓝色', '#56B4E9'),
    ('朱红色', '#D55E00'),
    ('蓝绿色', '#009E73'),
    ('黄色',   '#F0E442'),
    ('中蓝色', '#0072B2'),
    ('紫红色', '#CC79A7'),
    ('浅蓝色', '#AEC7E8'),
    ('浅橙色', '#FFBB78'),
    ('浅绿色', '#98DF8A'),
    ('浅红色', '#FF9896'),
    ('NPG红色','#E64B35'),
    ('石板蓝', '#3C5488'),
    ('亮黄色', '#FFFF33'),
]


def _luminance(hex_color):
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    return 0.299 * r + 0.587 * g + 0.114 * b


class _ColorCell(QWidget):
    """单色块：上方纯色按钮 + 下方十六进制值 + 颜色名称"""

    def __init__(self, name, hex_color, parent=None):
        super().__init__(parent)
        self._hex = hex_color
        layout = QVBoxLayout(self)
        layout.setSpacing(1)
        layout.setContentsMargins(0, 0, 0, 0)

        btn = QPushButton()
        btn.setFixedSize(72, 36)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setToolTip(f'{name}\n{hex_color}')
        btn.setStyleSheet(f'''
            QPushButton {{
                background-color: {hex_color};
                border: 1px solid #CCC;
                border-radius: 3px;
            }}
            QPushButton:hover {{
                border: 2px solid #4C8BF5;
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


class ColorGridDialog(QDialog):
    """颜色面板弹窗 —— 网格色板 + 自定义 RGB/Hex 输入"""
    color_selected = None

    def __init__(self, parent=None, current_hex='#000000'):
        super().__init__(parent)
        self.setWindowTitle('选择颜色')
        self.setWindowIcon(get_dialog_icon('color'))
        self.setModal(True)
        self.resize(600, 550)
        self._selected_hex = current_hex

        layout = QVBoxLayout(self)

        # ── 色板区域 ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(6)

        cols = 4
        for i, (name, hex_val) in enumerate(COLOR_PALETTE):
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
        self._custom_input.setPlaceholderText('例：#FF0000 或 255,0,0')
        self._custom_input.textChanged.connect(self._on_custom_input_changed)
        custom_layout.addWidget(self._custom_input)

        self._custom_preview = QFrame()
        self._custom_preview.setFixedSize(28, 28)
        self._custom_preview.setStyleSheet('border: 1px solid #999; background-color: #CCC;')
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
        self._preview.setStyleSheet(f'background-color: {current_hex}; border: 1px solid #999;')
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
        self._preview.setStyleSheet(f'background-color: {hex_val}; border: 1px solid #999;')
        self._hex_label.setText(hex_val)
        self._custom_input.setText(hex_val)

    def _on_custom_input_changed(self, text):
        parsed = _parse_color_input(text)
        if parsed:
            self._custom_preview.setStyleSheet(
                f'background-color: {parsed}; border: 1px solid #999;')
        else:
            self._custom_preview.setStyleSheet(
                'border: 1px solid #999; background-color: #CCC;')

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
        self._color_btn.setStyleSheet('background-color: #000000; border: 1px solid #999; border-radius: 3px;')
        self._color_btn.clicked.connect(self._pick_color)
        self._color_hex = '#000000'
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
            group_item.setForeground(QColor(0x4C, 0x8B, 0xF5))
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
            self._color_hex = '#000000'
        self._color_btn.setStyleSheet(
            f'background-color: {self._color_hex}; border: 1px solid #999; border-radius: 3px;')
        # 宽度
        lw = line.get_linewidth()
        self._width_combo.setCurrentText(str(lw))

    def _pick_color(self):
        dlg = ColorGridDialog(self, self._color_hex)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.color_selected:
            self._color_hex = dlg.color_selected
            self._color_btn.setStyleSheet(
                f'background-color: {self._color_hex}; border: 1px solid #999; border-radius: 3px;')

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
    def __init__(self, canvas, parent=None):
        super().__init__(canvas, parent)
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
        dlg = LineStyleDialog(self.canvas.figure, self.canvas, self)
        dlg.show()

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


class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, allow_fullscreen=True):
        # 宣纸图表底色，兼顾长时间观察与打印导出。
        self.fig, self.ax = plt.subplots(1, 1, figsize=(8, 6))
        self.fig.patch.set_facecolor('#F7F1E5')
        self.ax.set_facecolor('#F7F1E5')
        super().__init__(self.fig)
        self.setParent(parent)
        self._allow_fullscreen = allow_fullscreen
        self._last_plot_kind = None
        self._last_plot_payload = None
        self._fullscreen_dialog = None
        self._hover_annot = None
        self._hover_cid = None
        self._show_placeholder()

    def _show_placeholder(self):
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        for spine in self.ax.spines.values():
            spine.set_visible(False)
        self.ax.text(0.5, 0.5, '导入数据并点击“开始评估”\n曲线与失效阈值将在这里显示',
                     transform=self.ax.transAxes, ha='center', va='center',
                     fontsize=12, color='#6D756F', linespacing=1.6)
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

    def open_fullscreen(self):
        """打开独立全屏图表，不移动或破坏主窗口中的原图。"""
        if self._fullscreen_dialog is not None and self._fullscreen_dialog.isVisible():
            self._fullscreen_dialog.raise_()
            self._fullscreen_dialog.activateWindow()
            return
        dialog = ChartFullscreenDialog(self, self.window())
        self._fullscreen_dialog = dialog
        dialog.finished.connect(
            lambda _result: setattr(self, '_fullscreen_dialog', None))
        dialog.showFullScreen()

    def replay_last_plot(self, target_canvas):
        """把当前图表数据重绘到独立画布，保留缩放和平移能力。"""
        if self._last_plot_kind == 'results':
            target_canvas.plot_results(*self._last_plot_payload)
        elif self._last_plot_kind == 'tcp':
            target_canvas.plot_tcp_predictions(*self._last_plot_payload)

    def _calc_tick_interval(self, rated_capacity):
        if rated_capacity <= 0:
            return 0.2
        rough = rated_capacity / 5
        nice = [0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0]
        best = nice[0]
        for n in nice:
            if abs(n - rough) < abs(best - rough):
                best = n
        return best

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

            if self._hover_annot is None:
                self._hover_annot = self.fig.text(
                    fx, fy, text,
                    transform=self.fig.transFigure,
                    ha='left', va='top',
                    bbox=dict(boxstyle='round,pad=0.4',
                              facecolor='#FAF6EC', edgecolor='#315B5A',
                              alpha=0.95, linewidth=1.2),
                    fontsize=9, color='#202724', zorder=1000)
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
        """设置图例可拖动、可编辑、无边框"""
        legend = ax.legend()
        legend.set_draggable(True)
        legend.set_frame_on(False)
        for text in legend.get_texts():
            text.set_color('#202724')
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

    def plot_results(self, battery_names, battery_data,
                     prediction_by_battery, rated_capacity, threshold_ratio):
        self._last_plot_kind = 'results'
        self._last_plot_payload = (
            battery_names, battery_data, prediction_by_battery,
            rated_capacity, threshold_ratio)
        self.fig.clear()
        if hasattr(self, '_pick_cid'):
            self.fig.canvas.mpl_disconnect(self._pick_cid)
            self._pick_cid = None

        # 水墨图表：黛青实线、淡墨虚线、朱砂阈值。
        bg_color    = '#F7F1E5'
        fg_color    = '#202724'
        muted_color = '#59635D'
        real_c      = '#315B5A'   # 黛青实线 — 真实值
        pred_c      = '#6F7770'   # 淡墨虚线 — 预测值
        threshold_c = '#9E3D2F'   # 朱砂 — 失效阈值
        spine_color = '#7C8179'
        grid_color  = '#C5BBAA'
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

        for idx in range(total):
            ax = axes[idx]
            ax.set_facecolor(bg_color)
            battery_name = valid_names[idx]
            test_data = battery_data[battery_name]['capacity'].tolist()
            predict_data = prediction_by_battery[battery_name]
            x_test = [t for t in range(len(test_data))]

            predict_data = list(predict_data)
            if len(predict_data) < len(test_data):
                predict_data = predict_data + [np.nan] * (len(test_data) - len(predict_data))
            elif len(predict_data) > len(test_data):
                predict_data = predict_data[:len(test_data)]
            x_pred = [t for t in range(len(predict_data))]

            marker_step = max(1, len(x_test) // 24)
            ax.plot(x_test, test_data, color=real_c, linewidth=1.8,
                    marker='o', markersize=2.6, markevery=marker_step,
                    label='真实值', zorder=3)
            ax.plot(x_pred, predict_data, color=pred_c, linewidth=1.8,
                    linestyle='--', label='预测值', zorder=3)
            ax.axhline(y=threshold_val,
                       color=threshold_c, ls='--', linewidth=1.0,
                       label='失效阈值线', zorder=5)

            # 坐标轴边框：四边均显示，使用较亮颜色确保可见
            for spine in ax.spines.values():
                spine.set_visible(True)
                spine.set_color(spine_color)
                spine.set_linewidth(1.2)

            # 刻度线：向内、清晰可见
            ax.tick_params(axis='both', which='both', direction='in',
                           length=4, width=1, colors=muted_color, labelsize=9)

            # 网格
            ax.grid(True, color=grid_color, linewidth=0.5, alpha=0.5, zorder=0)

            # Y 轴范围：确保包含失效阈值线
            all_y = test_data + [v for v in predict_data if not np.isnan(v)]
            if all_y:
                max_val = max(max(all_y), threshold_val)
                interval = self._calc_tick_interval(rated_capacity)
                y_max = np.ceil(max_val / interval) * interval + interval
                y_ticks = np.arange(0, y_max + interval * 0.5, interval)
                ax.set_yticks(y_ticks)
                ax.set_ylim(0, y_max)

            self._make_legend_interactive(ax)
            ax.set_xlabel('放电循环', fontsize=10, color=fg_color)
            ax.set_ylabel('容量 (Ah)', fontsize=10, color=fg_color)
            ax.set_title(battery_name + ' 预测值与真实值对比',
                         fontsize=12, color=fg_color, fontweight='bold')

        for idx in range(total, len(axes)):
            axes[idx].axis('off')
            axes[idx].set_facecolor(bg_color)

        self.fig.tight_layout(rect=[0, 0, 1, 0.98])
        self._pick_cid = self.fig.canvas.mpl_connect('pick_event', self._on_legend_pick)
        self._install_hover('放电循环', '容量 (Ah)')
        self.draw()

    def plot_tcp_predictions(self, measured, predicted, rated_capacity, threshold_ratio):
        """实时 TCP 数据预测图：实测容量曲线 + 预测容量曲线 + 失效阈值线"""
        self._last_plot_kind = 'tcp'
        self._last_plot_payload = (
            measured, predicted, rated_capacity, threshold_ratio)
        self.fig.clear()
        if hasattr(self, '_pick_cid'):
            self.fig.canvas.mpl_disconnect(self._pick_cid)
            self._pick_cid = None

        # 与训练结果一致的水墨图表语义色。
        bg_color    = '#F7F1E5'
        fg_color    = '#202724'
        muted_color = '#59635D'
        real_c      = '#315B5A'   # 黛青实线 — 实测值
        pred_c      = '#6F7770'   # 淡墨虚线 — 预测值
        threshold_c = '#9E3D2F'
        spine_color = '#7C8179'
        grid_color  = '#C5BBAA'
        self.fig.patch.set_facecolor(bg_color)

        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor(bg_color)

        threshold_val = rated_capacity * threshold_ratio

        if len(measured) > 0:
            x_measured = list(range(len(measured)))
            self.ax.plot(x_measured, measured, color=real_c, marker='o',
                         markersize=3, linewidth=1.4, label='实测容量', zorder=3)

        if len(predicted) > 0:
            x_pred = list(range(len(measured) - 1, len(measured) - 1 + len(predicted)))
            self.ax.plot(x_pred, predicted, color=pred_c, linewidth=1.6,
                         linestyle='--', label='预测容量', zorder=3)

        self.ax.axhline(y=threshold_val,
                        color=threshold_c, ls='--', linewidth=1.0,
                        label='失效阈值线', zorder=5)

        # 坐标轴边框：四边均显示
        for spine in self.ax.spines.values():
            spine.set_visible(True)
            spine.set_color(spine_color)
            spine.set_linewidth(1.2)

        # 刻度线
        self.ax.tick_params(axis='both', which='both', direction='in',
                            length=4, width=1, colors=muted_color, labelsize=9)
        self.ax.grid(True, color=grid_color, linewidth=0.5, alpha=0.5, zorder=0)

        self.ax.set_xlabel('循环次数', fontsize=10, color=fg_color)
        self.ax.set_ylabel('容量 (Ah)', fontsize=10, color=fg_color)
        self.ax.set_title('实时 SOH 预测', fontsize=12,
                          color=fg_color, fontweight='bold')

        # Y 轴范围：确保包含失效阈值线
        all_y = list(measured) + list(predicted)
        if all_y:
            max_val = max(max(all_y), threshold_val)
            interval = self._calc_tick_interval(rated_capacity)
            y_max = np.ceil(max_val / interval) * interval + interval
            y_ticks = np.arange(0, y_max + interval * 0.5, interval)
            self.ax.set_yticks(y_ticks)
            self.ax.set_ylim(0, y_max)

        # 图例（无边框、白色文字）
        legend = self.ax.legend(loc='best', frameon=False)
        for text in legend.get_texts():
            text.set_color(fg_color)

        self.fig.tight_layout()
        self._install_hover('循环次数', '容量 (Ah)')
        self.draw()

    def save_figure(self, file_path):
        self.fig.savefig(file_path, dpi=300, bbox_inches='tight')


class ChartFullscreenDialog(QDialog):
    """可缩放、可平移的独立全屏训练结果视图。"""

    def __init__(self, source_canvas, parent=None):
        super().__init__(parent)
        self.setWindowTitle('训练结果 · 全屏观察')
        self.setWindowIcon(get_dialog_icon('chart'))
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(6)

        hint = QLabel('滚轮缩放 · 工具栏平移 · 双击图表或按 Esc 返回')
        hint.setProperty('role', 'subtitle')
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setAccessibleName('全屏图表操作提示')

        self.canvas = MplCanvas(self, allow_fullscreen=False)
        self.toolbar = CustomToolbar(self.canvas, self)
        layout.addWidget(hint)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas, 1)

        source_canvas.replay_last_plot(self.canvas)
        self._escape_shortcut = QShortcut(QKeySequence('Escape'), self)
        self._escape_shortcut.activated.connect(self.close)
