from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd
from scipy.io import savemat

from core.adapters import CALCEAdapter, NASAAdapter
from core.validation import validate_imported_item


def _calce_rows(cycles=5, start_capacity=1.1):
    rows = []
    base = pd.Timestamp("2026-01-01 00:00:00")
    for cycle in range(1, cycles + 1):
        capacity = start_capacity - 0.02 * (cycle - 1)
        rows.extend([
            {
                "Date_Time": base + pd.Timedelta(hours=cycle),
                "Cycle_Index": cycle,
                "Step_Index": 7,
                "Voltage(V)": 3.8,
                "Current(A)": -1.0,
                "Test_Time(s)": 0.0,
            },
            {
                "Date_Time": base + pd.Timedelta(hours=cycle, minutes=1),
                "Cycle_Index": cycle,
                "Step_Index": 7,
                "Voltage(V)": 3.4,
                "Current(A)": -1.0,
                "Test_Time(s)": capacity * 3600.0,
            },
        ])
    return pd.DataFrame(rows)


def _write_nasa_mat(path, capacities):
    cycles = np.empty(len(capacities), dtype=object)
    for index, capacity in enumerate(capacities):
        cycles[index] = {
            "type": "discharge",
            "data": {
                "Capacity": float(capacity),
                "Voltage_measured": np.asarray([3.8, 3.6, 3.4]),
                "Current_measured": np.asarray([-1.0, -1.0, -1.0]),
                "Time": np.asarray([0.0, 1800.0, 3600.0]),
            },
        }
    savemat(path, {"B0005": {"cycle": cycles}})


class Phase5GoldenDatasetTests(unittest.TestCase):
    def test_minimal_calce_csv_and_excel_have_identical_capacity_contract(self):
        expected = np.asarray([1.10, 1.08, 1.06, 1.04, 1.02])
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sources = (root / "golden.csv", root / "golden.xlsx")
            frame = _calce_rows()
            frame.to_csv(sources[0], index=False)
            frame.to_excel(sources[1], index=False)

            for source in sources:
                with self.subTest(extension=source.suffix):
                    batteries, names = CALCEAdapter().load_battery_data(
                        [str(source)], 3.8, 3.4, 2, 4, 7,
                        log_callback=None, stop_flag=lambda: False)

                    self.assertEqual(names, ["golden"])
                    np.testing.assert_array_equal(
                        batteries["golden"]["cycle"], np.arange(1, 6))
                    np.testing.assert_allclose(
                        batteries["golden"]["capacity"], expected,
                        rtol=1e-6)

    def test_minimal_nasa_mat_extracts_named_discharge_cycles(self):
        expected = np.asarray([1.10, 1.08, 1.06, 1.04, 1.02])
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "B0005.mat"
            _write_nasa_mat(path, expected)

            batteries, names = NASAAdapter().load_battery_data(
                [str(path)], 3.8, 3.4, 2, 4, 7,
                log_callback=None, stop_flag=lambda: False)

        self.assertEqual(names, ["B0005"])
        np.testing.assert_array_equal(
            batteries["B0005"]["cycle"], np.arange(1, 6))
        np.testing.assert_allclose(
            batteries["B0005"]["capacity"], expected, rtol=1e-6)

    def test_mixed_valid_corrupt_and_empty_inputs_keep_only_valid_battery(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            valid = root / "valid.csv"
            corrupt = root / "corrupt.csv"
            empty = root / "empty"
            empty.mkdir()
            _calce_rows().to_csv(valid, index=False)
            corrupt.write_bytes(b"\xff\x00not-a-table")
            logs = []

            batteries, names = CALCEAdapter().load_battery_data(
                [str(valid), str(corrupt), str(empty)],
                3.8, 3.4, 2, 4, 7,
                log_callback=logs.append, stop_flag=lambda: False)

        self.assertEqual(names, ["valid"])
        self.assertEqual(list(batteries), ["valid"])
        self.assertTrue(any("跳过" in line and "corrupt" in line
                            for line in logs))

    def test_actual_workbook_sheet_limit_is_rejected_before_data_loading(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "many-sheets.xlsx"
            with pd.ExcelWriter(path) as writer:
                for index in range(3):
                    _calce_rows().to_excel(
                        writer, sheet_name=f"sheet-{index}", index=False)

            errors = validate_imported_item(
                str(path), adapter_type="CALCE", window_size=3,
                rated_capacity=1.1, max_sheets=2)

        self.assertTrue(any("工作表数量" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
