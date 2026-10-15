#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""禁止在代码里硬编码颜色：所有色值必须集中在 theme_tokens.py。

用法::

    python tools/check_colors.py
    python tools/check_colors.py --allow battery_soh_app.py

扫描当前目录下的全部 ``*.py``，跳过 ``.venv`` / ``venv`` / ``tests`` / ``tools``
目录，并跳过 ``theme_tokens.py`` 本身。命中 ``#RRGGBB`` 形式的字面量就打印
``路径:行号: 片段``，片段截断到 90 字符。

退出码 0 表示干净；1 表示仍有硬编码颜色。
"""

import argparse
import os
import pathlib
import re
import sys

ALLOWED = {'theme_tokens.py'}
PATTERN = re.compile(r'#[0-9A-Fa-f]{6}\b')

SKIP_DIRS = {'.venv', 'venv', 'tests', 'tools', '.git', '__pycache__',
             '.codex_tmp_fund_analysis', '.workbuddy-ai', '.ruff_cache',
             '.pytest_cache', '.idea'}

#: 生成产物：由 scripts/build_all_in_one.py 从上面的源码拼出来，
#: 它里面的色值只是源码的副本，检查源码就够了。
SKIP_FILES = {'battery_soh_all_in_one.py'}


def main(argv=None):
    parser = argparse.ArgumentParser(description='检查硬编码颜色字面量')
    parser.add_argument('--allow', action='extend', nargs='+', default=[], metavar='FILE',
                        help='额外允许包含颜色字面量的文件名（可重复或一次给多个）')
    args = parser.parse_args(argv)

    allowed = ALLOWED | {pathlib.Path(name).name for name in args.allow}

    bad = []
    for dirpath, dirnames, filenames in os.walk('.'):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for filename in sorted(filenames):
            if not filename.endswith('.py'):
                continue
            if filename in allowed or filename in SKIP_FILES:
                continue
            path = pathlib.Path(dirpath) / filename
            try:
                lines = path.read_text(encoding='utf-8').splitlines()
            except (OSError, UnicodeDecodeError):
                continue
            for lineno, line in enumerate(lines, 1):
                if PATTERN.search(line):
                    snippet = line.strip()[:90]
                    bad.append(f'{path}:{lineno}: {snippet}')

    for item in bad:
        print(item)
    if not bad:
        print('没有硬编码颜色')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
