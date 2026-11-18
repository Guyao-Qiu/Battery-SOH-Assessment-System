#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""从 benchmark/results_<短commit>.json 与 benchmark/nasa_<短commit>.json 渲染 README 基准表。

用法::

    python tools/render_benchmark_table.py --input benchmark/results_cbcbfa9.json
    python tools/render_benchmark_table.py --nasa-input benchmark/nasa_6759ba3.json
    python tools/render_benchmark_table.py --check
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BEGIN_MARKER = '<!-- BENCH:BEGIN -->'
END_MARKER = '<!-- BENCH:END -->'
NASA_BEGIN_MARKER = '<!-- NASA:BEGIN -->'
NASA_END_MARKER = '<!-- NASA:END -->'
ABLATION_BEGIN_MARKER = '<!-- ABLATION:BEGIN -->'
ABLATION_END_MARKER = '<!-- ABLATION:END -->'
SKILL_THRESHOLD = 0.05

ABLATION_LABELS_ZH = {
    'capacity_only': '仅容量（基准）',
    'plus_dq_v': '+ `dq_v`',
    'plus_CCCT': '+ `CCCT`',
    'plus_CVCT': '+ `CVCT`',
    'plus_resistance': '+ `resistance`',
    'plus_ica_peak_v': '+ `ica_peak_v`（峰位）',
    'plus_ica_peak_h': '+ `ica_peak_h`（峰高）',
    'plus_ica_peak_area': '+ `ica_peak_area`（峰面积）',
    'plus_ica_all': '+ 全部 ICA（3 项）',
    'all_features': '全部特征（8 项）',
}

ABLATION_LABELS_EN = {
    'capacity_only': 'Capacity only (base)',
    'plus_dq_v': '+ `dq_v`',
    'plus_CCCT': '+ `CCCT`',
    'plus_CVCT': '+ `CVCT`',
    'plus_resistance': '+ `resistance`',
    'plus_ica_peak_v': '+ `ica_peak_v` (peak V)',
    'plus_ica_peak_h': '+ `ica_peak_h` (peak H)',
    'plus_ica_peak_area': '+ `ica_peak_area` (area)',
    'plus_ica_all': '+ All ICA (3)',
    'all_features': 'All features (8)',
}

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


def _append_macro_and_skill_tables(
    lines: list[str],
    models: dict,
    baselines: dict,
    start_keys: list[str],
    *,
    title_zh: str,
    title_en: str,
    lang: str,
    include_skill_table: bool = True,
    include_details: bool = True,
) -> None:
    if lang == 'zh':
        lines.append(f'### {title_zh}')
        lines.append('')
        lines.append(
            '| 模型 / 基线 | 一步 RMSE ↓ | 一步 MAE ↓ | 一步 R² ↑ | '
            + ' | '.join(f'{k} 递归 RMSE' for k in start_keys)
            + ' | 平均技能分 ↑ | 递归 RE ↓ |'
        )
    else:
        lines.append(f'### {title_en}')
        lines.append('')
        lines.append(
            '| Model / Baseline | 1-Step RMSE ↓ | 1-Step MAE ↓ | 1-Step R² ↑ | '
            + ' | '.join(f'{k} Roll RMSE' for k in start_keys)
            + ' | Mean Skill ↑ | Rec. RE ↓ |'
        )
    lines.append('|---|---:|---:|---:|' + '---:|' * len(start_keys) + '---:|---:|')

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

    if include_skill_table:
        lines.append('')
        if lang == 'zh':
            lines.append('#### 分起点技能分（相对平推基线 `1 − RMSE模型 / RMSE平推`，`< 0.05` 标 ⚠）')
            lines.append('')
            lines.append('| 模型 / 基线 | ' + ' | '.join(f'{k} 起点' for k in start_keys) + ' | 宏平均技能分 |')
        else:
            lines.append('#### Per-Origin Skill vs. Persistence (`1 − RMSE_model / RMSE_persistence`; `< 0.05` flagged ⚠)')
            lines.append('')
            lines.append('| Model / Baseline | ' + ' | '.join(f'{k} Origin' for k in start_keys) + ' | Macro Skill |')
        lines.append('|---|' + '---:|' * (len(start_keys) + 1))

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

    if include_details:
        lines.append('')
        if lang == 'zh':
            lines.append('<details>')
            lines.append('<summary>展开查看各「模型 × 电池」完整明细（一步指标、40%–70% 递归 RMSE/技能分、RUL 与截尾状态）</summary>')
            lines.append('')
            lines.append(
                '| 模型 | 电池 | 循环 | 一步 RMSE | 一步 MAE | 一步 R² | '
                + ' | '.join(f'{k} RMSE (技能)' for k in start_keys)
                + ' | 预测 EOL | 真实 EOL | 递归 RE | 截尾状态 |'
            )
        else:
            lines.append('<details>')
            lines.append('<summary>Expand per-(model × battery) details (1-step metrics, 40%–70% rolling RMSE/skill, EOL, RE & censoring)</summary>')
            lines.append('')
            lines.append(
                '| Model | Battery | Cycles | 1-Step RMSE | 1-Step MAE | 1-Step R² | '
                + ' | '.join(f'{k} RMSE (Skill)' for k in start_keys)
                + ' | Pred EOL | True EOL | Rec. RE | Status |'
            )
        lines.append('|---|---|---:|---:|---:|---:|' + '---|' * len(start_keys) + '---:|---:|---:|---|')

        for name, entry in models.items():
            for bat, b_res in entry.get('batteries', {}).items():
                one = b_res.get('one_step', {})
                rolling = b_res.get('rolling', {})
                rul = b_res.get('rul', {})
                roll_cells = []
                for sk in start_keys:
                    r_item = rolling.get(sk)
                    if not r_item:
                        roll_cells.append('—')
                        continue
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
                    r_item = rolling.get(sk)
                    if not r_item:
                        roll_cells.append('—')
                        continue
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


