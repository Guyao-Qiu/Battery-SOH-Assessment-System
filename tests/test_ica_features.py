import tempfile
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

from core.adapters import CALCEAdapter, _build_battery_dataframe
from core.ica import compute_ica_curve, extract_cycle_ica
from core.preprocess import (
    feature_fill_values,
    fill_feature_frame,
    generate_one_step_predictions,
    generate_recursive_predictions,
)
from core.protocol import feature_frame, rolling_origin_eval
from utils.config import DEFAULT_FEATURES, TrainConfig, normalize_feature_list


def _synthetic_cc_charge(peak_v=3.85, peak_amp=1.2, sigma=0.04, base_slope=0.4,
                         v_start=3.45, v_end=4.20, n_pts=200, current=0.55):
    """构造解析 dQ/dV 已知的恒流充电 (V, I, t) 序列。"""
    v = np.linspace(v_start, v_end, n_pts, dtype=np.float64)
    from scipy.special import erf

    q = (
        base_slope * (v - v_start)
        + 0.5 * peak_amp * sigma * np.sqrt(2.0 * np.pi)
        * (erf((v - peak_v) / (np.sqrt(2.0) * sigma))
           - erf((v_start - peak_v) / (np.sqrt(2.0) * sigma)))
    )
    t = q * 3600.0 / current
    i = np.full_like(v, current)
    return v, i, t


