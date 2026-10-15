import os
import unittest
from unittest.mock import patch


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _dispose_window(window, app):
    from matplotlib import pyplot as plt

    plt.close(window.canvas.fig)
    window.deleteLater()
    app.processEvents()


class StepSettingsUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication

        cls.app = QApplication.instance() or QApplication([])

    def test_step_parameters_are_manual_inputs_and_default_to_none(self):
        from PyQt6.QtGui import QValidator
        from PyQt6.QtWidgets import QLineEdit

        from ui.main_window import MainWindow

        with patch("ui.main_window.load_config", return_value={}):
            window = MainWindow()
        try:
            self.assertTrue(
                hasattr(window, "step_section"),
                "工步参数应有独立的“设置工步”下拉栏",
            )
            self.assertEqual(window.step_section.toggle.text(), "设置工步")
            self.assertFalse(window.step_section.toggle.isChecked())

            step_inputs = (
                window.cc_step_input,
                window.cv_step_input,
                window.discharge_step_input,
            )
            for step_input in step_inputs:
                self.assertIsInstance(step_input, QLineEdit)
                self.assertTrue(window.step_section.isAncestorOf(step_input))
                self.assertEqual(step_input.text(), "")
                self.assertEqual(step_input.placeholderText(), "无")
                state, _, _ = step_input.validator().validate("12", 2)
                self.assertEqual(state, QValidator.State.Acceptable)
                state, _, _ = step_input.validator().validate("abc", 3)
                self.assertEqual(state, QValidator.State.Invalid)

            config = window._build_config()
            self.assertIsNone(config.cc_step)
            self.assertIsNone(config.cv_step)
            self.assertIsNone(config.discharge_step)
        finally:
            _dispose_window(window, self.app)

    def test_imported_numeric_steps_round_trip_through_manual_inputs(self):
        from ui.main_window import MainWindow
        from utils.config import TrainConfig

        with patch("ui.main_window.load_config", return_value={}):
            window = MainWindow()
        config = TrainConfig(
            adapter_type="CALCE",
            cc_step=2,
            cv_step=4,
            discharge_step=7,
        )
        try:
            for name in (
                    "cc_step_input", "cv_step_input",
                    "discharge_step_input"):
                self.assertTrue(
                    hasattr(window, name),
                    "数字工步配置应由手动输入框承载",
                )
            window._apply_train_config(config)

            self.assertEqual(window.cc_step_input.text(), "2")
            self.assertEqual(window.cv_step_input.text(), "4")
            self.assertEqual(window.discharge_step_input.text(), "7")
            self.assertEqual(window._build_config(), config)
        finally:
            _dispose_window(window, self.app)

    def test_data_source_panel_stays_compact_after_steps_move_out(self):
        from PyQt6.QtWidgets import QGroupBox

        from ui.main_window import MainWindow

        with patch("ui.main_window.load_config", return_value={}):
            window = MainWindow()
        try:
            window.resize(1180, 700)
            window.show()
            self.app.processEvents()

            source_group = next(
                group for group in window.findChildren(QGroupBox)
                if group.title() == "数据源"
            )
            self.assertLessEqual(
                source_group.height(),
                100,
                "工步移出后，数据源区域不应继续占用四行参数的高度",
            )
        finally:
            _dispose_window(window, self.app)

    def test_nasa_steps_default_to_none_but_remain_user_editable(self):
        from ui.main_window import MainWindow

        saved_config = {
            "adapter_type": "NASA",
            "cc_step": None,
            "cv_step": None,
            "discharge_step": None,
        }
        with patch("ui.main_window.load_config", return_value=saved_config):
            window = MainWindow()
        try:
            step_inputs = (
                window.cc_step_input,
                window.cv_step_input,
                window.discharge_step_input,
            )
            self.assertTrue(
                all(step_input.isEnabled() for step_input in step_inputs),
                "工步即使当前数据格式不使用，也应允许用户自定义修改",
            )
            self.assertTrue(
                all(step_input.text() == "" for step_input in step_inputs))

            for step_input, value in zip(step_inputs, (3, 5, 108)):
                step_input.setText(str(value))

            config = window._build_config()
            self.assertEqual(
                (config.cc_step, config.cv_step, config.discharge_step),
                (3, 5, 108),
            )
        finally:
            _dispose_window(window, self.app)

    def test_invalid_or_blank_manual_step_text_maps_to_none(self):
        from ui.main_window import MainWindow

        with patch("ui.main_window.load_config", return_value={}):
            window = MainWindow()
        try:
            window.cc_step_input.setText("abc")
            window.cv_step_input.clear()
            window.discharge_step_input.setText("7")

            config = window._build_config()

            self.assertIsNone(config.cc_step)
            self.assertIsNone(config.cv_step)
            self.assertEqual(config.discharge_step, 7)
        finally:
            _dispose_window(window, self.app)


class StepSettingsValidationTests(unittest.TestCase):
    def test_training_config_defaults_to_no_step_selection(self):
        from utils.config import TrainConfig

        config = TrainConfig()

        self.assertIsNone(config.cc_step)
        self.assertIsNone(config.cv_step)
        self.assertIsNone(config.discharge_step)

    def test_calce_requires_selection_while_nasa_accepts_none(self):
        from core.validation import validate_training_config
        from utils.config import TrainConfig

        missing_steps = {
            "cc_step": None,
            "cv_step": None,
            "discharge_step": None,
        }

        calce_errors = validate_training_config(TrainConfig(
            adapter_type="CALCE", **missing_steps))
        nasa_errors = validate_training_config(TrainConfig(
            adapter_type="NASA", **missing_steps))

        self.assertTrue(
            any("设置工步" in error for error in calce_errors),
            calce_errors,
        )
        self.assertEqual(nasa_errors, [])


if __name__ == "__main__":
    unittest.main()
