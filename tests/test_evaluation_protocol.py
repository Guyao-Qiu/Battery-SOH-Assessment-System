import inspect
import importlib
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from core.preprocess import get_train_test
from core.train import train
from models.RF import train_rf
from models.XGBoost import train_xgboost


train_module = importlib.import_module("core.train")
preprocess_module = importlib.import_module("core.preprocess")


def _battery(capacity):
    return {
        "capacity": np.asarray(capacity, dtype=np.float32),
        "cycle": np.arange(len(capacity)),
        "health_indicator": np.asarray(capacity, dtype=np.float32),
        "capacity_raw": np.asarray(capacity, dtype=np.float32),
    }


class EvaluationIsolationTests(unittest.TestCase):
    def setUp(self):
        self.sentinel = 9876.5
        self.data = {
            "train_a": _battery(np.linspace(1.10, 0.92, 12)),
            "train_b": _battery(np.linspace(1.08, 0.90, 12)),
            "target": _battery([self.sentinel] * 12),
        }

    def test_target_battery_labels_never_enter_fold_training_data(self):
        train_x, train_y, _, _ = get_train_test(
            self.data, "target", window_size=3)

        self.assertNotIn(self.sentinel, train_x)
        self.assertNotIn(self.sentinel, train_y)

    def test_changing_target_early_labels_does_not_change_fold_training_data(self):
        first_x, first_y, _, _ = get_train_test(
            self.data, "target", window_size=3)
        changed = dict(self.data)
        changed["target"] = _battery(np.linspace(50.0, 40.0, 12))

        second_x, second_y, _, _ = get_train_test(
            changed, "target", window_size=3)

        np.testing.assert_array_equal(first_x, second_x)
        np.testing.assert_array_equal(first_y, second_y)

    def test_tree_trainers_require_a_validation_set_separate_from_test(self):
        for trainer in (train_xgboost, train_rf):
            with self.subTest(trainer=trainer.__name__):
                parameters = inspect.signature(trainer).parameters
                self.assertIn("val_x", parameters)
                self.assertIn("val_y", parameters)

    def test_multi_seed_primary_result_is_mean_not_test_best(self):
        per_seed = {
            10: ([10.0, 11.0], 3.0),
            11: ([40.0, 41.0], 1.0),
            12: ([90.0, 91.0], 2.0),
        }

        def fake_train_one(config, battery_dict, name, **kwargs):
            prediction, rmse = per_seed[kwargs["seed"]]
            metrics = {
                "rmse": rmse,
                "mae": rmse + 0.1,
                "r2": 1.0 - rmse / 10.0,
                "pearson": 0.9,
                "re": rmse / 10.0,
            }
            return prediction, metrics, {
                "protocol": "strict_zero_shot",
                "one_step_prediction": prediction,
                "recursive_prediction": [value - 0.2 for value in prediction],
                "one_step_metrics": {**metrics, "re": 0.99},
                "recursive_metrics": metrics,
                "rul_protocol": "recursive_future",
            }

        config = SimpleNamespace(
            window_size=1,
            mode="RNN",
            seed=10,
            n_seeds=3,
        )
        battery_dict = {"target": _battery([1.1, 1.0, 0.9, 0.8])}

        with patch.object(
                train_module, "_train_one_battery",
                side_effect=fake_train_one):
            results = train(config, battery_dict, ["target"])

        result = results["target"]
        self.assertAlmostEqual(result["score"], 2.0)
        self.assertAlmostEqual(result["detail"]["rmse"], 2.0)
        np.testing.assert_allclose(
            result["prediction"], [140.0 / 3.0, 143.0 / 3.0])
        self.assertIn("one_step_metrics", result["detail"])
        self.assertIn("recursive_metrics", result["detail"])
        self.assertEqual(
            result["detail"]["rul_protocol"], "recursive_future")
        self.assertAlmostEqual(
            result["detail"]["recursive_metrics"]["re"], 0.2)

    def test_train_checks_capacity_length_not_mapping_field_count(self):
        config = SimpleNamespace(
            window_size=1, mode="RNN", seed=1, n_seeds=1)
        battery_dict = {
            "target": {"capacity": np.asarray([1.1, 1.0, 0.9, 0.8])}}
        metrics = {
            "rmse": 0.1, "mae": 0.1, "r2": 0.9,
            "pearson": 0.95, "re": 0.2,
        }

        with patch.object(
                train_module, "_train_one_battery",
                return_value=([1.1, 1.0, 0.9, 0.8], metrics, {})) as fit:
            results = train(config, battery_dict, ["target"])

        fit.assert_called_once()
        self.assertEqual(list(results), ["target"])