def _append_repro_footer(lines: list[str], manifest: dict, lang: str) -> None:
    dataset = manifest.get('dataset', {})
    hardware = manifest.get('hardware', {})
    deps = manifest.get('dependencies', {})
    full_commit = manifest.get('source_commit', '')
    elapsed = manifest.get('elapsed_seconds')

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
        lines.append('- 软件：' + '；'.join(f'{k} {v}' for k, v in deps.items()))
        lines.append('')
        lines.append('| 电池 | 循环数 | 原始源文件树 SHA-256 | 清洗后容量序列 SHA-256 |')
        lines.append('|---|---:|---|---|')
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
        lines.append('- Software: ' + '; '.join(f'{k} {v}' for k, v in deps.items()))
        lines.append('')
        lines.append('| Battery | Cycles | Source SHA-256 | Cleaned Capacity SHA-256 |')
        lines.append('|---|---:|---|---|')

    for bat, info in dataset.items():
        lines.append(
            f'| {bat} | {info["cycles"]} | `{info["source_sha256"]}` | `{info["capacity_sha256"]}` |'
        )


def _render_block(manifest: dict, json_rel_path: str, lang: str = 'zh') -> str:
    models = manifest.get('models', {})
    baselines = manifest.get('baselines', {})
    short_commit = manifest.get('short_commit') or manifest.get('source_commit', '')[:7]
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
    else:
        lines.append(
            f'> Source: [`{json_rel_path}`]({json_rel_path}) · Commit: `{short_commit}` · '
            f'Protocol: `{manifest.get("protocol")}` · `threshold_ratio={base_cfg.get("threshold_ratio")}` · '
            f'`outlier_mode={base_cfg.get("outlier_mode")}`'
        )
    lines.append('')
    _append_macro_and_skill_tables(
        lines, models, baselines, start_keys,
        title_zh=f'宏平均总览（{len(models)} 个模型 + {len(baselines)} 条经验基线，CALCE `CS2_35`–`CS2_38` 留一电池，{n_seeds} 种子均值）',
        title_en=f'Macro Summary ({len(models)} Models + {len(baselines)} Baselines, CALCE `CS2_35`–`CS2_38` LOBO, {n_seeds}-Seed Mean)',
        lang=lang,
    )
    _append_repro_footer(lines, manifest, lang)
    return '\n'.join(lines)


