import os
import sys
import ctypes
import json
import glob
import logging

import pandas as pd
import torch
import numpy as np

from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication, QWidget, QMainWindow, QFileDialog, QLabel, QListWidget,
    QTextEdit, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QDoubleSpinBox,
    QSpinBox, QComboBox, QMessageBox, QSizePolicy,
    QSplitter, QScrollArea, QAbstractSpinBox, QAbstractItemView, QProgressBar, QStatusBar,
    QDialog, QFrame, QToolButton,
)
from PyQt6.QtGui import QTextCursor, QShortcut, QKeySequence, QFontMetrics
from ui.chart_show import MplCanvas, CustomToolbar, apply_sup_sub
from ui.worker import EvalWorker
from ui.animated_button import AnimatedButton
from ui.style import apply_theme
from utils.config import (
    TrainConfig,
    load_config,
    normalize_model_name,
    save_config,
)
from utils.logger import setup_logger
from utils.icon_generator import get_app_icon, get_dialog_icon, show_message
from core.adapters import get_adapter_list
# ── JSON 配置导入映射 ──────────────────────────────────────

def _map_metric(val):
    m = str(val).lower()
    return {'rmse': 'RMSE', 'mae': 'MAE', 'r2': 'R²', 'pearson': 'Pearson',
            're': 'RE', 'all': '全部'}.get(m, 'RMSE')

def _map_norm(val):
    m = str(val).lower()
    return {'rated': '额定容量归一化', 'minmax': 'MinMax', 'zscore': 'ZScore'}.get(m, '额定容量归一化')

def _map_device(val):
    m = str(val).lower()
    return {'cpu': 'CPU', 'cuda': 'GPU (CUDA)'}.get(m, 'CPU')

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


def _apply_windows_paper_caption(dlg):
    """在 Windows 11 上让此对话框的原生标题栏匹配宣纸主题。"""
    if sys.platform != 'win32':
        return
    try:
        hwnd = int(dlg.winId())
        dwm = ctypes.windll.dwmapi
        dark_mode = ctypes.c_int(0)
        dwm.DwmSetWindowAttribute(
            hwnd, 20, ctypes.byref(dark_mode), ctypes.sizeof(dark_mode))

        DWMWA_BORDER_COLOR = 34
        DWMWA_CAPTION_COLOR = 35
        DWMWA_TEXT_COLOR = 36
        # Windows COLORREF 使用 0x00BBGGRR。
        for attribute, colorref in (
                (DWMWA_BORDER_COLOR, 0x848D89),   # #898D84
                (DWMWA_CAPTION_COLOR, 0xD1E0E8),  # #E8E0D1
                (DWMWA_TEXT_COLOR, 0x242720)):     # #202724
            value = ctypes.c_uint(colorref)
            dwm.DwmSetWindowAttribute(
                hwnd, attribute, ctypes.byref(value), ctypes.sizeof(value))
    except (AttributeError, OSError, TypeError):
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


