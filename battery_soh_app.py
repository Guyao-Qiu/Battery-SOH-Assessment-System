import sys
import os
import traceback

# _StartupSplash 类依赖的 PyQt6 组件必须在类定义前导入
from PyQt6.QtWidgets import (QWidget, QProgressBar, QLabel,
                               QApplication)
from PyQt6.QtGui import QPainter, QColor, QIcon, QLinearGradient, QPen
from PyQt6.QtCore import Qt, QRectF


def concise_startup_error(error):
    """Return one safe line for a startup dialog; traceback stays in logs."""
    first_line = next(
        (line.strip() for line in str(error).splitlines() if line.strip()),
        error.__class__.__name__,
    )
    return f'加载核心模块失败：{first_line[:500]}'


def _get_icon():
    """加载 SOH.ico 作为应用图标（不导入 utils，避免提前触发 torch 导入）。"""
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    ico_path = os.path.join(base_path, 'SOH.ico')
    if os.path.exists(ico_path):
        return QIcon(ico_path)
    return QIcon()


class _StartupSplash(QWidget):
    """自定义启动闪屏：背景图 + 动态进度条 + 原生窗口控制按钮"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('startupSplash')
        self.setProperty('visualWorld', 'paperInk')

        # 标记：是否为程序代码主动关闭（区别于用户点击标题栏关闭按钮）
        self._programmatic_close = False

        # 窗口属性：置顶、保留标题栏以获得原生 最小化/最大化/关闭 按钮
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.CustomizeWindowHint |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.WindowMinimizeButtonHint |
            Qt.WindowType.WindowMaximizeButtonHint |
            Qt.WindowType.WindowCloseButtonHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setFixedSize(620, 400)
        self.setWindowTitle('电池 SOH 评估系统')

        self.setStyleSheet('''
            QLabel[role="splashBadge"] {
                color: #76563A;
                background: rgba(152, 101, 46, 0.08);
                border: 1px solid #98652E;
                border-radius: 9px;
                padding: 3px 8px;
                font-family: "Microsoft YaHei UI";
                font-size: 10px;
                font-weight: 600;
            }
            QLabel[role="splashTitle"] {
                color: #244743;
                background: transparent;
                font-family: "STZhongsong", "FangSong", "Microsoft YaHei UI";
                font-size: 26px;
                font-weight: 700;
                letter-spacing: 1px;
            }
            QLabel[role="splashSubtitle"] {
                color: #59635D;
                background: transparent;
                font-family: "Microsoft YaHei UI";
                font-size: 11px;
                letter-spacing: 1px;
            }
            QLabel[role="splashStage"] {
                color: #59635D;
                background: rgba(250, 246, 236, 0.78);
                border: 1px solid #C5BBAA;
                border-radius: 12px;
                font-family: "Microsoft YaHei UI";
                font-size: 11px;
                font-weight: 600;
                padding: 5px 10px;
            }
            QLabel[role="splashStage"][state="active"] {
                color: #FFF9ED;
                background: #315B5A;
                border-color: #244743;
            }
            QLabel[role="splashStage"][state="complete"] {
                color: #315B5A;
                background: rgba(49, 91, 90, 0.10);
                border-color: #52766E;
            }
        ''')

        self._badge_label = QLabel('本地研究评估', self)
        self._badge_label.setProperty('role', 'splashBadge')
        self._badge_label.setGeometry(476, 34, 106, 26)
        self._badge_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._title_label = QLabel('电池 SOH 评估系统', self)
        self._title_label.setProperty('role', 'splashTitle')
        self._title_label.setGeometry(104, 55, 390, 46)

        self._subtitle_label = QLabel(
            'Battery State of Health Assessment Workspace', self)
        self._subtitle_label.setProperty('role', 'splashSubtitle')
        self._subtitle_label.setGeometry(106, 101, 390, 24)

        self._stage_labels = []
        for index, text in enumerate(('数据准备', '模型加载', '工作台就绪')):
            label = QLabel(text, self)
            label.setProperty('role', 'splashStage')
            label.setProperty('state', 'active' if index == 0 else 'idle')
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setGeometry(48 + index * 190, 211, 144, 34)
            label.setAccessibleName(f'启动阶段：{text}')
            self._stage_labels.append(label)

        # ── 加载状态与百分比进度 ──
        self._status_label = QLabel('正在准备启动…', self)
        self._status_label.setGeometry(48, 302, 524, 24)
        self._status_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._status_label.setAccessibleName('当前加载阶段')
        self._status_label.setStyleSheet('''
            QLabel {
                color: #59635D;
                font-family: "Microsoft YaHei UI";
                font-size: 12px;
                font-weight: 500;
                background: transparent;
            }
        ''')

        self._progress = QProgressBar(self)
        self._progress.setGeometry(48, 337, 524, 22)
        self._progress.setTextVisible(True)
        self._progress.setFormat('%p%')
        self._progress.setAccessibleName('应用启动进度')
        self._progress.setMinimum(0)
        self._progress.setMaximum(100)
        self._progress.setValue(0)
        self._progress.setStyleSheet('''
            QProgressBar {
                border: 1px solid #898D84;
                border-radius: 6px;
                background-color: #FAF6EC;
                color: #202724;
                font-family: "Microsoft YaHei UI";
                font-size: 11px;
                font-weight: 600;
                text-align: center;
            }
            QProgressBar::chunk {
                border-radius: 5px;
                background: #315B5A;
            }
        ''')

        # 居中显示
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = (geo.width() - self.width()) // 2 + geo.x()
            y = (geo.height() - self.height()) // 2 + geo.y()
            self.move(x, y)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        paper = QLinearGradient(0, 0, self.width(), self.height())
        paper.setColorAt(0.0, QColor('#FAF6EC'))
        paper.setColorAt(0.58, QColor('#F3EDE0'))
        paper.setColorAt(1.0, QColor('#E8E0D1'))
        painter.fillRect(self.rect(), paper)

        painter.setPen(QPen(QColor(49, 91, 90, 14), 1))
        for offset in range(-120, 660, 28):
            painter.drawLine(offset, 0, offset + 180, self.height())

        painter.setPen(QPen(QColor('#315B5A'), 2))
        painter.setBrush(QColor(49, 91, 90, 18))
        painter.drawRoundedRect(QRectF(46, 55, 42, 56), 7, 7)
        painter.drawRect(QRectF(58, 49, 18, 7))
        painter.drawLine(57, 93, 77, 93)
        painter.drawLine(57, 83, 72, 83)
        painter.drawLine(57, 73, 67, 73)

        painter.setPen(QPen(QColor(137, 141, 132, 100), 1))
        painter.drawLine(48, 178, 572, 178)
        painter.drawLine(192, 228, 238, 228)
        painter.drawLine(382, 228, 428, 228)

        painter.setPen(QPen(QColor(49, 91, 90, 28), 1))
        painter.setBrush(QColor(49, 91, 90, 10))
        painter.drawEllipse(QRectF(468, 90, 92, 68))
        painter.drawEllipse(QRectF(493, 105, 48, 36))

        painter.setPen(QPen(QColor(137, 141, 132, 120), 1))
        painter.drawRoundedRect(QRectF(18, 18, 584, 364), 10, 10)
        painter.end()

    def set_progress(self, value, status):
        """更新真实启动阶段、百分比和窗口标题。"""
        progress = max(0, min(100, int(value)))
        self._progress.setValue(progress)
        self._status_label.setText(str(status))
        active_stage = 0 if progress < 75 else (1 if progress < 92 else 2)
        for index, label in enumerate(self._stage_labels):
            state = 'complete' if index < active_stage else (
                'active' if index == active_stage else 'idle')
            label.setProperty('state', state)
            label.style().unpolish(label)
            label.style().polish(label)
        self.setWindowTitle(f'电池 SOH 评估系统 · {progress}%')
        QApplication.processEvents()

    def closeEvent(self, event):
        """
        区分两种关闭场景：
        - 用户点击标题栏关闭按钮 → 强制退出整个进程
        - 主程序加载完成后主动关闭闪屏 → 仅关闭窗口，不退出进程
        """
        if self._programmatic_close:
            # 程序主动关闭，正常关闭窗口即可
            super().closeEvent(event)
        else:
            # 用户手动点击关闭按钮 → 退出整个应用
            sys.exit(0)


if __name__ == '__main__':
    # ── 阶段 1：立即创建 QApplication 并显示闪屏（目标 < 3秒）──
    # 注意：不在此处导入 utils/torch 等重模块，确保闪屏秒开
    app = QApplication(sys.argv)
    app.setApplicationDisplayName('Battery SOH Assessment System')
    app.setWindowIcon(_get_icon())

    # 立即显示启动闪屏
    qt_splash = _StartupSplash()
    qt_splash.show()
    qt_splash.set_progress(5, '正在准备应用界面…')
    app.processEvents()

    # ── 阶段 2：加载核心模块（进度 5% → 80%，最耗时）──
    qt_splash.set_progress(15, '正在加载计算与绘图组件…')
    app.processEvents()

    try:
        from ui.main_window import MainWindow
    except Exception as startup_error:
        traceback.print_exc()
        qt_splash._programmatic_close = True
        qt_splash.close()
        try:
            from utils.logger import setup_logger
            setup_logger().exception('加载核心模块失败')
        except Exception:
            traceback.print_exc()
        try:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                None, '启动失败', concise_startup_error(startup_error))
        except Exception:
            traceback.print_exc()
        sys.exit(1)

    qt_splash.set_progress(75, '核心组件加载完成')
    app.processEvents()

    # ── 阶段 3：初始化主窗口（进度 80% → 95%）──
    qt_splash.set_progress(82, '正在初始化主窗口…')
    app.processEvents()

    window = MainWindow()
    qt_splash.set_progress(92, '正在恢复配置与界面状态…')
    app.processEvents()

    window.show()
    qt_splash.set_progress(98, '正在呈现主界面…')
    app.processEvents()

    # ── 关闭闪屏（进度 100%）──
    # 标记为程序主动关闭，避免 closeEvent 中 sys.exit(0) 导致整个应用退出
    qt_splash.set_progress(100, '启动完成')
    qt_splash._programmatic_close = True
    qt_splash.close()
    qt_splash.deleteLater()

    sys.exit(app.exec())
