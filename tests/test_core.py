"""改进方案 E1：最小回归测试集。

覆盖方案里最关键的几条结论：

- 留一评估**不泄漏**（目标电池不进训练/验证/选择）；
- scaler 往返一致；
- 向量化滑窗与参考实现逐位相等；
- 右删失是**显式**状态，不能当成 0 或 −1；
- α 对无信息模型会坍缩（A3）；
- 滚动起点评估是**真正的未来预测**（A4）；
- TCP 解析拒绝畸形输入、RUL 计数正确（A10）；
- 主题 token 的对比度达标（C4）。
"""

import unittest

import numpy as np

from core.baselines import double_exp_forecast, linear_step, persistence_step
from core.evaluate import bootstrap_ci, relative_error_details
from core.preprocess import (
    CapacityScaler,
    FeatureScaler,
    build_instances,
    build_instances_fast,
    build_instances_mf,
    fit_persistence_blend,
    prepare_leave_one_out_split,
)
from core.protocol import (
    choose_blend_by_rollout,
    first_cross,
    recursive_forecast,
    rolling_origin_eval,
    skill_vs_persistence,
    summarize_rolling_rows,
)
from core.stream_protocol import forecast_eol, parse_message
from theme_tokens import THEMES, contrast


def _batteries():
    # 三块电池的容量取值范围互不重叠，任何泄漏都能被 isin 直接发现
    return {
        f'B{i}': {'capacity': (10.0 * i + np.linspace(2.0, 1.2, 60)).astype(
            np.float32)}
        for i in range(3)
    }


class LeakageTests(unittest.TestCase):
    def test_loo_split_has_no_target_leakage(self):
        data = _batteries()
        split = prepare_leave_one_out_split(data, 'B1', window_size=8)
        target_values = data['B1']['capacity']
        for array in (split.train_x, split.train_y, split.val_x, split.val_y):
            self.assertFalse(
                np.isin(array, target_values).any(),
                '目标电池的数据泄漏进了训练/验证集')
        self.assertTrue(np.isin(split.test_x, target_values).all())

    def test_changing_target_does_not_change_training_fold(self):
        data = _batteries()
        first = prepare_leave_one_out_split(data, 'B1', window_size=8)
        changed = dict(data)
        changed['B1'] = {'capacity': np.full(60, 999.0, dtype=np.float32)}
        second = prepare_leave_one_out_split(changed, 'B1', window_size=8)
        np.testing.assert_array_equal(first.train_x, second.train_x)
        np.testing.assert_array_equal(first.train_y, second.train_y)


class ScalerTests(unittest.TestCase):
    def test_capacity_scaler_roundtrip(self):
        values = np.linspace(1.2, 2.0, 50).astype(np.float32)
        for method in ('rated', 'zscore', 'minmax'):
            with self.subTest(method=method):
                scaler = CapacityScaler(method, 2.0).fit(values)
                self.assertTrue(np.allclose(
                    scaler.inverse_transform(scaler.transform(values)),
                    values, atol=1e-5))
                restored = CapacityScaler.from_dict(scaler.to_dict())
                self.assertTrue(np.allclose(
                    restored.transform(values), scaler.transform(values)))

    def test_feature_scaler_roundtrip(self):
        features = np.random.default_rng(0).normal(size=(20, 8, 3)).astype(
            np.float32)
        scaler = FeatureScaler().fit(features)
        restored = FeatureScaler.from_dict(scaler.to_dict())
        self.assertTrue(np.allclose(
            restored.transform(features), scaler.transform(features)))