class _HelpDialog(QDialog):
    """模型参数帮助对话框（非模态，随模型切换实时更新）"""
    def __init__(self, parent, mode):
        super().__init__(parent)
        self.setWindowTitle('参数设置帮助')
        self.setWindowIcon(get_dialog_icon('help'))
        self.resize(550, 600)
        self.setMinimumSize(450, 400)

        layout = QVBoxLayout(self)
        self._text = QTextEdit()
        self._text.setReadOnly(True)
        layout.addWidget(self._text)

        self.set_content(mode)

    def set_content(self, mode):
        content = MainWindow._HELP_CONTENT.get(mode, '<p>暂无该模型的帮助信息。</p>')
        self._text.setHtml(content)


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
    def __init__(self):
        super().__init__()
        self.setWindowTitle('电池 SOH 评估系统')
        self.setWindowIcon(get_app_icon())
        self.resize(1600, 900)
        self.setMinimumSize(1180, 700)

        self.imported_paths = []
        self.current_mode = 'RNN'
        self.worker = None
        self._eval_rated_capacity = 1.1
        self._eval_threshold_ratio = 0.8
        self.battery_dict = {}
        self.battery_list = []

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

    def apply_theme(self):
        """应用全局宣纸水墨主题样式。"""
        apply_theme(QApplication.instance())

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
        if 'device' in cfg and hasattr(self, 'device_combo'):
            idx = self.device_combo.findText(cfg['device'])
            if idx >= 0:
                self.device_combo.setCurrentIndex(idx)
        if 'norm_method' in cfg and hasattr(self, 'norm_combo'):
            idx = self.norm_combo.findText(cfg['norm_method'])
            if idx >= 0:
                self.norm_combo.setCurrentIndex(idx)
        # 数据源配置
        if 'adapter_type' in cfg and hasattr(self, 'adapter_combo'):
            idx = self.adapter_combo.findData(cfg['adapter_type'])
            if idx >= 0:
                self.adapter_combo.setCurrentIndex(idx)
        if 'cc_step' in cfg and hasattr(self, 'cc_step_spin'):
            self.cc_step_spin.setValue(cfg['cc_step'])
        if 'cv_step' in cfg and hasattr(self, 'cv_step_spin'):
            self.cv_step_spin.setValue(cfg['cv_step'])
        if 'discharge_step' in cfg and hasattr(self, 'discharge_step_spin'):
            self.discharge_step_spin.setValue(cfg['discharge_step'])
        # 触发适配器切换以更新控件状态
        if hasattr(self, '_on_adapter_changed'):
            self._on_adapter_changed()

    def _save_persisted_config(self):
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
            'metric': self.metric_combo.currentText(),
            'device': self.device_combo.currentText(),
            'norm_method': self.norm_combo.currentText(),
            'n_estimators': self.xgb_n_estimators_spin.value(),
            'learning_rate': self.xgb_learning_rate_spin.value(),
            'max_depth': self.xgb_max_depth_spin.value(),
            'subsample': self.xgb_subsample_spin.value(),
            'colsample_bytree': self.xgb_colsample_bytree_spin.value(),
            'min_samples_leaf': self.rf_min_samples_leaf_spin.value(),
            'max_features': self.rf_max_features_spin.value(),
            'patience': self.xgb_patience_spin.value(),
            'adapter_type': self.adapter_combo.currentData(),
            'cc_step': self.cc_step_spin.value(),
            'cv_step': self.cv_step_spin.value(),
            'discharge_step': self.discharge_step_spin.value(),
        }
        save_config(cfg)

    def closeEvent(self, event):
        if not self._request_worker_stop(timeout_ms=5000, closing=True):
            show_message(
                self, 'warning', '仍在安全停止',
                '训练线程尚未到达安全检查点，窗口暂不关闭。请稍候后再次关闭，避免损坏模型或报告。')
            event.ignore()
            return
        self._save_persisted_config()
        super().closeEvent(event)

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

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_widget = QWidget()
        center_widget = QWidget()
        right_widget = QWidget()

        splitter.addWidget(left_widget)
        splitter.addWidget(center_widget)
        splitter.addWidget(right_widget)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setSizes([320, 800, 400])
        splitter.setMinimumWidth(100)
        splitter.setHandleWidth(2)
        left_widget.setMinimumWidth(300)

        main_layout.addWidget(splitter, 1)

        self.build_left_panel(left_widget)
        self.build_center_panel(center_widget)
        self.build_right_panel(right_widget)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self._set_running_state(False, '准备就绪')

    def build_left_panel(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(0, 0, 6, 0)
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

        self.cc_step_spin = QSpinBox()
        self.cc_step_spin.setRange(0, 99)
        self.cc_step_spin.setValue(2)
        self.cc_step_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        source_layout.addRow('恒流充电工步:', self.cc_step_spin)

        self.cv_step_spin = QSpinBox()
        self.cv_step_spin.setRange(0, 99)
        self.cv_step_spin.setValue(4)
        self.cv_step_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        source_layout.addRow('恒压充电工步:', self.cv_step_spin)

        self.discharge_step_spin = QSpinBox()
        self.discharge_step_spin.setRange(0, 99)
        self.discharge_step_spin.setValue(7)
        self.discharge_step_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        source_layout.addRow('放电工步:', self.discharge_step_spin)

        source_group.setLayout(source_layout)

        param_group = QGroupBox('参数设置')
        param_layout = QVBoxLayout()
        param_layout.setContentsMargins(8, 10, 8, 8)
        param_layout.setSpacing(8)

        battery_section = CollapsibleSection('电池与失效判据')
        evaluation_section = CollapsibleSection('评估与验证')
        advanced_section = CollapsibleSection('模型高级参数', expanded=False)
        param_layout.addWidget(battery_section)
        param_layout.addWidget(evaluation_section)
        param_layout.addWidget(advanced_section)
        self._param_rows = []

        def _add_row(section, label_text, widget, modes):
            label = QLabel(label_text)
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
        _add_row(battery_section, 'SOH上电压 (V)', self.voltage_upper_spin,
                 ['RNN', 'GRU', 'LSTM', 'XGBoost', 'RF'])

        self.voltage_lower_spin = QDoubleSpinBox()
        self.voltage_lower_spin.setDecimals(2)
        self.voltage_lower_spin.setRange(0.5, 5.0)
        self.voltage_lower_spin.setSingleStep(0.05)
        self.voltage_lower_spin.setValue(3.4)
        self.voltage_lower_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        _add_row(battery_section, 'SOH下电压 (V)', self.voltage_lower_spin,
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
        _add_row(evaluation_section, '多种子数(置信区间)', self.n_seeds_spin,
                 ['RNN', 'GRU', 'LSTM', 'XGBoost', 'RF'])

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

        self.help_btn = AnimatedButton('帮助', 'ghost')
        self.help_btn.setShortcut(QKeySequence('F1'))
        self.help_btn.setToolTip('查看当前模型参数说明 (F1)')
        self.help_btn.clicked.connect(self.show_help)
        self.help_btn.setMaximumWidth(80)
        param_layout.addWidget(self.help_btn, 0, Qt.AlignmentFlag.AlignLeft)

        # 左侧三个面板（文件导入 / 数据源 / 参数设置）统一用垂直 splitter 分隔
        left_splitter = QSplitter(Qt.Orientation.Vertical)
        left_splitter.addWidget(file_group)
        left_splitter.addWidget(source_group)
        left_splitter.addWidget(param_scroll)
        left_splitter.setStretchFactor(0, 2)
        left_splitter.setStretchFactor(1, 0)
        left_splitter.setStretchFactor(2, 1)
        left_splitter.setSizes([200, 140, 300])
        left_splitter.setHandleWidth(2)

        layout.addWidget(left_splitter, 1)

        self._help_dialog = None
        self._update_param_panel('RNN')

    def build_center_panel(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(6, 0, 6, 0)
        layout.setSpacing(8)

        btn_layout = QHBoxLayout()
        model_label = QLabel('选择评估模型')
        model_label.setProperty('role', 'sectionTitle')
        btn_layout.addWidget(model_label)
        btn_layout.addSpacing(6)
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

        self.save_model_btn.setEnabled(False)
        self.unload_model_btn.setEnabled(False)
        self.tcp_btn.setEnabled(False)

        _configure_button_row(
            io_layout, (self.save_model_btn, self.load_model_btn,
                        self.unload_model_btn, self.tcp_btn))

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

        self.canvas = MplCanvas()
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.canvas.setToolTip('双击图表可进入独立全屏查看，按 Esc 退出')

        self.toolbar = CustomToolbar(self.canvas, self)

        layout.addLayout(btn_layout)
        layout.addLayout(io_layout)
        layout.addLayout(action_layout)
        layout.addWidget(self.run_status_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas, 1)

        self.select_mode('RNN')

    def build_right_panel(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(6, 0, 0, 0)
        layout.setSpacing(8)

        result_group = QGroupBox('结果展示')
        result_layout = QVBoxLayout()

        self.result_scroll = QScrollArea()
        self.result_scroll.setWidgetResizable(True)
        self.result_container = QWidget()
        self.result_container_layout = QVBoxLayout(self.result_container)
        self.result_container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.result_container_layout.setSpacing(8)
        self.result_scroll.setWidget(self.result_container)
        self._show_result_state(
            '等待评估结果',
            '导入数据并开始评估后，这里会显示失效循环、指标和置信区间。')

        result_layout.addWidget(self.result_scroll)
        result_group.setLayout(result_layout)

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

        log_group = QGroupBox('训练评估进程')
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)

        splitter = QSplitter(Qt.Orientation.Vertical)
        result_wrapper = QWidget()
        rw_layout = QVBoxLayout(result_wrapper)
        rw_layout.setContentsMargins(0, 0, 0, 0)
        rw_layout.addWidget(result_group)
        rw_layout.addLayout(op_layout)

        log_wrapper = QWidget()
        lw_layout = QVBoxLayout(log_wrapper)
        lw_layout.setContentsMargins(0, 0, 0, 0)
        lw_layout.addWidget(log_group)

        splitter.addWidget(result_wrapper)
        splitter.addWidget(log_wrapper)
        splitter.setSizes([300, 200])
        splitter.setHandleWidth(2)
        layout.addWidget(splitter)

    def _set_running_state(self, running, message):
        """同步主操作、停止按钮、进度和状态文字。"""
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
            self.adapter_combo, self.cc_step_spin, self.cv_step_spin,
            self.discharge_step_spin,
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
        self._update_param_panel(selected_mode)
        if self._help_dialog is not None and self._help_dialog.isVisible():
            self._help_dialog.set_content(selected_mode)

    def _update_param_panel(self, mode):
        for label, widget, modes in self._param_rows:
            visible = mode in modes
            label.setVisible(visible)
            widget.setVisible(visible)

    def _on_adapter_changed(self):
        """切换数据源适配器时，启用/禁用工步配置控件"""
        from core.adapters import ADAPTERS
        adapter_name = self.adapter_combo.currentData()
        adapter_cls = ADAPTERS.get(adapter_name)
        if adapter_cls is None:
            return
        needs_steps = adapter_cls.needs_step_config()
        self.cc_step_spin.setEnabled(needs_steps)
        self.cv_step_spin.setEnabled(needs_steps)
        self.discharge_step_spin.setEnabled(needs_steps)

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
        self.cc_step_spin.setValue(config.cc_step)
        self.cv_step_spin.setValue(config.cv_step)
        self.discharge_step_spin.setValue(config.discharge_step)
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

    def append_log(self, text):
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        text_with_br = text.replace('\n', '<br>')
        cursor.insertHtml(text_with_br + '<br>')
        self.logger.info(text)

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
            cc_step=self.cc_step_spin.value(),
            cv_step=self.cv_step_spin.value(),
            discharge_step=self.discharge_step_spin.value(),
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
        if len(self.imported_paths) == 0:
            show_message(self, 'warning', '提示', '请先导入文件或文件夹。')
            return
        config = self._build_config()
        from core.validation import validate_evaluation_request
        errors = validate_evaluation_request(
            config, self.imported_paths, log_callback=self.append_log)
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
            self._run_prediction()
        else:
            self._run_training()

    def _run_training(self):
        config = self._build_config()
        self._eval_rated_capacity = config.rated_capacity
        self._eval_threshold_ratio = config.threshold_ratio

        self.log_text.clear()
        self._show_result_state(
            '正在分析电池数据',
            '训练日志会持续更新。可随时点击“停止”结束当前任务。')
        self._set_running_state(True, '正在训练模型')
        self.logger.info(f'开始评估，配置：{config}')

        self.worker = EvalWorker(config, self.imported_paths)
        self.worker.log_signal.connect(self.append_log)
        self.worker.error_signal.connect(self.on_error)
        self.worker.result_signal.connect(self.on_result)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.final_model_signal.connect(self.on_final_model_ready)
        self.worker.start()

    def _run_prediction(self):
        config = self._build_config()
        config.window_size = self.loaded_metadata['window_size']
        if 'rated_capacity' in self.loaded_metadata:
            config.rated_capacity = self.loaded_metadata['rated_capacity']
        if 'threshold_ratio' in self.loaded_metadata:
            config.threshold_ratio = self.loaded_metadata['threshold_ratio']
        self._eval_rated_capacity = config.rated_capacity
        self._eval_threshold_ratio = config.threshold_ratio

        self.log_text.clear()
        self._show_result_state(
            '正在分析电池数据',
            '正在使用已加载模型生成预测结果。')
        self._set_running_state(True, '正在生成预测')

        from ui.predict_worker import PredictWorker
        self.worker = PredictWorker(
            self.loaded_model, self.loaded_metadata,
            self.imported_paths, config
        )
        self.worker.log_signal.connect(self.append_log)
        self.worker.error_signal.connect(self.on_error)
        self.worker.result_signal.connect(self.on_result)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()

    def pause_evaluation(self):
        if self.worker is not None and self.worker.isRunning():
            self.pause_btn.setEnabled(False)
            self.run_status_label.setText('正在安全停止，请稍候…')
            if self._request_worker_stop(timeout_ms=3000):
                self.append_log('评估已在安全检查点停止。')
                self._set_running_state(False, '评估已停止')
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
            self.worker = None
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
            self, '保存模型', f'outputs/model{default_ext}',
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
            self, '加载模型', 'outputs/',
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

        self.tcp_server = TCPServerWorker(
            self.loaded_model, self.loaded_metadata, config, port=8888
        )
        self.tcp_server.status_signal.connect(self.append_log)
        self.tcp_server.error_signal.connect(self.on_error)
        self.tcp_server.data_received_signal.connect(self._tcp_window.update_status)
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
        self.append_log('TCP 数据接入服务已启动，监听端口 8888...')

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
        rows = ['<table border="1" cellpadding="3" cellspacing="0">',
                '<tr><th>SOH (%)</th><th>循环次数</th><th>容量 (Ah)</th></tr>']
        for pct in [100, 95, 90, 85, 80]:
            info = soh_info.get(pct, {})
            cycle = info.get('cycle')
            cap = info.get('capacity')
            cycle_str = str(cycle) if cycle is not None else '-'
            cap_str = f'{cap:.4f}' if isinstance(cap, (int, float)) else '-'
            rows.append(f'<tr><td>{pct}%</td><td>{cycle_str}</td><td>{cap_str}</td></tr>')
        rows.append('</table>')
        self.soh_table_label.setText(''.join(rows))

    def on_rul_update(self, rul_info):
        rows = ['<table border="1" cellpadding="3" cellspacing="0">',
                '<tr><th>当前 SOH (%)</th><th>距 SOH=80% 剩余循环</th></tr>']
        for pct in [85, 84, 83, 82, 81]:
            remaining = rul_info.get(pct)
            r_str = str(remaining) if remaining is not None else '-'
            rows.append(f'<tr><td>{pct}%</td><td>{r_str}</td></tr>')
        rows.append('</table>')
        self.rul_table_label.setText(''.join(rows))

    def on_tcp_prediction(self, measured, predicted):
        self.canvas.plot_tcp_predictions(measured, predicted,
                                         self._eval_rated_capacity,
                                         self._eval_threshold_ratio)

    def save_chart(self):
        file_path, _ = QFileDialog.getSaveFileName(self, '保存图表', 'outputs/figures/', 'PNG 图片 (*.png);;JPG 图片 (*.jpg);;PDF 文件 (*.pdf)')
        if file_path:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            self.canvas.save_figure(file_path)
            show_message(self, 'success', '提示', '图表已保存。',
                         buttons=QMessageBox.StandardButton.Ok,
                         default=QMessageBox.StandardButton.Ok)


    def export_report(self):
        if not hasattr(self, '_last_detail') or not self._last_detail:
            show_message(self, 'warning', '提示', '请先完成一次训练评估。')
            return

        os.makedirs('outputs/reports', exist_ok=True)
        os.makedirs('outputs/figures', exist_ok=True)

        config = self._build_config()
        config_dict = config.to_dict()

        with open('outputs/reports/report.json', 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, ensure_ascii=False, indent=4)

        # 展平 detail 用于 Excel 导出（ci 字典展开为多列）
        export_rows = []
        for item in self._last_detail:
            row = {
                'battery': item.get('battery'),
                'cycles': item.get('cycles'),
                'model': item.get('model'),
                'rmse': item.get('rmse'),
                'mae': item.get('mae'),
                'r2': item.get('r2'),
                'pearson': item.get('pearson'),
                're': item.get('re'),
                'n_seeds': item.get('n_seeds', 1),
                'failure_cycle': item.get('failure_cycle'),
                'threshold': item.get('threshold'),
            }
            ci = item.get('ci', {})
            for key in ('rmse', 'mae', 'r2', 'pearson', 're'):
                if key in ci:
                    c = ci[key]
                    row[f'{key}_mean'] = c['mean']
                    row[f'{key}_std'] = c['std']
                    row[f'{key}_ci_lower'] = c['lower']
                    row[f'{key}_ci_upper'] = c['upper']
            export_rows.append(row)
        df = pd.DataFrame(export_rows)
        df.to_excel('outputs/reports/评估结果.xlsx', index=False)

        self.canvas.save_figure('outputs/figures/评估结果.png')

        show_message(self, 'success', '提示',
            '报告已导出至 outputs/reports/ 目录：\n'
            '- report.json（参数配置）\n'
            '- 评估结果.xlsx（评估指标）\n'
            '- outputs/figures/评估结果.png（预测图表）',
            buttons=QMessageBox.StandardButton.Ok,
            default=QMessageBox.StandardButton.Ok)

    def _install_sup_sub_shortcuts(self):
        """安装全局上下标快捷键 (Ctrl+= 上标, Ctrl+Shift+= 下标)"""
        sup_sc = QShortcut(QKeySequence('Ctrl+='), self)
        sup_sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        sup_sc.activated.connect(lambda: apply_sup_sub('^'))
        sub_sc = QShortcut(QKeySequence('Ctrl+Shift+='), self)
        sub_sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        sub_sc.activated.connect(lambda: apply_sup_sub('_'))
        self._sup_sub_shortcuts = [sup_sc, sub_sc]

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

    def on_error(self, msg):
        show_message(self, 'error', '错误', msg)
        self.append_log('错误：' + msg)
        self.logger.error(msg)
        self._set_running_state(False, '评估遇到错误')
        self._show_result_state('评估未完成', '请根据弹窗或训练日志中的提示检查数据和参数。')

    def on_finished(self):
        if not self.start_btn.isEnabled():
            self._set_running_state(False, '准备就绪')
        self.worker = None

    def on_result(self, results, elapsed):
        self._last_results = results
        self._last_score = [
            [result['score']] for result in results.values()
        ]
        self._last_pred = {
            name: result['prediction'] for name, result in results.items()
        }
        self._last_detail = [
            result['detail'] for result in results.values()
        ]
        self._last_elapsed = elapsed

        self.battery_list = list(results)
        self.battery_dict = {
            name: self.worker.battery_dict[name]
            for name in self.battery_list
            if name in self.worker.battery_dict
        }

        threshold = self._eval_rated_capacity * self._eval_threshold_ratio
        for name, result in results.items():
            item = result['detail']
            pred = result['prediction']
            recursive = item.get('recursive_prediction')
            one_step = item.get('one_step_prediction')
            if recursive is not None and one_step is not None:
                prefix_length = max(0, len(pred) - len(one_step))
                pred = list(pred[:prefix_length]) + list(recursive)
                item['failure_cycle_protocol'] = 'recursive_future'
            else:
                item['failure_cycle_protocol'] = 'legacy_prediction'
            failure_cycle = None
            for j, val in enumerate(pred):
                if val < threshold:
                    failure_cycle = j
                    break
            item['failure_cycle'] = failure_cycle
            item['threshold'] = threshold

        self.update_result_table(self._last_detail, elapsed)
        self.canvas.plot_results(self.battery_list, self.battery_dict, self._last_pred,
                                 self._eval_rated_capacity, self._eval_threshold_ratio)
        self.export_btn.setEnabled(True)
        self._set_running_state(False, f'评估完成，耗时 {elapsed:.2f}s')

    def _show_result_state(self, title, detail):
        """在结果区呈现空、加载、停止或错误状态。"""
        self.clear_result_display()
        state_label = QLabel(f'<b>{title}</b><br><span>{detail}</span>')
        state_label.setProperty('role', 'emptyState')
        state_label.setWordWrap(True)
        state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        state_label.setAccessibleName(f'{title}。{detail}')
        self.result_container_layout.addWidget(state_label)

    def clear_result_display(self):
        while self.result_container_layout.count():
            child = self.result_container_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def update_result_table(self, detail_list, elapsed):
        self.clear_result_display()
        selected_metric = self.metric_combo.currentText()
        show_all = (selected_metric == '全部')

        def _should_show(metric_name):
            if show_all:
                return True
            return selected_metric == metric_name

        for idx, item in enumerate(detail_list):
            battery_group = QGroupBox(item['battery'])
            battery_group.setProperty('role', 'resultCard')
            battery_group.setObjectName(f'result_card_{idx}')
            form_layout = QFormLayout()
            form_layout.setContentsMargins(14, 10, 14, 10)
            form_layout.setSpacing(6)

            form_layout.addRow('电池:', QLabel(str(item['battery'])))
            form_layout.addRow('循环数:', QLabel(str(item['cycles'])))
            form_layout.addRow('模型:', QLabel(str(item['model'])))

            ci = item.get('ci', {})
            n_seeds = item.get('n_seeds', 1)

            fc = item.get('failure_cycle')
            if fc is not None:
                fc_lbl = QLabel(f'第 {fc} 次循环')
                fc_lbl.setProperty('role', 'resultStatus')
                fc_lbl.setProperty('state', 'warning')
                form_layout.addRow('失效循环:', fc_lbl)
                cap_lbl = QLabel(f'{item["threshold"]:.2f} Ah')
                cap_lbl.setProperty('role', 'resultStatus')
                cap_lbl.setProperty('state', 'danger')
                form_layout.addRow('失效容量:', cap_lbl)
            else:
                ok_lbl = QLabel('未失效')
                ok_lbl.setProperty('role', 'resultStatus')
                ok_lbl.setProperty('state', 'success')
                form_layout.addRow('失效循环:', ok_lbl)

            # RMSE
            if _should_show('RMSE'):
                rmse_lbl = QLabel(f"{item['rmse']:.6f}")
                form_layout.addRow('RMSE:', rmse_lbl)
                if n_seeds > 1 and 'rmse' in ci:
                    c = ci['rmse']
                    ci_lbl = QLabel(f"{c['mean']:.4f} ± {c['std']:.4f}\n"
                                    f"95%CI: [{c['lower']:.4f}, {c['upper']:.4f}]")
                    ci_lbl.setStyleSheet('color: #59635D; font-size: 9pt;')
                    form_layout.addRow('  置信区间:', ci_lbl)

            # MAE
            if _should_show('MAE'):
                mae_lbl = QLabel(f"{item['mae']:.6f}")
                form_layout.addRow('MAE:', mae_lbl)
                if n_seeds > 1 and 'mae' in ci:
                    c = ci['mae']
                    ci_lbl = QLabel(f"{c['mean']:.4f} ± {c['std']:.4f}\n"
                                    f"95%CI: [{c['lower']:.4f}, {c['upper']:.4f}]")
                    ci_lbl.setStyleSheet('color: #59635D; font-size: 9pt;')
                    form_layout.addRow('  置信区间:', ci_lbl)

            # R²
            if _should_show('R²'):
                r2_lbl = QLabel(f"{item['r2']:.6f}")
                form_layout.addRow('R²:', r2_lbl)
                if n_seeds > 1 and 'r2' in ci:
                    c = ci['r2']
                    ci_lbl = QLabel(f"{c['mean']:.4f} ± {c['std']:.4f}\n"
                                    f"95%CI: [{c['lower']:.4f}, {c['upper']:.4f}]")
                    ci_lbl.setStyleSheet('color: #59635D; font-size: 9pt;')
                    form_layout.addRow('  置信区间:', ci_lbl)

            # Pearson
            if _should_show('Pearson'):
                pear_lbl = QLabel(f"{item['pearson']:.6f}")
                form_layout.addRow('Pearson:', pear_lbl)
                if n_seeds > 1 and 'pearson' in ci:
                    c = ci['pearson']
                    ci_lbl = QLabel(f"{c['mean']:.4f} ± {c['std']:.4f}\n"
                                    f"95%CI: [{c['lower']:.4f}, {c['upper']:.4f}]")
                    ci_lbl.setStyleSheet('color: #59635D; font-size: 9pt;')
                    form_layout.addRow('  置信区间:', ci_lbl)

            # RE
            if _should_show('RE'):
                re_lbl = QLabel(f"{item['re']:.6f}")
                form_layout.addRow('RE:', re_lbl)
                if n_seeds > 1 and 're' in ci:
                    c = ci['re']
                    ci_lbl = QLabel(f"{c['mean']:.4f} ± {c['std']:.4f}\n"
                                    f"95%CI: [{c['lower']:.4f}, {c['upper']:.4f}]")
                    ci_lbl.setStyleSheet('color: #59635D; font-size: 9pt;')
                    form_layout.addRow('  置信区间:', ci_lbl)

            if n_seeds > 1:
                ns_lbl = QLabel(f'{n_seeds} 次实验')
                ns_lbl.setStyleSheet('color: #315B5A; font-weight: 600;')
                form_layout.addRow('多种子数:', ns_lbl)

            battery_group.setLayout(form_layout)
            self.result_container_layout.addWidget(battery_group)
