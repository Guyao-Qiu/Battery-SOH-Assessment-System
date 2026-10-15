import os
import sys
import time
import traceback

# _StartupSplash 类依赖的 PyQt6 组件必须在类定义前导入
from PyQt6.QtWidgets import (
    QWidget, QProgressBar, QLabel, QApplication,
    QFrame, QHBoxLayout, QVBoxLayout,
)
from PyQt6.QtGui import QPainter, QColor, QIcon, QLinearGradient, QPen
from PyQt6.QtCore import Qt, QRectF, QSettings

# theme_tokens 是纯字典 + 纯函数，不 import 任何第三方库，
# 因此闪屏可以在 torch / matplotlib 加载之前就拿到颜色（U7③）。
from theme_tokens import DEFAULT_THEME, THEMES, THEME_SETTINGS_KEY


def concise_startup_error(error):
    """Return one safe line for a startup dialog; traceback stays in logs."""
    first_line = next(
        (line.strip() for line in str(error).splitlines() if line.strip()),
        error.__class__.__name__,
    )
    return f'加载核心模块失败：{first_line[:500]}'


def _saved_theme_mode():
    """读取已保存的主题；QSettings 很轻，可以在闪屏之前用。

    默认 **深色（墨夜）**——与 ``theme_tokens.DEFAULT_THEME`` 保持一致，
    否则闪屏会用浅色画一遍、主窗口再切成深色，启动瞬间闪一下白。
    """
    value = QSettings('BatterySOH', 'AssessmentSystem').value(
        THEME_SETTINGS_KEY, DEFAULT_THEME)
    mode = str(value).strip().lower() if value else DEFAULT_THEME
    return mode if mode in THEMES else DEFAULT_THEME


def _get_icon():
    """加载 SOH.ico 作为应用图标（不导入 utils，避免提前触发 torch 导入）。"""
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    ico_path = os.path.join(base_path, 'SOH.ico')
    if os.path.exists(ico_path):
        return QIcon(ico_path)
    return QIcon()


