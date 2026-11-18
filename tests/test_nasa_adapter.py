from pathlib import Path
import tempfile
import unittest

import numpy as np
from scipy.io import savemat

from core.adapters import NASAAdapter


def _write_nasa_struct(path: Path, key: str, cycles: list[dict]):
    payload = {key: {'cycle': np.asarray(cycles, dtype=object)}}
    savemat(str(path), payload)


class NasaAdapterRegressionTests(unittest.TestCase):
    def test_directory_with_multiple_mat_files_loads_separate_batteries(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'NASA'
            root.mkdir()
            for name, caps in (('B0005', [1.85, 1.80, 1.75]), ('B0006', [2.00, 1.95])):
                cycles = [
                    {
                        'type': 'discharge',
                        'data': {
                            'Capacity': np.array([[cap]], dtype=float),
                            'Voltage_measured': np.array([4.1, 3.8, 3.4, 2.8], dtype=float),
                            'Current_measured': np.array([-2.0, -2.0, -2.0, -2.0], dtype=float),
                            'Time': np.array([0.0, 300.0, 900.0, 1500.0], dtype=float),
                        },
                    }
                    for cap in caps
                ]
                _write_nasa_struct(root / f'{name}.mat', name, cycles)

            batteries, names = NASAAdapter().load_battery_data(
                [str(root)], 3.8, 3.4, None, None, None,
                log_callback=None, stop_flag=lambda: False,
            )

        self.assertEqual(names, ['B0005', 'B0006'])
        self.assertEqual(list(batteries['B0005']['capacity']), [1.85, 1.80, 1.75])
        self.assertEqual(list(batteries['B0006']['capacity']), [2.00, 1.95])

    def test_charge_cc_cv_split_does_not_confuse_dqv_window_with_cutoff(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'B0005.mat'
            # 0~2000s 从 3.5V 线性充至 4.2V (CC)；2000~3000s 保持 4.2V (CV)
            t_cc = np.linspace(0.0, 2000.0, 21)
            v_cc = np.linspace(3.5, 4.2, 21)
            t_cv = np.linspace(2100.0, 3000.0, 10)
            v_cv = np.full(10, 4.2)
            cycles = [
                {
                    'type': 'charge',
                    'data': {
                        'Time': np.concatenate([t_cc, t_cv]),
                        'Voltage_measured': np.concatenate([v_cc, v_cv]),
                    },
                },
                {
                    'type': 'discharge',
                    'data': {
                        'Capacity': np.array([[1.85]], dtype=float),
                        'Voltage_measured': np.array([4.1, 3.8, 3.4, 2.8], dtype=float),
                        'Current_measured': np.array([-2.0, -2.0, -2.0, -2.0], dtype=float),
                        'Time': np.array([0.0, 300.0, 900.0, 1500.0], dtype=float),
                    },
                },
            ]
            _write_nasa_struct(path, 'B0005', cycles)

            # voltage_upper=3.8 是 dq_v 窗口上界，不应被误当成 4.2V 充电恒压切换阈值
            batteries, _ = NASAAdapter().load_battery_data(
                [str(path)], 3.8, 3.4, None, None, None,
                log_callback=None, stop_flag=lambda: False,
            )

        df = batteries['B0005']
        self.assertAlmostEqual(float(df['CCCT'].iloc[0]), 1900.0, delta=150.0)
        self.assertAlmostEqual(float(df['CVCT'].iloc[0]), 1100.0, delta=150.0)

    def test_dqv_ignores_post_discharge_voltage_rebound(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'B0005.mat'
            # 0~1000s 恒流 -2.0A 放电，电压 4.0 -> 2.7V；其中 3.8V 在 t=200s，3.4V 在 t=600s
            # (但故意让放电采样落在 3.42V，而 1000~1300s 静置回弹恰好精确经过 3.400V)
            t = np.array([0.0, 200.0, 400.0, 600.0, 800.0, 1000.0, 1100.0, 1200.0, 1300.0])
            v = np.array([4.0, 3.80, 3.60, 3.42, 3.00, 2.70, 3.10, 3.400, 3.55])
            i = np.array([-2.0, -2.0, -2.0, -2.0, -2.0, -2.0, 0.0, 0.0, 0.0])
            cycles = [{
                'type': 'discharge',
                'data': {
                    'Capacity': np.array([[0.556]], dtype=float),
                    'Voltage_measured': v,
                    'Current_measured': i,
                    'Time': t,
                },
            }]
            _write_nasa_struct(path, 'B0005', cycles)

            batteries, _ = NASAAdapter().load_battery_data(
                [str(path)], 3.8, 3.4, None, None, None,
                log_callback=None, stop_flag=lambda: False,
            )

        dq_v = float(batteries['B0005']['dq_v'].iloc[0])
        # 真实 3.8V -> 3.42V 放电容量差为 2.0 * (600 - 200) / 3600 ≈ 0.222 Ah，
        # 若错误匹配静置回弹点 t=1200s 则会算出 ≈ 0.444 Ah
        self.assertLess(dq_v, 0.30)
        self.assertAlmostEqual(dq_v, 2.0 * 400.0 / 3600.0, places=3)


if __name__ == '__main__':
    unittest.main()
