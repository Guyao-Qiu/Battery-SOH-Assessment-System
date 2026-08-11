"""
AnimatedButton - 带水墨按压反馈的自定义 QPushButton
效果：
1. 墨晕（ink bloom）：从落点自然扩散，短促且不发光
2. 压印（wash）：按下瞬间产生低透明度墨色覆盖
3. 激活态：模型按钮的激活高亮
"""
import time
from PyQt6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, QPoint, QPointF, QSize,
    QTimer, pyqtProperty
)
from PyQt6.QtGui import (
    QPainter, QColor, QBrush, QPen, QRadialGradient
)
from PyQt6.QtWidgets import QPushButton


# 角色对应颜色（墨色、浅色、深色）
_ROLE_COLORS = {
    'default':  ('#315B5A', '#6F8C83', '#244743'),
    'primary':  ('#315B5A', '#6F8C83', '#244743'),
    'success':  ('#4F6B4F', '#80947A', '#3C533C'),
    'danger':   ('#9E3D2F', '#BE7468', '#7F2F26'),
    'warning':  ('#98652E', '#B98B58', '#744A20'),
    'ghost':    ('#414A45', '#777F79', '#2B332F'),
    'model':    ('#315B5A', '#6F8C83', '#244743'),
    'hero':     ('#315B5A', '#6F8C83', '#244743'),
}

# 墨晕与压印保持短促，避免持续动效干扰专业操作。
_INK_BLOOM_DURATION = 360
_WASH_DURATION = 180
_MAX_INK_BLOOMS = 2


class AnimatedButton(QPushButton):
    """带墨晕、压印和激活态的 QPushButton。"""

    def __init__(self, text='', role='default', parent=None):
        super().__init__(text, parent)
        self._role = role if role in _ROLE_COLORS else 'default'
        self._ink_blooms = []  # 每项: [x, y, start_ms, max_r]
        self._pressed_inside = False
        self._flash_value = 0.0  # 0~1
        self._active = False  # 模型选择激活态

        self.setProperty('role', self._role)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # 约 60fps 重绘定时器（仅在点击反馈期间运行）
        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(16)
        self._tick_timer.timeout.connect(self._on_tick)

        # 压印属性动画
        self._flash_anim = QPropertyAnimation(self, b'flashValue', self)
        self._flash_anim.setDuration(_WASH_DURATION)
        self._flash_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._flash_anim.finished.connect(lambda: self._tick_timer.stop())

    # ── Qt 属性（供动画使用） ───────────────────────
    def getFlashValue(self):
        return self._flash_value

    def setFlashValue(self, v):
        self._flash_value = v
        self.update()

    flashValue = pyqtProperty(float, getFlashValue, setFlashValue)

    # ── 模型激活态切换 ──────────────────────────────
    def set_active(self, active: bool):
        self._active = active
        self.setProperty('active', 'true' if active else 'false')
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    # ── 鼠标事件 ─────────────────────────────────────
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self.isEnabled():
            self._pressed_inside = True
            self._start_ink_bloom(e.position().toPoint())
            self._trigger_flash()
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        self._pressed_inside = False
        super().mouseReleaseEvent(e)

    # ── 闪光 ─────────────────────────────────────────
    def _trigger_flash(self):
        self._flash_anim.stop()
        self._flash_anim.setStartValue(0.0)
        self._flash_anim.setKeyValueAt(0.25, 1.0)
        self._flash_anim.setEndValue(0.0)
        self._flash_anim.start()
        # 启动重绘定时器驱动波纹
        if not self._tick_timer.isActive():
            self._tick_timer.start()

    # ── 墨晕 ─────────────────────────────────────────
    def _start_ink_bloom(self, pos: QPoint):
        max_r = float(max(self.width(), self.height()) * 0.72)
        self._ink_blooms.append([float(pos.x()), float(pos.y()),
                                 time.time() * 1000.0, max_r])
        while len(self._ink_blooms) > _MAX_INK_BLOOMS:
            self._ink_blooms.pop(0)
        if not self._tick_timer.isActive():
            self._tick_timer.start()
        self.update()

    def _on_tick(self):
        if not self._ink_blooms and self._flash_value <= 0.001:
            self._tick_timer.stop()
            self.update()
            return
        # 清理过期的墨晕
        now = time.time() * 1000.0
        self._ink_blooms = [r for r in self._ink_blooms
                            if (now - r[2]) < _INK_BLOOM_DURATION]
        self.update()

    # ── 自定义绘制：叠加墨晕与压印 ───────────────────
    def paintEvent(self, e):
        super().paintEvent(e)
        if not self._ink_blooms and self._flash_value <= 0.001:
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setClipRect(self.rect())

        # 低透明度压印，模拟墨色落在宣纸上的轻微洇染。
        if self._flash_value > 0.001:
            base_hex = _ROLE_COLORS[self._role][1]
            c = QColor(base_hex)
            c.setAlpha(int(48 * self._flash_value))
            grad = QRadialGradient(
                QPointF(self.rect().center()),
                max(self.width(), self.height()) * 0.6
            )
            grad.setColorAt(0.0, c)
            grad.setColorAt(1.0, QColor(c.red(), c.green(), c.blue(), 0))
            p.fillRect(self.rect(), QBrush(grad))

        # 墨晕没有霓虹描边，只保留柔和的中心与细薄外缘。
        now = time.time() * 1000.0
        for rx, ry, start_ms, max_r in self._ink_blooms:
            progress = (now - start_ms) / _INK_BLOOM_DURATION
            if progress >= 1.0 or progress < 0:
                continue
            # 缓动：OutCubic
            eased = 1.0 - (1.0 - progress) ** 3
            radius = eased * max_r
            opacity = 1.0 - progress

            main_hex = _ROLE_COLORS[self._role][0]

            # 填充
            c_fill = QColor(main_hex)
            c_fill.setAlpha(int(34 * opacity))
            p.setBrush(QBrush(c_fill))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(rx, ry), radius, radius)

            # 描边
            c_edge = QColor(main_hex)
            c_edge.setAlpha(int(80 * opacity))
            pen = QPen(c_edge)
            pen.setWidthF(1.0)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(rx, ry), radius, radius)

        p.end()


def make_button(text, role='default', parent=None):
    """工厂函数：创建带动画效果的按钮"""
    return AnimatedButton(text, role, parent)
