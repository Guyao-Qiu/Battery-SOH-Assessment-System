"""
图标生成器：app 图标 + 各对话框个性化图标 + QMessageBox 统一封装

设计原则：
  - 与深色 Quantum Lab 主题协调：所有线条使用 slate-400 (#94A3B8)，
    既不会在深色背景上"被吞掉"，也不会刺眼
  - 状态类图标（错误/警告/成功/信息）右下角叠加小色点作为语义提示，
    但保持低饱和度，避免抢眼
  - 同一图标仅生成一次并缓存，重复调用零开销
"""
from PyQt6.QtCore import Qt, QRectF, QPointF, QSize
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QLinearGradient, QPainterPath,
    QPolygonF, QPixmap, QIcon,
)
from PyQt6.QtWidgets import QMessageBox


# ─── 调色板（与 style.py / 主题一致） ─────────────────────────
_LINE_COLOR   = QColor(148, 163, 184)   # #94A3B8 slate-400（线条主色）
_LINE_STROKE  = 2.2                     # 对话框图标的描边略粗，便于在标题栏中识别
_ACCENT_STROKE = 2.4
_ACCENT_R     = 4.0                     # 角落小色点半径

_ACCENT_CYAN    = QColor(34, 211, 238)  # #22D3EE info / 通用
_ACCENT_CYAN_D  = QColor(6, 182, 212)   # #06B6D4
_ACCENT_EMERALD = QColor(16, 185, 129)  # #10B981 success
_ACCENT_AMBER   = QColor(245, 158, 11)  # #F59E0B warning
_ACCENT_RED     = QColor(239, 68, 68)   # #EF4444 error
_ACCENT_VIOLET  = QColor(139, 92, 246)  # #8B5CF6 model / NN


# ─── 1. App 图标（电池 + 心电图风格的 SOH 曲线） ─────────────
def _create_battery_icon(size=256):
    """生成 app 主图标：电池外框 + SOH 渐变填充 + 内部退化曲线。"""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    s = size
    m = s * 0.08

    # 电池主体
    body_left = m * 1.5
    body_top = m * 1.8 + s * 0.12
    body_w = s - m * 3
    body_h = s - m * 4 - s * 0.12
    body_radius = s * 0.06
    body_rect = QRectF(body_left, body_top, body_w, body_h)

    # 顶端电极
    terminal_w = s * 0.18
    terminal_h = s * 0.10
    terminal_left = body_left + body_w * 0.35
    terminal_top = m * 1.2
    terminal_path = QPainterPath()
    terminal_rect = QRectF(terminal_left, terminal_top, terminal_w, terminal_h)
    terminal_path.addRoundedRect(terminal_rect, s * 0.02, s * 0.02)
    painter.fillPath(terminal_path, QColor('#64748B'))

    # 内部绿色渐变填充（健康→衰减）
    fill_margin = s * 0.025
    fill_left = body_left + fill_margin
    fill_top = body_top + fill_margin
    fill_w = body_w - fill_margin * 2
    fill_h = body_h - fill_margin * 2
    fill_radius = body_radius - fill_margin * 0.5
    fill_rect = QRectF(fill_left, fill_top, fill_w, fill_h)

    gradient = QLinearGradient(fill_rect.topLeft(), fill_rect.bottomLeft())
    gradient.setColorAt(0.0, QColor('#4ADE80'))
    gradient.setColorAt(0.6, QColor('#22C55E'))
    gradient.setColorAt(1.0, QColor('#16A34A'))
    fill_path = QPainterPath()
    fill_path.addRoundedRect(fill_rect, fill_radius, fill_radius)
    painter.fillPath(fill_path, gradient)

    # 内部 SOH 退化曲线（白色折线，从左上降到右下）
    curve_pen = QPen(QColor('#FFFFFF'), max(2.0, s * 0.018))
    curve_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    curve_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(curve_pen)
    pts = [
        QPointF(fill_left + fill_w * 0.04, fill_top + fill_h * 0.18),
        QPointF(fill_left + fill_w * 0.28, fill_top + fill_h * 0.30),
        QPointF(fill_left + fill_w * 0.50, fill_top + fill_h * 0.55),
        QPointF(fill_left + fill_w * 0.74, fill_top + fill_h * 0.62),
        QPointF(fill_left + fill_w * 0.96, fill_top + fill_h * 0.86),
    ]
    painter.drawPolyline(pts)

    # 主体外框
    body_path = QPainterPath()
    body_path.addRoundedRect(body_rect, body_radius, body_radius)
    pen = QPen(QColor('#475569'), s * 0.025)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPath(body_path)

    pen2 = QPen(QColor('#475569'), s * 0.022)
    painter.setPen(pen2)
    painter.drawPath(terminal_path)

    painter.end()
    return pixmap


