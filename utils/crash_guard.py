"""全局异常兜底：把「闪退」变成「日志 + 一条非阻塞提示」。

背景：按 PyQt 的文档行为，回调（包括 ``QThread.run``）里未处理的 Python
异常在默认钩子下会触发 ``qFatal()`` 终止进程。项目此前没有安装
``sys.excepthook``，所以一个小笔误的后果不是「面板报错」，而是**整个程序闪退**。

用法（在创建 ``QApplication`` 之后、创建主窗口之前）::

    from utils.crash_guard import install_excepthooks, bridge
    install_excepthooks()
    bridge.error.connect(window.show_error_toast)
"""

import contextlib
import logging
import sys
import threading
import traceback

from PyQt6.QtCore import QObject, pyqtSignal


def _logger():
    # 延迟取 logger：crash_guard 会被启动引导在重库加载前导入，
    # 因此这里不在模块级 import utils.logger（它会拉起 utils 包链）。
    try:
        from utils.logger import setup_logger
        return setup_logger()
    except Exception:                     # noqa: BLE001 —— 兜底代码自身不能再抛
        return logging.getLogger('battery_soh')


class CrashBridge(QObject):
    """任何线程里的异常 → 信号 → 主线程弹窗。

    不要在子线程里直接创建 QMessageBox，所以统一走信号。
    """

    error = pyqtSignal(str)


#: 进程级单例；启动引导连接它的 ``error`` 信号即可
bridge = CrashBridge()


def report_exception(exc_type, exc, tb, context='未处理的异常'):
    """记录完整 traceback 并发出提示信号。"""
    if issubclass(exc_type, KeyboardInterrupt):
        return
    try:
        _logger().error(
            '%s\n%s', context,
            ''.join(traceback.format_exception(exc_type, exc, tb)))
    except Exception:                     # noqa: BLE001
        traceback.print_exception(exc_type, exc, tb)
    # 信号未连接 / 已被销毁时也必须静默：这里是崩溃兜底路径，不能再抛异常
    with contextlib.suppress(RuntimeError, TypeError):
        bridge.error.emit(f'{exc_type.__name__}: {exc}')


def install_excepthooks():
    """安装主线程与子线程的全局异常钩子。"""
    def hook(exc_type, exc, tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc, tb)
            return
        report_exception(exc_type, exc, tb)

    sys.excepthook = hook
    threading.excepthook = lambda args: hook(
        args.exc_type, args.exc_value, args.exc_traceback)
    return hook


def guarded_run(error_signal=None, log_context='线程异常'):
    """装饰器：让 ``QThread.run`` 优雅失败，而不是把异常抛给 Qt。

    用法::

        class Worker(QThread):
            error_signal = pyqtSignal(str)

            @guarded_run()
            def run(self):
                ...
    """
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as exc:      # noqa: BLE001 —— 线程边界必须兜底
                report_exception(type(exc), exc, exc.__traceback__, log_context)
                signal = error_signal
                if signal is None:
                    signal = getattr(self, 'error_signal', None)
                if signal is not None:
                    with contextlib.suppress(RuntimeError, TypeError):
                        signal.emit(f'{type(exc).__name__}: {exc}')
                return None
        wrapper.__name__ = getattr(func, '__name__', 'run')
        wrapper.__doc__ = func.__doc__
        return wrapper
    return decorator
