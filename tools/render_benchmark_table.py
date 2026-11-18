#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""从 benchmark/results_<短commit>.json 渲染 README 基准表。

用法::

    python tools/render_benchmark_table.py --input benchmark/results_cbcbfa9.json
    python tools/render_benchmark_table.py --input benchmark/results_cbcbfa9.json --check
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BEGIN_MARKER = '<!-- BENCH:BEGIN -->'
END_MARKER = '<!-- BENCH:END -->'
SKILL_THRESHOLD = 0.05

STATUS_ZH = {
    'observed': '已观测',
    'observed_censored': '真实删失',
    'prediction_censored': '预测删失',
    'both_censored': '双侧删失',
    'observed_initial_failure': '初始已失效',
    'prediction_initial_failure': '预测初始失效',
    'ok': '已检出',
    'pred_censored': '预测删失',
    'true_censored': '真实删失',
    'mixed': '多种子混合',
    'unavailable': '不可用',
}

BASELINE_EN = {
    '平推基线': 'Persistence',
    '线性外推': 'Linear Extrap.',
    '双指数': 'Double Exp.',
}


def _fmt_float(value, fmt='{:.4f}') -> str:
    if value is None:
        return '—'
    return fmt.format(float(value))


def _fmt_ci_cell(entry: dict | None, fmt='{:.4f}') -> str:
    if not entry or entry.get('mean') is None:
        return '—'
    mean = float(entry['mean'])
    std = entry.get('std')
    if std is None:
        return fmt.format(mean)
    return f'{fmt.format(mean)} ± {fmt.format(float(std))}'


def _fmt_skill(value, *, is_persistence: bool = False, lang: str = 'zh') -> str:
    if value is None:
        return '—'
    num = float(value)
    text = f'{num:+.3f}'
    if is_persistence:
        return f'{text}（基线）' if lang == 'zh' else f'{text} (base)'
    if num < SKILL_THRESHOLD:
        return f'{text} ⚠'
    return text


def _fmt_re(value) -> str:
    if value is None:
        return '—'
    return f'{float(value) * 100:.2f}%'


def _fmt_eol(value) -> str:
    if value is None:
        return 'N/A（截尾）'
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f'{value:.1f}'
    return str(value)


def _fmt_status(status: str | None, lang: str = 'zh') -> str:
    if not status:
        return '—'
    if lang == 'zh':
        return STATUS_ZH.get(status, status)
    return status


