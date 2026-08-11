import importlib
import importlib.util
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
import torch
import torch.nn as nn

import core.adapters as adapters_module
import core.train as train_module
from core.adapters import CALCEAdapter
from core.model_persistence import train_model_on_all_data
from utils.config import TrainConfig


batching_module = (
    importlib.import_module("core.batching")
    if importlib.util.find_spec("core.batching") else None
)


def _csv_rows(cycles=4):
    rows = []
    for cycle in range(1, cycles + 1):
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
    return rows


def _battery(length, start):
    return {
        "capacity": np.linspace(
            start, start - 0.25, length, dtype=np.float32),
    }


class BatchGuardNet(nn.Module):
    training_batch_sizes = []

    def __init__(self, hidden_dim, num_layers=1, mode="RNN"):
        super().__init__()
        self.output = nn.Linear(1, 1)

    def forward(self, inputs):
        if self.training:
            self.__class__.training_batch_sizes.append(inputs.shape[0])
        return self.output(inputs[:, -1, :])


class CalceReadEfficiencyTests(unittest.TestCase):
    def test_each_calce_file_is_fully_read_only_once(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "cell.csv"
            pd.DataFrame(_csv_rows()).to_csv(path, index=False)

            with patch.object(
                    adapters_module, "_read_data_file",
                    wraps=adapters_module._read_data_file) as full_read:
                battery_dict, battery_list = CALCEAdapter().load_battery_data(
                    [str(path)],
                    voltage_upper=3.8,
                    voltage_lower=3.4,
                    cc_step=2,
                    cv_step=4,
                    discharge_step=7,
                    log_callback=None,
                    stop_flag=lambda: False,
                )

        self.assertEqual(battery_list, ["cell"])
        self.assertEqual(list(battery_dict), ["cell"])
        self.assertEqual(full_read.call_count, 1)


class RecurrentBatchingTests(unittest.TestCase):
    def test_tensor_loader_keeps_training_batches_bounded_on_cpu(self):
        self.assertIsNotNone(batching_module)
        features = np.arange(1000 * 8, dtype=np.float32).reshape(1000, 8)
        targets = np.arange(1000, dtype=np.float32)

        loader = batching_module.make_tensor_loader(
            features, targets, batch_size=64, shuffle=False)
        batches = list(loader)

        self.assertEqual(sum(len(x) for x, _ in batches), 1000)
        self.assertLessEqual(max(len(x) for x, _ in batches), 64)
        self.assertTrue(all(x.device.type == "cpu" and y.device.type == "cpu"
                            for x, y in batches))

    def test_fold_and_final_rnn_training_use_bounded_batches(self):
        self.assertIsNotNone(batching_module)
        config = TrainConfig(
            mode="RNN",
            window_size=4,
            hidden_dim=2,
            epochs=1,
            patience=1,
            rated_capacity=1.2,
            norm_method="rated",
            device="cpu",
            n_seeds=1,
            seed=3,
        )
        data = {
            "a": _battery(180, 1.15),
            "b": _battery(180, 1.13),
            "target": _battery(180, 1.11),
        }
        protocol = {
            "one_step": {
                "prediction": np.asarray([1.0]),
                "metrics": {
                    "rmse": 0.1, "mae": 0.1, "r2": 0.9,
                    "pearson": 0.9, "re": None,
                    "re_status": "both_censored",
                },
            },
            "recursive": {
                "prediction": np.asarray([1.0]),
                "metrics": {
                    "rmse": 0.1, "mae": 0.1, "r2": 0.9,
                    "pearson": 0.9, "re": None,
                    "re_status": "both_censored",
                },
            },
            "rul_re": None,
        }
        BatchGuardNet.training_batch_sizes = []

        with patch.object(train_module, "Net", BatchGuardNet), \
                patch.object(
                    train_module, "evaluate_prediction_protocols",
                    return_value=protocol), \
                patch(
                    "core.model_persistence.Net", BatchGuardNet):
            train_module._train_one_battery(config, data, "target", seed=3)
            train_model_on_all_data(config, data, list(data))

        self.assertGreater(len(BatchGuardNet.training_batch_sizes), 2)
        self.assertLessEqual(
            max(BatchGuardNet.training_batch_sizes),
            batching_module.DEFAULT_BATCH_SIZE,
        )


if __name__ == "__main__":
    unittest.main()