class WindowTests(unittest.TestCase):
    def test_fast_windows_equal_reference(self):
        sequence = np.random.default_rng(0).normal(size=100).astype(np.float32)
        x0, y0 = build_instances(sequence, 16)
        x1, y1 = build_instances_fast(sequence, 16)
        self.assertTrue(np.array_equal(x0, x1))
        self.assertTrue(np.array_equal(y0, y1))

    def test_fast_windows_handle_short_input(self):
        x, y = build_instances_fast(np.arange(5, dtype=np.float32), 16)
        self.assertEqual(x.shape, (0, 16))
        self.assertEqual(y.shape, (0,))

    def test_multifeature_capacity_channel_matches_single_feature(self):
        import pandas as pd

        sequence = np.linspace(2.0, 1.2, 40)
        frame = pd.DataFrame({
            'capacity': sequence,
            'dq_v': sequence * 0.5,
            'CCCT': np.linspace(3000, 2000, 40),
        })
        x_single, y_single = build_instances(sequence.astype(np.float32), 8)
        x_multi, y_multi = build_instances_mf(frame, 8)
        self.assertEqual(x_multi.shape, (len(x_single), 8, 3))
        # 容量通道必须与单特征版逐位一致
        np.testing.assert_allclose(x_multi[:, :, 0], x_single)
        np.testing.assert_allclose(y_multi, y_single)

    def test_multifeature_fill_is_causal_only(self):
        import pandas as pd

        frame = pd.DataFrame({
            'capacity': np.linspace(2.0, 1.0, 30),
            'dq_v': [np.nan] * 5 + list(np.linspace(1.0, 0.5, 25)),
        })
        x, _ = build_instances_mf(frame, 4, cols=('capacity', 'dq_v'),
                                  fill_values={'capacity': 1.5, 'dq_v': 0.7})
        # 前向填充只用过去：第一个窗口里的 dq_v 应是训练统计量而非未来值
        self.assertEqual(x.shape[0], 26)
        self.assertTrue(np.isfinite(x).all())


class CensoringTests(unittest.TestCase):
    def test_first_cross_is_explicit_about_censoring(self):
        self.assertEqual(first_cross([2.0, 1.9, 1.5, 1.3], 1.4), 3)
        self.assertIsNone(first_cross([2.0, 1.9, 1.8], 1.4))

    def test_relative_error_distinguishes_censoring_states(self):
        self.assertIsNone(relative_error_details(
            [1.0, 0.95, 0.90], [1.0, 0.94, 0.89], 0.8)['value'])
        self.assertEqual(
            relative_error_details(
                [1.0, 0.95, 0.90], [1.0, 0.94, 0.89], 0.8)['status'],
            'both_censored')
        # 真实序列一开始就已低于阈值 → 初始失效（不是「误差 1.0」）
        self.assertEqual(
            relative_error_details(
                [0.79, 0.78, 0.77], [0.79, 0.78, 0.77], 0.8)['status'],
            'observed_initial_failure')


class BlendTests(unittest.TestCase):
    def test_blend_collapses_for_uninformative_model(self):
        rng = np.random.default_rng(1)
        last = np.linspace(2.0, 1.4, 200)
        windows = np.repeat(last[:, None], 8, axis=1).astype(np.float32)
        targets = (last - 0.003).astype(np.float32)
        noisy = (last + rng.normal(0, 0.05, 200)).astype(np.float32)
        self.assertLess(fit_persistence_blend(windows, targets, noisy), 0.2)

    def test_blend_by_rollout_collapses_a_harmful_model(self):
        data = {
            'a': {'capacity': np.linspace(2.0, 1.4, 120).astype(np.float32)},
        }

        def harmful(windows):
            # 明显劣于平推：把预测推向窗口末值 + 0.5
            return np.asarray(windows)[:, -1] + 0.5

        alpha, _ = choose_blend_by_rollout(harmful, data, ['a'], 8)
        self.assertLess(alpha, 0.2)

    def test_blend_by_rollout_keeps_a_helpful_model(self):
        data = {
            'a': {'capacity': np.linspace(2.0, 1.4, 120).astype(np.float32)},
        }

        def helpful(windows):
            return np.asarray(windows)[:, -1] - 0.005

        alpha, _ = choose_blend_by_rollout(helpful, data, ['a'], 8)
        self.assertGreater(alpha, 0.5)


