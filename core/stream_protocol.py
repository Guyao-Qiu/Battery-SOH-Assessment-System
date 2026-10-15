"""TCP 实时预测的纯 Python 部分（不依赖 Qt，可直接单元测试）。

``ui/tcp_server.py`` 只负责收发字节和发信号；解析、预测、限流都在这里，
因此这些逻辑可以在没有 PyQt6 的环境里被完整测试。
"""

import json
import math
import time
from collections import deque

import numpy as np


#: 单条消息上限（字节）
MAX_LINE = 4096
#: 缓冲区上限（循环数）；deque(maxlen=...) 满了自动丢弃最旧的点
MAX_BUFFER = 5000
#: 单次递归预测的最大步数（防止「永远越不过阈值」时跑满）
MAX_FORECAST_STEPS = 1500


def _reject_constant(name):
    # 拒绝 NaN / Infinity / -Infinity：它们不是合法 JSON，且会污染预测
    raise ValueError(f'非法 JSON 常量: {name}')


def parse_message(raw, rated_capacity):
    """解析一行 TCP 消息，**永不抛异常**。

    返回 ``('reset', None)`` / ``('sample', 容量Ah)`` / ``('error', 原因)``。
    """
    if not isinstance(raw, (bytes, bytearray)):
        return 'error', '消息必须是字节串'
    if len(raw) > MAX_LINE:
        return 'error', '消息过长'
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError:
        return 'error', '消息不是合法 UTF-8'
    try:
        msg = json.loads(text, parse_constant=_reject_constant)
    except (ValueError, RecursionError) as exc:
        return 'error', f'不是合法 JSON: {type(exc).__name__}'
    if not isinstance(msg, dict):
        return 'error', '消息必须是 JSON 对象'
    if msg.get('reset') is True:
        return 'reset', None
    if 'capacity' not in msg:
        return 'error', '缺少 capacity 字段'
    capacity = msg['capacity']
    # bool 是 int 的子类，必须显式排除，否则 True 会被当成 1.0 Ah
    if isinstance(capacity, bool) or not isinstance(capacity, (int, float)):
        return 'error', 'capacity 必须是数值'
    try:
        capacity = float(capacity)
    except (OverflowError, ValueError):
        return 'error', 'capacity 数值过大'
    if not math.isfinite(capacity):
        return 'error', 'capacity 必须是有限数值'
    try:
        rated = float(rated_capacity)
    except (TypeError, ValueError):
        return 'error', '额定容量无效'
    if not math.isfinite(rated) or rated <= 0:
        return 'error', '额定容量无效'
    if not 0.0 < capacity <= 2.0 * rated:
        return 'error', f'capacity 超出合理范围 (0, {2 * rated:g}] Ah'
    return 'sample', capacity


def forecast_eol(history, window, step_fn, threshold, max_steps=MAX_FORECAST_STEPS):
    """递归预测直到容量首次低于阈值。

    返回 ``(rul, forecast)``：

    - ``rul``      = 「从最新一个**已观测**循环算起，还要再过几个循环越过阈值」
                     （真正的 RUL）；当前已低于阈值返回 0；``max_steps`` 内
                     不会越过返回 ``None``；
    - ``forecast`` = 预测的容量序列（用于画图）。

    旧实现的「RUL」是 ``cycle_80 − cycle_stage``，即「SOH 从 pct% 掉到 80%
    需要多少个循环」，不是从现在起的剩余寿命。
    """
    hist = [float(value) for value in np.asarray(
        history, dtype=np.float64).reshape(-1)]
    if len(hist) < window:
        raise ValueError('历史长度小于窗口')
    if hist[-1] < threshold:
        return 0, []
    win, out = hist[-window:], []
    for step in range(1, max_steps + 1):
        next_values = np.asarray(
            step_fn(np.asarray(win, dtype=np.float32).reshape(1, -1)),
            dtype=np.float64).reshape(-1)
        if len(next_values) != 1 or not np.isfinite(next_values[0]):
            raise ValueError('递归预测器必须为单个窗口返回一个有限数值')
        nxt = float(next_values[0])
        out.append(nxt)
        win = win[1:] + [nxt]
        if nxt < threshold:
            return step, out
    return None, out


