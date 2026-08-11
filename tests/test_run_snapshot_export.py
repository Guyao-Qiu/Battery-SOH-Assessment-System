import errno
import importlib
import importlib.util
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
import unittest
from unittest.mock import patch

import pandas as pd

from ui.predict_worker import PredictWorker
from ui.worker import EvalWorker
from utils.config import TrainConfig


def _optional_module(name):
    if importlib.util.find_spec(name) is None:
        return None
    return importlib.import_module(name)


run_snapshot_module = _optional_module("core.run_snapshot")
report_export_module = _optional_module("core.report_export")


class FakeCanvas:
    def save_figure(self, path):
        Path(path).write_bytes(b"chart")


class PermissionDeniedCanvas:
    def save_figure(self, path):
        raise PermissionError(errno.EACCES, "locked", str(path))


class SnapshotAndExportTests(unittest.TestCase):
    def _snapshot_api(self):
        self.assertIsNotNone(
            run_snapshot_module,
            "P1-15 requires an immutable RunSnapshot implementation",
        )
        return run_snapshot_module.RunSnapshot

    def _export_api(self):
        self.assertIsNotNone(
            report_export_module,
            "P1-15 requires atomic report export helpers",
        )
        return report_export_module

    def _completed_snapshot(self, run_id="20260811T010203Z-abcd1234"):
        RunSnapshot = self._snapshot_api()
        config = TrainConfig(window_size=3, rated_capacity=1.1)
        snapshot = RunSnapshot.capture(
            config,
            ["C:/data/cell.csv"],
            now=datetime(2026, 8, 11, 1, 2, 3, tzinfo=timezone.utc),
            run_id=run_id,
        )
        return snapshot.with_results({
            "cell": {
                "score": 0.1,
                "prediction": [1.1, 1.0, 0.9],
                "detail": {
                    "battery": "cell",
                    "cycles": 3,
                    "model": "RNN",
                    "rmse": 0.1,
                    "mae": 0.08,
                    "r2": 0.9,
                    "pearson": 0.95,
                    "re": 0.2,
                    "n_seeds": 1,
                    "failure_cycle": None,
                    "threshold": 0.88,
                },
            },
        }, elapsed_seconds=1.25)

    def test_snapshot_deep_copies_and_freezes_paths_and_config(self):
        RunSnapshot = self._snapshot_api()
        config = TrainConfig(window_size=3)
        paths = ["first.csv"]

        snapshot = RunSnapshot.capture(
            config, paths,
            now=datetime(2026, 8, 11, tzinfo=timezone.utc),
            run_id="20260811T000000Z-fixed",
        )
        config.window_size = 99
        paths.append("later.csv")

        self.assertEqual(snapshot.imported_paths, ("first.csv",))
        self.assertEqual(snapshot.config["window_size"], 3)
        with self.assertRaises(TypeError):
            snapshot.config["window_size"] = 4

    def test_workers_defensively_copy_config_and_paths(self):
        config = TrainConfig(window_size=3)
        paths = ["first.csv"]
        eval_worker = EvalWorker(config, paths)
        predict_worker = PredictWorker(
            object(), {"mode": "RF", "window_size": 3}, paths, config)

        config.window_size = 99
        paths.append("later.csv")

        self.assertEqual(eval_worker.config.window_size, 3)
        self.assertEqual(predict_worker.config.window_size, 3)
        self.assertEqual(tuple(eval_worker.imported_paths), ("first.csv",))
        self.assertEqual(tuple(predict_worker.imported_paths), ("first.csv",))

    def test_export_uses_snapshot_and_creates_run_id_directory(self):
        api = self._export_api()
        snapshot = self._completed_snapshot()

        with tempfile.TemporaryDirectory() as temp_dir:
            artifacts = api.export_run_report(
                snapshot, FakeCanvas(), base_directory=temp_dir)
            run_directory = Path(artifacts["run_directory"])
            report_path = Path(artifacts["report_json"])
            excel_path = Path(artifacts["metrics_excel"])
            chart_path = Path(artifacts["chart_image"])

            self.assertEqual(run_directory.name, snapshot.run_id)
            self.assertTrue(report_path.is_file())
            self.assertTrue(excel_path.is_file())
            self.assertEqual(chart_path.read_bytes(), b"chart")

            payload = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["run"]["run_id"], snapshot.run_id)
            self.assertEqual(payload["config"]["window_size"], 3)
            self.assertEqual(
                payload["imported_paths"], ["C:/data/cell.csv"])
            self.assertEqual(payload["run"]["elapsed_seconds"], 1.25)
            metrics = pd.read_excel(excel_path)
            self.assertEqual(metrics.loc[0, "battery"], "cell")

    def test_existing_report_requires_confirmation_before_overwrite(self):
        api = self._export_api()
        snapshot = self._completed_snapshot()

        with tempfile.TemporaryDirectory() as temp_dir:
            first = api.export_run_report(
                snapshot, FakeCanvas(), base_directory=temp_dir)
            report_path = Path(first["report_json"])
            original = report_path.read_bytes()
            confirmations = []

            with self.assertRaises(api.ExportCancelled):
                api.export_run_report(
                    snapshot,
                    FakeCanvas(),
                    base_directory=temp_dir,
                    confirm_overwrite=lambda paths: (
                        confirmations.append(tuple(paths)) or False),
                )

            self.assertEqual(report_path.read_bytes(), original)
            self.assertEqual(len(confirmations), 1)
            self.assertIn(report_path, confirmations[0])

    def test_export_failure_is_actionable_and_leaves_no_partial_files(self):
        api = self._export_api()
        snapshot = self._completed_snapshot()

        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(api.ReportExportError) as raised:
                api.export_run_report(
                    snapshot,
                    PermissionDeniedCanvas(),
                    base_directory=temp_dir,
                )

            self.assertIn("关闭正在占用", str(raised.exception))
            run_directory = Path(temp_dir) / snapshot.run_id
            if run_directory.exists():
                self.assertEqual(list(run_directory.iterdir()), [])

            disk_error = api.friendly_export_error(
                OSError(errno.ENOSPC, "disk full"))
            self.assertIn("磁盘空间", disk_error)

    def test_main_window_export_does_not_rebuild_live_ui_config(self):
        self._export_api()
        snapshot = self._completed_snapshot()
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        from ui.main_window import MainWindow

        app = QApplication.instance() or QApplication([])
        window = MainWindow()
        window._last_run_snapshot = snapshot
        try:
            with patch.object(
                    window, "_build_config",
                    side_effect=AssertionError("live UI must not be read")), \
                    patch("ui.main_window.export_run_report") as exporter, \
                    patch("ui.main_window.show_message"):
                exporter.return_value = {
                    "run_directory": "outputs/runs/example",
                    "report_json": "outputs/runs/example/report.json",
                    "metrics_excel": "outputs/runs/example/results.xlsx",
                    "chart_image": "outputs/runs/example/chart.png",
                }
                window.export_report()

            exporter.assert_called_once()
            self.assertIs(exporter.call_args.args[0], snapshot)
        finally:
            window.deleteLater()
            app.processEvents()


if __name__ == "__main__":
    unittest.main()
