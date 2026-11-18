#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""下载并校验 NASA PCoE 电池老化数据集（B0005 / B0006 / B0007 / B0018）。

用法::

    python tools/fetch_nasa.py
    python tools/fetch_nasa.py --out dataset/NASA
"""

from __future__ import annotations

import argparse
import hashlib
import io
from pathlib import Path
import sys
import tempfile
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / 'dataset' / 'NASA'

NASA_ZIP_URL = 'https://phm-datasets.s3.amazonaws.com/NASA/5.+Battery+Data+Set.zip'
EXPECTED_SHA256 = {
    'B0005.mat': '0eae4585baf3f200c09fe24c5ab884f1889679fc75206ca1aa19da704104f0b0',
    'B0006.mat': 'fa818ab4db5db8ab21e910b6dd6c3e20d3761bb9672089e1a4de8f96074616c5',
    'B0007.mat': 'd022afa086efaf54ab5b63f05220f5be178c8027e2fa8d68589db0e85a441a3b',
    'B0018.mat': 'd1e6c923a43ea1c9666b3a90bbb521757a067fd60b4d17dbfaa49c50b179da69',
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def verify_existing(out_dir: Path) -> bool:
    for name, expected in EXPECTED_SHA256.items():
        target = out_dir / name
        if not target.is_file():
            return False
        if sha256_file(target) != expected:
            return False
    return True


def _extract_targets(zip_path: Path, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    extracted = []
    with zipfile.ZipFile(zip_path) as archive:
        members = {Path(name).name: name for name in archive.namelist() if not name.endswith('/')}
        # 顶层压缩包里可能直接有 .mat，也可能嵌套子 zip（如 1. BatteryAgingARC-FY08Q4.zip）
        for target_name in EXPECTED_SHA256:
            if target_name in members:
                dest = out_dir / target_name
                with archive.open(members[target_name]) as src, dest.open('wb') as dst:
                    while True:
                        buf = src.read(1024 * 1024)
                        if not buf:
                            break
                        dst.write(buf)
                extracted.append(dest)

        if len(extracted) < len(EXPECTED_SHA256):
            for inner_name in archive.namelist():
                if not inner_name.lower().endswith('.zip'):
                    continue
                with archive.open(inner_name) as inner_stream:
                    inner_bytes = io.BytesIO(inner_stream.read())
                with zipfile.ZipFile(inner_bytes) as inner_zip:
                    inner_members = {
                        Path(n).name: n
                        for n in inner_zip.namelist()
                        if not n.endswith('/')
                    }
                    for target_name in EXPECTED_SHA256:
                        dest = out_dir / target_name
                        if dest.is_file():
                            continue
                        if target_name in inner_members:
                            with inner_zip.open(inner_members[target_name]) as src, dest.open('wb') as dst:
                                while True:
                                    buf = src.read(1024 * 1024)
                                    if not buf:
                                        break
                                    dst.write(buf)
                            extracted.append(dest)
    return extracted


def fetch_nasa(out_dir: Path = DEFAULT_OUT, url: str = NASA_ZIP_URL, timeout: int = 60) -> int:
    if verify_existing(out_dir):
        print(f'已校验 {out_dir} 下全部 4 个 NASA MAT 文件（SHA-256 通过）')
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    req = Request(url, headers={'User-Agent': 'BatterySOH-Fetch/1.0'})
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            zip_path = Path(tmp_dir) / 'nasa_battery.zip'
            print(f'正在下载：{url}')
            with urlopen(req, timeout=timeout) as resp:  # nosec B310
                content_type = str(resp.headers.get('Content-Type', '')).lower()
                if 'text/html' in content_type:
                    raise RuntimeError(f'返回网页而非压缩包（可能需要登录或验证码）：Content-Type={content_type}')
                total = int(resp.headers.get('Content-Length', 0) or 0)
                downloaded = 0
                with zip_path.open('wb') as dst:
                    while True:
                        chunk = resp.read(1024 * 1024)
                        if not chunk:
                            break
                        dst.write(chunk)
                        downloaded += len(chunk)
                        if total:
                            pct = downloaded * 100.0 / total
                            print(f'\r进度：{downloaded / 1048576:.1f} / {total / 1048576:.1f} MB ({pct:.1f}%)', end='', flush=True)
                print()
            _extract_targets(zip_path, out_dir)
    except (HTTPError, URLError, OSError, RuntimeError, zipfile.BadZipFile) as exc:
        print(f'ERROR: 下载或解压 NASA 数据失败：{exc}', file=sys.stderr)
        print(
            f'请手动从 {url} 下载并解压 B0005.mat / B0006.mat / B0007.mat / B0018.mat 放入：\n  {out_dir}',
            file=sys.stderr,
        )
        return 1

    for name, expected in EXPECTED_SHA256.items():
        target = out_dir / name
        if not target.is_file():
            print(f'ERROR: 解压后缺少 {target}', file=sys.stderr)
            return 1
        actual = sha256_file(target)
        if actual != expected:
            print(f'ERROR: {name} SHA-256 校验失败：实际 {actual} != 预期 {expected}', file=sys.stderr)
            return 1
        print(f'SHA-256 OK: {name} ({actual})')
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='下载并校验 NASA PCoE B0005/B0006/B0007/B0018 数据')
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT, help='解压目录（默认 dataset/NASA）')
    parser.add_argument('--url', default=NASA_ZIP_URL, help='NASA PCoE 官方公开压缩包 URL')
    parser.add_argument('--timeout', type=int, default=60, help='请求超时时间（秒）')
    args = parser.parse_args(argv)
    return fetch_nasa(args.out, url=args.url, timeout=args.timeout)


if __name__ == '__main__':
    raise SystemExit(main())