def soh_stage_table(history, window, step_fn, rated_capacity,
                    max_steps=MAX_FORECAST_STEPS):
    """给出 SOH 阶段表：每个百分比首次到达的循环序号（相对最新观测点）。

    与 :func:`forecast_eol` 同一口径：SOH 一律定义为 ``C / C_rated``。
    """
    if rated_capacity <= 0:
        raise ValueError('额定容量必须为正数')
    hist = [float(value) for value in np.asarray(
        history, dtype=np.float64).reshape(-1)]
    table = {}
    for pct in (100, 95, 90, 85, 80):
        target = rated_capacity * pct / 100.0
        offset = None
        for index, value in enumerate(hist):
            if value <= target:
                offset = index - (len(hist) - 1)
                break
        if offset is None and len(hist) >= window:
            win = hist[-window:]
            for step in range(1, max_steps + 1):
                next_values = np.asarray(
                    step_fn(np.asarray(win, dtype=np.float32).reshape(1, -1)),
                    dtype=np.float64).reshape(-1)
                nxt = float(next_values[0])
                win = win[1:] + [nxt]
                if nxt <= target:
                    offset = step
                    break
        table[pct] = {
            'cycle_offset': offset,
            'reached': offset is not None and offset <= 0,
        }
    return table


class Throttle:
    """限流：两次预测之间至少间隔 ``min_interval`` 秒。

    其余样本只入缓冲、不触发预测，避免「每条消息同步做上千步递归」把接收
    线程堵死。
    """

    def __init__(self, min_interval=1.0):
        self.min_interval = float(min_interval)
        self._last = 0.0

    def ready(self):
        now = time.monotonic()
        if now - self._last >= self.min_interval:
            self._last = now
            return True
        return False


def new_buffer():
    """有上限的容量历史缓冲。"""
    return deque(maxlen=MAX_BUFFER)


class PredictionJob:
    """把「解析 → 缓冲 → 预测」串起来的纯逻辑对象（不依赖 Qt）。

    UI 层只负责把信号接出去，因此这里可以直接单测。
    """

    def __init__(self, window, step_fn, threshold, rated_capacity,
                 min_interval=1.0):
        self.window = int(window)
        self.step_fn = step_fn
        self.threshold = float(threshold)
        self.rated_capacity = float(rated_capacity)
        self.buffer = new_buffer()
        self.throttle = Throttle(min_interval)

    def reset(self):
        self.buffer.clear()

    def history(self):
        return list(self.buffer)

    def feed(self, capacity):
        """接收一个容量样本，返回 ``(should_predict, history)``。"""
        self.buffer.append(float(capacity))
        history = list(self.buffer)
        should_predict = (
            len(history) >= self.window and self.throttle.ready())
        return should_predict, history

    def predict(self, history=None):
        """在（给定的）历史快照上做一次真正的 RUL 预测。

        ``history`` 为 ``None`` 时用当前缓冲。传入快照可以让预测在**独立线程**
        里跑，而接收线程继续追加新样本——否则一次最长 1500 步的递归预测会把
        接收阻塞住（实测：单步 2.6 ms 时最坏阻塞约 4 s，sklearn 的 9.7 ms
        则接近 15 s）。
        """
        if history is None:
            history = list(self.buffer)
        history = [float(value) for value in history]
        if len(history) < self.window:
            raise ValueError('历史长度小于窗口')
        rul, forecast = forecast_eol(
            history, self.window, self.step_fn, self.threshold)
        return {
            'rul': rul,
            'forecast': forecast,
            'history': history,
            'soh_stages': soh_stage_table(
                history, self.window, self.step_fn, self.rated_capacity),
        }


class LatestOnlyQueue:
    """只保留**最新**一项的容量 1 队列（供实时预测使用）。

    预测比数据慢时，中间那些过时的请求没有价值：界面只关心「当前缓冲对应的
    那一次预测」。因此放新项时直接丢弃尚未处理的旧项，队列永不积压。
    """

    def __init__(self):
        import queue

        self._queue = queue.Queue(maxsize=1)

    def put_latest(self, item):
        """放入最新项，返回是否替换掉了尚未处理的旧项。"""
        import queue

        replaced = False
        while True:
            try:
                self._queue.put_nowait(item)
                return replaced
            except queue.Full:
                try:
                    self._queue.get_nowait()
                    replaced = True
                except queue.Empty:
                    pass

    def get(self, timeout=None):
        import queue

        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None
