import importlib
import inspect
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from utils.config import TrainConfig


validation = importlib.import_module("core.validation")


def _valid_calce_frame(cycle_count=4):
    rows = []
    base = pd.Timestamp("2026-01-01 00:00:00")
    for cycle in range(1, cycle_count + 1):
        for offset, seconds in enumerate((0.0, 3600.0)):
            rows.append({
                "Date_Time": base + pd.Timedelta(hours=len(rows)),
                "Cycle_Index": cycle,
                "Step_Index": 7,
                "Voltage(V)": 4.0 - offset,
                "Current(A)": -1.0,
                "Test_Time(s)": seconds,
            })
    return pd.DataFrame(rows)


class EvaluationParameterValidationTests(unittest.TestCase):
    def test_rejects_invalid_voltage_steps_capacity_threshold_and_window(self):
        validate_config = getattr(validation, "validate_training_config", None)
        self.assertIsNotNone(validate_config)
        config = TrainConfig(
            voltage_upper=3.2,
            voltage_lower=3.4,
            cc_step=2,
            cv_step=2,
            discharge_step=2,
            rated_capacity=float("nan"),
            threshold_ratio=0.01,
            window_size=0,
        )

        errors = validate_config(config)

        joined = "\n".join(errors)
        self.assertIn("上电压", joined)
        self.assertIn("工步", joined)
        self.assertIn("额定容量", joined)
        self.assertIn("阈值", joined)
        self.assertIn("窗口", joined)


class CalceDataValidationTests(unittest.TestCase):
    def test_valid_frame_requires_more_discharge_cycles_than_window(self):
        validate_frame = getattr(validation, "validate_calce_dataframe", None)
        self.assertIsNotNone(validate_frame)
        valid = _valid_calce_frame(cycle_count=4)

        self.assertEqual(
            validate_frame(
                valid, discharge_step=7, window_size=3,
                rated_capacity=1.1), [])
        errors = validate_frame(
            valid, discharge_step=7, window_size=4,
            rated_capacity=1.1)
        self.assertTrue(any("窗口" in error for error in errors))

    def test_rejects_duplicate_nonfinite_unordered_and_wrong_current_data(self):
        validate_frame = getattr(validation, "validate_calce_dataframe", None)
        self.assertIsNotNone(validate_frame)
        cases = {}

        duplicate = _valid_calce_frame()
        duplicate.insert(
            len(duplicate.columns), "VoltageCopy", duplicate["Voltage(V)"],
            allow_duplicates=True)
        duplicate.columns = [
            *duplicate.columns[:-1], "Voltage(V)"]
        cases["重复列"] = duplicate

        nonfinite = _valid_calce_frame()
        nonfinite.loc[0, "Voltage(V)"] = np.inf
        cases["有限"] = nonfinite

        time_reversed = _valid_calce_frame()
        time_reversed.loc[1, "Test_Time(s)"] = -1.0
        cases["时间"] = time_reversed

        cycle_reversed = _valid_calce_frame()
        cycle_reversed.loc[4:, "Cycle_Index"] = [1, 1, 3, 3]
        cases["循环"] = cycle_reversed

        charging_current = _valid_calce_frame()
        charging_current["Current(A)"] = 1.0
        cases["电流"] = charging_current

        unreasonable_capacity = _valid_calce_frame()
        unreasonable_capacity.loc[
            unreasonable_capacity["Test_Time(s)"] > 0,
            "Test_Time(s)"] = 36000.0
        cases["容量"] = unreasonable_capacity

        for expected, frame in cases.items():
            with self.subTest(expected=expected):
                errors = validate_frame(
                    frame, discharge_step=7, window_size=3,
                    rated_capacity=1.1)
                self.assertTrue(
                    any(expected in error for error in errors), errors)

    def test_file_validator_exposes_resource_and_adapter_limits(self):
        signature = inspect.signature(validation.validate_imported_item)
        for name in (
                "adapter_type", "window_size", "rated_capacity",
                "max_file_bytes", "max_rows", "max_columns",
                "max_sheets", "max_structure_depth"):
            with self.subTest(name=name):
                self.assertIn(name, signature.parameters)

    def test_oversized_file_is_rejected_before_dataframe_read(self):
        validate_limits = getattr(
            validation, "validate_file_resource_limits", None)
        self.assertIsNotNone(validate_limits)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "large.csv"
            path.write_text("placeholder", encoding="utf-8")
            with patch.object(
                    validation.os.path, "getsize", return_value=101), patch(
                        "pandas.read_csv") as read_csv:
                errors = validate_limits(
                    str(path), max_file_bytes=100, max_sheets=32)

        self.assertTrue(any("大小" in error for error in errors), errors)
        read_csv.assert_not_called()


class NasaDataValidationTests(unittest.TestCase):
    def test_nasa_structure_uses_capacity_cycles_not_calce_columns(self):
        validate_structure = getattr(
            validation, "validate_nasa_structure", None)
        self.assertIsNotNone(validate_structure)
        structure = {
            "cycle": [
                {"type": "discharge", "data": {"Capacity": value}}
                for value in (1.1, 1.0, 0.9, 0.8)
            ]
        }

        errors = validate_structure(
            structure, window_size=3, rated_capacity=1.1,
            max_structure_depth=8)

        self.assertEqual(errors, [])

    def test_nasa_structure_rejects_excess_depth_and_bad_capacity(self):
        validate_structure = getattr(
            validation, "validate_nasa_structure", None)
        self.assertIsNotNone(validate_structure)
        too_deep = {"child": {"child": {"child": {"child": {}}}}}
        errors = validate_structure(
            too_deep, window_size=1, rated_capacity=1.1,
            max_structure_depth=3)
        self.assertTrue(any("深度" in error for error in errors), errors)

        bad_capacity = {
            "cycle": [
                {"type": "discharge", "data": {"Capacity": value}}
                for value in (1.1, np.inf, 20.0)
            ]
        }
        errors = validate_structure(
            bad_capacity, window_size=1, rated_capacity=1.1,
            max_structure_depth=8)
        joined = "\n".join(errors)
        self.assertIn("有限", joined)
        self.assertIn("容量", joined)


class MainWindowValidationGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_invalid_request_is_blocked_before_worker_starts(self):
        from ui.main_window import MainWindow
        window = MainWindow()
        window.imported_paths = ["not-read-because-config-is-invalid.csv"]
        window.voltage_upper_spin.setValue(3.4)
        window.voltage_lower_spin.setValue(3.4)
        started = []
        window._run_training = lambda: started.append(True)

        try:
            with patch("ui.main_window.show_message") as message:
                window.start_evaluation()
            self.assertEqual(started, [])
            self.assertTrue(message.called)
            self.assertIn("上电压", message.call_args.args[3])
        finally:
            window.deleteLater()
            self.app.processEvents()


if __name__ == "__main__":
    unittest.main()
