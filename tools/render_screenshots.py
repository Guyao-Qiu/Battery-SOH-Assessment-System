"""渲染 README 用的界面截图（浅色 / 深色两套主题）。

用法::

    python tools/render_screenshots.py            # 输出到 assets/screenshots/
    python tools/render_screenshots.py --out DIR

优先使用**原生窗口平台**（Windows 下 ``platform = windows``），这样截图与本机
真实界面完全一致；无显示环境时自动退回 ``offscreen``。

注意：``offscreen`` 平台插件不使用 Windows 字体引擎，``QFontDatabase`` 可能是
空的，中文会变成方框。``ui.fonts.install_fonts()`` 会显式注册系统中文字体，
所以两种平台下都能得到正确的中文渲染。
"""

import argparse
import os
import sys
import warnings

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
warnings.filterwarnings('ignore')

# 只在调用方没有指定时才使用 offscreen（例如 CI）。
os.environ.setdefault('MPLBACKEND', 'Agg')


def _pick_platform():
    """有显示器就用原生平台，否则 offscreen。"""
    if os.environ.get('QT_QPA_PLATFORM'):
        return os.environ['QT_QPA_PLATFORM']
    if sys.platform.startswith('win') or sys.platform == 'darwin':
        return None                      # 让 Qt 自己选原生平台
    if os.environ.get('DISPLAY'):
        return None
    return 'offscreen'


def _demo_run():
    """构造一份可复现的演示结果（合成电池 + 完整 details）。"""
    import numpy as np
    import pandas as pd

    cycles = 140
    k = np.arange(cycles)
    progress = k / (cycles - 1)
    shape = 0.55 * progress + 0.45 * (
        np.exp(3.2 * progress) - 1) / (np.exp(3.2) - 1)

    def frame(seed, rated, end):
        rng = np.random.default_rng(seed)
        capacity = rated - (rated - end) * shape + rng.normal(0, 0.008, cycles)
        return pd.DataFrame({
            'cycle': np.arange(1, cycles + 1),
            'capacity': capacity.astype(np.float32),
            'dq_v': (capacity * 0.55).astype(np.float32),
            'CCCT': (3000 - 1200 * shape).astype(np.float32),
            'CVCT': (1500 - 600 * shape).astype(np.float32),
            'resistance': (0.02 + 0.03 * shape).astype(np.float32),
        })

    rated, end = 2.0, 1.29
    data = {'CS2_35': frame(1, rated, end)}
    nominal = data['CS2_35']['capacity'].to_numpy(dtype=np.float64)
    start = 70
    forecast = (nominal[start:] - 0.02).tolist()

    detail = {
        'battery': 'CS2_35', 'cycles': cycles, 'model': 'RF',
        'rmse': 0.0312, 'mae': 0.0244, 'r2': 0.9812, 'pearson': 0.9906,
        're': 0.052, 're_status': 'observed', 'n_seeds': 5,
        'persistence_blend': 0.72, 'rmse_skill_vs_persistence': 0.842,
        'primary_start_frac': 0.5, 'forecast_start': start,
        'forecast': forecast,
        'forecast_band': (list(np.asarray(forecast) - 0.04),
                          list(np.asarray(forecast) + 0.04)),
        'threshold': rated * 0.7,
        'rolling_rows': [
            {'start_frac': 0.4, 'start': 56, 'battery': 'CS2_35',
             'rmse': 0.0402, 'mae': 0.0310, 'true_rul': 52, 'pred_rul': 55,
             'rul_err': 3, 'rul_rel_err': 0.058, 'within_20pct': True,
             'status': 'ok'},
            {'start_frac': 0.5, 'start': 70, 'battery': 'CS2_35',
             'rmse': 0.0312, 'mae': 0.0244, 'true_rul': 38, 'pred_rul': 40,
             'rul_err': 2, 'rul_rel_err': 0.053, 'within_20pct': True,
             'status': 'ok'},
        ],
        'rolling': {
            'per_start': {
                0.4: {'n': 2, 'rmse': 0.0402, 'mae': 0.0310, 'detected': 2,
                      'needs_detection': 2, 'mean_abs_rul_err': 3.0,
                      'skill': 0.81},
                0.5: {'n': 2, 'rmse': 0.0312, 'mae': 0.0244, 'detected': 2,
                      'needs_detection': 2, 'mean_abs_rul_err': 2.0,
                      'skill': 0.84},
            },
            'overall': {'n': 2, 'rmse': 0.0357, 'mae': 0.0277, 'detected': 2,
                        'needs_detection': 2, 'mean_abs_rul_err': 2.5,
                        'skill': 0.83},
        },
        'baselines': {'平推基线': {'rmse': 0.1966},
                      '线性外推': {'rmse': 0.1521},
                      '双指数': {'rmse': 0.1804}},
        'ci': {'rmse': {'mean': 0.0312, 'std': 0.0021,
                        'lower': 0.0285, 'upper': 0.0339}},
    }
    prediction = nominal[:start].tolist() + forecast
    return data, {battery: prediction for battery in data}, rated, 0.7, detail


def render(out_dir, width=1600, height=950):
    from PyQt6.QtWidgets import QApplication

    from ui.fonts import diagnostics, install_fonts
    from ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    install_fonts(app)
    info = diagnostics()
    print(f'平台={app.platformName()}  字体族={info["family_count"]}  '
          f'UI 字体={info["resolved"]["ui"]}  中文可用={info["cjk_ok"]}')
    if not info['cjk_ok']:
        print('⚠ 未找到可用的中文字体，截图可能出现方框', file=sys.stderr)

    data, prediction, rated, ratio, detail = _demo_run()
    os.makedirs(out_dir, exist_ok=True)
    written = []

    for mode, suffix in (('dark', 'dark'), ('light', 'light')):
        window = MainWindow()
        try:
            window.resize(width, height)
            window.apply_theme(mode)
            window.metric_combo.setCurrentText('RMSE')
            window.update_result_table([detail], elapsed=12.3)
            window.canvas.plot_results(
                ['CS2_35'], data, prediction, rated, ratio,
                details={'CS2_35': detail})
            window.show()
            app.processEvents()
            path = os.path.join(out_dir, f'main-{suffix}.png')
            window.grab().save(path)
            written.append(path)
            print(f'{suffix}: {window.width()}x{window.height()} -> {path} '
                  f'({os.path.getsize(path)} bytes)')
        finally:
            window.deleteLater()
            app.processEvents()
    return written


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--out', default=os.path.join(ROOT, 'assets', 'screenshots'),
        help='输出目录（默认 assets/screenshots）')
    parser.add_argument('--width', type=int, default=1600)
    parser.add_argument('--height', type=int, default=950)
    args = parser.parse_args()

    platform = _pick_platform()
    if platform:
        os.environ['QT_QPA_PLATFORM'] = platform
    render(args.out, args.width, args.height)


if __name__ == '__main__':
    main()
