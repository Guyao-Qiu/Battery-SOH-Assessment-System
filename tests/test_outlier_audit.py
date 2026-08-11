import importlib
import inspect
import unittest

import numpy as np
import pandas as pd


preprocess = importlib.import_module("core.preprocess")
adapters = importlib.import_module("core.adapters")


class AuditableOutlierFilterTests(unittest.TestCase):
    def test_stable_windows_and_two_sigma_boundary_are_retained(self):
        filter_outliers = getattr(
            preprocess, "filter_capacity_outliers", None)
        self.assertIsNotNone(filter_outliers)

        stable = filter_outliers(np.ones(40), bins=40)
        boundary = filter_outliers([0, 0, 0, 0, 1], bins=5)

        np.testing.assert_array_equal(stable.indices, np.arange(40))
        np.testing.assert_array_equal(boundary.indices, np.arange(5))
        self.assertEqual(stable.removed_count, 0)

    def test_filter_reports_mask_count_and_reason_and_can_be_disabled(self):
        filter_outliers = getattr(
            preprocess, "filter_capacity_outliers", None)
        self.assertIsNotNone(filter_outliers)
        values = np.asarray([1.0] * 10 + [100.0, np.nan])

        filtered = filter_outliers(values, bins=12, protect_knees=False)
        disabled = filter_outliers(values, bins=12, enabled=False)

        self.assertEqual(len(filtered.mask), len(values))
        self.assertEqual(filtered.removed_count, 2)
        self.assertIn("非有限", filtered.reasons[11])
        self.assertIn("局部", filtered.reasons[10])
        np.testing.assert_array_equal(disabled.indices, np.arange(11))
        self.assertEqual(disabled.removed_count, 1)

    def test_persistent_degradation_knee_is_protected(self):
        filter_outliers = getattr(
            preprocess, "filter_capacity_outliers", None)
        self.assertIsNotNone(filter_outliers)
        values = np.asarray([1.0] * 37 + [0.80, 0.79, 0.78])

        protected = filter_outliers(values, bins=40, protect_knees=True)
        unprotected = filter_outliers(values, bins=40, protect_knees=False)

        self.assertTrue({37, 38, 39}.issubset(set(protected.indices)))
        self.assertTrue({37, 38, 39}.intersection(set(unprotected.removed_indices)))
        self.assertTrue({37, 38, 39}.intersection(set(protected.protected_indices)))


class CycleAlignmentTests(unittest.TestCase):
    @staticmethod
    def _frame():
        rows = []
        for cycle, duration, has_discharge in (
                (10, 10.0, True), (20, 20.0, False), (30, 30.0, True)):
            rows.extend([
                {"Cycle_Index": cycle, "Step_Index": 2,
                 "Voltage(V)": 3.5, "Current(A)": 1.0,
                 "Test_Time(s)": 0.0},
                {"Cycle_Index": cycle, "Step_Index": 2,
                 "Voltage(V)": 4.0, "Current(A)": 1.0,
                 "Test_Time(s)": duration},
                {"Cycle_Index": cycle, "Step_Index": 4,
                 "Voltage(V)": 4.1, "Current(A)": 0.2,
                 "Test_Time(s)": 0.0},
                {"Cycle_Index": cycle, "Step_Index": 4,
                 "Voltage(V)": 4.1, "Current(A)": 0.1,
                 "Test_Time(s)": duration / 2},
            ])
            if has_discharge:
                rows.extend([
                    {"Cycle_Index": cycle, "Step_Index": 7,
                     "Voltage(V)": 4.0, "Current(A)": -1.0,
                     "Test_Time(s)": 0.0},
                    {"Cycle_Index": cycle, "Step_Index": 7,
                     "Voltage(V)": 3.0, "Current(A)": -1.0,
                     "Test_Time(s)": 3600.0},
                ])
        return pd.DataFrame(rows)

    def test_original_cycles_and_features_stay_aligned_after_skips(self):
        result = adapters._extract_capacity_from_tabular(
            self._frame(), voltage_upper=3.8, voltage_lower=3.4,
            cc_step=2, cv_step=4, discharge_step=7,
            log_callback=None, name="cell")
        self.assertEqual(len(result), 6)
        cycles, capacities, health, resistance, ccct, cvct = result
        self.assertEqual(cycles, [10, 30])
        self.assertEqual(ccct, [10.0, 30.0])
        self.assertEqual(cvct, [5.0, 15.0])
        self.assertTrue(all(
            len(values) == len(cycles)
            for values in (capacities, health, resistance, ccct, cvct)))

        signature = inspect.signature(adapters._build_battery_dataframe)
        self.assertIn("cycle_indices", signature.parameters)
        frame = adapters._build_battery_dataframe(
            cycles, capacities, health, resistance, ccct, cvct,
            "cell", None)
        self.assertEqual(frame["cycle"].tolist(), [10, 30])
        audit = frame.attrs["outlier_audit"]
        self.assertEqual(audit["input_count"], 2)
        self.assertEqual(audit["kept_count"], 2)
        self.assertEqual(audit["removed_count"], 0)
        self.assertEqual(len(audit["mask"]), 2)


if __name__ == "__main__":
    unittest.main()
