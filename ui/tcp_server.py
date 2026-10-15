"""实验性 TCP 实时预测服务。

改进方案 A1 / A10 的落地：

- **A1**：旧实现里 ``initial_capacity`` 从未定义，只要预测序列越过 SOH=80%
  就会抛 ``NameError``；而它在 ``QThread.run()`` 里执行，未捕获异常会让整个进程
  闪退。现在 SOH 一律按 ``C / C_rated`` 计算，并且 ``run()`` 有异常兜底。
- **A10**：默认只绑定 ``127.0.0.1``；可选局域网模式 + token 握手；消息解析
  （``core.stream_protocol.parse_message``，19 种畸形输入全部返回 error、不抛异常）；
  缓冲有上限（``deque(maxlen=5000)``）；每条消息不再同步跑上千步递归（限流 +
  独立预测线程）；RUL 语义修正为「距最新已观测循环还有几个未来循环越过阈值」。
"""

import secrets
import socket
import threading

from PyQt6.QtCore import QThread, pyqtSignal

from core.prediction import predict_capacity_batch
from core.stream_protocol import (
    MAX_LINE,
    LatestOnlyQueue,
    PredictionJob,
    parse_message,
)
from utils.crash_guard import guarded_run


DEFAULT_HOST = '127.0.0.1'
LAN_HOST = '0.0.0.0'
DEFAULT_PORT = 8888