class PredictionProtocolTests(unittest.TestCase):
    def test_one_step_and_recursive_future_use_distinct_history_rules(self):
        one_step = getattr(
            preprocess_module, "generate_one_step_predictions", None)
        recursive = getattr(
            preprocess_module, "generate_recursive_predictions", None)
        self.assertIsNotNone(one_step)
        self.assertIsNotNone(recursive)

        sequence = np.asarray([1.0, 2.0, 100.0, 200.0], dtype=np.float32)

        def predict_next(windows):
            windows = np.asarray(windows)
            return windows[:, -1] + 1.0

        one_truth, one_prediction = one_step(
            sequence, window_size=2, predict_batch=predict_next)
        recursive_truth, recursive_prediction = recursive(
            sequence, window_size=2, predict_batch=predict_next)

        np.testing.assert_allclose(one_truth, [100.0, 200.0])
        np.testing.assert_allclose(recursive_truth, one_truth)
        np.testing.assert_allclose(one_prediction, [3.0, 101.0])
        np.testing.assert_allclose(recursive_prediction, [3.0, 4.0])

    def test_protocol_result_has_separate_fields_and_rul_uses_recursive_path(self):
        evaluate_protocols = getattr(
            train_module, "evaluate_prediction_protocols", None)
        self.assertIsNotNone(evaluate_protocols)

        sequence = np.asarray(
            [1.0, 0.9, 0.85, 0.79, 0.70], dtype=np.float32)

        def predict_next(windows):
            windows = np.asarray(windows)
            return windows[:, -1] - 0.05

        result = evaluate_protocols(
            sequence=sequence,
            window_size=2,
            predict_batch=predict_next,
            rated_capacity=1.0,
            threshold_ratio=0.8,
        )

        self.assertEqual(set(result), {"one_step", "recursive", "rul_re"})
        self.assertIn("prediction", result["one_step"])
        self.assertIn("prediction", result["recursive"])
        self.assertEqual(
            result["recursive"]["metrics"]["re"], result["rul_re"])

    def test_readme_marks_existing_benchmark_as_old_protocol_result(self):
        readme = (Path(__file__).resolve().parents[1] / "README.md").read_text(
            encoding="utf-8")

        self.assertIn("旧方法结果", readme)
        self.assertIn("严格零样本跨电池评估", readme)

    def test_ui_failure_cycle_comes_from_recursive_future_prediction(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        from ui.main_window import MainWindow

        app = QApplication.instance() or QApplication([])
        window = MainWindow()
        window._eval_rated_capacity = 1.0
        window._eval_threshold_ratio = 0.8
        window.worker = SimpleNamespace(
            battery_list=["cell"],
            battery_dict={"cell": {"capacity": np.asarray(
                [1.0, 0.9, 0.88, 0.86], dtype=np.float32)}},
        )
        detail = {
            "battery": "cell",
            "recursive_prediction": [0.85, 0.75],
            "one_step_prediction": [0.88, 0.86],
        }
        results = {
            "cell": {
                "score": 0.1,
                "prediction": [1.0, 0.9, 0.88, 0.86],
                "detail": detail,
            }
        }

        try:
            with patch.object(window, "update_result_table"), \
                    patch.object(window.canvas, "plot_results"), \
                    patch.object(window, "_set_running_state"):
                window.on_result(results, 0.1)

            self.assertEqual(detail["failure_cycle"], 3)
            self.assertEqual(
                detail["failure_cycle_protocol"], "recursive_future")
        finally:
            window.deleteLater()
            app.processEvents()


if __name__ == "__main__":
    unittest.main()