class RollingOriginTests(unittest.TestCase):
    def test_rolling_eval_is_recursive_not_one_step(self):
        sequence = np.linspace(2.0, 1.0, 100)

        # 一个「一步很好、递归会漂移」的模型：预测值 = 窗口末值 + 0.05
        def drifting(windows):
            return np.asarray(windows)[:, -1] + 0.05

        rows = rolling_origin_eval(sequence, 8, drifting, 1.4)
        self.assertTrue(rows)
        for row in rows:
            self.assertEqual(row['start_frac'] in (0.4, 0.5, 0.6, 0.7), True)
            # 递归漂移会让 RMSE 明显大于 0.05
            self.assertGreater(row['rmse'], 0.05)

    def test_rolling_eval_reports_true_censoring(self):
        sequence = np.linspace(2.0, 1.9, 100)     # 永不失效
        rows = rolling_origin_eval(
            sequence, 8, lambda w: w[:, -1], 1.4)
        self.assertTrue(rows)
        self.assertTrue(all(row['status'] == 'true_censored' for row in rows))

    def test_skill_is_positive_for_a_model_better_than_persistence(self):
        sequence = np.linspace(2.0, 1.0, 200)

        def perfect(windows):
            window = np.asarray(windows)[0]
            slope = (window[-1] - window[0]) / (len(window) - 1)
            return np.asarray([window[-1] + slope])

        rows = rolling_origin_eval(sequence, 8, perfect, 1.4)
        baseline = {
            row['start_frac']: row['rmse']
            for row in rolling_origin_eval(
                sequence, 8, lambda w: w[:, -1], 1.4)
        }
        self.assertGreater(skill_vs_persistence(rows, baseline), 0.5)

    def test_summary_counts_batteries_not_seeds(self):
        rows = [
            {'start_frac': 0.5, 'start': 50, 'battery': 'a', 'rmse': 0.1,
             'mae': 0.1, 'true_rul': 10, 'pred_rul': 11, 'rul_err': 1,
             'status': 'ok'},
            {'start_frac': 0.5, 'start': 50, 'battery': 'b', 'rmse': 0.2,
             'mae': 0.2, 'true_rul': 10, 'pred_rul': 13, 'rul_err': 3,
             'status': 'ok'},
        ]
        summary = summarize_rolling_rows(rows)
        self.assertEqual(summary['overall']['n'], 2)
        self.assertAlmostEqual(summary['overall']['rmse'], 0.15)
        self.assertAlmostEqual(
            summary['overall']['mean_abs_rul_err'], 2.0)

    def test_bootstrap_ci_widens_with_fewer_batteries(self):
        mean, lo, hi = bootstrap_ci([0.1, 0.2, 0.3, 0.4])
        self.assertAlmostEqual(mean, 0.25)
        self.assertLess(lo, mean)
        self.assertGreater(hi, mean)
        # 单块电池无法给出区间
        single_mean, single_lo, single_hi = bootstrap_ci([0.3])
        self.assertEqual((single_mean, single_lo, single_hi), (0.3, 0.3, 0.3))
        # 全缺失不应崩溃
        nan_mean, _, _ = bootstrap_ci([None, float('nan')])
        self.assertTrue(np.isnan(nan_mean))


class BaselineTests(unittest.TestCase):
    def test_persistence_and_linear_steps(self):
        windows = np.asarray([[2.0, 1.9, 1.8]], dtype=np.float32)
        np.testing.assert_allclose(persistence_step(windows), [1.8])
        np.testing.assert_allclose(linear_step(windows), [1.7], atol=1e-6)

    def test_double_exp_never_explodes(self):
        history = np.linspace(2.0, 1.4, 60)
        future = double_exp_forecast(history, 200)
        self.assertEqual(len(future), 200)
        self.assertTrue(np.all(np.isfinite(future)))
        # 退化模型不应给出高于历史最大值的预测
        self.assertLessEqual(float(np.max(future)), 1.5 * float(np.max(history)))

    def test_recursive_forecast_uses_step_fn(self):
        forecast = recursive_forecast(
            lambda w: w[:, -1] - 0.1, np.full(4, 2.0), 3)
        np.testing.assert_allclose(forecast, [1.9, 1.8, 1.7], atol=1e-6)


