import importlib
import os
import unittest
from unittest.mock import Mock, patch

from battery_soh_app import concise_startup_error
from ui.worker import EvalWorker
from utils.config import TrainConfig


worker_module = importlib.import_module("ui.worker")


class SafeLogPresentationTests(unittest.TestCase):
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

    def test_untrusted_log_text_is_rendered_literally_not_as_html(self):
        payload = '<img src="missing" onerror="boom">cell.xlsx'

        self.window.append_log(payload)

        self.assertIn(payload, self.window.log_text.toPlainText())
        self.assertNotIn("<img", self.window.log_text.toHtml().lower())

    def test_error_dialog_is_concise_while_local_log_keeps_full_detail(self):
        full_error = (
            '预测失败：坏数据\nTraceback (most recent call last):\n'
            '  File "C:/private/project/worker.py", line 12')

        with patch("ui.main_window.show_message") as message, \
                patch.object(self.window.logger, "error") as log_error:
            self.window.on_error(full_error)

        shown_text = message.call_args.args[3]
        self.assertIn("预测失败：坏数据", shown_text)
        self.assertNotIn("Traceback", shown_text)
        self.assertNotIn("C:/private", shown_text)
        log_error.assert_called_once_with(full_error)


class WorkerErrorBoundaryTests(unittest.TestCase):
    def test_worker_logs_traceback_locally_and_emits_concise_error(self):
        setup_logger = getattr(worker_module, "setup_logger", None)
        self.assertIsNotNone(setup_logger)
        logger = Mock()
        worker = EvalWorker(TrainConfig(), ["broken.csv"])
        errors = []
        worker.error_signal.connect(errors.append)

        with patch(
                "ui.worker.load_battery_from_paths",
                side_effect=RuntimeError("broken parser")), \
                patch("ui.worker.setup_logger", return_value=logger):
            worker.run()

        self.assertEqual(len(errors), 1)
        self.assertIn("broken parser", errors[0])
        self.assertNotIn("Traceback", errors[0])
        logger.exception.assert_called_once()


class StartupErrorBoundaryTests(unittest.TestCase):
    def test_startup_dialog_message_omits_traceback_and_local_paths(self):
        error = RuntimeError(
            "模块损坏\nTraceback (most recent call last):\n"
            '  File "C:/private/project/bootstrap.py", line 10'
        )

        message = concise_startup_error(error)

        self.assertIn("模块损坏", message)
        self.assertNotIn("Traceback", message)
        self.assertNotIn("C:/private", message)


if __name__ == "__main__":
    unittest.main()
