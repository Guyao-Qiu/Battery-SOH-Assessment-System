from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QSplitter,
    QWidget, QSizePolicy,
)
from ui.chart_show import MplCanvas
from utils.icon_generator import get_dialog_icon


class TcpDisplayWindow(QDialog):
    """TCP 实时数据接入独立显示窗口"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('实时数据接入 — SOH / RUL 预测')
        self.setWindowIcon(get_dialog_icon('tcp'))
        self.resize(1200, 800)
        self.setMinimumSize(900, 600)

        self._measured = []
        self._predicted = []
        self._current_capacity = None
        self._current_soh = None

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # ── 状态栏 ──
        self.status_label = QLabel('等待数据...')
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(
            'font-size: 14px; font-weight: bold; padding: 10px;'
            ' color: #315B5A; background: #FAF6EC;'
            ' border: 1px solid #898D84; border-radius: 4px;'
            ' letter-spacing: 1px;'
        )
        layout.addWidget(self.status_label)

        # ── 图表 ──
        self.canvas = MplCanvas()
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.canvas, 2)

        # ── 底部：SOH 表 / RUL 表 ──
        bottom = QWidget()
        bottom_layout = QHBoxLayout(bottom)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(10)

        soh_group = QGroupBox('SOH 阶段预测')
        soh_layout = QVBoxLayout()
        self.soh_label = QLabel('等待数据...')
        self.soh_label.setTextFormat(Qt.TextFormat.RichText)
        self.soh_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.soh_label.setWordWrap(True)
        soh_layout.addWidget(self.soh_label)
        soh_group.setLayout(soh_layout)

        rul_group = QGroupBox('剩余使用寿命 (RUL)')
        rul_layout = QVBoxLayout()
        self.rul_label = QLabel('等待数据...')
        self.rul_label.setTextFormat(Qt.TextFormat.RichText)
        self.rul_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.rul_label.setWordWrap(True)
        rul_layout.addWidget(self.rul_label)
        rul_group.setLayout(rul_layout)

        bottom_layout.addWidget(soh_group, 1)
        bottom_layout.addWidget(rul_group, 1)
        layout.addWidget(bottom, 1)

    def update_status(self, capacity, soh):
        self._current_capacity = capacity
        self._current_soh = soh
        self.status_label.setText(
            f'当前容量：{capacity:.6f} Ah  |  SOH：{soh:.1f}%  |  '
            f'已接收 {len(self._measured)} 个循环')

    def update_chart(self, measured, predicted, rated_capacity, threshold_ratio):
        self._measured = list(measured)
        self._predicted = list(predicted)
        self.canvas.plot_tcp_predictions(
            measured, predicted, rated_capacity, threshold_ratio)

    def update_soh(self, soh_info):
        rows = [
            '<table border="0" cellpadding="6" cellspacing="0" width="100%"',
            '       style="border-collapse:collapse; color:#202724; font-size:10pt;">',
            '<tr style="background:#315B5A; color:#FFF9ED; font-weight:bold;">',
            '<th>SOH (%)</th><th>循环次数</th><th>容量 (Ah)</th></tr>'
        ]
        for pct in [100, 95, 90, 85, 80]:
            info = soh_info.get(pct, {})
            cycle = info.get('cycle')
            cap = info.get('capacity')
            cycle_str = str(cycle) if cycle is not None else '-'
            cap_str = f'{cap:.4f}' if isinstance(cap, (int, float)) else '-'
            rows.append(
                f'<tr style="background:#F3EDE0; border-bottom:1px solid #C5BBAA;">'
                f'<td style="color:#315B5A; font-weight:bold;">{pct}%</td>'
                f'<td>{cycle_str}</td><td>{cap_str}</td></tr>'
            )
        rows.append('</table>')
        self.soh_label.setText(''.join(rows))

    def update_rul(self, rul_info):
        rows = [
            '<table border="0" cellpadding="6" cellspacing="0" width="100%"',
            '       style="border-collapse:collapse; color:#202724; font-size:10pt;">',
            '<tr style="background:#4F6B4F; color:#FFF9ED; font-weight:bold;">',
            '<th>当前 SOH (%)</th><th>距 SOH=80% 剩余循环</th></tr>'
        ]
        for pct in [85, 84, 83, 82, 81]:
            remaining = rul_info.get(pct)
            r_str = str(remaining) if remaining is not None else '-'
            rows.append(
                f'<tr style="background:#F3EDE0; border-bottom:1px solid #C5BBAA;">'
                f'<td style="color:#3F6045; font-weight:bold;">{pct}%</td>'
                f'<td>{r_str}</td></tr>'
            )
        rows.append('</table>')
        self.rul_label.setText(''.join(rows))

    def closeEvent(self, event):
        self.hide()
        event.ignore()
