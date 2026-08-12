import sys
import os
import traceback

# _StartupSplash 类依赖的 PyQt6 组件必须在类定义前导入
from PyQt6.QtWidgets import (QWidget, QProgressBar,
                              QApplication)
from PyQt6.QtGui import QPixmap, QPainter, QColor, QIcon
from PyQt6.QtCore import Qt


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
        self.setFixedSize(520, 360)
        self.setWindowTitle('正在启动...')

        # ── 背景图片 ──
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        splash_path = os.path.join(base_path, 'splash.png')
        if os.path.exists(splash_path):
            self._bg_pixmap = QPixmap(splash_path).scaled(
                self.size(), Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
        else:
            self._bg_pixmap = QPixmap(self.size())
            self._bg_pixmap.fill(QColor(15, 23, 42))

        # ── 进度条（底部，无文字）──
        self._progress = QProgressBar(self)
        self._progress.setGeometry(40, 310, 440, 8)
        self._progress.setTextVisible(False)       # 不显示内部文字
        self._progress.setMinimum(0)
        self._progress.setMaximum(100)
        self._progress.setValue(0)
        self._progress.setStyleSheet('''
            QProgressBar {
                border: none;
                border-radius: 4px;
                background-color: rgba(51, 65, 85, 0.9);
            }
            QProgressBar::chunk {
                border-radius: 4px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #22D3EE, stop:1 #06B6D4);
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
        painter.drawPixmap(self.rect(), self._bg_pixmap)
        painter.end()

    def set_progress(self, value):
        """更新进度条值（0-100）。"""
        self._progress.setValue(int(value))
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
    app.setWindowIcon(_get_icon())

    # 立即显示启动闪屏
    qt_splash = _StartupSplash()
    qt_splash.show()
    qt_splash.set_progress(5)
    app.processEvents()

    # ── 阶段 2：加载核心模块（进度 5% → 80%，最耗时）──
    qt_splash.set_progress(15)
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

    qt_splash.set_progress(75)
    app.processEvents()

    # ── 阶段 3：初始化主窗口（进度 80% → 95%）──
    qt_splash.set_progress(82)
    app.processEvents()

    window = MainWindow()
    qt_splash.set_progress(92)
    app.processEvents()

    window.show()
    qt_splash.set_progress(98)
    app.processEvents()

    # ── 关闭闪屏（进度 100%）──
    # 标记为程序主动关闭，避免 closeEvent 中 sys.exit(0) 导致整个应用退出
    qt_splash._programmatic_close = True
    qt_splash.close()
    qt_splash.deleteLater()

    sys.exit(app.exec())