def _render_block(manifest: dict, json_rel_path: str, lang: str = 'zh') -> str:
    models = manifest.get('models', {})
    baselines = manifest.get('baselines', {})
    dataset = manifest.get('dataset', {})
    hardware = manifest.get('hardware', {})
    deps = manifest.get('dependencies', {})
    short_commit = manifest.get('short_commit') or manifest.get('source_commit', '')[:7]
    full_commit = manifest.get('source_commit', '')
    elapsed = manifest.get('elapsed_seconds')
    base_cfg = manifest.get('base_config', {})
    starts = manifest.get('rolling_starts', [0.4, 0.5, 0.6, 0.7])
    start_keys = [f'{int(round(s * 100))}%' for s in starts]
    first_model = next(iter(models.values()), {})
    n_seeds = len(first_model.get('seeds', [])) or int(base_cfg.get('n_seeds', 5))

    lines = []
    if lang == 'zh':
        lines.append(
            f'> 来源文件：[`{json_rel_path}`]({json_rel_path}) · 提交：`{short_commit}` · '
            f'协议：`{manifest.get("protocol")}` · 阈值比例：`{base_cfg.get("threshold_ratio")}` · '
            f'离群点模式：`{base_cfg.get("outlier_mode")}`'
        )
        lines.append('')
        lines.append(f'### 宏平均总览（{len(models)} 个模型 + {len(baselines)} 条经验基线，CALCE `CS2_35`–`CS2_38` 留一电池，{n_seeds} 种子均值）')
        lines.append('')
        lines.append(
            '| 模型 / 基线 | 一步 RMSE ↓ | 一步 MAE ↓ | 一步 R² ↑ | '
            '40% 递归 RMSE | 50% 递归 RMSE | 60% 递归 RMSE | 70% 递归 RMSE | '
            '平均技能分 ↑ | 递归 RE ↓ |'
        )
        lines.append('|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|')
    else:
        lines.append(
            f'> Source: [`{json_rel_path}`]({json_rel_path}) · Commit: `{short_commit}` · '
            f'Protocol: `{manifest.get("protocol")}` · `threshold_ratio={base_cfg.get("threshold_ratio")}` · '
            f'`outlier_mode={base_cfg.get("outlier_mode")}`'
        )
        lines.append('')
        lines.append(
            f'### Macro Summary ({len(models)} Models + {len(baselines)} Baselines, CALCE `CS2_35`–`CS2_38` LOBO, {n_seeds}-Seed Mean)'
        )
        lines.append('')
        lines.append(
            '| Model / Baseline | 1-Step RMSE ↓ | 1-Step MAE ↓ | 1-Step R² ↑ | '
            '40% Roll RMSE | 50% Roll RMSE | 60% Roll RMSE | 70% Roll RMSE | '
            'Mean Skill ↑ | Rec. RE ↓ |'
        )
        lines.append('|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|')

    for name, entry in models.items():
        macro = entry.get('macro_average', {})
        r_start = macro.get('rolling_by_start', {})
        roll_cells = [_fmt_float((r_start.get(k) or {}).get('rmse')) for k in start_keys]
        skill_text = _fmt_skill(macro.get('rolling_mean_skill'), lang=lang)
        lines.append(
            f'| **{name}** | {_fmt_float(macro.get("one_step_rmse"))} | '
            f'{_fmt_float(macro.get("one_step_mae"))} | '
            f'{_fmt_float(macro.get("one_step_r2"))} | '
            + ' | '.join(roll_cells)
            + f' | {skill_text} | {_fmt_re(macro.get("re"))} |'
        )

    for b_name, entry in baselines.items():
        macro = entry.get('macro_average', {})
        r_start = macro.get('rolling_by_start', {})
        roll_cells = [_fmt_float((r_start.get(k) or {}).get('rmse')) for k in start_keys]
        disp_name = b_name if lang == 'zh' else BASELINE_EN.get(b_name, b_name)
        is_pers = b_name == '平推基线'
        skill_text = _fmt_skill(macro.get('rolling_mean_skill'), is_persistence=is_pers, lang=lang)
        lines.append(
            f'| {disp_name} | {_fmt_float(macro.get("one_step_rmse"))} | '
            f'{_fmt_float(macro.get("one_step_mae"))} | '
            f'{_fmt_float(macro.get("one_step_r2"))} | '
            + ' | '.join(roll_cells)
            + f' | {skill_text} | {_fmt_re(macro.get("re"))} |'
        )

    lines.append('')
    if lang == 'zh':
        lines.append('### 分起点技能分（相对平推基线 `1 − RMSE模型 / RMSE平推`，`< 0.05` 标 ⚠）')
        lines.append('')
        lines.append('| 模型 / 基线 | 40% 起点 | 50% 起点 | 60% 起点 | 70% 起点 | 宏平均技能分 |')
        lines.append('|---|---:|---:|---:|---:|---:|')
    else:
        lines.append('### Per-Origin Skill vs. Persistence (`1 − RMSE_model / RMSE_persistence`; `< 0.05` flagged ⚠)')
        lines.append('')
        lines.append('| Model / Baseline | 40% Origin | 50% Origin | 60% Origin | 70% Origin | Macro Skill |')
        lines.append('|---|---:|---:|---:|---:|---:|')

    for name, entry in models.items():
        macro = entry.get('macro_average', {})
        r_start = macro.get('rolling_by_start', {})
        cells = [_fmt_skill((r_start.get(k) or {}).get('skill'), lang=lang) for k in start_keys]
        lines.append(
            f'| **{name}** | ' + ' | '.join(cells)
            + f' | {_fmt_skill(macro.get("rolling_mean_skill"), lang=lang)} |'
        )
    for b_name, entry in baselines.items():
        if b_name == '平推基线':
            continue
        macro = entry.get('macro_average', {})
        r_start = macro.get('rolling_by_start', {})
        disp_name = b_name if lang == 'zh' else BASELINE_EN.get(b_name, b_name)
        cells = [_fmt_skill((r_start.get(k) or {}).get('skill'), lang=lang) for k in start_keys]
        lines.append(
            f'| {disp_name} | ' + ' | '.join(cells)
            + f' | {_fmt_skill(macro.get("rolling_mean_skill"), lang=lang)} |'
        )

    lines.append('')
    if lang == 'zh':
        lines.append('<details>')
        lines.append('<summary>展开查看各「模型 × 电池」完整明细（一步指标、40%–70% 递归 RMSE/技能分、RUL 与截尾状态）</summary>')
        lines.append('')
        lines.append(
            '| 模型 | 电池 | 循环 | 一步 RMSE | 一步 MAE | 一步 R² | '
            '40% RMSE (技能) | 50% RMSE (技能) | 60% RMSE (技能) | 70% RMSE (技能) | '
            '预测 EOL | 真实 EOL | 递归 RE | 截尾状态 |'
        )
        lines.append('|---|---|---:|---:|---:|---:|---|---|---|---|---:|---:|---:|---|')
    else:
        lines.append('<details>')
        lines.append('<summary>Expand per-(model × battery) details (1-step metrics, 40%–70% rolling RMSE/skill, EOL, RE & censoring)</summary>')
        lines.append('')
        lines.append(
            '| Model | Battery | Cycles | 1-Step RMSE | 1-Step MAE | 1-Step R² | '
            '40% RMSE (Skill) | 50% RMSE (Skill) | 60% RMSE (Skill) | 70% RMSE (Skill) | '
            'Pred EOL | True EOL | Rec. RE | Status |'
        )
        lines.append('|---|---|---:|---:|---:|---:|---|---|---|---|---:|---:|---:|---|')

    for name, entry in models.items():
        for bat, b_res in entry.get('batteries', {}).items():
            one = b_res.get('one_step', {})
            rolling = b_res.get('rolling', {})
            rul = b_res.get('rul', {})
            roll_cells = []
            for sk in start_keys:
                r_item = rolling.get(sk) or {}
                rmse_val = (r_item.get('rmse') or {}).get('mean')
                skill_val = (r_item.get('skill') or {}).get('mean')
                roll_cells.append(
                    f'{_fmt_float(rmse_val)} ({_fmt_skill(skill_val, lang=lang)})'
                )
            lines.append(
                f'| {name} | {bat} | {b_res.get("cycles")} | '
                f'{_fmt_ci_cell(one.get("rmse"))} | '
                f'{_fmt_ci_cell(one.get("mae"))} | '
                f'{_fmt_ci_cell(one.get("r2"))} | '
                + ' | '.join(roll_cells)
                + f' | {_fmt_eol(rul.get("pred_eol_cycle_mean"))} | '
                f'{_fmt_eol(rul.get("true_eol_cycle"))} | '
                f'{_fmt_ci_cell(rul.get("re"), fmt="{:.2%}") if rul.get("re") else "—"} | '
                f'{_fmt_status(rul.get("re_status"), lang=lang)} |'
            )

    for b_name, entry in baselines.items():
        disp_name = b_name if lang == 'zh' else BASELINE_EN.get(b_name, b_name)
        is_pers = b_name == '平推基线'
        for bat, b_res in entry.get('batteries', {}).items():
            one = b_res.get('one_step', {})
            rolling = b_res.get('rolling', {})
            rul = b_res.get('rul', {})
            roll_cells = []
            for sk in start_keys:
                r_item = rolling.get(sk) or {}
                roll_cells.append(
                    f'{_fmt_float(r_item.get("rmse"))} '
                    f'({_fmt_skill(r_item.get("skill"), is_persistence=is_pers, lang=lang)})'
                )
            lines.append(
                f'| {disp_name} | {bat} | {b_res.get("cycles")} | '
                f'{_fmt_float(one.get("rmse"))} | '
                f'{_fmt_float(one.get("mae"))} | '
                f'{_fmt_float(one.get("r2"))} | '
                + ' | '.join(roll_cells)
                + f' | {_fmt_eol(rul.get("pred_eol_cycle"))} | '
                f'{_fmt_eol(rul.get("true_eol_cycle"))} | '
                f'{_fmt_re(rul.get("re"))} | '
                f'{_fmt_status(rul.get("re_status"), lang=lang)} |'
            )

    lines.append('')
    lines.append('</details>')
    lines.append('')

    if lang == 'zh':
        lines.append('复现实验环境与数据哈希：')
        lines.append('')
        lines.append(f'- 源提交：`{full_commit}`')
        if elapsed is not None:
            lines.append(f'- 总耗时：{elapsed:.2f} 秒')
        lines.append(
            f'- 硬件：{hardware.get("cpu", "unknown")}；GPU：{hardware.get("gpu", "unknown")}；'
            f'驱动：{hardware.get("driver", "unknown")}；CUDA：{hardware.get("torch_cuda", "unknown")}'
        )
        lines.append(
            '- 软件：' + '；'.join(f'{k} {v}' for k, v in deps.items())
        )
        lines.append('')
        lines.append('| 电池 | 循环数 | 原始源文件树 SHA-256 | 清洗后容量序列 SHA-256 |')
        lines.append('|---|---:|---|---|')
        for bat, info in dataset.items():
            lines.append(
                f'| {bat} | {info["cycles"]} | `{info["source_sha256"]}` | `{info["capacity_sha256"]}` |'
            )
    else:
        lines.append('Reproducibility metadata & dataset hashes:')
        lines.append('')
        lines.append(f'- Source commit: `{full_commit}`')
        if elapsed is not None:
            lines.append(f'- Elapsed seconds: {elapsed:.2f} s')
        lines.append(
            f'- Hardware: {hardware.get("cpu", "unknown")}; GPU: {hardware.get("gpu", "unknown")}; '
            f'Driver: {hardware.get("driver", "unknown")}; CUDA: {hardware.get("torch_cuda", "unknown")}'
        )
        lines.append(
            '- Software: ' + '; '.join(f'{k} {v}' for k, v in deps.items())
        )
        lines.append('')
        lines.append('| Battery | Cycles | Source Tree SHA-256 | Cleaned Capacity SHA-256 |')
        lines.append('|---|---:|---|---|')
        for bat, info in dataset.items():
            lines.append(
                f'| {bat} | {info["cycles"]} | `{info["source_sha256"]}` | `{info["capacity_sha256"]}` |'
            )

    return '\n'.join(lines)


