import inspect
import os
import unittest
from unittest.mock import patch


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class StartupSplashProgressTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication

        cls.app = QApplication.instance() or QApplication([])

    def test_progress_shows_percentage_and_current_loading_stage(self):
        from battery_soh_app import _StartupSplash

        self.assertIn("status", inspect.signature(
            _StartupSplash.set_progress).parameters)
        splash = _StartupSplash()
        try:
            splash.set_progress(42, "正在加载计算组件…")

            self.assertEqual(splash._progress.value(), 42)
            self.assertTrue(splash._progress.isTextVisible())
            self.assertEqual(splash._progress.format(), "%p%")
            self.assertEqual(splash._status_label.text(), "正在加载计算组件…")
        finally:
            splash._programmatic_close = True
            splash.close()
            splash.deleteLater()
            self.app.processEvents()


class EvaluationStartupFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication

        cls.app = QApplication.instance() or QApplication([])

    def test_start_evaluation_skips_deep_file_validation(self):
        from ui.main_window import MainWindow

        window = MainWindow()
        window.imported_paths = ["large-battery-folder"]
        started = []
        window._run_training = started.append

        try:
            with patch(
                    "core.validation.validate_evaluation_request",
                    return_value=[]) as deep_validation:
                window.start_evaluation()

            deep_validation.assert_not_called()
            self.assertEqual(len(started), 1)
        finally:
            window.deleteLater()
            self.app.processEvents()


if __name__ == "__main__":
    unittest.main()