class TcpProtocolTests(unittest.TestCase):
    def test_parser_rejects_malformed_input(self):
        for raw in (b'not json', b'[1]', b'{"capacity": "1.8"}',
                    b'{"capacity": NaN}', b'{"capacity": -1}',
                    b'{"capacity": 1e999}', b'[' * 3000, b'\xff',
                    b'{"capacity": true}', b'{}', b'null',
                    b'{"capacity": Infinity}', b'{"capacity": 1e400}'):
            with self.subTest(raw=raw[:30]):
                self.assertEqual(parse_message(raw, 2.0)[0], 'error')

    def test_parser_accepts_valid_sample_and_reset(self):
        self.assertEqual(parse_message(b'{"capacity": 1.83}', 2.0),
                         ('sample', 1.83))
        self.assertEqual(parse_message(b'{"reset": true}', 2.0),
                         ('reset', None))
        # 超出合理范围
        self.assertEqual(parse_message(b'{"capacity": 9.0}', 2.0)[0], 'error')

    def test_forecast_eol_counts_future_cycles(self):
        history = [1.9 - 0.01 * i for i in range(30)]
        rul, forecast = forecast_eol(
            history, 16, lambda w: w[:, -1] - 0.01, 1.4)
        self.assertEqual(rul, len(forecast))
        self.assertEqual(rul, 22)

    def test_forecast_eol_returns_none_when_never_crossing(self):
        history = [1.9 - 0.01 * i for i in range(30)]
        rul, forecast = forecast_eol(
            history, 16, lambda w: w[:, -1], 1.4, max_steps=50)
        self.assertIsNone(rul)
        self.assertEqual(len(forecast), 50)

    def test_forecast_eol_is_zero_when_already_failed(self):
        rul, forecast = forecast_eol(
            [1.0, 0.9, 0.8], 2, lambda w: w[:, -1], 1.4)
        self.assertEqual(rul, 0)
        self.assertEqual(forecast, [])


class ThemeTokenTests(unittest.TestCase):
    def test_body_text_meets_wcag_aa_in_both_themes(self):
        for name, tokens in THEMES.items():
            with self.subTest(theme=name):
                self.assertGreaterEqual(
                    contrast(tokens['text'], tokens['bg_base']), 4.5)
                self.assertGreaterEqual(
                    contrast(tokens['text_muted'], tokens['bg_elevated']), 4.5)
                self.assertGreaterEqual(
                    contrast(tokens['text_muted'], tokens['bg_hover']), 4.5)
                # 非文本（边框）需要 ≥ 3:1
                self.assertGreaterEqual(
                    contrast(tokens['border'], tokens['bg_deep']), 3.0)
                self.assertGreaterEqual(
                    contrast(tokens['border'], tokens['bg_surface']), 3.0)

    def test_chart_elements_are_visible_on_chart_background(self):
        for name, tokens in THEMES.items():
            with self.subTest(theme=name):
                for key in ('chart_measured', 'chart_forecast',
                            'chart_threshold'):
                    self.assertGreaterEqual(
                        contrast(tokens[key], tokens['chart_bg']), 3.0)

    def test_series_palette_is_visible_on_chart_background(self):
        for name, tokens in THEMES.items():
            with self.subTest(theme=name):
                for color in tokens['chart_series']:
                    self.assertGreaterEqual(
                        contrast(color, tokens['chart_bg']), 3.0)

    def test_themes_are_distinct(self):
        self.assertNotEqual(THEMES['light']['bg_base'],
                            THEMES['dark']['bg_base'])
        self.assertNotEqual(THEMES['light']['text'], THEMES['dark']['text'])


