import inspect
import importlib
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from core.adapters import CALCEAdapter
from core.train import train
from ui.predict_worker import PredictWorker


train_module = importlib.import_module("core.train")


def _battery(capacity):
    return {"capacity": np.asarray(capacity, dtype=np.float32)}


class LastValueRegressor:
    def predict(self, windows):
        windows = np.asarray(windows, dtype=np.float32)
        return windows[:, -1] * 0.98


class NamedResultContractTests(unittest.TestCase):
    def test_adapter_only_lists_batteries_that_were_loaded_successfully(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            invalid_path = temp_path / "invalid.csv"
            valid_path = temp_path / "valid.csv"
            pd.DataFrame({"unexpected": [1]}).to_csv(
                invalid_path, index=False)

            rows = []
            for cycle in range(1, 5):
                rows.extend([
                    {
                        "Date_Time": "2026-01-01 00:00:00",
                        "Cycle_Index": cycle,
                        "Step_Index": 7,
                        "Voltage(V)": 3.8,
                        "Current(A)": -1.0,
                        "Test_Time(s)": 0.0,
                    },
                    {
                        "Date_Time": "2026-01-01 00:00:01",
                        "Cycle_Index": cycle,
                        "Step_Index": 7,
                        "Voltage(V)": 3.4,
                        "Current(A)": -1.0,
                        "Test_Time(s)": 3600.0 - cycle,
                    },
                ])
            pd.DataFrame(rows).to_csv(valid_path, index=False)

            battery_dict, battery_list = CALCEAdapter().load_battery_data(
                [str(invalid_path), str(valid_path)],
                voltage_upper=3.8,
                voltage_lower=3.4,
                cc_step=2,
                cv_step=4,
                discharge_step=7,
                log_callback=None,
                stop_flag=lambda: False,
            )

        self.assertEqual(battery_list, ["valid"])
        self.assertEqual(list(battery_dict), ["valid"])

    def test_training_results_are_keyed_by_battery_name(self):
        config = SimpleNamespace(
            window_size=1, mode="RNN", seed=1, n_seeds=1)
        battery_dict = {
            "short": _battery([1.0, 0.9]),
            "good": _battery([1.0, 0.9, 0.8, 0.7]),
        }
        metrics = {
            "rmse": 0.1,
            "mae": 0.08,
            "r2": 0.9,
            "pearson": 0.95,
            "re": 0.2,
        }

        with patch.object(
                train_module, "_train_one_battery",
                return_value=([1.0, 0.9, 0.8, 0.7], metrics, {})):
            results = train(
                config, battery_dict, ["short", "good"])

        self.assertIsInstance(results, dict)
        self.assertEqual(list(results), ["good"])
        self.assertEqual(
            set(results["good"]), {"score", "prediction", "detail"})
        self.assertEqual(results["good"]["detail"]["battery"], "good")

    def test_prediction_worker_emits_one_name_keyed_result_object(self):
        scaler = {
            "method": "rated",
            "rated_capacity": 1.1,
            "scale": 1.1,
            "offset": 0.0,
        }
        metadata = {
            "mode": "RF",
            "window_size": 3,
            "rated_capacity": 1.1,
            "scaler": scaler,
        }
        config = SimpleNamespace(
            rated_capacity=1.1,
            threshold_ratio=0.8,
            device="cpu",
            voltage_upper=3.8,
            voltage_lower=3.4,
            adapter_type="CALCE",
            cc_step=2,
            cv_step=4,
            discharge_step=7,
            metric="rmse",
        )
        batteries = {
            "short": _battery([1.1, 1.0, 0.9, 0.8]),
            "good": _battery(
                [1.10, 1.05, 1.00, 0.96, 0.91, 0.86, 0.81, 0.76]),
        }
        worker = PredictWorker(
            LastValueRegressor(), metadata, ["ignored"], config)
        payloads = []
        errors = []
        worker.result_signal.connect(lambda *args: payloads.append(args))
        worker.error_signal.connect(errors.append)

        with patch(
                "core.dataload.load_battery_from_paths",
                return_value=(batteries, ["short", "good"])):
            worker.run()

        self.assertEqual(errors, [])
        self.assertEqual(len(payloads), 1)
        self.assertEqual(len(payloads[0]), 2)
        results, _elapsed = payloads[0]
        self.assertEqual(list(results), ["good"])
        self.assertEqual(results["good"]["detail"]["battery"], "good")

    def test_chart_accepts_predictions_keyed_by_battery_name(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        from ui.chart_show import MplCanvas

        parameters = inspect.signature(MplCanvas.plot_results).parameters
        self.assertIn("prediction_by_battery", parameters)

        app = QApplication.instance() or QApplication([])
        canvas = MplCanvas()
        battery_data = {
            "skipped": _battery([9.0, 9.0, 9.0]),
            "good": _battery([1.0, 0.9, 0.8]),
        }
        try:
            canvas.plot_results(
                ["skipped", "good"],
                battery_data,
                {"good": [1.0, 0.91, 0.81]},
                rated_capacity=1.0,
                threshold_ratio=0.8,
            )
            plotted_titles = [axis.get_title() for axis in canvas.fig.axes]
            self.assertEqual(plotted_titles, ["good 预测值与真实值对比"])
        finally:
            canvas.deleteLater()
            app.processEvents()


if __name__ == "__main__":
    unittest.main()
