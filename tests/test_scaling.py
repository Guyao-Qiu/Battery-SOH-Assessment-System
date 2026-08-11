import importlib
from pathlib import Path
import tempfile
import unittest

import numpy as np
import torch

from core.preprocess import prepare_leave_one_out_split
from core.model_persistence import (
    load_model,
    save_model,
    train_model_on_all_data,
)
from models.rnn_model import Net


preprocess_module = importlib.import_module("core.preprocess")
train_module = importlib.import_module("core.train")


def _battery(values):
    return {"capacity": np.asarray(values, dtype=np.float32)}


class CapacityScalerTests(unittest.TestCase):
    def test_three_scalers_apply_expected_formula_and_inverse(self):
        scaler_type = getattr(preprocess_module, "CapacityScaler", None)
        self.assertIsNotNone(scaler_type)
        values = np.asarray([1.0, 2.0, 3.0], dtype=np.float32)

        cases = {
            "rated": np.asarray([0.5, 1.0, 1.5]),
            "minmax": np.asarray([0.0, 0.5, 1.0]),
            "zscore": (values - 2.0) / np.std(values),
        }
        for method, expected in cases.items():
            with self.subTest(method=method):
                scaler = scaler_type(method=method, rated_capacity=2.0)
                scaler.fit(values)
                transformed = scaler.transform(values)
                np.testing.assert_allclose(transformed, expected, rtol=1e-6)
                np.testing.assert_allclose(
                    scaler.inverse_transform(transformed), values, rtol=1e-6)

    def test_scaler_fit_uses_training_batteries_only(self):
        scaler_type = getattr(preprocess_module, "CapacityScaler", None)
        self.assertIsNotNone(scaler_type)
        data = {
            "train_a": _battery([1.0, 2.0, 3.0, 4.0, 5.0]),
            "train_b": _battery([2.0, 3.0, 4.0, 5.0, 6.0]),
            "target": _battery([9999.0] * 5),
        }
        split = prepare_leave_one_out_split(
            data, "target", window_size=2)

        scaler = scaler_type(method="minmax").fit(split.training_values)

        self.assertEqual(scaler.maximum, 6.0)
        self.assertNotEqual(scaler.maximum, 9999.0)

    def test_scaler_metadata_round_trip_preserves_transform(self):
        scaler_type = getattr(preprocess_module, "CapacityScaler", None)
        self.assertIsNotNone(scaler_type)
        original = scaler_type(method="zscore").fit([0.7, 0.8, 0.9, 1.0])

        restored = scaler_type.from_dict(original.to_dict())

        np.testing.assert_allclose(
            restored.transform([0.75, 0.95]),
            original.transform([0.75, 0.95]),
        )


