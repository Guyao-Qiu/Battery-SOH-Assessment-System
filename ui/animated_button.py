"""
AnimatedButton - 带水墨按压反馈的自定义 QPushButton
效果：
1. 墨晕（ink bloom）：从落点自然扩散，短促且不发光
2. 压印（wash）：按下瞬间产生低透明度墨色覆盖
3. 激活态：模型按钮的激活高亮
"""
import sys
import time
from PyQt6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, QPoint, QPointF, QSize,
    QTimer, pyqtProperty
)
from PyQt6.QtGui import (
    QPainter, QColor, QBrush, QPen, QRadialGradient
)
from PyQt6.QtWidgets import QPushButton

from theme_tokens import get_theme


# 角色对应颜色（墨色、浅色、深色）——取值全部来自 theme_tokens。
# 键仍是角色名，这样构造函数里的 `role in _ROLE_COLORS` 判断保持原样；
# 值为 ``(token, token, token)`` 三元组：主墨色 / 压印色 / 深色。
_ROLE_COLORS = {
    'default':  ('primary', 'primary_l', 'primary_d'),
    'primary':  ('primary', 'primary_l', 'primary_d'),
    'success':  ('success', 'success_l', 'success_d'),
    'danger':   ('danger', 'danger_d', 'danger_d'),
    'warning':  ('warning', 'warning', 'warning'),
    'ghost':    ('text_dim', 'text_muted', 'text'),
    'model':    ('primary', 'primary_l', 'primary_d'),
    'hero':     ('primary', 'primary_l', 'primary_d'),
}

#: 当前主题模式，仅在拿不到 ``ui.style`` 时兜底。
_current_theme_mode = 'light'


def set_button_theme(mode):
    """设置按钮动画跟随的主题（``'light'`` / ``'dark'``）。"""
    global _current_theme_mode
    _current_theme_mode = str(mode).strip().lower()


def _tokens():
    """当前主题 token：优先问**已加载**的 ``ui.style``。

    用 ``sys.modules`` 而不是 ``import ui.style``：``ui/__init__.py`` 会连带
    导入 main_window / torch，而按钮可能在重库加载完成前就被创建；本模块
    也因此绝不反向被 ``ui.style`` 导入，不存在循环导入。
    """
    style = sys.modules.get('ui.style')
    if style is not None:
        try:
            return style.theme_tokens()
        except (AttributeError, KeyError, ImportError):
            # ui.style 已加载但没有 theme_tokens（例如版本不匹配）时回退
            return get_theme(_current_theme_mode)
    return get_theme(_current_theme_mode)


def _role_color(role, index):
    """取某角色的第 ``index`` 个 token 对应的 ``'#RRGGBB'``。"""
    return _tokens()[_ROLE_COLORS[role][index]]


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
            c = QColor(_role_color(self._role, 1))
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

            main_hex = _role_color(self._role, 0)

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
