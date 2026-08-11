import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import torch

from core.model_persistence import save_model
from core.prediction import predict_capacity_batch
from core.preprocess import CapacityScaler
from models.rnn_model import Net


def _metadata():
    scaler = CapacityScaler(
        method="rated", rated_capacity=1.1).fit([0.7, 0.8, 0.9])
    return {
        "mode": "RNN",
        "model_type": "RNN",
        "window_size": 2,
        "hidden_dim": 4,
        "rated_capacity": 1.1,
        "threshold_ratio": 0.8,
        "scaler": scaler.to_dict(),
    }


class PredictionDeviceTests(unittest.TestCase):
    def test_recurrent_model_and_input_fall_back_to_same_available_device(self):
        class RecordingModel:
            def __init__(self):
                self.model_device = None
                self.input_device = None

            def to(self, device):
                self.model_device = str(torch.device(device))
                return self

            def eval(self):
                return self

            def __call__(self, tensor):
                self.input_device = str(tensor.device)
                return tensor[:, -1, :]

        model = RecordingModel()
        with patch.object(torch.cuda, "is_available", return_value=False):
            result = predict_capacity_batch(
                model, _metadata(), [[0.9, 0.8]], device="cuda")

        self.assertEqual(model.model_device, "cpu")
        self.assertEqual(model.input_device, "cpu")
        np.testing.assert_allclose(result, [0.8], rtol=1e-6)


class LoadedModelSessionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from ui.main_window import MainWindow
        self.window = MainWindow()

    def tearDown(self):
        self.window.deleteLater()
        self.app.processEvents()

    def test_failed_load_keeps_previous_model_and_metadata_together(self):
        previous_model = object()
        previous_metadata = {"mode": "RF", "window_size": 2}
        self.window.loaded_model = previous_model
        self.window.loaded_metadata = previous_metadata

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "broken.pt"
            path.write_bytes(b"broken")
            with self.assertRaises(ValueError):
                self.window.load_model_from_path(str(path))

        self.assertIs(self.window.loaded_model, previous_model)
        self.assertIs(self.window.loaded_metadata, previous_metadata)

    def test_successful_load_commits_pair_and_unload_returns_to_training(self):
        torch.manual_seed(13)
        model = Net(hidden_dim=4, num_layers=1, mode="RNN")
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "model.pt"
            save_model(model, _metadata(), str(path))

            self.window.load_model_from_path(str(path))

        self.assertIsNotNone(self.window.loaded_model)
        self.assertEqual(self.window.loaded_metadata["mode"], "RNN")
        self.assertTrue(self.window.unload_model_btn.isEnabled())

        self.window.unload_model()

        self.assertIsNone(self.window.loaded_model)
        self.assertIsNone(self.window.loaded_metadata)
        self.assertFalse(self.window.unload_model_btn.isEnabled())
        self.assertFalse(self.window.tcp_btn.isEnabled())


if __name__ == "__main__":
    unittest.main()
