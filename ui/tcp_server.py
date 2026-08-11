import json
import socket
import numpy as np

from PyQt6.QtCore import QThread, pyqtSignal, QMutex
from core.prediction import predict_capacity_batch


class TCPServerWorker(QThread):
    status_signal = pyqtSignal(str)
    data_received_signal = pyqtSignal(float, float)
    soh_update_signal = pyqtSignal(dict)
    rul_update_signal = pyqtSignal(dict)
    prediction_signal = pyqtSignal(list, list)
    error_signal = pyqtSignal(str)

    def __init__(self, model, metadata, config, port=8888, parent=None):
        super().__init__(parent)
        self._model = model
        self._metadata = metadata
        self.config = config
        self.port = port
        self._stop_requested = False
        self._buffer = []
        self._mutex = QMutex()

    def request_stop(self):
        self._stop_requested = True

    def stop_requested(self):
        return self._stop_requested

    @property
    def buffer(self):
        return list(self._buffer)

    def run(self):
        mode = self._metadata['mode']
        window_size = self._metadata['window_size']
        rated_capacity = self._metadata.get('rated_capacity', self.config.rated_capacity)
        device = self.config.device

        server_socket = None
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind(('0.0.0.0', self.port))
            server_socket.listen(1)
            server_socket.settimeout(1.0)
            self.status_signal.emit(f'TCP 服务已启动，监听端口 {self.port}，等待客户端连接...')

            while not self._stop_requested:
                try:
                    conn, addr = server_socket.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break

                self.status_signal.emit(f'客户端已连接：{addr[0]}:{addr[1]}')
                conn.settimeout(1.0)
                remaining = b''

                while not self._stop_requested:
                    try:
                        data = conn.recv(4096)
                    except socket.timeout:
                        continue
                    except OSError:
                        break

                    if not data:
                        self.status_signal.emit('客户端已断开')
                        break

                    remaining += data
                    while b'\n' in remaining:
                        line, remaining = remaining.split(b'\n', 1)
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            msg = json.loads(line.decode('utf-8'))
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            self.status_signal.emit(f'警告：无法解析消息：{line[:100]}')
                            continue

                        if msg.get('reset'):
                            self._mutex.lock()
                            self._buffer.clear()
                            self._mutex.unlock()
                            self.status_signal.emit('缓冲区已重置')
                            continue

                        capacity = msg.get('capacity')
                        if capacity is None:
                            continue

                        self._mutex.lock()
                        self._buffer.append(float(capacity))
                        buf_copy = list(self._buffer)
                        self._mutex.unlock()

                        if len(buf_copy) >= 1:
                            soh = (capacity / rated_capacity * 100) if rated_capacity > 0 else 0
                            self.data_received_signal.emit(capacity, soh)

                        if len(buf_copy) >= window_size:
                            self._run_prediction(buf_copy, mode, window_size,
                                                 rated_capacity, device)

                try:
                    conn.close()
                except OSError:
                    pass

        except OSError as e:
            self.error_signal.emit(f'TCP 服务启动失败：{e}')
        finally:
            if server_socket:
                try:
                    server_socket.close()
                except OSError:
                    pass
            self.status_signal.emit('TCP 服务已停止')

    def _run_prediction(self, buffer, mode, window_size, rated_capacity, device):
        threshold = rated_capacity * self.config.threshold_ratio
        max_steps = 2000

        window = list(buffer[-window_size:])
        predictions = []

        for _ in range(max_steps):
            if self._stop_requested:
                break
            try:
                x = np.asarray(window, dtype=np.float32).reshape(1, -1)
                pred = float(predict_capacity_batch(
                    self._model, self._metadata, x, device=device)[0])
                predictions.append(pred)
                window = window[1:] + [pred]
                if pred < threshold:
                    break
            except Exception:
                break

        full_sequence = buffer + predictions
        self.prediction_signal.emit(buffer, predictions)

        soh_info = {}
        for pct in [100, 95, 90, 85, 80]:
            target_cap = rated_capacity * pct / 100.0
            cycle, cap = self._find_stage(full_sequence, buffer, predictions, target_cap, pct > 99)
            soh_info[pct] = {'cycle': cycle, 'capacity': cap}
        self.soh_update_signal.emit(soh_info)

        if soh_info.get(80, {}).get('cycle') is not None:
            cycle_80 = soh_info[80]['cycle']
            rul_info = {}
            for pct in [85, 84, 83, 82, 81]:
                target_cap = initial_capacity * pct / 100.0
                cycle_stage, _ = self._find_stage(full_sequence, buffer, predictions, target_cap, False)
                if cycle_stage is not None:
                    rul_info[pct] = max(0, cycle_80 - cycle_stage)
                else:
                    rul_info[pct] = None
            self.rul_update_signal.emit(rul_info)

    def _find_stage(self, full_sequence, buffer, predictions, target_cap, allow_equal):
        """在完整序列中找到容量首次 <= target_cap 的循环索引"""
        for i, cap in enumerate(full_sequence):
            if allow_equal:
                if cap <= target_cap:
                    return i, float(cap)
            else:
                if cap < target_cap:
                    return i, float(cap)
        return None, None