_DEFAULT_ICON = None


def get_app_icon():
    """返回 app 主图标（优先加载 SOH.ico，不存在时回退到代码生成）。"""
    global _DEFAULT_ICON
    if _DEFAULT_ICON is None:
        import os
        ico_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'SOH.ico')
        if os.path.exists(ico_path):
            _DEFAULT_ICON = QIcon(ico_path)
        else:
            _DEFAULT_ICON = QIcon(_create_battery_icon(256))
    return _DEFAULT_ICON


# ─── 2. 各对话框个性化图标（64×64，slate-400 线条 + 角落彩色点） ──
_DIALOG_SIZE = QSize(64, 64)


def _accent_dot(p, accent, x, y):
    """在 (x, y) 画一个填充小圆点（accent 为 None 时跳过）。"""
    if accent is None:
        return
    p.save()
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(accent)
    p.drawEllipse(QPointF(x, y), _ACCENT_R, _ACCENT_R)
    p.restore()


def _new_dialog_pixmap(draw_func, accent=None):
    """生成一个 64×64 对话框图标。"""
    pix = QPixmap(_DIALOG_SIZE)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(_LINE_COLOR, _LINE_STROKE))
    p.setBrush(Qt.BrushStyle.NoBrush)
    draw_func(p, _DIALOG_SIZE.width(), accent)
    p.end()
    return pix


# 每个绘制函数签名： (p, size: int, accent: QColor|None)
# 统一约定：圆点放在右上角 (size-7, 7)

def _draw_help(p, s, accent):
    """问号圆圈 — 帮助/参数说明。"""
    cx, cy = s / 2, s / 2
    r = s * 0.34
    p.drawEllipse(QPointF(cx, cy), r, r)
    # ? 上弧
    p.drawArc(int(cx - r * 0.32), int(cy - r * 0.72),
              int(r * 0.64), int(r * 0.50),
              int(45 * 16), int(200 * 16))
    # ? 立柱
    p.drawLine(int(cx), int(cy - r * 0.18),
               int(cx), int(cy + r * 0.05))
    # ? 圆点
    p.drawPoint(QPointF(cx, cy + r * 0.32))
    _accent_dot(p, accent, s - 7, 7)


def _draw_tcp(p, s, accent):
    """TCP/网络 — 中央节点 + 三层扇形波 + 端点小点。"""
    cx, cy = s / 2, s * 0.62
    # 三个端点
    p.drawPoint(QPointF(cx, cy))
    p.drawPoint(QPointF(cx - s * 0.30, cy - s * 0.04))
    p.drawPoint(QPointF(cx + s * 0.30, cy - s * 0.04))
    # 三层弧
    for r in (s * 0.18, s * 0.30, s * 0.42):
        p.drawArc(int(cx - r), int(cy - r * 0.95),
                  int(r * 2), int(r * 1.9),
                  int(35 * 16), int(110 * 16))
    # 底部接收端水平线
    p.drawLine(int(s * 0.20), int(cy + s * 0.22),
               int(s * 0.80), int(cy + s * 0.22))
    _accent_dot(p, accent, s - 7, 7)


