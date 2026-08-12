from pathlib import Path
import tempfile
import unittest

import numpy as np

from core.model_persistence import load_model, save_model, train_model_on_all_data
from core.prediction import predict_capacity_batch
from utils.config import TrainConfig


class ModelArtifactSmokeTests(unittest.TestCase):
    def test_all_five_models_train_save_load_and_predict(self):
        battery_dict = {
            "cell_a": {"capacity": np.asarray(
                [1.10, 1.08, 1.06, 1.04, 1.02, 1.00], dtype=np.float32)},
            "cell_b": {"capacity": np.asarray(
                [1.09, 1.07, 1.05, 1.03, 1.01, 0.99], dtype=np.float32)},
            "cell_c": {"capacity": np.asarray(
                [1.08, 1.06, 1.04, 1.02, 1.00, 0.98], dtype=np.float32)},
        }
        names = list(battery_dict)

        with tempfile.TemporaryDirectory() as temp_dir:
            for mode in ("RNN", "GRU", "LSTM", "XGBoost", "RF"):
                with self.subTest(mode=mode):
                    config = TrainConfig(
                        mode=mode,
                        window_size=2,
                        hidden_dim=4,
                        epochs=2,
                        rated_capacity=1.1,
                        threshold_ratio=0.8,
                        norm_method="minmax",
                        device="cpu",
                        seed=17,
                        patience=1,
                        n_estimators=2,
                        learning_rate=0.1,
                        max_depth=2,
                        min_samples_leaf=1,
                        max_features=1.0,
                    )
                    model, metadata = train_model_on_all_data(
                        config, battery_dict, names)
                    expected = predict_capacity_batch(
                        model, metadata, [[1.02, 1.00]])
                    suffix = ".pt" if mode in ("RNN", "GRU", "LSTM") else ".joblib"
                    path = Path(temp_dir) / f"{mode}{suffix}"
                    save_model(model, metadata, str(path))
                    loaded_model, loaded_metadata = load_model(
                        str(path), allow_unsafe_joblib=(suffix == ".joblib"))
                    prediction = predict_capacity_batch(
                        loaded_model, loaded_metadata, [[1.02, 1.00]])

                    self.assertEqual(loaded_metadata["mode"], mode)
                    self.assertEqual(
                        loaded_metadata["final_training_sample_count"], 12)
                    self.assertEqual(prediction.shape, (1,))
                    self.assertTrue(np.isfinite(prediction[0]))
                    np.testing.assert_allclose(
                        prediction, expected, rtol=1e-6, atol=1e-6)


if __name__ == "__main__":
    unittest.main()
