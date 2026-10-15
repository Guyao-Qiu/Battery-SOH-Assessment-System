"""A1 / A10 的端到端验证：真实 socket、真实线程、真实预测。

这是改进方案 §8「TCP：畸形输入不崩溃；默认只监听本机；预测不阻塞接收」
的自动化版本。它不依赖显示器（``QT_QPA_PLATFORM=offscreen`` 即可）。
"""

import json
import os
import socket
import time
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import numpy as np


def _free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(('127.0.0.1', 0))
        return probe.getsockname()[1]


class _FakeModel:
    """线性下降的确定性模型：每步 -0.01 Ah。"""

    def predict(self, windows):
        windows = np.asarray(windows, dtype=np.float64)
        if windows.ndim == 3:
            windows = windows[:, :, 0]
        return (windows[:, -1] - 0.01).astype(np.float32)


def _metadata(window=8, rated=2.0):
    from core.preprocess import CapacityScaler

    scaler = CapacityScaler('rated', rated).fit([rated])
    return {
        'mode': 'RF',
        'window_size': window,
        'rated_capacity': rated,
        'scaler': scaler.to_dict(),
        'persistence_blend': 1.0,
    }


class TcpServerEndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication

        cls.app = QApplication.instance() or QApplication([])

    def _config(self, threshold_ratio=0.7):
        from types import SimpleNamespace

        return SimpleNamespace(
            rated_capacity=2.0,
            threshold_ratio=threshold_ratio,
            device='cpu',
            window_size=8,
        )

    def _start(self, model=None, **kwargs):
        from ui.tcp_server import TCPServerWorker

        port = _free_port()
        worker = TCPServerWorker(
            model if model is not None else _FakeModel(),
            _metadata(), self._config(), port=port,
            min_interval=0.0, **kwargs)
        events = {'status': [], 'error': [], 'rul': [], 'soh': []}
        worker.status_signal.connect(events['status'].append)
        worker.error_signal.connect(events['error'].append)
        worker.rul_update_signal.connect(events['rul'].append)
        worker.soh_update_signal.connect(events['soh'].append)
        worker.start()
        # 等待监听就绪
        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline:
            try:
                with socket.create_connection(('127.0.0.1', port), timeout=0.3):
                    break
            except OSError:
                self.app.processEvents()
                time.sleep(0.05)
        else:
            worker.request_stop()
            worker.wait(3000)
            self.fail('TCP 服务未能在 10 秒内开始监听')
        return worker, port, events

    def _stop(self, worker):
        worker.request_stop()
        worker.wait(5000)
        self.app.processEvents()

    def _send(self, port, payloads, settle=0.6):
        with socket.create_connection(('127.0.0.1', port), timeout=5.0) as sock:
            for payload in payloads:
                if isinstance(payload, str):
                    payload = payload.encode('utf-8')
                sock.sendall(payload + b'\n')
            time.sleep(settle)
        # 给接收线程时间处理完
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(0.05)

    def test_default_binding_is_localhost_only(self):
        from ui.tcp_server import DEFAULT_HOST, TCPServerWorker

        worker = TCPServerWorker(
            _FakeModel(), _metadata(), self._config(), port=0)
        try:
            self.assertEqual(worker.host, DEFAULT_HOST)
            self.assertEqual(worker.host, '127.0.0.1')
            self.assertFalse(worker.allow_lan)
            # 非局域网模式不应要求 token
            self.assertIsNone(worker.auth_token)
        finally:
            worker.request_stop()
            worker.wait(3000)

    def test_lan_mode_generates_a_token(self):
        from ui.tcp_server import TCPServerWorker

        worker = TCPServerWorker(
            _FakeModel(), _metadata(), self._config(), port=0, allow_lan=True)
        try:
            self.assertEqual(worker.host, '0.0.0.0')
            self.assertTrue(worker.auth_token)
        finally:
            worker.request_stop()
            worker.wait(3000)

    def test_crossing_the_threshold_produces_rul_without_crashing(self):
        """A1 的核心回归：旧实现在这里抛 NameError 并让整个进程闪退。"""
        worker, port, events = self._start()
        try:
            # 2.0 Ah 起，每循环 -0.012 Ah；阈值 = 2.0 * 0.7 = 1.4 Ah。
            # 只发到最新观测值仍**高于**阈值（1.412 Ah），此时模型（每步 -0.01）
            # 还需两步越阈，因此 RUL 应为正数。
            payloads = [
                json.dumps({'capacity': 2.0 - 0.012 * index})
                for index in range(50)
            ]
            self._send(port, payloads)
            self.assertEqual(events['error'], [])
            self.assertTrue(events['rul'], '越过 SOH=80% 后应给出 RUL')
            rul = events['rul'][-1]
            # 真正的 RUL 语义：距最新已观测循环还有几个未来循环越过阈值
            self.assertIn('definition', rul)
            self.assertEqual(rul['unit'], 'cycles')
            self.assertIsNotNone(rul['rul'])
            self.assertGreater(rul['rul'], 0)
            self.assertTrue(worker.isRunning(), '服务不应因预测而退出')
        finally:
            self._stop(worker)

    def test_rul_is_zero_once_the_model_is_already_below_threshold(self):
        """容量已低于阈值时，RUL 必须是 0（而不是旧实现的「还有几循环」）。"""
        worker, port, events = self._start()
        try:
            # 直接发到 1.2 Ah（< 1.4 Ah 阈值）
            payloads = [
                json.dumps({'capacity': 2.0 - 0.02 * index})
                for index in range(45)
            ]
            self._send(port, payloads)
            self.assertEqual(events['error'], [])
            self.assertTrue(events['rul'])
            self.assertEqual(events['rul'][-1]['rul'], 0)
        finally:
            self._stop(worker)

    def test_malformed_messages_do_not_crash_or_kill_the_server(self):
        worker, port, events = self._start()
        try:
            self._send(port, [
                b'not json',
                b'{"capacity": "abc"}',
                b'{"capacity": NaN}',
                b'{"capacity": -1}',
                b'[1, 2, 3]',
                b'',
                b'{"capacity": 1e999}',
                b'\xff\xfe',
                b'{"reset": true}',
                b'{"capacity": 1.9}',
            ])
            self.assertEqual(events['error'], [], '畸形输入不应触发错误信号')
            self.assertTrue(worker.isRunning(), '服务不应因畸形输入退出')
            # 至少应有一条警告
            warnings = [s for s in events['status'] if s.startswith('警告')]
            self.assertTrue(warnings, '畸形输入应产生可见警告')
            self.assertTrue(any('重置' in s for s in events['status']))
        finally:
            self._stop(worker)

    def test_buffer_has_a_hard_upper_bound(self):
        from core.stream_protocol import MAX_BUFFER

        worker, port, events = self._start()
        try:
            # 发送超过上限的样本；deque(maxlen=...) 应丢弃最旧的点
            payloads = [
                json.dumps({'capacity': 1.9}) for _ in range(MAX_BUFFER + 50)
            ]
            self._send(port, payloads, settle=1.0)
            self.assertEqual(events['error'], [])
            self.assertLessEqual(len(worker.buffer), MAX_BUFFER)
        finally:
            self._stop(worker)

    def test_reset_clears_the_buffer(self):
        worker, port, events = self._start()
        try:
            self._send(port, [b'{"capacity": 1.95}'])
            self.assertTrue(worker.buffer)
            self._send(port, [b'{"reset": true}'])
            self.assertEqual(worker.buffer, [])
        finally:
            self._stop(worker)

    def test_prediction_does_not_block_receiving(self):
        """A10：一次最坏情况（走满 max_steps）的预测不得阻塞后续消息的处理。

        旧实现把上千步递归放在接收线程里同步执行，客户端在预测期间发出的
        ``reset`` / 新样本要等整段预测结束才被读到。现在预测在独立线程里跑，
        接收线程只把快照塞进「最新优先」队列。
        """
        from core.stream_protocol import MAX_FORECAST_STEPS

        block_per_step = 0.0026

        class SlowFlatModel:
            """永不越阈（走满最大步数）+ 每步固定耗时，放大阻塞效应。"""

            def predict(self, windows):
                time.sleep(block_per_step)
                windows = np.asarray(windows, dtype=np.float64)
                if windows.ndim == 3:
                    windows = windows[:, :, 0]
                return np.full(len(windows), 1.8, dtype=np.float32)

        worst_case = MAX_FORECAST_STEPS * block_per_step
        worker, port, events = self._start(model=SlowFlatModel())
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=30) as sock:
                for index in range(8):
                    sock.sendall(json.dumps(
                        {'capacity': 1.95 - 0.001 * index}).encode() + b'\n')
                time.sleep(0.5)

                sock.sendall(json.dumps({'capacity': 1.90}).encode() + b'\n')
                time.sleep(0.02)
                started = time.perf_counter()
                sock.sendall(b'{"reset": true}\n')

                deadline = time.monotonic() + worst_case * 3
                while time.monotonic() < deadline:
                    # 跨线程信号是队列投递的，必须转一下事件循环才能观察
                    self.app.processEvents()
                    if any('重置' in text for text in events['status']):
                        break
                    time.sleep(0.005)

            self.app.processEvents()
            handled = [text for text in events['status'] if '重置' in text]
            self.assertTrue(handled, '预测进行中时 reset 仍应被处理')
            delay = time.perf_counter() - started
            self.assertLess(
                delay, worst_case / 2,
                f'接收被预测阻塞了 {delay:.2f}s（一次预测约 {worst_case:.2f}s）')
        finally:
            self._stop(worker)


class SendDemoScriptTests(unittest.TestCase):
    def test_send_demo_fails_cleanly_without_a_server(self):
        import subprocess
        import sys

        port = _free_port()
        result = subprocess.run(
            [sys.executable, '-X', 'utf8', 'tools/send_demo.py',
             '127.0.0.1', str(port)],
            capture_output=True, text=True, timeout=60,
        )
        self.assertNotEqual(result.returncode, 0)
        combined = result.stdout + result.stderr
        self.assertIn('连接被拒绝', combined)


if __name__ == '__main__':
    unittest.main()