def _render_nasa_block(manifest: dict, json_rel_path: str, lang: str = 'zh') -> str:
    exp_a = manifest.get('experiment_a', {})
    exp_b = manifest.get('experiment_b', {})
    short_commit = manifest.get('short_commit') or manifest.get('source_commit', '')[:7]
    base_cfg = manifest.get('base_config', {})
    starts = manifest.get('rolling_starts', [0.4, 0.5, 0.6, 0.7])
    start_keys = [f'{int(round(s * 100))}%' for s in starts]
    first_model = next(iter(exp_a.get('models', {}).values()), {})
    n_seeds = len(first_model.get('seeds', [])) or int(base_cfg.get('n_seeds', 5))

    lines = []
    if lang == 'zh':
        lines.append(
            f'> 来源文件：[`{json_rel_path}`]({json_rel_path}) · 提交：`{short_commit}` · '
            f'NASA 额定容量：`{base_cfg.get("rated_capacity")} Ah` · 阈值比例：`{base_cfg.get("threshold_ratio")}`（1.40 Ah） · '
            f'离群点模式：`{base_cfg.get("outlier_mode")}`'
        )
    else:
        lines.append(
            f'> Source: [`{json_rel_path}`]({json_rel_path}) · Commit: `{short_commit}` · '
            f'NASA `rated_capacity={base_cfg.get("rated_capacity")} Ah` · `threshold_ratio={base_cfg.get("threshold_ratio")}` (1.40 Ah) · '
            f'`outlier_mode={base_cfg.get("outlier_mode")}`'
        )
    lines.append('')
    _append_macro_and_skill_tables(
        lines,
        exp_a.get('models', {}),
        exp_a.get('baselines', {}),
        start_keys,
        title_zh=f'实验 A（同源泛化）：NASA 4 节电池留一验证（`B0005`/`B0006`/`B0007`/`B0018`，{n_seeds} 种子均值）',
        title_en=f'Experiment A (In-Domain): NASA 4-Cell LOBO (`B0005`/`B0006`/`B0007`/`B0018`, {n_seeds}-Seed Mean)',
        lang=lang,
        include_skill_table=False,
        include_details=True,
    )
    lines.append('')
    _append_macro_and_skill_tables(
        lines,
        exp_b.get('models', {}),
        exp_b.get('baselines', {}),
        start_keys,
        title_zh=f'实验 B（跨数据集压力测试）：CALCE 全量训练 → NASA 零样本测试（统一按 `SOH = C / C_rated` 归一化，{n_seeds} 种子均值）',
        title_en=f'Experiment B (Cross-Dataset Stress Test): CALCE-Trained → NASA Zero-Shot (`SOH = C / C_rated`, {n_seeds}-Seed Mean)',
        lang=lang,
        include_skill_table=False,
        include_details=True,
    )

    impact = manifest.get('outlier_impact', {})
    if impact:
        lines.append('')
        if lang == 'zh':
            lines.append('### 容量再生对离群点清洗与 EOL 判定的影响')
            lines.append('')
            lines.append('| 电池 | `off` 循环数 | `chunked` 剔除数 | 可选 `mark` 标记数 | 再生跳变 (>0.02 Ah) | 0.7 阈值 EOL (`chunked` / `off`) | 0.80 (80%) 阈值 EOL (去抖1 vs 去抖3, `off`) |')
            lines.append('|---|---:|---:|---:|---:|---|---|')
        else:
            lines.append('### Impact of Capacity Regeneration on Outlier Cleaning & EOL')
            lines.append('')
            lines.append('| Battery | `off` Cycles | `chunked` Removed | `mark` Flagged | Regen Jumps (>0.02 Ah) | 0.7 EOL (`chunked` / `off`) | 0.8 EOL (debounce 1 vs 3, `off`) |')
            lines.append('|---|---:|---:|---:|---:|---|---|')
        for bat in impact.get('off', {}):
            off_row = impact['off'][bat]
            chk_row = impact.get('chunked', {}).get(bat, {})
            mrk_row = impact.get('mark', {}).get(bat, {})
            eol07 = f'{_fmt_eol(chk_row.get("eol_cycle_07_d1"))} / {_fmt_eol(off_row.get("eol_cycle_07_d1"))}'
            eol08 = f'{_fmt_eol(off_row.get("eol_cycle_08_d1"))} vs {_fmt_eol(off_row.get("eol_cycle_08_d3"))}'
            lines.append(
                f'| {bat} | {off_row.get("cycles")} | {chk_row.get("removed_count")} | '
                f'{mrk_row.get("marked_count")} | {off_row.get("regen_jumps_gt_002ah")} | '
                f'{eol07} | {eol08} |'
            )

    _append_repro_footer(lines, manifest, lang)
    return '\n'.join(lines)