def _draw_error(p, s, accent):
    """错误 — 圆 + 红色加粗 X。"""
    cx, cy = s / 2, s / 2
    r = s * 0.34
    p.drawEllipse(QPointF(cx, cy), r, r)
    k = r * 0.55
    p.drawLine(int(cx - k), int(cy - k), int(cx + k), int(cy + k))
    p.drawLine(int(cx + k), int(cy - k), int(cx - k), int(cy + k))
    _accent_dot(p, accent, s - 7, 7)


def _draw_warning(p, s, accent):
    """警告 — 三角 + !。"""
    cx = s / 2
    top_y = s * 0.16
    base_y = s * 0.84
    base_half = s * 0.32
    tri = QPolygonF([
        QPointF(cx, top_y),
        QPointF(cx - base_half, base_y),
        QPointF(cx + base_half, base_y),
    ])
    p.drawPolygon(tri)
    # ! 立柱
    p.drawLine(int(cx), int(s * 0.40), int(cx), int(s * 0.65))
    # ! 圆点
    p.drawPoint(QPointF(cx, s * 0.74))
    _accent_dot(p, accent, s - 7, 7)


def _draw_info(p, s, accent):
    """信息 — 圆 + i。"""
    cx, cy = s / 2, s / 2
    r = s * 0.34
    p.drawEllipse(QPointF(cx, cy), r, r)
    p.drawPoint(QPointF(cx, s * 0.30))   # i 顶
    p.drawLine(int(cx), int(s * 0.42),
               int(cx), int(s * 0.66))    # i 身
    _accent_dot(p, accent, s - 7, 7)


def _draw_success(p, s, accent):
    """成功 — 圆 + 勾。"""
    cx, cy = s / 2, s / 2
    r = s * 0.34
    p.drawEllipse(QPointF(cx, cy), r, r)
    # 勾
    p.drawPolyline([
        QPointF(cx - r * 0.50, cy + r * 0.05),
        QPointF(cx - r * 0.10, cy + r * 0.40),
        QPointF(cx + r * 0.55, cy - r * 0.35),
    ])
    _accent_dot(p, accent, s - 7, 7)


def _draw_folder(p, s, accent):
    """文件夹 — 经典文件柜造型。"""
    m = s * 0.18
    # 标签片
    p.drawPolyline([
        QPointF(m, m + s * 0.04),
        QPointF(m + s * 0.30, m + s * 0.04),
        QPointF(m + s * 0.38, m + s * 0.14),
        QPointF(m + s * 0.38, m + s * 0.18),
    ])
    # 主体
    p.drawPolyline([
        QPointF(m + s * 0.38, m + s * 0.18),
        QPointF(s - m, m + s * 0.18),
        QPointF(s - m, s - m),
        QPointF(m, s - m),
        QPointF(m, m + s * 0.04),
    ])
    # 中线
    p.drawLine(int(m + s * 0.05), int(m + s * 0.55),
               int(s - m - s * 0.05), int(m + s * 0.55))
    _accent_dot(p, accent, s - 7, 7)


def _draw_save(p, s, accent):
    """保存 — 软盘 + 下箭头（与工具栏一致但放大）。"""
    m = s * 0.18
    # 主体
    p.drawRect(int(m), int(m), int(s - 2 * m), int(s - 2 * m))
    # 右上角折角缺口
    p.drawLine(int(s - m - 9), int(m), int(s - m), int(m + 9))
    p.drawLine(int(s - m - 9), int(m), int(s - m - 9), int(m + 9))
    p.drawLine(int(s - m - 9), int(m + 9), int(s - m), int(m + 9))
    # 金属读写片
    p.drawRect(int(m + 6), int(s - m - 12), int(s - 2 * m - 12), 6)
    # 中央向下箭头
    cx = s / 2
    p.drawLine(int(cx), int(m + 12), int(cx), int(s - m - 4))
    p.drawPolyline([
        QPointF(cx - 4, s - m - 8),
        QPointF(cx, s - m - 4),
        QPointF(cx + 4, s - m - 8),
    ])
    _accent_dot(p, accent, s - 7, 7)


