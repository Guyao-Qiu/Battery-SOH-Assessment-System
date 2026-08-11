import importlib
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from core.preprocess import CapacityScaler


predict_worker_module = importlib.import_module("ui.predict_worker")


class LastValueRegressor:
    def predict(self, windows):
        windows = np.asarray(windows, dtype=np.float32)
        return windows[:, -1] * 0.98


class LoadedModelMetricTests(unittest.TestCase):
    def setUp(self):
        scaler = CapacityScaler(
            method="minmax", rated_capacity=1.1).fit(
                [0.7, 0.8, 0.9, 1.0, 1.1])
        self.metadata = {
            "mode": "RF",
            "window_size": 3,
            "rated_capacity": 1.1,
            "scaler": scaler.to_dict(),
        }
        self.capacity = np.asarray(
            [1.10, 1.05, 1.00, 0.96, 0.91, 0.86, 0.81, 0.76],
            dtype=np.float32,
        )

    def test_loaded_prediction_uses_calc_all_metrics_and_protocol_fields(self):
        evaluate_sequence = getattr(
            predict_worker_module, "evaluate_loaded_sequence", None)
        self.assertIsNotNone(evaluate_sequence)

        prediction, detail = evaluate_sequence(
            LastValueRegressor(), self.metadata, self.capacity,
            threshold_ratio=0.8, device="cpu")

        self.assertEqual(len(prediction), len(self.capacity))
        for metric in ("rmse", "mae", "r2", "pearson", "re"):
            self.assertIn(metric, detail)
        self.assertIn("one_step_metrics", detail)
        self.assertIn("recursive_metrics", detail)
        self.assertEqual(detail["re"], detail["recursive_metrics"]["re"])

    def test_metric_summary_selects_requested_metric_or_all(self):
        summarize = getattr(
            predict_worker_module, "summarize_selected_metrics", None)
        self.assertIsNotNone(summarize)
        details = [
            {"rmse": 1.0, "mae": 2.0, "r2": 3.0,
             "pearson": 4.0, "re": 5.0},
            {"rmse": 3.0, "mae": 4.0, "r2": 5.0,
             "pearson": 6.0, "re": 7.0},
        ]

        expected = {
            "rmse": 2.0,
            "mae": 3.0,
            "r2": 4.0,
            "pearson": 5.0,
            "re": 6.0,
        }
        for metric, mean in expected.items():
            with self.subTest(metric=metric):
                self.assertEqual(
                    summarize(details, metric), {metric: mean})
        self.assertEqual(summarize(details, "all"), expected)

    def test_worker_runs_each_single_metric_and_all_without_key_error(self):
        config_base = dict(
            rated_capacity=1.1,
            threshold_ratio=0.8,
            device="cpu",
            voltage_upper=3.8,
            voltage_lower=3.4,
            adapter_type="CALCE",
            cc_step=2,
            cv_step=4,
            discharge_step=7,
        )
        battery_dict = {"cell": {"capacity": self.capacity}}

        for metric in ("rmse", "mae", "r2", "pearson", "re", "all"):
            with self.subTest(metric=metric):
                config = SimpleNamespace(**config_base, metric=metric)
                worker = predict_worker_module.PredictWorker(
                    LastValueRegressor(), self.metadata,
                    ["ignored"], config)
                results = []
                errors = []
                logs = []
                worker.result_signal.connect(
                    lambda named_results, elapsed:
                    results.append(named_results))
                worker.error_signal.connect(errors.append)
                worker.log_signal.connect(logs.append)

                with patch(
                        "core.dataload.load_battery_from_paths",
                        return_value=(battery_dict, ["cell"])):
                    worker.run()

                self.assertEqual(errors, [])
                self.assertEqual(len(results), 1)
                self.assertEqual(list(results[0]), ["cell"])
                detail = results[0]["cell"]["detail"]
                if metric == "all":
                    for label in ("RMSE", "MAE", "R²", "Pearson", "RE"):
                        self.assertTrue(any(label in line for line in logs))
                else:
                    expected_mean = detail[metric]
                    self.assertAlmostEqual(
                        results[0]["cell"]["score"], expected_mean)


if __name__ == "__main__":
    unittest.main()