def _fmt_delta(value, is_percent: bool = False) -> str:
    if value is None:
        return '—'
    val = float(value)
    if abs(val) < 1e-9:
        return '0.00%' if is_percent else '0.0000'
    sign = '+' if val > 0 else ''
    return f'{sign}{val * 100:.2f}%' if is_percent else f'{sign}{val:.4f}'


def _fmt_delta_skill(value) -> str:
    if value is None:
        return '—'
    val = float(value)
    if abs(val) < 1e-9:
        return '0.000'
    sign = '+' if val > 0 else ''
    return f'{sign}{val:.3f}'


def _render_ablation_block(manifest: dict, json_rel_path: str, lang: str = 'zh') -> str:
    configs = manifest.get('configs', {})
    short_commit = manifest.get('short_commit') or manifest.get('source_commit', '')[:7]
    base_cfg = manifest.get('base_config', {})
    first_cfg = next(iter(configs.values()), {})
    model_names = list(first_cfg.get('models', {}).keys())
    first_model = next(iter(first_cfg.get('models', {}).values()), {})
    first_bat = next(iter(first_model.get('batteries', {}).values()), {})
    n_seeds = len(first_bat.get('seeds', [])) or int(base_cfg.get('n_seeds', 5))

    lines = []
    if lang == 'zh':
        lines.append(
            f'> 来源文件：[`{json_rel_path}`]({json_rel_path}) · 提交：`{short_commit}` · '
            f'协议：`{manifest.get("protocol")}` · CALCE `CS2_35`–`CS2_38` 留一法 · '
            f'{n_seeds} 种子均值 · 基准阈值比例：`{base_cfg.get("threshold_ratio")}` · '
            f'离群点模式：`{base_cfg.get("outlier_mode")}`'
        )
    else:
        lines.append(
            f'> Source: [`{json_rel_path}`]({json_rel_path}) · Commit: `{short_commit}` · '
            f'Protocol: `{manifest.get("protocol")}` · CALCE `CS2_35`–`CS2_38` LOBO · '
            f'{n_seeds}-Seed Mean · `threshold_ratio={base_cfg.get("threshold_ratio")}` · '
            f'`outlier_mode={base_cfg.get("outlier_mode")}`'
        )

    labels_map = ABLATION_LABELS_ZH if lang == 'zh' else ABLATION_LABELS_EN
    for model_label in model_names:
        lines.append('')
        if lang == 'zh':
            lines.append(f'### `{model_label}` 特征消融（CALCE 4 节电池留一宏平均，{n_seeds} 种子）')
            lines.append('')
            lines.append('| 特征组合 | 特征数 | 一步 RMSE ↓ | Δ 一步 RMSE | 递归均 RMSE ↓ | Δ 递归 RMSE | 平均技能分 ↑ | Δ 技能分 | 递归 RE ↓ |')
            lines.append('|---|---:|---:|---:|---:|---:|---:|---:|---:|')
        else:
            lines.append(f'### `{model_label}` Feature Ablation (CALCE 4-Cell LOBO Macro Mean, {n_seeds}-Seed)')
            lines.append('')
            lines.append('| Feature Subset | #F | 1-Step RMSE ↓ | Δ 1-Step | Roll RMSE ↓ | Δ Roll RMSE | Mean Skill ↑ | Δ Skill | Rec. RE ↓ |')
            lines.append('|---|---:|---:|---:|---:|---:|---:|---:|---:|')

        for cfg_key, cfg_entry in configs.items():
            m_entry = cfg_entry.get('models', {}).get(model_label)
            if not m_entry:
                continue
            macro = m_entry.get('macro_average', {})
            delta = m_entry.get('delta_vs_capacity_only', {})
            n_feats = len(cfg_entry.get('feature_columns', []))
            label = labels_map.get(cfg_key, f'`{cfg_key}`')
            is_base = cfg_key == 'capacity_only'
            d_one = '0.0000' if is_base else _fmt_delta(delta.get('one_step_rmse'))
            d_roll = '0.0000' if is_base else _fmt_delta(delta.get('rolling_mean_rmse'))
            d_skill = '0.000' if is_base else _fmt_delta_skill(delta.get('rolling_mean_skill'))
            lines.append(
                f'| {label} | {n_feats} | '
                f'{_fmt_float(macro.get("one_step_rmse"))} | {d_one} | '
                f'{_fmt_float(macro.get("rolling_mean_rmse"))} | {d_roll} | '
                f'{_fmt_skill(macro.get("rolling_mean_skill"), lang=lang)} | {d_skill} | '
                f'{_fmt_re(macro.get("re"))} |'
            )

    ica_sum = manifest.get('cs2_35_ica_summary', {})
    if ica_sum:
        lines.append('')
        if lang == 'zh':
            lines.append('代表电池 `CS2_35` 因果 ICA 主峰与容量相关性统计：')
            lines.append('')
            lines.append('| ICA 特征 | 有效循环 / NaN | 首周期值 → 末周期值 | 与容量 Pearson r |')
            lines.append('|---|---:|---|---:|')
        else:
            lines.append('Representative cell `CS2_35` causal ICA peak statistics:')
            lines.append('')
            lines.append('| ICA Feature | Valid / NaN | First → Last Cycle | Pearson r vs Capacity |')
            lines.append('|---|---:|---|---:|')
        for feat, info in ica_sum.items():
            first_v = _fmt_float(info.get('first_valid'), '{:.3f}')
            last_v = _fmt_float(info.get('last_valid'), '{:.3f}')
            corr_v = _fmt_float(info.get('pearson_with_capacity'), '{:.4f}')
            lines.append(
                f'| `{feat}` | {info.get("valid_count")} / {info.get("nan_count")} | '
                f'{first_v} → {last_v} | {corr_v} |'
            )

    _append_repro_footer(lines, manifest, lang)
    return '\n'.join(lines)