def _draw_color(p, s, accent):
    """颜色 — 调色板 + 多色点。"""
    cx, cy = s / 2, s * 0.55
    r = s * 0.34
    # 调色板外轮廓（椭圆）
    p.drawEllipse(QPointF(cx, cy), r, r * 0.85)
    # 拇指孔
    p.setBrush(Qt.GlobalColor.transparent)
    p.drawEllipse(QPointF(cx + r * 0.45, cy + r * 0.20), r * 0.18, r * 0.18)
    # 色点
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(_ACCENT_RED)
    p.drawEllipse(QPointF(cx - r * 0.45, cy - r * 0.35), 3, 3)
    p.setBrush(_ACCENT_AMBER)
    p.drawEllipse(QPointF(cx - r * 0.10, cy - r * 0.65), 3, 3)
    p.setBrush(_ACCENT_EMERALD)
    p.drawEllipse(QPointF(cx + r * 0.30, cy - r * 0.45), 3, 3)
    p.setBrush(_ACCENT_CYAN)
    p.drawEllipse(QPointF(cx + r * 0.55, cy + r * 0.05), 3, 3)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(_LINE_COLOR, _LINE_STROKE))
    _accent_dot(p, accent, s - 7, 7)


def _draw_line(p, s, accent):
    """线条样式 — 实线/虚线/点线 三种。"""
    m = s * 0.16
    # 实线
    p.drawLine(int(m), int(s * 0.30), int(s - m), int(s * 0.30))
    # 虚线
    pen = p.pen()
    pen.setStyle(Qt.PenStyle.DashLine)
    p.setPen(pen)
    p.drawLine(int(m), int(s * 0.52), int(s - m), int(s * 0.52))
    # 点线
    pen.setStyle(Qt.PenStyle.DotLine)
    p.setPen(pen)
    p.drawLine(int(m), int(s * 0.74), int(s - m), int(s * 0.74))
    p.setPen(QPen(_LINE_COLOR, _LINE_STROKE))
    _accent_dot(p, accent, s - 7, 7)


def _draw_subplot(p, s, accent):
    """子图 — 2×2 网格。"""
    m = s * 0.18
    p.drawRect(int(m), int(m), int(s - 2 * m), int(s - 2 * m))
    p.drawLine(int(s / 2), int(m), int(s / 2), int(s - m))
    p.drawLine(int(m), int(s / 2), int(s - m), int(s / 2))
    _accent_dot(p, accent, s - 7, 7)


def _draw_axis(p, s, accent):
    """坐标轴 — X/Y 轴 + 折线（带色高亮）。"""
    m = s * 0.18
    # Y
    p.drawLine(int(m), int(m), int(m), int(s - m))
    # X
    p.drawLine(int(m), int(s - m), int(s - m), int(s - m))
    # Y 箭头
    p.drawPolyline([
        QPointF(m - 3, m + 5),
        QPointF(m, m),
        QPointF(m + 3, m + 5),
    ])
    # X 箭头
    p.drawPolyline([
        QPointF(s - m - 5, s - m - 3),
        QPointF(s - m, s - m),
        QPointF(s - m - 5, s - m + 3),
    ])
    # 折线（用 accent 突出）
    if accent is not None:
        pen = p.pen()
        pen.setColor(accent)
        pen.setWidthF(_ACCENT_STROKE)
        p.setPen(pen)
        p.drawPolyline([
            QPointF(m + 3, s - m - 3),
            QPointF(s * 0.35, s * 0.55),
            QPointF(s * 0.55, s * 0.68),
            QPointF(s * 0.75, s * 0.32),
            QPointF(s - m - 3, s * 0.45),
        ])
        p.setPen(QPen(_LINE_COLOR, _LINE_STROKE))
    _accent_dot(p, accent, s - 7, 7)