class IcaFeatureTests(unittest.TestCase):
    def test_synthetic_voltage_curve_recovers_peak_location_height_and_area(self):
        v, i, t = _synthetic_cc_charge(peak_v=3.85, peak_amp=1.5, sigma=0.04)
        grid, dq_dv = compute_ica_curve(v, i, t)
        self.assertGreater(len(grid), 20)
        self.assertEqual(len(grid), len(dq_dv))

        pv, ph, pa = extract_cycle_ica(v, i, t)
        self.assertTrue(np.isfinite(pv) and np.isfinite(ph) and np.isfinite(pa))
        self.assertAlmostEqual(pv, 3.85, delta=0.015)
        self.assertAlmostEqual(ph, 1.5 + 0.4, delta=0.20)
        self.assertGreater(pa, 0.2)

    def test_missing_short_or_invalid_curves_return_nan(self):
        for v, i, t in (
            ([], [], []),
            (np.linspace(3.5, 4.2, 5), np.full(5, 0.5), np.arange(5) * 10.0),
            (np.linspace(3.90, 3.92, 40), np.full(40, 0.5), np.arange(40) * 10.0),
            (np.linspace(3.5, 4.2, 40), np.full(40, -0.5), np.arange(40) * 10.0),
            (np.full(30, np.nan), np.full(30, 0.5), np.arange(30) * 10.0),
        ):
            pv, ph, pa = extract_cycle_ica(v, i, t)
            self.assertTrue(np.isnan(pv))
            self.assertTrue(np.isnan(ph))
            self.assertTrue(np.isnan(pa))

    def test_calce_ica_extraction_is_strictly_causal_across_cycles(self):
        v1, i1, t1 = _synthetic_cc_charge(peak_v=3.85, peak_amp=1.5)
        v2, i2, t2 = _synthetic_cc_charge(peak_v=3.98, peak_amp=0.6)

        def make_cycle_df(cyc_idx, v, i, t, t_offset):
            cc = pd.DataFrame({
                'Cycle_Index': cyc_idx,
                'Step_Index': 2,
                'Test_Time(s)': t + t_offset,
                'Voltage(V)': v,
                'Current(A)': i,
                'Date_Time': '2020-01-01 00:00:00',
            })
            dis = pd.DataFrame({
                'Cycle_Index': cyc_idx,
                'Step_Index': 7,
                'Test_Time(s)': np.array([0.0, 100.0, 200.0]) + t_offset + t[-1] + 10.0,
                'Voltage(V)': np.array([4.1, 3.6, 3.2]),
                'Current(A)': np.array([-1.0, -1.0, -1.0]),
                'Date_Time': '2020-01-01 00:00:00',
            })
            return pd.concat([cc, dis], ignore_index=True)

        with tempfile.TemporaryDirectory() as tmp:
            p1 = Path(tmp) / 'c1.csv'
            make_cycle_df(1, v1, i1, t1, 0.0).to_csv(p1, index=False)
            d1, _ = CALCEAdapter().load_battery_data(
                [str(p1)], 3.8, 3.4, 2, 4, 7, None, None, outlier_mode='off',
            )
            df_only_1 = d1['c1']

            p2 = Path(tmp) / 'cell.csv'
            pd.concat([
                make_cycle_df(1, v1, i1, t1, 0.0),
                make_cycle_df(2, v2, i2, t2, 10000.0),
            ], ignore_index=True).to_csv(p2, index=False)
            d2, _ = CALCEAdapter().load_battery_data(
                [str(p2)], 3.8, 3.4, 2, 4, 7, None, None, outlier_mode='off',
            )
            df_both = d2['cell']

        for col in ('ica_peak_v', 'ica_peak_h', 'ica_peak_area'):
            self.assertAlmostEqual(
                float(df_only_1[col].iloc[0]),
                float(df_both[col].iloc[0]),
                places=10,
            )
        self.assertGreater(float(df_both['ica_peak_v'].iloc[1]), float(df_both['ica_peak_v'].iloc[0]))

    def test_downstream_multifeature_pipeline_handles_ica_nans_causally(self):
        n = 30
        df = _build_battery_dataframe(
            list(range(1, n + 1)),
            np.linspace(1.1, 0.7, n),
            np.linspace(0.5, 0.3, n),
            np.full(n, 0.05),
            np.full(n, 1500.0),
            np.full(n, 500.0),
            'SYNTH',
            None,
            outlier_mode='off',
            ica_peak_v=[np.nan, np.nan] + list(np.linspace(3.85, 4.05, n - 2)),
            ica_peak_h=[np.nan] + list(np.linspace(5.0, 2.0, n - 1)),
            ica_peak_area=[np.nan] * 3 + list(np.linspace(0.8, 0.2, n - 3)),
        )
        cols = ('capacity', 'ica_peak_v', 'ica_peak_h', 'ica_peak_area')
        fills = feature_fill_values(df, cols)
        filled = fill_feature_frame(df, cols=cols, fill_values=fills)
        self.assertFalse(np.isnan(filled.to_numpy()).any())
        # 前置 NaN 只能用训练集均值填充，不能回填后续第 3 周期的值
        self.assertAlmostEqual(float(filled['ica_peak_v'].iloc[0]), fills['ica_peak_v'], places=5)

        frame_np = feature_frame({'SYNTH': df}, 'SYNTH', cols, fill_values=fills)
        self.assertEqual(frame_np.shape, (n, 4))
        self.assertFalse(np.isnan(frame_np).any())

        def dummy_step(windows):
            arr = np.asarray(windows, dtype=np.float64)
            return arr[:, -1, 0] - 0.01

        t_one, p_one = generate_one_step_predictions(frame_np, 8, dummy_step)
        t_rec, p_rec = generate_recursive_predictions(frame_np, 8, dummy_step)
        rows = rolling_origin_eval(frame_np, 8, dummy_step, 0.77, starts=(0.5, 0.7))
        self.assertEqual(len(t_one), n - 8)
        self.assertEqual(len(p_one), n - 8)
        self.assertEqual(len(t_rec), n - 8)
        self.assertEqual(len(p_rec), n - 8)
        self.assertEqual(len(rows), 2)

    def test_feature_config_supports_ica_and_preserves_capacity_only_default(self):
        self.assertEqual(DEFAULT_FEATURES, ('capacity',))
        self.assertEqual(TrainConfig().feature_columns, ('capacity',))
        self.assertEqual(
            normalize_feature_list(('ica_peak_v', 'ica_peak_h', 'ica_peak_area')),
            ('capacity', 'ica_peak_v', 'ica_peak_h', 'ica_peak_area'),
        )


if __name__ == '__main__':
    unittest.main()
