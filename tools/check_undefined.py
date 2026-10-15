#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""找"用了但从未定义"的全局名字（可放进 CI）。

用法::

    python tools/check_undefined.py core models ui utils

退出码 0 表示没有发现；1 表示存在可疑引用。

原理：用 ``symtable`` 逐个模块解析作用域表。若某个函数/类作用域里出现了一个
符号，它满足"是全局名 + 被引用 + 从未被赋值"，而且这个名字既不在模块顶层
定义过（赋值 / import / def / class / global 声明），也不在内建名字表里，
那它几乎必然是打错的变量名或漏掉的赋值 —— 也就是"用了但从未定义"。

这类问题在运行时才炸（NameError），静态跑一遍能提前发现。例如
``ui/tcp_server.py`` 里把 ``rated_capacity`` 写成了 ``initial_capacity``。
"""

import builtins
import pathlib
import symtable
import sys

BUILTINS = set(dir(builtins)) | {'__file__', '__name__', '__doc__'}


def _walk(table, module_names, path, found):
    for sym in table.get_symbols():
        name = sym.get_name()
        if (table.get_type() != 'module' and sym.is_global() and sym.is_referenced()
                and not sym.is_assigned() and name not in module_names and name not in BUILTINS):
            found.append((path, table.get_name(), name, table.get_lineno()))
    for child in table.get_children():
        _walk(child, module_names, path, found)


def check_file(path):
    top = symtable.symtable(pathlib.Path(path).read_text(encoding='utf-8'), str(path), 'exec')
    module_names = {s.get_name() for s in top.get_symbols()
                    if s.is_assigned() or s.is_imported() or s.is_namespace() or s.is_declared_global()}
    found = []
    _walk(top, module_names, path, found)
    return found


if __name__ == '__main__':
    problems = []
    for root in sys.argv[1:] or ['.']:
        for py in sorted(pathlib.Path(root).rglob('*.py')):
            problems += check_file(py)
    for path, func, name, line in problems:
        print(f'{path}: 函数 {func}（第 {line} 行起）使用了未定义的名字 {name!r}')
    sys.exit(1 if problems else 0)
