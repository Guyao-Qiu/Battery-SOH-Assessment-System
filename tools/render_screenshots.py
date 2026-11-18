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
    """构造 CS2_35 真实量纲演示结果（优先读取内置 CS2_35，缺失时用同量纲曲线兜底）。"""
    import numpy as np
    import pandas as pd

    rated, ratio = 1.1, 0.7
    cs35_dir = os.path.join(ROOT, 'dataset', 'CS2_35')
    data = None
    if os.path.isdir(cs35_dir):
        try:
            from core.dataload import load_battery_from_paths
            loaded_dict, _ = load_battery_from_paths(
                [cs35_dir], adapter_type='CALCE', outlier_mode='chunked')
            if 'CS2_35' in loaded_dict and len(loaded_dict['CS2_35']) > 100:
                data = {'CS2_35': loaded_dict['CS2_35']}
        except Exception:
            data = None

    if data is None:
        cycles = 896
        k = np.arange(cycles)
        progress = k / (cycles - 1)
        shape = 0.55 * progress + 0.45 * (
            np.exp(3.2 * progress) - 1) / (np.exp(3.2) - 1)
        rng = np.random.default_rng(1)
        capacity = rated - (rated - 0.30) * shape + rng.normal(0, 0.005, cycles)
        data = {
            'CS2_35': pd.DataFrame({
                'cycle': np.arange(1, cycles + 1),
                'capacity': capacity.astype(np.float32),
                'dq_v': (capacity * 0.55).astype(np.float32),
                'CCCT': (3000 - 1200 * shape).astype(np.float32),
                'CVCT': (1500 - 600 * shape).astype(np.float32),
                'resistance': (0.04 + 0.03 * shape).astype(np.float32),
            }),
        }

    nominal = data['CS2_35']['capacity'].to_numpy(dtype=np.float64)
    cycles = int(len(nominal))
    start = int(round(cycles * 0.6))
    forecast_arr = np.clip(nominal[start:] - 0.012, 0.15, rated * 1.1)
    forecast = forecast_arr.tolist()

    detail = {
        'battery': 'CS2_35', 'cycles': cycles, 'model': 'RF',
        'rmse': 0.0136, 'mae': 0.0071, 'r2': 0.9960, 'pearson': 0.9980,
        're': 0.052, 're_status': 'observed', 'n_seeds': 5,
        'persistence_blend': 0.72, 'rmse_skill_vs_persistence': 0.139,
        'primary_start_frac': 0.6, 'forecast_start': start,
        'forecast': forecast,
        'threshold': rated * ratio,
        'rolling_rows': [
            {'start_frac': 0.4, 'start': int(cycles * 0.4), 'battery': 'CS2_35',
             'rmse': 0.3052, 'mae': 0.2204, 'true_rul': 282, 'pred_rul': None,
             'rul_err': None, 'rul_rel_err': None, 'within_20pct': False,
             'status': 'pred_censored'},
            {'start_frac': 0.6, 'start': start, 'battery': 'CS2_35',
             'rmse': 0.2801, 'mae': 0.2159, 'true_rul': 103, 'pred_rul': 110,
             'rul_err': 7, 'rul_rel_err': 0.068, 'within_20pct': True,
             'status': 'ok'},
        ],
        'rolling': {
            'per_start': {
                0.4: {'n': 1, 'rmse': 0.3052, 'mae': 0.2204, 'detected': 0,
                      'needs_detection': 1, 'mean_abs_rul_err': None,
                      'skill': 0.045},
                0.6: {'n': 1, 'rmse': 0.2801, 'mae': 0.2159, 'detected': 1,
                      'needs_detection': 1, 'mean_abs_rul_err': 7.0,
                      'skill': 0.139},
            },
            'overall': {'n': 2, 'rmse': 0.2927, 'mae': 0.2182, 'detected': 1,
                        'needs_detection': 2, 'mean_abs_rul_err': 7.0,
                        'skill': 0.139},
        },
        'baselines': {'平推基线': {'rmse': 0.3254},
                      '线性外推': {'rmse': 0.1978},
                      '双指数': {'rmse': 0.3011}},
        'ci': {'rmse': {'mean': 0.0136, 'std': 0.0002,
                        'lower': 0.0133, 'upper': 0.0139}},
    }
    prediction = nominal[:start].tolist() + forecast
    return data, {battery: prediction for battery in data}, rated, ratio, detail


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
            window.select_mode(detail['model'])
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
