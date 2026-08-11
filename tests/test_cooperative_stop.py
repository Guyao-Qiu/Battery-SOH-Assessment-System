import importlib
import inspect
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

import core.train as train_module
from core.model_persistence import train_model_on_all_data
from models.RF import train_rf
from models.XGBoost import train_xgboost
from ui.worker import EvalWorker
from utils.config import TrainConfig


cancellation = importlib.import_module("core.cancellation") if (
    Path(__file__).resolve().parents[1] / "core" / "cancellation.py"
).exists() else None


def _battery(values):
    return {"capacity": np.asarray(values, dtype=np.float32)}


def _data():
    return {
        "a": _battery([1.1, 1.0, 0.9, 0.8, 0.7, 0.6]),
        "b": _battery([1.2, 1.1, 1.0, 0.9, 0.8, 0.7]),
        "c": _battery([1.3, 1.2, 1.1, 1.0, 0.9, 0.8]),
    }


class WorkerInterruptionTests(unittest.TestCase):
    def test_worker_stop_sets_qthread_interruption_flag(self):
        worker = EvalWorker(TrainConfig(), [])
        self.assertFalse(worker.isInterruptionRequested())

        worker.request_stop()

        self.assertTrue(worker.isInterruptionRequested())
        self.assertTrue(worker.stop_requested())

    def test_training_entry_points_accept_stop_checkpoints(self):
        self.assertIn("stop_flag", inspect.signature(train_rf).parameters)
        self.assertIn("stop_flag", inspect.signature(train_xgboost).parameters)

    def test_cancelled_rnn_and_final_training_never_return_partial_results(self):
        self.assertIsNotNone(cancellation)
        cancelled = cancellation.TrainingCancelled
        config = TrainConfig(
            mode="RNN", window_size=2, hidden_dim=4, epochs=2,
            rated_capacity=1.3, norm_method="rated", device="cpu",
            n_seeds=1,
        )
        data = _data()

        with self.assertRaises(cancelled):
            train_module._train_one_battery(
                config, data, "c", stop_flag=lambda: True)
        with self.assertRaises(cancelled):
            train_model_on_all_data(
                config, data, list(data), stop_flag=lambda: True)


class MainWindowStopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from ui.main_window import MainWindow
        self.window = MainWindow()

    def tearDown(self):
        self.window.worker = None
        self.window.deleteLater()
        self.app.processEvents()

    def test_source_has_no_forced_qthread_termination(self):
        source = (
            Path(__file__).resolve().parents[1] / "ui" / "main_window.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn(".terminate(", source)

    def test_running_state_freezes_result_affecting_controls(self):
        self.window.final_trained_model = object()
        self.window.loaded_model = object()
        self.window._set_running_state(True, "运行中")

        for control in (
                self.window.import_btn, self.window.import_dir_btn,
                self.window.import_json_btn, self.window.delete_btn,
                self.window.import_list, self.window.load_model_btn,
                self.window.save_model_btn, self.window.unload_model_btn,
                self.window.export_btn, self.window.rnn_btn,
                self.window.feature_size_spin):
            with self.subTest(control=control.objectName() or type(control).__name__):
                self.assertFalse(control.isEnabled())
        self.assertTrue(self.window.pause_btn.isEnabled())

    def test_stop_timeout_keeps_worker_and_reports_instead_of_terminating(self):
        class SlowWorker:
            def __init__(self):
                self.stop_requested = False
                self.interruption_requested = False
                self.terminated = False

            def isRunning(self):
                return True

            def request_stop(self):
                self.stop_requested = True

            def requestInterruption(self):
                self.interruption_requested = True

            def wait(self, timeout):
                return False

            def terminate(self):
                self.terminated = True

        worker = SlowWorker()
        self.window.worker = worker
        self.window._set_running_state(True, "运行中")

        with patch("ui.main_window.show_message") as message:
            self.window.pause_evaluation()

        self.assertIs(self.window.worker, worker)
        self.assertTrue(worker.stop_requested)
        self.assertTrue(worker.interruption_requested)
        self.assertFalse(worker.terminated)
        self.assertTrue(message.called)
        self.assertFalse(self.window.start_btn.isEnabled())

    def test_close_timeout_ignores_close_event_and_preserves_running_worker(self):
        from PyQt6.QtGui import QCloseEvent

        class SlowWorker:
            def __init__(self):
                self.terminated = False

            def isRunning(self):
                return True

            def request_stop(self):
                pass

            def requestInterruption(self):
                pass

            def wait(self, timeout):
                return False

            def terminate(self):
                self.terminated = True

        worker = SlowWorker()
        self.window.worker = worker
        event = QCloseEvent()
        with patch("ui.main_window.show_message") as message:
            self.window.closeEvent(event)

        self.assertFalse(event.isAccepted())
        self.assertIs(self.window.worker, worker)
        self.assertFalse(worker.terminated)
        self.assertTrue(message.called)


if __name__ == "__main__":
    unittest.main()