class _StartupSplash(QWidget):
    """自定义启动闪屏：背景图 + 动态进度条 + 原生窗口控制按钮。

    U7 的改动：
    - 进度条文字移到条外（条内文字压在填充块上只有 2.01:1，读不清）；
    - 颜色全部来自 ``theme_tokens``，深色主题下不会再闪一块浅色窗口；
    - 字号用 pt（跟随系统字号设置）；
    - 去掉最大化按钮（固定尺寸下它是纯视觉噪声）；
    - 用户点关闭时设置取消标志，让主流程在下一个检查点干净退出，
      而不是在某次 ``processEvents()`` 里直接 ``sys.exit(0)``。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('startupSplash')
        self.setProperty('visualWorld', 'paperInk')

        # 标记：是否为程序代码主动关闭（区别于用户点击标题栏关闭按钮）
        self._programmatic_close = False
        # 用户请求取消启动
        self.cancelled = False

        self.T = THEMES[_saved_theme_mode()]

        # 窗口属性：置顶、保留标题栏以获得原生 最小化/关闭 按钮
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.CustomizeWindowHint |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.WindowMinimizeButtonHint |
            Qt.WindowType.WindowCloseButtonHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setFixedSize(620, 400)
        self.setWindowTitle('电池 SOH 评估系统')

        T = self.T
        self.setStyleSheet(f'''
            QLabel[role="splashTitle"] {{
                color: {T['primary_d']};
                background: transparent;
                font-family: "STZhongsong", "FangSong", "Microsoft YaHei UI";
                font-size: 19pt;
                font-weight: 700;
                letter-spacing: 1px;
            }}
            QLabel[role="splashSubtitle"] {{
                color: {T['text_muted']};
                background: transparent;
                font-family: "Microsoft YaHei UI";
                font-size: 9pt;
                letter-spacing: 1px;
            }}
            QFrame[role="splashBattery"] {{
                background: rgba(0, 0, 0, 0);
                border: 2px solid {T['primary']};
                border-radius: 7px;
            }}
            QFrame[role="splashBatteryTerminal"] {{
                background: {T['primary']};
                border: none;
                border-radius: 2px;
            }}
            QFrame[role="splashBatteryLine"] {{
                background: {T['primary']};
                border: none;
            }}
        ''')

        self._identity_widget = QWidget(self)
        self._identity_widget.setObjectName('splashIdentity')
        self._identity_widget.setGeometry(70, 78, 480, 108)
        identity_layout = QHBoxLayout(self._identity_widget)
        identity_layout.setContentsMargins(0, 0, 0, 0)
        identity_layout.setSpacing(16)
        identity_layout.addStretch(1)

        battery_mark = QWidget()
        battery_mark.setFixedSize(58, 72)
        battery = QFrame(battery_mark)
        battery.setProperty('role', 'splashBattery')
        battery.setGeometry(4, 8, 46, 58)
        terminal = QFrame(battery_mark)
        terminal.setProperty('role', 'splashBatteryTerminal')
        terminal.setGeometry(17, 2, 20, 7)
        for width, y in ((22, 22), (27, 33), (19, 44)):
            line = QFrame(battery)
            line.setProperty('role', 'splashBatteryLine')
            line.setGeometry(11, y, width, 2)
        identity_layout.addWidget(battery_mark)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(1)
        self._title_label = QLabel('电池 SOH 评估系统')
        self._title_label.setProperty('role', 'splashTitle')
        self._title_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._subtitle_label = QLabel(
            'Battery State of Health Assessment Workspace')
        self._subtitle_label.setProperty('role', 'splashSubtitle')
        text_layout.addWidget(self._title_label)
        text_layout.addWidget(self._subtitle_label)
        identity_layout.addLayout(text_layout)
        identity_layout.addStretch(1)

        # ── 加载状态与百分比进度 ──
        # 状态文字区域缩窄，把右侧留给条外的百分比（避免重叠与截断）
        self._status_label = QLabel('正在准备启动…', self)
        self._status_label.setGeometry(48, 302, 452, 24)
        self._status_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._status_label.setAccessibleName('当前加载阶段')
        self._status_label.setWordWrap(False)
        self._status_label.setStyleSheet(f'''
            QLabel {{
                color: {T['text_muted']};
                font-family: "Microsoft YaHei UI";
                font-size: 9pt;
                font-weight: 500;
                background: transparent;
            }}
        ''')

        self._percent_label = QLabel('0%', self)
        self._percent_label.setGeometry(508, 302, 64, 24)
        self._percent_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._percent_label.setAccessibleName('应用启动百分比')
        self._percent_label.setStyleSheet(f'''
            QLabel {{
                color: {T['text']};
                font-family: "Microsoft YaHei UI";
                font-size: 9pt;
                font-weight: 700;
                background: transparent;
            }}
        ''')

        self._progress = QProgressBar(self)
        self._progress.setGeometry(48, 337, 524, 22)
        # U7②：关掉条内文字，百分比放到状态行右侧（对比度从 2.01:1 提升到达标）
        self._progress.setTextVisible(False)
        self._progress.setAccessibleName('应用启动进度')
        self._progress.setMinimum(0)
        self._progress.setMaximum(100)
        self._progress.setValue(0)
        self._progress.setStyleSheet(f'''
            QProgressBar {{
                border: 1px solid {T['border']};
                border-radius: 6px;
                background-color: {T['bg_surface']};
            }}
            QProgressBar::chunk {{
                border-radius: 5px;
                background: {T['primary']};
            }}
        ''')

        # 居中显示
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = (geo.width() - self.width()) // 2 + geo.x()
            y = (geo.height() - self.height()) // 2 + geo.y()
            self.move(x, y)

    def paintEvent(self, event):
        T = self.T
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        paper = QLinearGradient(0, 0, self.width(), self.height())
        paper.setColorAt(0.0, QColor(T['bg_surface']))
        paper.setColorAt(0.58, QColor(T['bg_base']))
        paper.setColorAt(1.0, QColor(T['bg_deep']))
        painter.fillRect(self.rect(), paper)

        glow = QColor(T['primary'])
        glow.setAlpha(14)
        painter.setPen(QPen(glow, 1))
        for offset in range(-120, 660, 28):
            painter.drawLine(offset, 0, offset + 180, self.height())

        edge = QColor(T['border'])
        edge.setAlpha(100)
        painter.setPen(QPen(edge, 1))
        painter.drawLine(48, 220, 572, 220)

        edge = QColor(T['border'])
        edge.setAlpha(120)
        painter.setPen(QPen(edge, 1))
        painter.drawRoundedRect(QRectF(18, 18, 584, 364), 10, 10)
        painter.end()

    def set_progress(self, value, status):
        """更新真实启动阶段、百分比和窗口标题。"""
        progress = max(0, min(100, int(value)))
        self._progress.setValue(progress)
        self._percent_label.setText(f'{progress}%')
        self._status_label.setText(str(status))
        self._status_label.setToolTip(str(status))
        self.setWindowTitle(f'电池 SOH 评估系统 · {progress}%')
        QApplication.processEvents()

    def closeEvent(self, event):
        """
        区分两种关闭场景：
        - 用户点击标题栏关闭按钮 → 只设置取消标志，让主流程干净退出
        - 主程序加载完成后主动关闭闪屏 → 仅关闭窗口，不退出进程
        """
        if self._programmatic_close:
            super().closeEvent(event)
            return
        # 不在 processEvents() 中途 sys.exit(0)（那会绕过清理逻辑）
        self.cancelled = True
        event.ignore()


#: 需要预导入的重库及其进度区间。逐个导入可以让每一段等待都有说明，
#: 而不是从 15% 直接跳到 75% 且进度条冻结（U7①）。
HEAVY_IMPORTS = (
    ('PyTorch', 'torch', 15, 45),
    ('Matplotlib', 'matplotlib.pyplot', 45, 55),
    ('Pandas', 'pandas', 55, 62),
    ('XGBoost', 'xgboost', 62, 68),
    ('PyQt 界面组件', 'PyQt6.QtWidgets', 68, 72),
)


def _preload_heavy_modules(splash):
    """预导入重库，返回是否被用户取消。"""
    import importlib

    for label, module, start, _end in HEAVY_IMPORTS:
        if splash.cancelled:
            return True
        splash.set_progress(start, f'正在加载 {label}…')
        try:
            importlib.import_module(module)
        except ImportError as error:
            # 可选依赖缺失不应阻止启动（例如没有 xgboost 也能用 RNN）
            splash.set_progress(start, f'{label} 不可用，已跳过（{error}）')
    return splash.cancelled


def fail_startup(splash, stage, error):
    """统一的启动失败出口：日志 + 简短对话框 + 退出码 1。"""
    traceback.print_exc()
    splash._programmatic_close = True
    splash.close()
    try:
        from utils.logger import setup_logger
        setup_logger().exception('启动失败：%s', stage)
    except Exception:
        traceback.print_exc()
    try:
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(None, '启动失败', concise_startup_error(error))
    except Exception:
        traceback.print_exc()
    sys.exit(1)


if __name__ == '__main__':
    # ── 阶段 1：立即创建 QApplication 并显示闪屏（目标 < 3 秒）──
    # 注意：不在此处导入 utils/torch 等重模块，确保闪屏秒开
    app = QApplication(sys.argv)
    app.setApplicationDisplayName('Battery SOH Assessment System')
    app.setWindowIcon(_get_icon())

    # 字体引导：必须早于任何控件创建。PyQt6 的 offscreen/minimal 平台插件
    # 不使用 Windows 字体引擎，QFontDatabase 可能为空 → 中文全变方框。
    # install_fonts 会显式注册系统中文字体（见 ui/fonts.py）。
    from ui.fonts import install_fonts
    install_fonts(app)

    # A1：安装全局异常钩子，把「闪退」变成「日志 + 一条非阻塞提示」。
    # crash_guard 只依赖 PyQt6.QtCore，很轻，可以在这里导入。
    from utils.crash_guard import bridge, install_excepthooks
    install_excepthooks()

    # 立即显示启动闪屏
    qt_splash = _StartupSplash()
    qt_splash.show()
    qt_splash.set_progress(5, '正在准备应用界面…')
    app.processEvents()

    # ── 阶段 2：加载核心模块（进度 15% → 72%，最耗时）──
    try:
        if _preload_heavy_modules(qt_splash):
            sys.exit(0)
        qt_splash.set_progress(72, '正在加载界面模块…')
        from ui.main_window import MainWindow
    except Exception as startup_error:
        fail_startup(qt_splash, '加载核心模块', startup_error)

    qt_splash.set_progress(75, '核心组件加载完成')
    app.processEvents()

    # ── 阶段 3：初始化主窗口（进度 82% → 98%）──
    # U7⑤：这一段此前在 try 保护之外，构造主窗口时出任何异常都会
    # 「闪屏一闪就没了」；现在纳入同一个保护。
    try:
        qt_splash.set_progress(82, '正在初始化主窗口…')
        app.processEvents()
        window = MainWindow()
        # A1：任何线程里未捕获的异常 → 非阻塞提示
        bridge.error.connect(window.show_error_toast)
        qt_splash.set_progress(92, '正在恢复配置与界面状态…')
        app.processEvents()
        window.show()
    except Exception as startup_error:
        fail_startup(qt_splash, '初始化主窗口', startup_error)

    qt_splash.set_progress(98, '正在呈现主界面…')
    app.processEvents()

    # ── 关闭闪屏（进度 100%）──
    # 标记为程序主动关闭，避免 closeEvent 中 sys.exit(0) 导致整个应用退出
    qt_splash.set_progress(100, '启动完成')
    qt_splash._programmatic_close = True
    qt_splash.close()
    qt_splash.deleteLater()

    sys.exit(app.exec())
