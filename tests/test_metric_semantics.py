import importlib
import importlib.util
import os
import unittest

from core.evaluate import calc_all_metrics, relative_error


evaluate_module = importlib.import_module("core.evaluate")
predict_worker_module = importlib.import_module("ui.predict_worker")
result_semantics_module = (
    importlib.import_module("core.result_semantics")
    if importlib.util.find_spec("core.result_semantics") else None
)


class RelativeErrorSemanticsTests(unittest.TestCase):
    def test_missing_threshold_crossing_is_censored_not_worst_case_one(self):
        self.assertIsNone(
            relative_error(
                [1.0, 0.95, 0.90],
                [1.0, 0.94, 0.89],
                threshold=0.8,
            )
        )

    def test_initial_failure_is_reported_as_undefined(self):
        self.assertIsNone(
            relative_error(
                [0.79, 0.78, 0.77],
                [0.79, 0.78, 0.77],
                threshold=0.8,
            )
        )

    def test_metric_payload_distinguishes_censoring_states(self):
        details = getattr(evaluate_module, "relative_error_details", None)
        self.assertIsNotNone(details)

        cases = [
            (
                [1.0, 0.9, 0.7], [1.0, 0.85, 0.75],
                "observed", 0.0,
            ),
            (
                [1.0, 0.9, 0.85], [1.0, 0.85, 0.75],
                "observed_censored", None,
            ),
            (
                [1.0, 0.9, 0.7], [1.0, 0.9, 0.85],
                "prediction_censored", None,
            ),
            (
                [1.0, 0.9, 0.85], [1.0, 0.9, 0.85],
                "both_censored", None,
            ),
            (
                [0.7, 0.6], [0.7, 0.6],
                "observed_initial_failure", None,
            ),
        ]
        for truth, prediction, status, value in cases:
            with self.subTest(status=status):
                result = details(truth, prediction, threshold=0.8)
                self.assertEqual(result["status"], status)
                self.assertEqual(result["value"], value)

        metrics = calc_all_metrics(
            [1.0, 0.9, 0.85],
            [1.0, 0.85, 0.75],
            rated_capacity=1.0,
            threshold_ratio=0.8,
        )
        self.assertIsNone(metrics["re"])
        self.assertEqual(metrics["re_status"], "observed_censored")


class FailureCycleSemanticsTests(unittest.TestCase):
    def test_failure_cycles_use_original_cycle_identifiers(self):
        self.assertIsNotNone(result_semantics_module)
        analyze = result_semantics_module.analyze_failure_cycles

        result = analyze(
            cycle_ids=[101, 105, 110, 120],
            measured=[1.0, 0.9, 0.79, 0.75],
            predicted=[1.0, 0.91, 0.84, 0.78],
            threshold=0.8,
        )

        self.assertEqual(result["measured_failure_cycle"], 110)
        self.assertEqual(result["predicted_failure_cycle"], 120)
        self.assertEqual(result["measured_failure_status"], "failed")
        self.assertEqual(result["predicted_failure_status"], "failed")

    def test_no_crossing_is_distinguished_from_predicted_failure(self):
        self.assertIsNotNone(result_semantics_module)
        analyze = result_semantics_module.analyze_failure_cycles

        result = analyze(
            cycle_ids=[10, 20, 30],
            measured=[1.0, 0.9, 0.85],
            predicted=[1.0, 0.85, 0.79],
            threshold=0.8,
        )

        self.assertIsNone(result["measured_failure_cycle"])
        self.assertEqual(
            result["measured_failure_status"], "not_observed")
        self.assertEqual(result["predicted_failure_cycle"], 30)
        self.assertEqual(result["predicted_failure_status"], "failed")


class MetricPresentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_unavailable_metric_has_safe_na_formatter_and_mean(self):
        formatter = getattr(
            importlib.import_module("ui.main_window"),
            "format_metric_value", None)
        mean_available = getattr(
            predict_worker_module, "mean_available_metric", None)
        self.assertIsNotNone(formatter)
        self.assertIsNotNone(mean_available)
        self.assertEqual(formatter(None), "N/A（截尾）")
        self.assertIsNone(mean_available([None, float("nan")]))
        self.assertEqual(mean_available([None, 0.2, 0.4]), 0.3)

    def test_ui_explains_ci_is_only_within_fold_seed_variation(self):
        from PyQt6.QtWidgets import QLabel
        main_window_module = importlib.import_module("ui.main_window")
        self.assertIsNotNone(getattr(
            main_window_module, "format_metric_value", None))
        MainWindow = main_window_module.MainWindow

        window = MainWindow()
        detail = {
            "battery": "cell",
            "cycles": 3,
            "model": "RNN",
            "rmse": 0.1,
            "mae": 0.08,
            "r2": 0.9,
            "pearson": 0.95,
            "re": None,
            "re_status": "observed_censored",
            "n_seeds": 3,
            "ci": {
                "rmse": {
                    "mean": 0.1,
                    "std": 0.01,
                    "lower": 0.08,
                    "upper": 0.12,
                },
            },
        }
        try:
            window.metric_combo.setCurrentText("全部")
            window.update_result_table([detail], elapsed=1.0)
            texts = [label.text() for label in
                     window.result_container.findChildren(QLabel)]
            self.assertTrue(any(
                "同一留一折" in text and "随机种子" in text
                for text in texts))
            self.assertIn("N/A（截尾）", texts)
        finally:
            window.deleteLater()
            self.app.processEvents()


if __name__ == "__main__":
    unittest.main()