def _find_latest(root: Path, pattern: str) -> Path | None:
    candidates = sorted(
        (root / 'benchmark').glob(pattern),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def _replace_marker_block(text: str, replacement: str, begin: str, end: str) -> str:
    if begin not in text or end not in text:
        raise ValueError(f'缺少标记 {begin} / {end}')
    before, rest = text.split(begin, 1)
    _, after = rest.split(end, 1)
    return f'{before}{begin}\n{replacement}\n{end}{after}'


def _extract_marker_block(text: str, begin: str, end: str) -> str | None:
    if begin not in text or end not in text:
        return None
    _, rest = text.split(begin, 1)
    current, _ = rest.split(end, 1)
    return current.strip('\r\n')


def _rel_path(input_path: Path, root: Path) -> str:
    try:
        return input_path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return input_path.as_posix()


def check_benchmark_tables(
    input_path: Path,
    root: Path = ROOT,
    *,
    nasa_input: Path | None = None,
    ablation_input: Path | None = None,
) -> list[str]:
    manifest = json.loads(input_path.read_text(encoding='utf-8'))
    rel_path = _rel_path(input_path, root)

    nasa_manifest = None
    nasa_rel = ''
    if nasa_input is not None and nasa_input.is_file():
        nasa_manifest = json.loads(nasa_input.read_text(encoding='utf-8'))
        nasa_rel = _rel_path(nasa_input, root)

    ablation_manifest = None
    ablation_rel = ''
    if ablation_input is not None and ablation_input.is_file():
        ablation_manifest = json.loads(ablation_input.read_text(encoding='utf-8'))
        ablation_rel = _rel_path(ablation_input, root)

    problems = []
    for filename, lang in (('README.md', 'zh'), ('README_EN.md', 'en')):
        path = root / filename
        text = path.read_text(encoding='utf-8')
        current = _extract_marker_block(text, BEGIN_MARKER, END_MARKER)
        if current is None:
            problems.append(f'{filename} 缺少 {BEGIN_MARKER} / {END_MARKER}')
        else:
            expected = _render_block(manifest, rel_path, lang=lang).strip('\r\n')
            if current.replace('\r\n', '\n') != expected.replace('\r\n', '\n'):
                problems.append(f'{filename} 基准表与 {rel_path} 不一致')

        if nasa_manifest is not None:
            cur_nasa = _extract_marker_block(text, NASA_BEGIN_MARKER, NASA_END_MARKER)
            if cur_nasa is None:
                problems.append(f'{filename} 缺少 {NASA_BEGIN_MARKER} / {NASA_END_MARKER}')
            else:
                exp_nasa = _render_nasa_block(nasa_manifest, nasa_rel, lang=lang).strip('\r\n')
                if cur_nasa.replace('\r\n', '\n') != exp_nasa.replace('\r\n', '\n'):
                    problems.append(f'{filename} NASA 泛化表与 {nasa_rel} 不一致')

        if ablation_manifest is not None:
            cur_abl = _extract_marker_block(text, ABLATION_BEGIN_MARKER, ABLATION_END_MARKER)
            if cur_abl is None:
                problems.append(f'{filename} 缺少 {ABLATION_BEGIN_MARKER} / {ABLATION_END_MARKER}')
            else:
                exp_abl = _render_ablation_block(ablation_manifest, ablation_rel, lang=lang).strip('\r\n')
                if cur_abl.replace('\r\n', '\n') != exp_abl.replace('\r\n', '\n'):
                    problems.append(f'{filename} 消融表与 {ablation_rel} 不一致')
    return problems


def render_benchmark_tables(
    input_path: Path | None = None,
    root: Path = ROOT,
    *,
    nasa_input: Path | None = None,
    ablation_input: Path | None = None,
) -> list[Path]:
    calce_manifest = json.loads(input_path.read_text(encoding='utf-8')) if input_path else None
    calce_rel = _rel_path(input_path, root) if input_path else ''
    nasa_manifest = json.loads(nasa_input.read_text(encoding='utf-8')) if nasa_input else None
    nasa_rel = _rel_path(nasa_input, root) if nasa_input else ''
    ablation_manifest = json.loads(ablation_input.read_text(encoding='utf-8')) if ablation_input else None
    ablation_rel = _rel_path(ablation_input, root) if ablation_input else ''

    updated = []
    for filename, lang in (('README.md', 'zh'), ('README_EN.md', 'en')):
        path = root / filename
        text = path.read_text(encoding='utf-8')
        new_text = text
        if calce_manifest is not None:
            block = _render_block(calce_manifest, calce_rel, lang=lang)
            new_text = _replace_marker_block(new_text, block, BEGIN_MARKER, END_MARKER)
        if nasa_manifest is not None:
            nasa_block = _render_nasa_block(nasa_manifest, nasa_rel, lang=lang)
            new_text = _replace_marker_block(new_text, nasa_block, NASA_BEGIN_MARKER, NASA_END_MARKER)
        if ablation_manifest is not None:
            abl_block = _render_ablation_block(ablation_manifest, ablation_rel, lang=lang)
            new_text = _replace_marker_block(new_text, abl_block, ABLATION_BEGIN_MARKER, ABLATION_END_MARKER)
        if new_text != text:
            path.write_text(new_text, encoding='utf-8')
            updated.append(path)
    return updated


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='从基准 JSON 渲染 README 表格')
    parser.add_argument('--input', type=Path, default=None, help='CALCE 基准 JSON 路径')
    parser.add_argument('--nasa-input', type=Path, default=None, help='NASA 泛化基准 JSON 路径')
    parser.add_argument('--ablation-input', type=Path, default=None, help='特征消融 JSON 路径')
    parser.add_argument('--check', action='store_true', help='校验 README 基准表是否与 JSON 一致')
    args = parser.parse_args(argv)

    input_path = args.input if args.input is not None else _find_latest(ROOT, 'results_*.json')
    nasa_path = args.nasa_input if args.nasa_input is not None else _find_latest(ROOT, 'nasa_*.json')
    ablation_path = args.ablation_input if args.ablation_input is not None else _find_latest(ROOT, 'ablation_*.json')

    if input_path is None and nasa_path is None and ablation_path is None:
        raise FileNotFoundError('未找到 benchmark/results_*.json、nasa_*.json 或 ablation_*.json')

    if args.check:
        problems = check_benchmark_tables(
            input_path, ROOT, nasa_input=nasa_path, ablation_input=ablation_path,
        )
        if problems:
            for p in problems:
                print(f'ERROR: {p}', file=sys.stderr)
            return 1
        print('README 基准表与 JSON 一致')
        return 0

    updated = render_benchmark_tables(
        input_path, ROOT, nasa_input=nasa_path, ablation_input=ablation_path,
    )
    for path in updated:
        print(f'已更新 {path.name}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
