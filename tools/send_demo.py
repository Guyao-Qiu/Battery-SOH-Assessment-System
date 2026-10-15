#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""向本机 TCP 服务灌入一段递减容量，让预测越过 80%，再发一条非法消息。

用法::

    python tools/send_demo.py [host] [port]

默认 127.0.0.1:8888。修复前：程序在容量序列越过 80% 时退出（或在 TCP 面板里
抛出 NameError）；修复后：RUL 表正常出现，非法消息只产生一条警告。

只依赖标准库，不导入 PyQt6，方便在纯命令行环境里复现问题。
"""

import json
import socket
import sys
import time

HOST_DEFAULT = '127.0.0.1'
PORT_DEFAULT = 8888
N_MESSAGES = 60
BASE_CAPACITY = 2.0
DECAY_PER_STEP = 0.012
SEND_INTERVAL = 0.05

# 依次发送的非法消息：非数值容量、NaN、非 JSON 文本
INVALID_PAYLOADS = [
    b'{"capacity": "abc"}\n',
    b'{"capacity": NaN}\n',
    b'not json\n',
]


def send_line(sock, payload):
    sock.sendall(payload)


def main(argv):
    host = argv[1] if len(argv) > 1 else HOST_DEFAULT
    try:
        port = int(argv[2]) if len(argv) > 2 else PORT_DEFAULT
    except ValueError:
        print(f'端口号无效：{argv[2]!r}，应为整数。', file=sys.stderr)
        return 2

    print(f'目标服务 {host}:{port}')
    print(f'准备发送 {N_MESSAGES} 条递减容量消息（每条约 {SEND_INTERVAL}s）…')

    try:
        with socket.create_connection((host, port), timeout=5.0) as sock:
            sock.settimeout(10.0)

            last_capacity = BASE_CAPACITY
            for i in range(N_MESSAGES):
                capacity = BASE_CAPACITY - DECAY_PER_STEP * i
                last_capacity = capacity
                payload = json.dumps({'capacity': capacity}).encode('utf-8') + b'\n'
                send_line(sock, payload)
                if i % 10 == 9 or i == N_MESSAGES - 1:
                    print(f'  已发送 {i + 1}/{N_MESSAGES} 条，最新容量 {capacity:.4f}')
                time.sleep(SEND_INTERVAL)

            print(f'容量已从 {BASE_CAPACITY:.4f} 递减到 {last_capacity:.4f}（约 '
                  f'{last_capacity / BASE_CAPACITY * 100:.1f}%），应已越过 80% 阈值。')

            for payload in INVALID_PAYLOADS:
                print(f'发送非法消息：{payload!r}')
                send_line(sock, payload)
                time.sleep(SEND_INTERVAL)

            print('演示消息发送完毕，正常关闭连接。')
    except ConnectionRefusedError:
        print(f'连接被拒绝：{host}:{port} 上没有服务在监听。'
              f'请先启动 Battery SOH 程序并开启 TCP 服务，再运行本脚本。', file=sys.stderr)
        return 1
    except socket.timeout:
        print(f'连接 {host}:{port} 超时：服务未响应。', file=sys.stderr)
        return 1
    except OSError as exc:
        print(f'网络错误：无法与 {host}:{port} 通信（{exc}）。', file=sys.stderr)
        return 1

    print('演示完成：若 RUL 表正常出现且非法消息只产生警告，则修复生效。')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