class SharedPredictionScalingTests(unittest.TestCase):
    def test_rnn_receives_scaled_tensor_and_returns_raw_capacity(self):
        scaler_type = getattr(preprocess_module, "CapacityScaler", None)
        prediction_module = importlib.import_module("core.prediction") if (
            Path(__file__).resolve().parents[1] / "core" / "prediction.py"
        ).exists() else None
        predict_batch = getattr(
            prediction_module, "predict_capacity_batch", None)
        self.assertIsNotNone(scaler_type)
        self.assertIsNotNone(predict_batch)

        class RecordingModel:
            def __init__(self):
                self.received = None

            def to(self, device):
                return self

            def __call__(self, tensor):
                self.received = tensor.detach().cpu().numpy().copy()
                return tensor[:, -1, :]

        windows = np.asarray([[1.0, 2.0, 3.0]], dtype=np.float32)
        for method in ("rated", "minmax", "zscore"):
            with self.subTest(method=method):
                scaler = scaler_type(method=method, rated_capacity=2.0).fit(
                    [1.0, 2.0, 3.0, 4.0])
                model = RecordingModel()
                metadata = {
                    "mode": "RNN",
                    "window_size": 3,
                    "scaler": scaler.to_dict(),
                }

                prediction = predict_batch(
                    model, metadata, windows, device="cpu")

                expected_tensor = scaler.transform(windows).reshape(1, 3, 1)
                np.testing.assert_allclose(model.received, expected_tensor)
                np.testing.assert_allclose(prediction, [3.0], rtol=1e-6)

    def test_saved_loaded_model_keeps_scaler_prediction_consistent(self):
        scaler_type = getattr(preprocess_module, "CapacityScaler", None)
        prediction_path = (
            Path(__file__).resolve().parents[1] / "core" / "prediction.py")
        prediction_module = importlib.import_module("core.prediction") if (
            prediction_path.exists()) else None
        predict_batch = getattr(
            prediction_module, "predict_capacity_batch", None)
        self.assertIsNotNone(scaler_type)
        self.assertIsNotNone(predict_batch)

        torch.manual_seed(7)
        model = Net(hidden_dim=4, num_layers=1, mode="RNN")
        scaler = scaler_type(method="minmax").fit([0.7, 0.8, 0.9, 1.0])
        metadata = {
            "mode": "RNN",
            "window_size": 3,
            "hidden_dim": 4,
            "rated_capacity": 1.1,
            "scaler": scaler.to_dict(),
        }
        windows = np.asarray([[0.9, 0.85, 0.8]], dtype=np.float32)
        before = predict_batch(model, metadata, windows, device="cpu")

        with tempfile.TemporaryDirectory() as temp_dir:
            path = str(Path(temp_dir) / "trusted_test_model.pt")
            save_model(model, metadata, path)
            loaded_model, loaded_metadata = load_model(path)
            after = predict_batch(
                loaded_model, loaded_metadata, windows, device="cpu")

        np.testing.assert_allclose(after, before, rtol=1e-6, atol=1e-6)

    def test_fold_training_records_scaler_fitted_without_target_battery(self):
        config_base = dict(
            window_size=2,
            hidden_dim=4,
            mode="RF",
            epochs=1,
            device="cpu",
            rated_capacity=2.0,
            threshold_ratio=0.8,
            seed=3,
            n_estimators=2,
            learning_rate=0.1,
            max_depth=3,
            subsample=1.0,
            colsample_bytree=1.0,
            min_samples_leaf=1,
            max_features=1.0,
            patience=2,
        )
        data = {
            "train_a": _battery([1.0, 1.1, 1.2, 1.3, 1.4, 1.5]),
            "train_b": _battery([1.2, 1.3, 1.4, 1.5, 1.6, 1.7]),
            "target": _battery([9999.0, 9998.0, 9997.0, 9996.0, 9995.0]),
        }

        for method in ("rated", "minmax", "zscore"):
            with self.subTest(method=method):
                config = type("Config", (), {
                    **config_base, "norm_method": method})()
                _, _, detail = train_module._train_one_battery(
                    config, data, "target", seed=3)

                self.assertIn("scaler", detail)
                self.assertEqual(detail["scaler"]["method"], method)
                self.assertLess(detail["scaler"]["maximum"], 10.0)

    def test_final_model_metadata_contains_fitted_scaler(self):
        config = type("Config", (), {
            "mode": "RF",
            "window_size": 2,
            "rated_capacity": 2.0,
            "seed": 3,
            "device": "cpu",
            "norm_method": "zscore",
            "n_estimators": 2,
            "max_depth": 3,
            "min_samples_leaf": 1,
            "max_features": 1.0,
            "patience": 2,
        })()
        data = {
            "train_a": _battery([1.0, 1.1, 1.2, 1.3, 1.4, 1.5]),
            "train_b": _battery([1.2, 1.3, 1.4, 1.5, 1.6, 1.7]),
        }

        _, metadata = train_model_on_all_data(
            config, data, ["train_a", "train_b"])

        self.assertIn("scaler", metadata)
        self.assertEqual(metadata["scaler"]["method"], "zscore")

    def test_tcp_prediction_calls_shared_scaler_path(self):
        tcp_module = importlib.import_module("ui.tcp_server")
        shared_predict = getattr(tcp_module, "predict_capacity_batch", None)
        self.assertIsNotNone(shared_predict)

        scaler = preprocess_module.CapacityScaler(
            method="minmax", rated_capacity=2.0).fit([1.0, 2.0, 3.0])
        metadata = {
            "mode": "RF",
            "window_size": 2,
            "scaler": scaler.to_dict(),
        }
        config = type("Config", (), {
            "rated_capacity": 2.0,
            "threshold_ratio": 0.4,
            "device": "cpu",
        })()
        worker = tcp_module.TCPServerWorker(
            object(), metadata, config, port=0)
        calls = []

        def stop_after_one(model, used_metadata, windows, device):
            calls.append((model, used_metadata, np.asarray(windows), device))
            worker._stop_requested = True
            return np.asarray([1.7])

        from unittest.mock import patch
        with patch.object(
                tcp_module, "predict_capacity_batch",
                side_effect=stop_after_one):
            worker._run_prediction(
                [2.0, 1.9], "RF", 2, 2.0, "cpu")

        self.assertEqual(len(calls), 1)
        self.assertIs(calls[0][1], metadata)
        np.testing.assert_allclose(calls[0][2], [[2.0, 1.9]])

    def test_legacy_tree_model_without_scaler_keeps_raw_input_contract(self):
        prediction_module = importlib.import_module("core.prediction")

        class ConstantRegressor:
            def predict(self, windows):
                return np.full(len(windows), 0.5, dtype=np.float32)

        metadata = {
            "mode": "RF",
            "window_size": 2,
            "rated_capacity": 2.0,
        }

        prediction = prediction_module.predict_capacity_batch(
            ConstantRegressor(), metadata, [[1.5, 1.4]], device="cpu")

        np.testing.assert_allclose(prediction, [0.5])


if __name__ == "__main__":
    unittest.main()