class TCPServerWorker(QThread):
    status_signal = pyqtSignal(str)
    data_received_signal = pyqtSignal(float, float)
    soh_update_signal = pyqtSignal(dict)
    rul_update_signal = pyqtSignal(dict)
    prediction_signal = pyqtSignal(list, list)
    error_signal = pyqtSignal(str)

    def __init__(self, model, metadata, config, port=DEFAULT_PORT,
                 host=DEFAULT_HOST, allow_lan=False, auth_token=None,
                 min_interval=1.0, parent=None):
        super().__init__(parent)
        self._model = model
        self._metadata = metadata
        self.config = config
        self.port = int(port)
        self.allow_lan = bool(allow_lan)
        # 只有显式开启局域网模式才监听 0.0.0.0
        self.host = LAN_HOST if self.allow_lan else DEFAULT_HOST
        self._auth_token = auth_token if auth_token else (
            secrets.token_hex(8) if self.allow_lan else None)
        self.min_interval = float(min_interval)
        self._stop_requested = False
        # 用普通 Lock + try/finally 取代手动 QMutex.lock()/unlock()：
        # 两者之间一旦抛异常，旧代码会永久死锁
        self._lock = threading.Lock()

        # 解析 / 缓冲 / 限流 / 预测都在纯 Python 的 PredictionJob 里，
        # 因此这些逻辑可以在没有 Qt 的环境下完整单测（A10）。
        metadata = metadata or {}
        self._rated_capacity = float(
            metadata.get('rated_capacity', config.rated_capacity))
        self._window_size = int(
            metadata.get('window_size', config.window_size))
        self._device = getattr(config, 'device', 'cpu')
        self._threshold = self._rated_capacity * float(config.threshold_ratio)
        self._job = PredictionJob(
            window=self._window_size,
            step_fn=self._predict_windows,
            threshold=self._threshold,
            rated_capacity=self._rated_capacity,
            min_interval=self.min_interval,
        )
        # 预测线程 + 「最新优先」队列（A10：预测不阻塞接收）
        self._pending = LatestOnlyQueue()
        self._predict_thread = None

    def _predict_windows(self, windows):
        """递归预测的 step_fn：走共用的 predict_capacity_batch。"""
        return predict_capacity_batch(
            self._model, self._metadata, windows, device=self._device)

    # ── 生命周期 ──────────────────────────────────────────────
    def request_stop(self):
        self._stop_requested = True

    def stop_requested(self):
        return self._stop_requested

    @property
    def buffer(self):
        with self._lock:
            return self._job.history()

    @property
    def auth_token(self):
        """局域网模式下需要客户端在首条消息里提供的 token。"""
        return self._auth_token

    # ── 主循环 ────────────────────────────────────────────────
    @guarded_run(log_context='TCP 服务线程异常')
    def run(self):
        window_size = self._window_size
        rated_capacity = self._rated_capacity

        server_socket = None
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((self.host, self.port))
            server_socket.listen(1)
            server_socket.settimeout(1.0)
            self._start_prediction_thread()
            if self.allow_lan:
                self.status_signal.emit(
                    f'TCP 服务已启动（局域网模式），监听 {self.host}:{self.port}；'
                    f'客户端首条消息需带 token：{self._auth_token}')
            else:
                self.status_signal.emit(
                    f'TCP 服务已启动，仅监听本机 {self.host}:{self.port}，'
                    '等待客户端连接...')

            while not self._stop_requested:
                try:
                    conn, addr = server_socket.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break

                self.status_signal.emit(f'客户端已连接：{addr[0]}:{addr[1]}')
                conn.settimeout(1.0)
                try:
                    self._serve_connection(conn, rated_capacity, window_size)
                except OSError as exc:
                    self.status_signal.emit(f'连接中断：{exc}')
                finally:
                    try:
                        conn.close()
                    except OSError:
                        pass
                    self.status_signal.emit('客户端已断开')

        except OSError as exc:
            self.error_signal.emit(f'TCP 服务启动失败：{exc}')
        finally:
            if server_socket:
                try:
                    server_socket.close()
                except OSError:
                    pass
            self._join_prediction_thread()
            self.status_signal.emit('TCP 服务已停止')

    def _start_prediction_thread(self):
        """启动独立预测线程（A10：预测不阻塞接收）。"""
        self._predict_thread = threading.Thread(
            target=self._prediction_loop,
            name='tcp-prediction',
            daemon=True,
        )
        self._predict_thread.start()

    def _join_prediction_thread(self, timeout=10.0):
        thread = self._predict_thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=timeout)
        self._predict_thread = None

    def _serve_connection(self, conn, rated_capacity, window_size):
        """逐行处理一个客户端的消息；畸形输入只产生警告，不抛异常。"""
        remaining = b''
        authenticated = self._auth_token is None

        while not self._stop_requested:
            try:
                data = conn.recv(4096)
            except socket.timeout:
                continue
            if not data:
                return
            remaining += data
            # 防止无换行的长报文把内存吃满
            if len(remaining) > 16 * MAX_LINE:
                self.status_signal.emit('警告：未换行数据过长，已丢弃缓冲')
                remaining = b''
                continue

            while b'\n' in remaining:
                line, remaining = remaining.split(b'\n', 1)
                line = line.strip()
                if not line:
                    continue

                if not authenticated:
                    authenticated = self._check_token(line)
                    continue

                kind, value = parse_message(line, rated_capacity)
                if kind == 'error':
                    self.status_signal.emit(f'警告：{value}')
                    continue
                if kind == 'reset':
                    self._job.reset()
                    self.status_signal.emit('缓冲区已重置')
                    continue

                should_predict, history = self._job.feed(value)
                self.data_received_signal.emit(
                    value, value / rated_capacity * 100.0
                    if rated_capacity > 0 else 0.0)
                if should_predict:
                    # A10：只把快照塞进「最新优先」队列，预测在独立线程里跑，
                    # 接收线程立刻回去读下一条消息，不会被上千步递归堵住。
                    self._pending.put_latest(history)

    def _prediction_loop(self):
        """独立预测线程：阻塞式消费最新快照，发完信号再取下一个。"""
        while not self._stop_requested:
            history = self._pending.get(timeout=0.2)
            if history is None:
                continue
            if self._stop_requested:
                break
            self._predict_and_emit(history)

    def _check_token(self, line):
        """局域网模式的 token 握手：首条消息必须是 ``{"token": "..."}``。"""
        import json

        try:
            message = json.loads(line.decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            self.status_signal.emit('警告：认证失败，连接已关闭')
            raise OSError('认证失败')
        token = message.get('token') if isinstance(message, dict) else None
        if not isinstance(token, str) or not secrets.compare_digest(
                token, self._auth_token):
            self.status_signal.emit('警告：token 不匹配，连接已关闭')
            raise OSError('认证失败')
        self.status_signal.emit('客户端认证通过')
        return True

    def _predict_and_emit(self, history):
        """做一次真正的 RUL 预测；出错时记录并上报，而不是静默 break。

        本方法在**预测线程**里执行（见 :meth:`_prediction_loop`），因此可以
        安全地耗上数秒而不影响接收。
        """
        try:
            result = self._job.predict(history)
        except Exception as exc:                      # noqa: BLE001
            self.status_signal.emit(f'警告：预测失败（{type(exc).__name__}: {exc}）')
            return
        forecast = result['forecast']
        self.prediction_signal.emit(result['history'], forecast)
        self.soh_update_signal.emit(result['soh_stages'])
        self.rul_update_signal.emit({
            'rul': result['rul'],
            'threshold': self._job.threshold,
            'rated_capacity': self._job.rated_capacity,
            'unit': 'cycles',
            'definition': '距最新已观测循环还有几个未来循环越过失效阈值',
        })


class TcpPredictionServer(TCPServerWorker):
    """向后兼容别名（旧代码可能按这个名字导入）。"""