def _draw_legend(p, s, accent):
    """图例 — 色块 + 文本行。"""
    m = s * 0.20
    p.drawRect(int(m), int(m), int(s - 2 * m), int(s - 2 * m))
    # 三行色块 + 文本线
    rows = [(0.18, _ACCENT_CYAN), (0.45, _ACCENT_EMERALD), (0.72, _ACCENT_AMBER)]
    for ry, color in rows:
        y = int(m + (s - 2 * m) * ry)
        p.fillRect(int(m + 4), y, int(s * 0.16), 4, color)
        p.drawLine(int(m + s * 0.24), y + 2,
                   int(s - m - 4), y + 2)
    _accent_dot(p, accent, s - 7, 7)


def _draw_chart(p, s, accent):
    """图表 — 折线图（与 toolbar 中 _chart 风格保持一致）。"""
    m = s * 0.18
    # 坐标轴
    p.drawLine(int(m), int(s - m), int(s - m), int(s - m))
    p.drawLine(int(m), int(m), int(m), int(s - m))
    # 折线
    pen = p.pen()
    pen.setWidthF(_ACCENT_STROKE)
    p.setPen(pen)
    p.drawPolyline([
        QPointF(m + 2, s - m - 2),
        QPointF(s * 0.30, s * 0.55),
        QPointF(s * 0.50, s * 0.70),
        QPointF(s * 0.70, s * 0.30),
        QPointF(s - m - 2, s * 0.45),
    ])
    p.setPen(QPen(_LINE_COLOR, _LINE_STROKE))
    _accent_dot(p, accent, s - 7, 7)


def _draw_model(p, s, accent):
    """模型 — 3-2-1 全连接神经网络。"""
    m = s * 0.18
    left_x  = m + 4
    mid_x   = s / 2
    right_x = s - m - 4
    left_ys  = [m + 6, s / 2, s - m - 6]
    mid_ys   = [s * 0.32, s * 0.68]
    right_ys = [s / 2]

    # 浅色连接线
    pen = p.pen()
    pen.setWidthF(0.9)
    p.setPen(pen)
    for y1 in left_ys:
        for y2 in mid_ys:
            p.drawLine(QPointF(left_x, y1), QPointF(mid_x, y2))
    for y1 in mid_ys:
        for y2 in right_ys:
            p.drawLine(QPointF(mid_x, y1), QPointF(right_x, y2))

    # 节点
    p.setPen(QPen(_LINE_COLOR, _LINE_STROKE))
    for x, ys in [(left_x, left_ys), (mid_x, mid_ys), (right_x, right_ys)]:
        for y in ys:
            p.drawEllipse(QPointF(x, y), 3.2, 3.2)

    _accent_dot(p, accent, s - 7, 7)


def _draw_import(p, s, accent):
    """导入 — 文件 + 向下箭头。"""
    m = s * 0.18
    # 文件
    p.drawRect(int(m + 6), int(m), int(s * 0.55), int(s * 0.62))
    p.drawLine(int(m + 6 + s * 0.10), int(m),
               int(m + 6 + s * 0.10), int(m - 4))
    p.drawLine(int(m + 6 + s * 0.10), int(m - 4),
               int(m + 6 + s * 0.32), int(m - 4))
    p.drawLine(int(m + 6 + s * 0.32), int(m - 4),
               int(m + 6 + s * 0.32), int(m))
    # 向下箭头
    cx = s * 0.78
    p.drawLine(int(cx), int(m + s * 0.10),
               int(cx), int(s - m))
    p.drawPolyline([
        QPointF(cx - 5, s - m - 6),
        QPointF(cx, s - m),
        QPointF(cx + 5, s - m - 6),
    ])
    _accent_dot(p, accent, s - 7, 7)


