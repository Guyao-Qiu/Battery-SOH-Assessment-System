import hashlib
import unittest
from unittest.mock import patch

import numpy as np
import torch
import torch.nn as nn

from core.model_persistence import train_model_on_all_data
from utils.config import TrainConfig


def _battery(values):
    return {"capacity": np.asarray(values, dtype=np.float32)}


def _data():
    return {
        "cell_a": _battery([1.00, 0.98, 0.96, 0.94, 0.92, 0.90]),
        "cell_b": _battery([1.10, 1.08, 1.06, 1.04, 1.02, 1.00]),
        "cell_c": _battery([9.90, 9.80, 9.70, 9.60, 9.50, 9.40]),
    }


def _config(mode):
    return TrainConfig(
        mode=mode,
        window_size=2,
        hidden_dim=4,
        epochs=2,
        rated_capacity=10.0,
        threshold_ratio=0.8,
        norm_method="minmax",
        device="cpu",
        seed=5,
        patience=1,
        n_estimators=2,
        max_depth=2,
        min_samples_leaf=1,
        max_features=1.0,
    )


class FinalAllBatteryTrainingTests(unittest.TestCase):
    def test_random_forest_final_fit_uses_every_valid_battery(self):
        fit_sizes = []

        class RecordingRF:
            def __init__(self, n_estimators, **kwargs):
                self.n_estimators = n_estimators

            def fit(self, x, y):
                fit_sizes.append(len(x))
                self.mean_ = float(np.mean(y))
                return self

            def predict(self, x):
                return np.full(len(x), self.mean_, dtype=np.float32)

        with patch(
                "sklearn.ensemble.RandomForestRegressor", RecordingRF):
            _, metadata = train_model_on_all_data(
                _config("RF"), _data(), ["cell_a", "cell_b", "cell_c"])

        self.assertEqual(fit_sizes[-1], 12)
        self._assert_complete_final_metadata(metadata)
        self.assertAlmostEqual(metadata["scaler"]["maximum"], 9.9, places=5)

    def test_xgboost_final_fit_uses_every_valid_battery(self):
        fit_calls = []

        class Booster:
            best_iteration = 0

        class RecordingXGB:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

            def fit(self, x, y, **kwargs):
                fit_calls.append({"size": len(x), "kwargs": kwargs})
                return self

            def get_booster(self):
                return Booster()

        with patch("xgboost.XGBRegressor", RecordingXGB):
            _, metadata = train_model_on_all_data(
                _config("XGBoost"), _data(),
                ["cell_a", "cell_b", "cell_c"])

        self.assertEqual(fit_calls[-1]["size"], 12)
        self.assertNotIn("eval_set", fit_calls[-1]["kwargs"])
        self._assert_complete_final_metadata(metadata)

    def test_recurrent_final_fit_uses_every_valid_battery(self):
        instances = []

        class RecordingNet(nn.Module):
            def __init__(self, hidden_dim, num_layers, mode):
                super().__init__()
                self.weight = nn.Parameter(torch.ones(1))
                self.training_batch_sizes = []
                instances.append(self)

            def forward(self, x):
                if self.training:
                    self.training_batch_sizes.append(len(x))
                return x[:, -1, :] * self.weight

        with patch("core.model_persistence.Net", RecordingNet):
            final_model, metadata = train_model_on_all_data(
                _config("RNN"), _data(),
                ["cell_a", "cell_b", "cell_c"])

        self.assertGreaterEqual(len(instances), 2)
        self.assertIs(final_model, instances[-1])
        self.assertIn(12, final_model.training_batch_sizes)
        self._assert_complete_final_metadata(metadata)

    def _assert_complete_final_metadata(self, metadata):
        self.assertEqual(metadata["final_training_sample_count"], 12)
        self.assertEqual(
            metadata["training_batteries"],
            ["cell_a", "cell_b", "cell_c"])
        self.assertEqual(set(metadata["battery_hashes"]),
                         {"cell_a", "cell_b", "cell_c"})
        self.assertRegex(metadata["data_hash"], r"^[0-9a-f]{64}$")
        self.assertNotEqual(metadata["data_hash"], hashlib.sha256(b"").hexdigest())
        self.assertIn("training_params", metadata)
        self.assertIn("library_versions", metadata)
        self.assertIn("feature_schema", metadata)
        self.assertIn("created_at", metadata)


if __name__ == "__main__":
    unittest.main()
