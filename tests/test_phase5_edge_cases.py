import unittest

import numpy as np

from core.evaluate import calc_all_metrics, relative_error_details
from core.preprocess import drop_outlier, filter_capacity_outliers


class Phase5OutlierBoundaryTests(unittest.TestCase):
    def test_nonfinite_points_are_removed_without_moving_finite_indices(self):
        values = np.asarray([1.1, np.nan, 1.0, np.inf, 0.9, -np.inf])

        result = filter_capacity_outliers(values, bins=6)

        np.testing.assert_array_equal(result.indices, [0, 2, 4])
        np.testing.assert_array_equal(result.removed_indices, [1, 3, 5])
        self.assertEqual(drop_outlier(values, len(values), 6).tolist(),
                         [0, 2, 4])
        self.assertTrue(all("非有限" in result.reasons[index]
                            for index in (1, 3, 5)))


class Phase5RelativeErrorBoundaryTests(unittest.TestCase):
    def test_normal_and_multiple_crossings_use_the_first_crossing(self):
        normal = relative_error_details(
            [1.0, 0.9, 0.79, 0.78],
            [1.0, 0.9, 0.85, 0.79],
            threshold=0.8,
        )
        repeated = relative_error_details(
            [1.0, 0.79, 0.82, 0.78],
            [1.0, 0.9, 0.79, 0.75],
            threshold=0.8,
        )

        self.assertEqual(normal["status"], "observed")
        self.assertEqual(normal["true_crossing_index"], 2)
        self.assertEqual(normal["predicted_crossing_index"], 3)
        self.assertAlmostEqual(normal["value"], 0.5)
        self.assertEqual(repeated["true_crossing_index"], 1)
        self.assertEqual(repeated["predicted_crossing_index"], 2)
        self.assertAlmostEqual(repeated["value"], 1.0)

    def test_no_crossing_initial_failure_and_truncation_are_explicit(self):
        both_censored = relative_error_details(
            [1.0, 0.9], [1.0, 0.85], threshold=0.8)
        initial = relative_error_details(
            [0.79, 0.75], [1.0, 0.7], threshold=0.8)
        prediction_censored = relative_error_details(
            [1.0, 0.79], [1.0, 0.9], threshold=0.8)

        self.assertEqual(both_censored["status"], "both_censored")
        self.assertIsNone(both_censored["value"])
        self.assertEqual(initial["status"], "observed_initial_failure")
        self.assertIsNone(initial["value"])
        self.assertEqual(prediction_censored["status"],
                         "prediction_censored")
        self.assertIsNone(prediction_censored["value"])


class Phase5MetricDegenerateInputTests(unittest.TestCase):
    def test_empty_mismatched_and_nonfinite_sequences_are_rejected_clearly(self):
        cases = (
            ([], [], "非空"),
            ([1.0], [1.0, 0.9], "长度"),
            ([1.0, np.nan], [1.0, 0.9], "有限"),
            ([1.0, 0.9], [1.0, np.inf], "有限"),
        )

        for truth, prediction, expected in cases:
            with self.subTest(expected=expected):
                with self.assertRaisesRegex(ValueError, expected):
                    calc_all_metrics(
                        truth, prediction,
                        rated_capacity=1.0, threshold_ratio=0.8)

    def test_short_and_constant_sequences_return_stable_metric_payloads(self):
        short = calc_all_metrics(
            [1.0], [0.9], rated_capacity=1.0, threshold_ratio=0.8)
        constant = calc_all_metrics(
            [1.0, 1.0, 1.0], [1.0, 1.0, 1.0],
            rated_capacity=1.0, threshold_ratio=0.8)

        self.assertAlmostEqual(short["rmse"], 0.1)
        self.assertAlmostEqual(short["mae"], 0.1)
        self.assertEqual(short["r2"], 0.0)
        self.assertEqual(short["pearson"], 0.0)
        self.assertEqual(short["re_status"], "both_censored")
        self.assertEqual(constant["rmse"], 0.0)
        self.assertEqual(constant["mae"], 0.0)
        self.assertEqual(constant["r2"], 1.0)
        self.assertEqual(constant["pearson"], 0.0)
        for key in ("rmse", "mae", "r2", "pearson"):
            self.assertTrue(np.isfinite(short[key]))
            self.assertTrue(np.isfinite(constant[key]))


if __name__ == "__main__":
    unittest.main()
