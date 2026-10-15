from pathlib import Path
import json
import os
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from core.model_persistence import (
    save_model,
    train_model_on_all_data,
)
from core.report_export import export_run_report
from ui.predict_worker import PredictWorker
from ui.worker import EvalWorker
from utils.config import TrainConfig


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _write_calce_battery(path, start_capacity):
    rows = []
    base = pd.Timestamp("2026-01-01 00:00:00")
    for cycle in range(1, 9):
        capacity = start_capacity - 0.025 * (cycle - 1)
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
    pd.DataFrame(rows).to_csv(path, index=False)


class Phase5UiWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication

        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from ui.main_window import MainWindow

        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.paths = []
        for name, capacity in (
                ("cell_a", 1.10), ("cell_b", 1.09), ("cell_c", 1.08)):
            path = self.root / f"{name}.csv"
            _write_calce_battery(path, capacity)
            self.paths.append(str(path))
        self.window = MainWindow()

    def tearDown(self):
        self.window.deleteLater()
        self.app.processEvents()
        self.temp_dir.cleanup()

    def _import_paths_through_ui(self):
        with patch(
                "ui.main_window.QFileDialog.getOpenFileNames",
                return_value=(self.paths, "数据文件")):
            self.window.import_files()
        self.assertEqual(self.window.imported_paths, self.paths)
        self.assertEqual(self.window.import_list.count(), 3)

    def _set_fast_common_controls(self):
        self.window.adapter_combo.setCurrentIndex(
            self.window.adapter_combo.findData("CALCE"))
        for step_input, value in (
                (self.window.cc_step_input, 2),
                (self.window.cv_step_input, 4),
                (self.window.discharge_step_input, 7)):
            step_input.setText(str(value))
        self.window.feature_size_spin.setValue(2)
        self.window.n_seeds_spin.setValue(1)
        self.window.norm_combo.setCurrentText("MinMax")
        self.window.device_combo.setCurrentText("CPU")

    def test_import_select_train_render_and_export_real_report_bundle(self):
        self._import_paths_through_ui()
        self._set_fast_common_controls()
        self.window.select_mode("RF")
        self.window.metric_combo.setCurrentText("全部")
        self.window.rf_n_estimators_spin.setValue(3)
        self.window.rf_max_depth_spin.setValue(2)

        with patch.object(EvalWorker, "start", EvalWorker.run), patch(
                "ui.main_window.show_message"):
            self.window.start_evaluation()

        snapshot = self.window._last_run_snapshot
        self.assertIsNotNone(snapshot)
        self.assertEqual(list(snapshot.results_dict()),
                         ["cell_a", "cell_b", "cell_c"])
        self.assertEqual(self.window.current_mode, "RF")
        # U1：结果区改为可排序表格。3 块电池 → 3 行数据 + 3 行经验基线 + 1 行汇总
        rows = self.window.result_model.rows()
        self.assertEqual(
            len([r for r in rows if not r.get('is_baseline')]), 3)
        self.assertEqual(len(self.window.result_model.display_rows()),
                         len(rows) + 1)
        self.assertTrue(self.window.export_btn.isEnabled())
        self.assertIsNotNone(self.window.final_trained_model)

        report_root = self.root / "reports"

        def export_to_temp(snapshot_arg, canvas, confirm_overwrite=None):
            return export_run_report(
                snapshot_arg,
                canvas,
                base_directory=report_root,
                confirm_overwrite=confirm_overwrite,
            )

        with patch(
                "ui.main_window.export_run_report",
                side_effect=export_to_temp), patch(
                    "ui.main_window.show_message"):
            self.window.export_report()

        run_directory = report_root / snapshot.run_id
        self.assertEqual(
            sorted(path.name for path in run_directory.iterdir()),
            ["report.json", "评估结果.png", "评估结果.xlsx"],
        )
        report = json.loads(
            (run_directory / "report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["config"]["mode"], "RF")
        self.assertEqual(sorted(report["results"]),
                         ["cell_a", "cell_b", "cell_c"])

    def test_load_model_and_batch_predict_every_metric_selection(self):
        battery_dict = {
            name: {
                "capacity": np.linspace(
                    start, start - 0.175, 8, dtype=np.float32)
            }
            for name, start in (
                ("cell_a", 1.10), ("cell_b", 1.09), ("cell_c", 1.08))
        }
        config = TrainConfig(
            mode="RNN",
            window_size=2,
            hidden_dim=3,
            epochs=1,
            patience=1,
            rated_capacity=1.1,
            norm_method="minmax",
            device="cpu",
            seed=23,
            n_seeds=1,
        )
        model, metadata = train_model_on_all_data(
            config, battery_dict, list(battery_dict))
        model_path = self.root / "safe-model.pt"
        save_model(model, metadata, model_path)

        self._import_paths_through_ui()
        self._set_fast_common_controls()
        self.window.load_model_from_path(model_path)
        self.assertEqual(self.window.current_mode, "RNN")

        for metric_text in ("RMSE", "MAE", "R²", "Pearson", "RE", "全部"):
            with self.subTest(metric=metric_text):
                self.window.metric_combo.setCurrentText(metric_text)
                with patch.object(
                        PredictWorker, "start", PredictWorker.run), patch(
                            "ui.main_window.show_message"):
                    self.window.start_evaluation()

                results = self.window._last_run_snapshot.results_dict()
                self.assertEqual(list(results),
                                 ["cell_a", "cell_b", "cell_c"])
                # U1：3 块电池各一行（另有基线与汇总行）
                battery_rows = [
                    row for row in self.window.result_model.rows()
                    if not row.get('is_baseline')
                ]
                self.assertEqual(len(battery_rows), 3)
                for result in results.values():
                    detail = result["detail"]
                    for metric in ("rmse", "mae", "r2", "pearson", "re"):
                        self.assertIn(metric, detail)


if __name__ == "__main__":
    unittest.main()
