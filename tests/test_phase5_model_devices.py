from pathlib import Path
import json
import tempfile
import unittest

import numpy as np
import torch

from core.model_persistence import load_model, save_model
from core.prediction import predict_capacity_batch
from core.preprocess import CapacityScaler
from models.rnn_model import Net


def _metadata():
    scaler = CapacityScaler(
        method="rated", rated_capacity=1.1).fit([0.8, 0.9, 1.0, 1.1])
    return {
        "mode": "RNN",
        "model_type": "RNN",
        "window_size": 2,
        "hidden_dim": 3,
        "rated_capacity": 1.1,
        "threshold_ratio": 0.8,
        "scaler": scaler.to_dict(),
    }


class Phase5ModelDeviceTests(unittest.TestCase):
    def test_cpu_saved_model_loads_on_cpu_and_predicts(self):
        model = Net(hidden_dim=3, num_layers=1, mode="RNN").cpu()
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "cpu-model.pt"
            save_model(model, _metadata(), path)

            loaded, metadata = load_model(path)
            prediction = predict_capacity_batch(
                loaded, metadata, [[1.0, 0.9]], device="cpu")

        self.assertEqual(next(loaded.parameters()).device.type, "cpu")
        self.assertEqual(prediction.shape, (1,))
        self.assertTrue(np.isfinite(prediction[0]))

    def test_incompatible_format_version_is_rejected_before_weight_loading(self):
        model = Net(hidden_dim=3, num_layers=1, mode="RNN").cpu()
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "future-model.pt"
            save_model(model, _metadata(), path)
            sidecar = Path(f"{path}.meta.json")
            metadata = json.loads(sidecar.read_text(encoding="utf-8"))
            metadata["format_version"] = 999
            sidecar.write_text(
                json.dumps(metadata, ensure_ascii=False), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "格式版本"):
                load_model(path)

    @unittest.skipUnless(
        torch.cuda.is_available(), "CUDA hardware is not available")
    def test_real_cuda_prediction_moves_loaded_cpu_model_and_input_together(self):
        model = Net(hidden_dim=3, num_layers=1, mode="RNN").cpu()
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "cuda-compatible.pt"
            save_model(model, _metadata(), path)
            loaded, metadata = load_model(path)
            self.assertEqual(next(loaded.parameters()).device.type, "cpu")

            prediction = predict_capacity_batch(
                loaded, metadata, [[1.0, 0.9]], device="cuda")
            torch.cuda.synchronize()

        self.assertEqual(next(loaded.parameters()).device.type, "cuda")
        self.assertTrue(np.isfinite(prediction[0]))


if __name__ == "__main__":
    unittest.main()