def _draw_export(p, s, accent):
    """导出 — 文件 + 向上箭头。"""
    m = s * 0.18
    # 文件
    p.drawRect(int(m + 6), int(m + s * 0.30), int(s * 0.55), int(s * 0.62))
    p.drawLine(int(m + 6 + s * 0.10), int(m + s * 0.30),
               int(m + 6 + s * 0.10), int(m + s * 0.30 - 4))
    p.drawLine(int(m + 6 + s * 0.10), int(m + s * 0.30 - 4),
               int(m + 6 + s * 0.32), int(m + s * 0.30 - 4))
    p.drawLine(int(m + 6 + s * 0.32), int(m + s * 0.30 - 4),
               int(m + 6 + s * 0.32), int(m + s * 0.30))
    # 向上箭头
    cx = s * 0.78
    p.drawLine(int(cx), int(m),
               int(cx), int(s - m - s * 0.10))
    p.drawPolyline([
        QPointF(cx - 5, m + 6),
        QPointF(cx, m),
        QPointF(cx + 5, m + 6),
    ])
    _accent_dot(p, accent, s - 7, 7)


_DIALOG_DRAW_FUNCS = {
    'help':        _draw_help,
    'tcp':         _draw_tcp,
    'error':       _draw_error,
    'warning':     _draw_warning,
    'info':        _draw_info,
    'success':     _draw_success,
    'question':    _draw_help,
    'folder':      _draw_folder,
    'save':        _draw_save,
    'color':       _draw_color,
    'line':        _draw_line,
    'subplot':     _draw_subplot,
    'axis':        _draw_axis,
    'legend':      _draw_legend,
    'chart':       _draw_chart,
    'model':       _draw_model,
    'import':      _draw_import,
    'export':      _draw_export,
}

# 状态 → 角落小色点（柔和，不抢眼）
_ACCENT_FOR_KIND = {
    'help':        _ACCENT_CYAN,
    'tcp':         _ACCENT_CYAN,
    'error':       _ACCENT_RED,
    'warning':     _ACCENT_AMBER,
    'info':        _ACCENT_CYAN,
    'success':     _ACCENT_EMERALD,
    'question':    _ACCENT_CYAN,
    'folder':      _ACCENT_CYAN,
    'save':        _ACCENT_CYAN,
    'color':       _ACCENT_CYAN,
    'line':        _ACCENT_CYAN,
    'subplot':     _ACCENT_CYAN,
    'axis':        _ACCENT_CYAN_D,
    'legend':      _ACCENT_CYAN,
    'chart':       _ACCENT_CYAN_D,
    'model':       _ACCENT_VIOLET,
    'import':      _ACCENT_CYAN,
    'export':      _ACCENT_EMERALD,
}

_dialog_icon_cache = {}


def get_dialog_icon(kind):
    """根据对话框类型返回对应的 QIcon（带缓存）。

    支持的 kind：
      app / help / tcp / error / warning / info / success / question /
      folder / save / color / line / subplot / axis / legend / chart /
      model / import / export
    """
    if kind == 'app':
        return get_app_icon()
    if kind not in _dialog_icon_cache:
        accent = _ACCENT_FOR_KIND.get(kind)
        fn = _DIALOG_DRAW_FUNCS[kind]
        pix = _new_dialog_pixmap(fn, accent)
        _dialog_icon_cache[kind] = QIcon(pix)
    return _dialog_icon_cache[kind]


# 简化别名：只取回 pixmap（用于 QMessageBox.setIconPixmap）
def get_dialog_pixmap(kind, size=48):
    """获取指定 kind 的对话框图标 pixmap（用于嵌入到 QMessageBox 内部）。"""
    icon = get_dialog_icon(kind)
    return icon.pixmap(QSize(size, size))


