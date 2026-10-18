import unittest
import importlib
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from core.model_persistence import train_model_on_all_data
from core.prediction import predict_capacity_batch
import core.preprocess as preprocess_module


train_module = importlib.import_module("core.train")


def _battery(values):
    return {"capacity": np.asarray(values, dtype=np.float32)}


class PersistenceBlendTests(unittest.TestCase):
    def test_validation_fit_shrinks_a_harmful_model_to_persistence(self):
        fit_persistence_blend = getattr(
            preprocess_module, "fit_persistence_blend", None)
        self.assertIsNotNone(fit_persistence_blend)
        windows = np.asarray([
            [1.00, 0.99],
            [0.99, 0.98],
            [0.98, 0.97],
        ], dtype=np.float32)
        truth = np.asarray([0.98, 0.97, 0.96], dtype=np.float32)
        harmful_prediction = windows[:, -1] + 0.5

        blend = fit_persistence_blend(
            windows, truth, harmful_prediction)

        self.assertEqual(blend, 0.0)

    def test_shared_prediction_applies_persisted_blend(self):
        class HarmfulModel:
            def predict(self, windows):
                return windows[:, -1] + 0.5

        metadata = {
            "mode": "RF",
            "window_size": 2,
            "rated_capacity": 1.0,
            "persistence_blend": 0.0,
        }
        windows = np.asarray([[1.0, 0.9], [0.9, 0.8]], dtype=np.float32)

        prediction = predict_capacity_batch(
            HarmfulModel(), metadata, windows)

        np.testing.assert_allclose(prediction, windows[:, -1])

    def test_fold_calibration_uses_training_battery_validation_only(self):
        class HarmfulModel:
            """总是把预测推向窗口末值 + 0.5：明显劣于平推。"""

            def fit(self, x, y):
                return self

            def predict(self, windows):
                return windows[:, -1] + 0.5

        config = SimpleNamespace(
            window_size=2,
            hidden_dim=4,
            mode="RF",
            epochs=1,
            device="cpu",
            rated_capacity=1.0,
            threshold_ratio=0.8,
            norm_method="rated",
            seed=3,
            n_seeds=1,
            n_estimators=2,
            max_depth=2,
            min_samples_leaf=1,
            max_features=1.0,
            patience=1,
            feature_columns=("capacity",),
            inner_cv=False,
            to_dict=lambda: {},
        )
        data = {
            "train_a": _battery([1.00, 0.99, 0.98, 0.97, 0.96, 0.95]),
            "train_b": _battery([1.02, 1.01, 1.00, 0.99, 0.98, 0.97]),
            "target": _battery([9.0, 8.0, 7.0, 6.0, 5.0, 4.0]),
        }

        with patch("core.model_factory.RandomForestRegressor",
                   lambda **kwargs: HarmfulModel()):
            _, _, detail = train_module._train_one_battery(
                config, data, "target", seed=3)

        # 最初样式：不做 α 收缩标定，也不做滚动起点评估。
        self.assertNotIn("persistence_blend", detail)
        self.assertNotIn("rolling_rows", detail)
        # 头条指标回到一步预测，且模型输出不再被 α 压回平推。
        np.testing.assert_allclose(
            detail["one_step_prediction"], [8.5, 7.5, 6.5, 5.5])
        self.assertEqual(detail["one_step_metrics"]["rmse"], 0.0)
        self.assertEqual(detail["rul_protocol"], "recursive_future")

    def test_final_model_does_not_shrink_to_persistence(self):
        class RecordingRF:
            def __init__(self, n_estimators, **kwargs):
                self.n_estimators = n_estimators

            def fit(self, x, y):
                return self

            def predict(self, x):
                return x[:, -1] + 0.5

        config = SimpleNamespace(
            mode="RF",
            window_size=2,
            rated_capacity=1.0,
            threshold_ratio=0.8,
            norm_method="rated",
            seed=3,
            device="cpu",
            n_estimators=2,
            max_depth=2,
            min_samples_leaf=1,
            max_features=1.0,
            patience=1,
            to_dict=lambda: {},
        )
        data = {
            "cell_a": _battery([1.00, 0.99, 0.98, 0.97, 0.96, 0.95]),
            "cell_b": _battery([1.02, 1.01, 1.00, 0.99, 0.98, 0.97]),
        }

        with patch(
                "core.model_factory.RandomForestRegressor", RecordingRF):
            _, metadata = train_model_on_all_data(
                config, data, ["cell_a", "cell_b"])

        # 最初样式：模型输出原样使用，不再向平推收缩。
        self.assertIn("persistence_blend", metadata)
        self.assertEqual(metadata["persistence_blend"], 1.0)


class CausalCleaningTests(unittest.TestCase):
    def test_future_values_cannot_change_an_earlier_filter_decision(self):
        prefix = np.asarray([0.0, 0.0, 0.0, 0.0, 0.0, 10.0])
        extended = np.concatenate((prefix, np.full(4, 10.0)))

        prefix_result = preprocess_module.filter_capacity_outliers(
            prefix, bins=10, protect_knees=False)
        extended_result = preprocess_module.filter_capacity_outliers(
            extended, bins=10, protect_knees=False)

        np.testing.assert_array_equal(
            prefix_result.mask, extended_result.mask[:len(prefix)])


if __name__ == "__main__":
    unittest.main()
