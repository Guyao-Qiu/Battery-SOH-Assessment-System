"""悬浮圆形主题按钮 —— 可自由拖动，替代原顶部条里的文字按钮。

设计要点：
- 圆形（固定 40×40）、无文字，只显示目标主题的图标（月/日）；
- 按住拖动即可把它挪到窗口任意位置，位置按窗口比例持久化，
  窗口缩放后仍停在相对同一处；
- 单击（未拖动）触发主题切换；
- 半透明底 + 细描边，悬浮在内容之上但不抢焦点。
"""

from PyQt6.QtCore import Qt, QPoint, QSettings, QSize
from PyQt6.QtWidgets import QPushButton

from utils.icon_generator import get_dialog_icon

#: 与主窗口共用的 QSettings 组织/应用名（见 ui.main_window 顶部常量）。
SETTINGS_ORG = 'BatterySOH'
SETTINGS_APP = 'AssessmentSystem'
#: 悬浮按钮位置（相对父窗口的比例）持久化键。
POSITION_KEY = 'theme_button_position'

_BUTTON_SIZE = 40
#: 判定为“拖动”而非“单击”的位移阈值（像素）。
_DRAG_THRESHOLD = 4


class FloatingThemeButton(QPushButton):
    """圆形、可拖动的主题切换按钮。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('floatingTheme')
        self.setProperty('role', 'floatingTheme')
        self.setFixedSize(_BUTTON_SIZE, _BUTTON_SIZE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFlat(True)
        self.setAccessibleName('切换浅色或深色主题（可拖动）')
        self._drag_origin = None
        self._drag_offset = QPoint()
        self._dragged = False

    # ── 图标与提示随主题更新 ─────────────────────────────
    def sync_to_theme(self, mode):
        """``mode`` 为当前主题；图标表示**点击后会切到**的目标主题。"""
        target = 'light' if mode == 'dark' else 'dark'
        icon_kind = 'sun' if target == 'light' else 'moon'
        self.setIcon(get_dialog_icon(icon_kind))
        self.setIconSize(QSize(22, 22))
        target_text = '宣纸（浅色）' if target == 'light' else '墨夜（深色）'
        self.setToolTip(f'切换到{target_text}（Ctrl+T）；按住可拖动位置')

    # ── 拖动 ────────────────────────────────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_origin = event.globalPosition().toPoint()
            self._drag_offset = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft())
            self._dragged = False
        # 仍然交给基类：保留按压视觉反馈与正常 clicked 语义
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        parent = self.parent()
        if self._drag_origin is None or parent is None:
            super().mouseMoveEvent(event)
            return
        global_pos = event.globalPosition().toPoint()
        if (global_pos - self._drag_origin).manhattanLength() > _DRAG_THRESHOLD:
            if not self._dragged:
                self._dragged = True
                # 取消按压态：拖动松手不应再被算作一次点击
                self.setDown(False)
            self.move(self._clamped_position(
                parent.mapFromGlobal(global_pos - self._drag_offset)))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._dragged:
            self._drag_origin = None
            self._dragged = False
            self.setDown(False)
            self._save_position()
            event.accept()
            return
        self._drag_origin = None
        super().mouseReleaseEvent(event)

    def _clamped_position(self, position):
        """把按钮限制在父窗口内部，避免拖出可视区域后找不回来。"""
        parent = self.parent()
        if parent is None:
            return position
        max_x = max(0, parent.width() - self.width())
        max_y = max(0, parent.height() - self.height())
        return QPoint(
            min(max(position.x(), 0), max_x),
            min(max(position.y(), 0), max_y),
        )

    # ── 位置持久化（按窗口比例存，缩放窗口后仍相对同位） ──
    def _save_position(self):
        parent = self.parent()
        if parent is None or parent.width() <= 0 or parent.height() <= 0:
            return
        settings = QSettings(SETTINGS_ORG, SETTINGS_APP)
        settings.setValue(POSITION_KEY, [
            self.x() / parent.width(),
            self.y() / parent.height(),
        ])

    def restore_or_default_position(self):
        """按保存的比例还原位置；没有记录时停在右上角（原顶栏按钮处）。"""
        parent = self.parent()
        if parent is None:
            return
        settings = QSettings(SETTINGS_ORG, SETTINGS_APP)
        saved = settings.value(POSITION_KEY)
        if saved:
            try:
                x_ratio, y_ratio = float(saved[0]), float(saved[1])
            except (TypeError, ValueError, IndexError):
                saved = None
        if saved:
            position = QPoint(
                int(parent.width() * x_ratio),
                int(parent.height() * y_ratio),
            )
        else:
            position = QPoint(
                max(0, parent.width() - self.width() - 16), 12)
        self.move(self._clamped_position(position))