# ─── 3. QMessageBox 统一封装（自动应用主题色 + 个性化图标） ──────
_ICON_ROLE_MAP = {
    'error':    QMessageBox.Icon.Critical,
    'warning':  QMessageBox.Icon.Warning,
    'info':     QMessageBox.Icon.Information,
    'success':  QMessageBox.Icon.Information,
    'question': QMessageBox.Icon.Question,
}

# 中文按钮文案
_BTN_TEXT = {
    'ok': '确定',
    'cancel': '取消',
    'yes': '是',
    'no': '否',
    'save': '保存',
    'discard': '不保存',
    'open': '打开',
    'close': '关闭',
    'apply': '应用',
    'reset': '重置',
}


def show_message(parent, kind, title, text, *, buttons=None, default=None):
    """弹出 QMessageBox，自动设置标题栏 + 内部图标为个性化版本。

    参数：
        parent  : 父窗口
        kind    : 'error' / 'warning' / 'info' / 'success' / 'question'
        title   : 标题
        text    : 正文
        buttons : 可选，QMessageBox.StandardButton 组合；默认只显示"确定"
        default : 默认按钮

    返回：QMessageBox.StandardButton（即用户点击的按钮）
    """
    mb = QMessageBox(parent)
    mb.setIcon(_ICON_ROLE_MAP.get(kind, QMessageBox.Icon.Information))
    mb.setWindowTitle(title)
    mb.setText(text)

    # 内部图标用个性化版本
    pixmap = get_dialog_pixmap(kind, 48)
    mb.setIconPixmap(pixmap)

    # 标题栏图标
    mb.setWindowIcon(get_dialog_icon(kind))

    # 按钮
    if buttons is not None:
        mb.setStandardButtons(buttons)
        if default is not None:
            mb.setDefaultButton(default)

    # 中文化按钮（仅识别 PyQt6 内置角色，不破坏其他自定义按钮）
    _translate_msgbox_buttons(mb)

    return mb.exec()


def _translate_msgbox_buttons(mb):
    """将 QMessageBox 的标准按钮文案改为中文。"""
    mapping = {
        QMessageBox.StandardButton.Ok: '确定',
        QMessageBox.StandardButton.Cancel: '取消',
        QMessageBox.StandardButton.Yes: '是',
        QMessageBox.StandardButton.No: '否',
        QMessageBox.StandardButton.Save: '保存',
        QMessageBox.StandardButton.Discard: '不保存',
        QMessageBox.StandardButton.Open: '打开',
        QMessageBox.StandardButton.Close: '关闭',
        QMessageBox.StandardButton.Apply: '应用',
        QMessageBox.StandardButton.Reset: '重置',
        QMessageBox.StandardButton.YesToAll: '全部是',
        QMessageBox.StandardButton.NoToAll: '全部否',
        QMessageBox.StandardButton.Abort: '中止',
        QMessageBox.StandardButton.Retry: '重试',
        QMessageBox.StandardButton.Ignore: '忽略',
        QMessageBox.StandardButton.Help: '帮助',
    }
    for btn in mb.buttons():
        std = mb.standardButton(btn)
        if std in mapping:
            btn.setText(mapping[std])


# ─── 4. QInputDialog 包装（个性化图标 + 中文化按钮） ──────────────
def input_get_item(parent, title, label, items, current=0, editable=False, icon_kind='axis'):
    """替代 QInputDialog.getItem，自动应用个性化图标。"""
    from PyQt6.QtWidgets import QInputDialog
    dlg = QInputDialog(parent)
    dlg.setWindowTitle(title)
    dlg.setLabelText(label)
    dlg.setComboBoxEditable(editable)
    dlg.setComboBoxItems(list(items))
    if 0 <= current < len(items):
        dlg.setCurrentIndex(current)
    dlg.setWindowIcon(get_dialog_icon(icon_kind))
    if dlg.exec() == QMessageBox.StandardButton.Ok:
        return dlg.currentText(), True
    return '', False
