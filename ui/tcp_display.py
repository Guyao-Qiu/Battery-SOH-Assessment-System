"""TCP 实时数据接入独立显示窗口。

A10 后服务端发出的数据形状变了：

- ``soh_update_signal``  → ``{pct: {'cycle_offset': int|None, 'reached': bool}}``
- ``rul_update_signal``  → ``{'rul': int|None, 'threshold': float,
  'rated_capacity': float, 'unit': 'cycles', 'definition': str}``

旧实现把 RUL 当成「SOH 从 pct% 掉到 80% 需要多少个循环」，那**不是**从现在起的
剩余寿命；这里按新语义展示。
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QWidget,
    QSizePolicy,
)
from ui.chart_show import MplCanvas
from ui.style import theme_tokens
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
        self._tokens = theme_tokens()

        self._build_ui()

    def _build_ui(self):
        tokens = self._tokens
        layout = QVBoxLayout(self)

        # ── 状态栏 ──
        self.status_label = QLabel('等待数据...')
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setProperty('role', 'resultSummaryTitle')
        self.status_label.setStyleSheet(
            f'font-size: 14px; font-weight: bold; padding: 10px;'
            f' color: {tokens["primary_d"]};'
            f' background: {tokens["bg_surface"]};'
            f' border: 1px solid {tokens["border"]}; border-radius: 4px;'
            ' letter-spacing: 1px;'
        )
        layout.addWidget(self.status_label)

        # ── 图表 ──
        self.canvas = MplCanvas()
        self.canvas.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
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

    # ── 主题 ─────────────────────────────────────────────────
    def apply_theme_tokens(self, tokens):
        self._tokens = tokens
        if self._measured or self._predicted:
            self.canvas.apply_theme_tokens(tokens)
            self.canvas.plot_tcp_predictions(
                self._measured, self._predicted,
                self._rated_capacity, self._threshold_ratio)

    # ── 更新 ─────────────────────────────────────────────────
    def update_status(self, capacity, soh):
        self._current_capacity = capacity
        self._current_soh = soh
        self.status_label.setText(
            f'当前容量：{capacity:.4f} Ah  |  SOH：{soh:.1f}%  |  '
            f'已接收 {len(self._measured)} 个循环')

    def update_chart(self, measured, predicted, rated_capacity, threshold_ratio):
        self._measured = list(measured)
        self._predicted = list(predicted)
        self._rated_capacity = rated_capacity
        self._threshold_ratio = threshold_ratio
        self.canvas.plot_tcp_predictions(
            measured, predicted, rated_capacity, threshold_ratio)

    def update_soh(self, soh_info):
        tokens = self._tokens
        rows = [
            '<table border="0" cellpadding="6" cellspacing="0" width="100%"',
            '       style="border-collapse:collapse;'
            f' color:{tokens["text"]}; font-size:10pt;">',
            f'<tr style="background:{tokens["primary"]};'
            f' color:{tokens["on_accent"]}; font-weight:bold;">',
            '<th>SOH (%)</th><th>距最新循环</th><th>状态</th></tr>',
        ]
        for pct in (100, 95, 90, 85, 80):
            info = soh_info.get(pct, {}) or {}
            offset = info.get('cycle_offset')
            reached = info.get('reached')
            offset_str = '—' if offset is None else f'{offset:+d}'
            if offset is None:
                state = '预测期内未到达'
            elif reached:
                state = '✓ 已到达'
            else:
                state = '预测中'
            rows.append(
                f'<tr style="background:{tokens["bg_base"]};'
                f' border-bottom:1px solid {tokens["border_soft"]};">'
                f'<td style="color:{tokens["primary"]}; font-weight:bold;">'
                f'{pct}%</td>'
                f'<td>{offset_str}</td><td>{state}</td></tr>'
            )
        rows.append('</table>')
        self.soh_label.setText(''.join(rows))

    def update_rul(self, rul_info):
        tokens = self._tokens
        rul = rul_info.get('rul')
        threshold = rul_info.get('threshold')
        rated = rul_info.get('rated_capacity')
        if rul is None:
            value_text = '预测期内不会越过失效阈值'
        elif rul == 0:
            value_text = '0 个循环（当前已低于失效阈值）'
        else:
            value_text = f'{int(rul)} 个循环'
        threshold_text = (
            f'{threshold:.4f} Ah'
            f'（额定 {rated:.4f} Ah 的 '
            f'{(threshold / rated * 100) if rated else 0:.0f}%）'
            if threshold is not None and rated else '—')
        rows = [
            '<table border="0" cellpadding="6" cellspacing="0" width="100%"',
            '       style="border-collapse:collapse;'
            f' color:{tokens["text"]}; font-size:10pt;">',
            f'<tr style="background:{tokens["success"]};'
            f' color:{tokens["on_accent"]}; font-weight:bold;">',
            '<th>项目</th><th>数值</th></tr>',
            f'<tr style="background:{tokens["bg_base"]};">'
            f'<td>剩余寿命 (RUL)</td><td>{value_text}</td></tr>',
            f'<tr style="background:{tokens["bg_base"]};">'
            f'<td>失效阈值</td><td>{threshold_text}</td></tr>',
            '</table>',
            f'<p style="color:{tokens["text_muted"]}; font-size:9pt;">'
            f'{rul_info.get("definition", "")}</p>',
        ]
        self.rul_label.setText(''.join(rows))

    def closeEvent(self, event):
        self.hide()
        event.ignore()