class FailureDebounceTests(unittest.TestCase):
    """A12：首次下穿即失效会被单点噪声误判，去抖应当可开启且向后兼容。"""

    #: 第 3 个循环起持续低于阈值
    SUSTAINED = [2.0, 1.9, 1.8, 1.39, 1.38, 1.37, 1.36, 1.35, 1.34, 1.33]
    #: 只有第 2 个循环单点下穿
    NOISY = [2.0, 1.9, 1.39, 1.8, 1.7, 1.6, 1.5, 1.45, 1.42, 1.41]

    def test_default_matches_the_legacy_first_crossing_semantics(self):
        for sequence in (self.SUSTAINED, self.NOISY, [2.0, 1.39],
                         [2.0, 1.9], [1.0]):
            with self.subTest(sequence=sequence):
                array = np.asarray(sequence)
                below = np.flatnonzero(array < 1.4)
                expected = int(below[0]) if len(below) else None
                self.assertEqual(first_cross(sequence, 1.4), expected)
                self.assertEqual(first_cross(sequence, 1.4, 1), expected)

    def test_debounce_ignores_a_single_noise_dip(self):
        self.assertEqual(first_cross(self.NOISY, 1.4, 3), None)
        # 关掉去抖就会误判 —— 这正是要修的行为
        self.assertEqual(first_cross(self.NOISY, 1.4, 1), 2)

    def test_debounce_reports_the_first_crossing_not_the_confirmation(self):
        for run in (2, 3, 4):
            with self.subTest(run=run):
                self.assertEqual(first_cross(self.SUSTAINED, 1.4, run), 3)

    def test_debounce_handles_short_and_never_crossing_sequences(self):
        self.assertIsNone(first_cross([2.0, 1.39], 1.4, 3))
        self.assertIsNone(first_cross([2.0, 1.9], 1.4, 3))
        self.assertIsNone(first_cross([], 1.4, 3))

    def test_only_one_failure_implementation_exists(self):
        from core.result_semantics import first_failure_index

        for sequence in (self.SUSTAINED, self.NOISY, [2.0, 1.9]):
            for run in (1, 3):
                with self.subTest(sequence=sequence, run=run):
                    self.assertEqual(
                        first_cross(sequence, 1.4, run),
                        first_failure_index(sequence, 1.4, run))

    def test_rolling_eval_honours_debounce(self):
        """滚动评估里的 true_rul 也必须按去抖后的判定来算。"""
        sequence = np.asarray(self.SUSTAINED * 12)  # 拉长到够多个起点
        step = lambda w: np.full(len(w), w[:, -1].mean())        # noqa: E731
        strict = rolling_origin_eval(sequence, 4, step, 1.4, starts=(0.5,))
        lenient = rolling_origin_eval(
            sequence, 4, step, 1.4, starts=(0.5,), debounce=1)
        self.assertEqual(strict[0]['true_rul'], lenient[0]['true_rul'])

    def test_config_normalises_debounce(self):
        from utils.config import TrainConfig

        self.assertEqual(TrainConfig().eol_debounce, 1)
        self.assertEqual(TrainConfig(eol_debounce=3).eol_debounce, 3)
        # 非法值回落到兼容默认
        for bad in (0, -2, None, 'x'):
            with self.subTest(value=bad):
                self.assertEqual(
                    TrainConfig(eol_debounce=bad).eol_debounce, 1)
        # 旧配置别名可读
        self.assertEqual(
            TrainConfig.from_dict({'failure_debounce': 3}).eol_debounce, 3)

    def test_seed_setup_reports_whether_it_was_strict(self):
        """A12：严格确定性必须如实返回，而不是悄悄假装已经确定。"""
        from utils.config import setup_seed

        result = setup_seed(3)
        self.assertIsInstance(result, bool)
        # 同一进程内重复设置不应抛异常
        self.assertIsInstance(setup_seed(3, deterministic=True), bool)


