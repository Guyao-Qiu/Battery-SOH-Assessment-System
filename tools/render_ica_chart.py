#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""绘制代表电池（CALCE CS2_35）的 ICA 主峰随循环退化演化图。

默认输出到 ``assets/ica_peak_evolution.png``，配色遵循 ``theme_tokens.LIGHT``。
"""

from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path
import sys

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.adapters import _read_data_file, _read_data_sort_date  # noqa: E402
from core.dataload import load_battery_from_paths  # noqa: E402
from core.ica import compute_ica_curve  # noqa: E402
from core.validation import normalize_column_names  # noqa: E402
from theme_tokens import LIGHT  # noqa: E402
from utils.config import TrainConfig  # noqa: E402


def _configure_fonts() -> None:
    plt.rcParams['font.sans-serif'] = [
        'Microsoft YaHei', 'SimHei', 'Noto Sans CJK SC', 'DejaVu Sans',
    ]
    plt.rcParams['axes.unicode_minus'] = False


def _sample_ica_curves(battery_dir: Path, cc_step: int, discharge_step: int):
    files = sorted(glob.glob(str(battery_dir / '*.xlsx')), key=_read_data_sort_date)
    if not files:
        return []
    pick_indices = sorted({0, len(files) // 3, (2 * len(files)) // 3, max(0, len(files) - 2)})
    cycle_counter = 0
    curves = []
    target_set = set(pick_indices)
    captured_files = set()
    for f_idx, f_path in enumerate(files):
        df = _read_data_file(f_path)
        normalize_column_names(df)
        cyc_list = sorted(df['Cycle_Index'].unique())
        for c in cyc_list:
            g = df[df['Cycle_Index'] == c]
            is_d = g['Step_Index'].to_numpy() == discharge_step
            if int(np.sum(is_d)) <= 1:
                continue
            cycle_counter += 1
            if f_idx in target_set and f_idx not in captured_files:
                is_cc = g['Step_Index'].to_numpy() == cc_step
                if is_cc.any():
                    grid, dq_dv = compute_ica_curve(
                        g['Voltage(V)'].to_numpy(dtype=float)[is_cc],
                        g['Current(A)'].to_numpy(dtype=float)[is_cc],
                        g['Test_Time(s)'].to_numpy(dtype=float)[is_cc],
                    )
                    if len(grid) > 0:
                        curves.append((cycle_counter, grid, dq_dv))
                        captured_files.add(f_idx)
    return curves


def render_ica_chart(out_path: Path) -> Path:
    _configure_fonts()
    cfg = TrainConfig.from_dict(
        json.loads((ROOT / 'config.json').read_text(encoding='utf-8'))
    )
    battery_dir = ROOT / 'dataset' / 'CS2_35'
    battery_dict, _ = load_battery_from_paths(
        [str(battery_dir)],
        voltage_upper=cfg.voltage_upper,
        voltage_lower=cfg.voltage_lower,
        adapter_type='CALCE',
        cc_step=cfg.cc_step,
        cv_step=cfg.cv_step,
        discharge_step=cfg.discharge_step,
        outlier_mode=cfg.outlier_mode,
    )
    df = battery_dict['CS2_35']
    cycles = np.asarray(df['cycle'], dtype=np.float64)
    cap = np.asarray(df['capacity'], dtype=np.float64)
    peak_v = np.asarray(df['ica_peak_v'], dtype=np.float64)
    peak_h = np.asarray(df['ica_peak_h'], dtype=np.float64)
    peak_area = np.asarray(df['ica_peak_area'], dtype=np.float64)

    curves = _sample_ica_curves(battery_dir, cfg.cc_step, cfg.discharge_step)
    palette = LIGHT['chart_series']

    fig, (ax_left, ax_right) = plt.subplots(
        1, 2, figsize=(13.2, 5.0), dpi=160,
        facecolor=LIGHT['chart_bg'],
    )
    for ax in (ax_left, ax_right):
        ax.set_facecolor(LIGHT['chart_bg'])
        ax.grid(True, linestyle='--', linewidth=0.6, alpha=0.55, color=LIGHT['chart_grid'])
        for spine in ax.spines.values():
            spine.set_color(LIGHT['chart_spine'])
        ax.tick_params(colors=LIGHT['text'])

    # 左图：代表循环的 CC dQ/dV 曲线演化
    for idx, (cyc_num, grid, dq_dv) in enumerate(curves):
        color = palette[idx % len(palette)]
        ax_left.plot(
            grid, dq_dv,
            linewidth=2.0, color=color,
            label=f'第 {cyc_num} 循环',
        )
    ax_left.set_title('CS2_35 恒流充电 ICA (dQ/dV) 曲线演化', color=LIGHT['text'], fontsize=12, fontweight='bold')
    ax_left.set_xlabel('充电电压 (V)', color=LIGHT['text'])
    ax_left.set_ylabel('增量容量 dQ/dV (Ah/V)', color=LIGHT['text'])
    ax_left.legend(frameon=True, facecolor=LIGHT['bg_surface'], edgecolor=LIGHT['border_soft'], labelcolor=LIGHT['text'])

    # 右图：主峰高度 / 面积衰减 与 峰位电压右移
    m_h = np.isfinite(peak_h) & np.isfinite(cap)
    m_v = np.isfinite(peak_v) & np.isfinite(cap)
    m_a = np.isfinite(peak_area) & np.isfinite(cap)
    r_h = float(np.corrcoef(cap[m_h], peak_h[m_h])[0, 1]) if int(np.sum(m_h)) >= 2 else np.nan
    r_v = float(np.corrcoef(cap[m_v], peak_v[m_v])[0, 1]) if int(np.sum(m_v)) >= 2 else np.nan
    r_a = float(np.corrcoef(cap[m_a], peak_area[m_a])[0, 1]) if int(np.sum(m_a)) >= 2 else np.nan

    l1 = ax_right.plot(
        cycles[m_h], peak_h[m_h],
        color=palette[0], linewidth=1.6,
        label=f'主峰高度 H_peak (Ah/V, r={r_h:+.3f})',
    )
    l2 = ax_right.plot(
        cycles[m_a], peak_area[m_a] * 5.0,
        color=palette[2], linewidth=1.6, linestyle='--',
        label=f'主峰面积 5×A_peak (Ah, r={r_a:+.3f})',
    )
    ax_right.set_title('ICA 主峰特征随循环演化（CS2_35）', color=LIGHT['text'], fontsize=12, fontweight='bold')
    ax_right.set_xlabel('放电循环次数', color=LIGHT['text'])
    ax_right.set_ylabel('峰高 H_peak (Ah/V) / 5×峰面积 (Ah)', color=palette[0])

    ax_right2 = ax_right.twinx()
    ax_right2.spines['top'].set_visible(False)
    ax_right2.spines['right'].set_color(palette[1])
    ax_right2.tick_params(colors=palette[1])
    l3 = ax_right2.plot(
        cycles[m_v], peak_v[m_v],
        color=palette[1], linewidth=1.6, alpha=0.9,
        label=f'主峰位置 V_peak (V, r={r_v:+.3f})',
    )
    ax_right2.set_ylabel('主峰电压 V_peak (V)', color=palette[1])

    ax_right.set_ylim(0.5, 6.8)
    ax_right2.set_ylim(3.86, 4.24)
    lines = l1 + l2 + l3
    labels = [ln.get_label() for ln in lines]
    ax_right.legend(
        lines, labels, loc='upper center',
        frameon=True, facecolor=LIGHT['bg_surface'],
        edgecolor=LIGHT['border_soft'], labelcolor=LIGHT['text'],
        fontsize=9,
    )

    fig.tight_layout(pad=1.6)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=160, facecolor=fig.get_facecolor())
    plt.close(fig)
    return out_path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='生成 CS2_35 ICA 主峰演化图')
    parser.add_argument('--out', type=Path, default=ROOT / 'assets' / 'ica_peak_evolution.png')
    args = parser.parse_args(argv)
    out = render_ica_chart(args.out)
    print(f'ica_chart={out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