def _find_latest_results(root: Path) -> Path:
    candidates = sorted(
        (root / 'benchmark').glob('results_*.json'),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError('未找到 benchmark/results_*.json，请先运行基准脚本或指定 --input')
    return candidates[0]


def _replace_marker_block(text: str, replacement: str) -> str:
    if BEGIN_MARKER not in text or END_MARKER not in text:
        raise ValueError(f'缺少标记 {BEGIN_MARKER} / {END_MARKER}')
    before, rest = text.split(BEGIN_MARKER, 1)
    _, after = rest.split(END_MARKER, 1)
    return f'{before}{BEGIN_MARKER}\n{replacement}\n{END_MARKER}{after}'


def _extract_marker_block(text: str) -> str | None:
    if BEGIN_MARKER not in text or END_MARKER not in text:
        return None
    _, rest = text.split(BEGIN_MARKER, 1)
    current, _ = rest.split(END_MARKER, 1)
    return current.strip('\r\n')


def check_benchmark_tables(input_path: Path, root: Path = ROOT) -> list[str]:
    manifest = json.loads(input_path.read_text(encoding='utf-8'))
    try:
        rel_path = input_path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        rel_path = input_path.as_posix()

    problems = []
    for filename, lang in (('README.md', 'zh'), ('README_EN.md', 'en')):
        path = root / filename
        text = path.read_text(encoding='utf-8')
        current = _extract_marker_block(text)
        if current is None:
            problems.append(f'{filename} 缺少 {BEGIN_MARKER} / {END_MARKER}')
            continue
        expected = _render_block(manifest, rel_path, lang=lang).strip('\r\n')
        if current.replace('\r\n', '\n') != expected.replace('\r\n', '\n'):
            problems.append(f'{filename} 基准表与 {rel_path} 不一致')
    return problems


def render_benchmark_tables(input_path: Path, root: Path = ROOT) -> list[Path]:
    manifest = json.loads(input_path.read_text(encoding='utf-8'))
    try:
        rel_path = input_path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        rel_path = input_path.as_posix()

    updated = []
    for filename, lang in (('README.md', 'zh'), ('README_EN.md', 'en')):
        path = root / filename
        text = path.read_text(encoding='utf-8')
        block = _render_block(manifest, rel_path, lang=lang)
        new_text = _replace_marker_block(text, block)
        if new_text != text:
            path.write_text(new_text, encoding='utf-8')
            updated.append(path)
    return updated


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='从基准 JSON 渲染 README 表格')
    parser.add_argument('--input', type=Path, default=None, help='基准 JSON 路径')
    parser.add_argument('--check', action='store_true', help='校验 README 基准表是否与 JSON 一致')
    args = parser.parse_args(argv)

    input_path = args.input if args.input is not None else _find_latest_results(ROOT)
    if args.check:
        problems = check_benchmark_tables(input_path, ROOT)
        if problems:
            for p in problems:
                print(f'ERROR: {p}', file=sys.stderr)
            return 1
        print('README 基准表与 JSON 一致')
        return 0

    updated = render_benchmark_tables(input_path, ROOT)
    for path in updated:
        print(f'已更新 {path.name}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