class OutlierModeTests(unittest.TestCase):
    """A12：离群点默认只标记不删除（容量再生是真实物理，不该被当成噪声删掉）。"""

    @staticmethod
    def _series():
        rng = np.random.default_rng(0)
        base = np.linspace(2.0, 1.3, 80)
        base[40] += 0.35        # 容量再生
        base[60] += 0.30        # 单点尖峰
        return base + rng.normal(0, 0.004, 80)

    def test_mark_mode_keeps_every_row(self):
        from core.preprocess import filter_capacity_outliers

        series = self._series()
        result = filter_capacity_outliers(series, bins=40, mode='mark')
        self.assertEqual(len(result.indices), len(series))
        self.assertEqual(result.removed_count, 0)
        self.assertTrue(np.allclose(series[result.indices], series))
        # 但可疑点确实被标记出来了
        self.assertGreater(result.marked_count, 0)
        self.assertEqual(result.mode, 'mark')

    def test_delete_mode_is_strictly_more_aggressive(self):
        from core.preprocess import filter_capacity_outliers

        series = self._series()
        marked = filter_capacity_outliers(series, bins=40, mode='mark')
        deleted = filter_capacity_outliers(series, bins=40, mode='delete')
        self.assertEqual(deleted.removed_count, marked.marked_count)
        self.assertEqual(len(deleted.indices),
                         len(series) - deleted.removed_count)
        self.assertEqual(deleted.mode, 'delete')

    def test_off_mode_detects_nothing(self):
        from core.preprocess import filter_capacity_outliers

        result = filter_capacity_outliers(self._series(), bins=40, mode='off')
        self.assertEqual(result.marked_count, 0)
        self.assertEqual(result.removed_count, 0)
        self.assertEqual(result.mode, 'off')

    def test_legacy_enabled_flag_still_maps_to_the_old_behaviour(self):
        from core.preprocess import filter_capacity_outliers

        series = self._series()
        self.assertEqual(
            filter_capacity_outliers(series, 40, True).removed_count,
            filter_capacity_outliers(series, 40, mode='delete').removed_count)
        self.assertEqual(
            filter_capacity_outliers(series, 40, False).marked_count,
            filter_capacity_outliers(series, 40, mode='off').marked_count)

    def test_unknown_mode_is_rejected(self):
        from core.preprocess import filter_capacity_outliers

        with self.assertRaises(ValueError):
            filter_capacity_outliers(self._series(), bins=40, mode='nope')

    def test_adapter_defaults_to_mark_and_reports_it(self):
        from core import adapters

        series = self._series().tolist()
        cycles = list(range(1, len(series) + 1))
        empty = [None] * len(series)
        frame = adapters._build_battery_dataframe(
            cycles, series, empty, empty, empty, empty, 'cell', None)
        audit = frame.attrs['outlier_audit']
        self.assertEqual(audit['mode'], 'mark')
        self.assertEqual(audit['kept_count'], len(series))
        self.assertEqual(audit['removed_count'], 0)
        self.assertEqual(audit['marked_count'], len(audit['marked_indices']))

    def test_adapter_legacy_flag_still_deletes(self):
        from core import adapters

        series = self._series().tolist()
        cycles = list(range(1, len(series) + 1))
        empty = [None] * len(series)
        frame = adapters._build_battery_dataframe(
            cycles, series, empty, empty, empty, empty, 'cell', None,
            clean_outliers=True)
        audit = frame.attrs['outlier_audit']
        self.assertEqual(audit['mode'], 'delete')
        self.assertLess(audit['kept_count'], len(series))


if __name__ == '__main__':
    unittest.main()
