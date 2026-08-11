import importlib
import importlib.util
import inspect
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

from core.train import _train_one_battery
from ui.worker import EvalWorker
from utils.config import TrainConfig, save_config
from utils.logger import setup_logger


paths_module = (
    importlib.import_module("utils.paths")
    if importlib.util.find_spec("utils.paths") else None
)


def _battery(values):
    return {"capacity": np.asarray(values, dtype=np.float32)}


class ProjectPathTests(unittest.TestCase):
    def test_runtime_paths_are_absolute_and_anchored_to_project(self):
        self.assertIsNotNone(paths_module)
        project_root = Path(__file__).resolve().parents[1]

        self.assertEqual(paths_module.PROJECT_ROOT, project_root)
        self.assertTrue(paths_module.CONFIG_FILE.is_absolute())
        self.assertEqual(paths_module.CONFIG_FILE, project_root / "config.json")
        self.assertEqual(paths_module.OUTPUTS_DIR, project_root / "outputs")
        self.assertEqual(paths_module.LOG_DIR, project_root / "outputs")

    def test_logger_default_no_longer_depends_on_current_directory(self):
        self.assertIsNotNone(paths_module)
        self.assertEqual(inspect.signature(setup_logger).parameters[
            "log_dir"].default, None)

    def test_config_save_failure_is_not_silently_swallowed(self):
        with patch("builtins.open", side_effect=PermissionError("denied")):
            with self.assertRaises(PermissionError):
                save_config({"mode": "RNN"})

    def test_main_window_reports_config_save_failure(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        from ui.main_window import MainWindow

        app = QApplication.instance() or QApplication([])
        window = MainWindow()
        try:
            with patch(
                    "ui.main_window.save_config",
                    side_effect=PermissionError("denied")), \
                    patch("ui.main_window.show_message") as message, \
                    patch.object(window.logger, "error") as log_error:
                try:
                    saved = window._save_persisted_config()
                except PermissionError as error:
                    self.fail(f"save failure escaped the UI handler: {error}")

            self.assertFalse(saved)
            message.assert_called_once()
            log_error.assert_called_once()
        finally:
            window.deleteLater()
            app.processEvents()


class ProgressContractTests(unittest.TestCase):
    def test_rnn_training_reports_battery_seed_epoch_and_elapsed(self):
        parameters = inspect.signature(_train_one_battery).parameters
        self.assertIn("progress_callback", parameters)

        config = TrainConfig(
            mode="RNN",
            window_size=1,
            hidden_dim=2,
            epochs=2,
            patience=2,
            rated_capacity=1.1,
            threshold_ratio=0.8,
            n_seeds=1,
            seed=7,
            device="cpu",
        )
        data = {
            "a": _battery([1.1, 1.05, 1.0, 0.95, 0.9, 0.85]),
            "b": _battery([1.12, 1.06, 1.01, 0.96, 0.91, 0.86]),
            "target": _battery([1.1, 1.04, 0.98, 0.92, 0.86, 0.8]),
        }
        events = []

        _train_one_battery(
            config,
            data,
            "target",
            seed=7,
            progress_callback=events.append,
        )

        epoch_events = [
            event for event in events if event["phase"] == "rnn_epoch"]
        self.assertEqual([event["epoch"] for event in epoch_events], [1, 2])
        self.assertTrue(all(event["battery"] == "target"
                            for event in epoch_events))
        self.assertTrue(all(event["seed"] == 7 for event in epoch_events))
        self.assertTrue(all(event["elapsed_seconds"] >= 0
                            for event in epoch_events))

    def test_worker_emits_real_stage_progress_events(self):
        worker = EvalWorker(TrainConfig(window_size=1), ["cell.csv"])
        events = []
        errors = []
        worker.progress_signal.connect(events.append)
        worker.error_signal.connect(errors.append)
        battery_dict = {
            "cell": _battery([1.1, 1.0, 0.9, 0.8]),
        }
        results = {
            "cell": {
                "score": 0.1,
                "prediction": [1.1, 1.0, 0.9, 0.8],
                "detail": {
                    "battery": "cell",
                    "cycles": 4,
                    "model": "RNN",
                    "rmse": 0.1,
                    "mae": 0.1,
                    "r2": 0.9,
                    "pearson": 0.9,
                    "re": None,
                    "n_seeds": 1,
                    "ci": {},
                },
            },
        }

        with patch(
                "ui.worker.load_battery_from_paths",
                return_value=(battery_dict, ["cell"])), \
                patch("ui.worker.train", return_value=results), \
                patch(
                    "core.model_persistence.train_model_on_all_data",
                    return_value=(object(), {"mode": "RNN"})):
            worker.run()

        self.assertEqual(errors, [])
        phases = [event["phase"] for event in events]
        self.assertEqual(
            phases,
            ["loading", "evaluation", "final_training", "complete"],
        )
        required = {
            "phase", "battery", "seed", "epoch",
            "current", "total", "elapsed_seconds",
        }
        self.assertTrue(all(set(event) == required for event in events))

    def test_main_window_renders_determinate_progress_context(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        from ui.main_window import MainWindow

        self.assertTrue(hasattr(MainWindow, "on_progress"))
        app = QApplication.instance() or QApplication([])
        window = MainWindow()
        event = {
            "phase": "rnn_epoch",
            "battery": "CS2_35",
            "seed": 7,
            "epoch": 2,
            "current": 2,
            "total": 10,
            "elapsed_seconds": 1.5,
        }
        try:
            window.on_progress(event)
            self.assertEqual(window.progress_bar.minimum(), 0)
            self.assertEqual(window.progress_bar.maximum(), 10)
            self.assertEqual(window.progress_bar.value(), 2)
            status = window.run_status_label.text()
            self.assertIn("CS2_35", status)
            self.assertIn("seed=7", status)
            self.assertIn("epoch=2", status)
            self.assertIn("1.5s", status)
        finally:
            window.deleteLater()
            app.processEvents()


if __name__ == "__main__":
    unittest.main()
