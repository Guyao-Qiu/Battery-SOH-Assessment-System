import os
import unittest


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _dispose_window(window, app):
    from matplotlib import pyplot as plt

    plt.close(window.canvas.fig)
    window.deleteLater()
    app.processEvents()


class UiPolishLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication

        cls.app = QApplication.instance() or QApplication([])

    def test_results_and_log_are_grouped_as_task_tabs(self):
        from ui.main_window import MainWindow

        window = MainWindow()
        try:
            self.assertTrue(
                hasattr(window, "right_tabs"),
                "右侧结果与日志应使用任务页签收拢视觉层级",
            )
            self.assertEqual(
                [window.right_tabs.tabText(index) for index in range(2)],
                ["评估结果", "训练日志"],
            )
        finally:
            _dispose_window(window, self.app)

    def test_running_state_surfaces_the_training_log(self):
        from ui.main_window import MainWindow

        window = MainWindow()
        try:
            window.right_tabs.setCurrentIndex(window.result_tab_index)
            window._set_running_state(True, "正在训练模型")

            self.assertEqual(
                window.right_tabs.currentIndex(),
                window.log_tab_index,
            )
        finally:
            _dispose_window(window, self.app)

    def test_completed_results_start_with_a_compact_summary(self):
        from ui.main_window import MainWindow

        window = MainWindow()
        details = [
            {
                "battery": "cell_a",
                "cycles": 120,
                "model": "RNN",
                "measured_failure_cycle": None,
                "failure_cycle": None,
                "rmse": 0.10,
                "mae": 0.08,
                "r2": 0.95,
                "pearson": 0.98,
                "re": None,
                "n_seeds": 2,
                "ci": {},
            },
            {
                "battery": "cell_b",
                "cycles": 140,
                "model": "RNN",
                "measured_failure_cycle": None,
                "failure_cycle": None,
                "rmse": 0.20,
                "mae": 0.16,
                "r2": 0.90,
                "pearson": 0.96,
                "re": None,
                "n_seeds": 2,
                "ci": {},
            },
        ]
        try:
            window.metric_combo.setCurrentText("RMSE")
            window.update_result_table(details, elapsed=12.34)

            self.assertTrue(
                hasattr(window, "result_summary"),
                "结果卡片前应有一眼可读的运行摘要",
            )
            self.assertFalse(window.result_summary.isHidden())
            self.assertEqual(window.result_summary_title.text(), "2 块电池 · RNN")
            self.assertEqual(window.result_summary_metric.text(), "平均 RMSE 0.150000")
            self.assertIn("12.34 秒", window.result_summary_meta.text())
            self.assertEqual(
                window.right_tabs.currentIndex(),
                window.result_tab_index,
            )
        finally:
            _dispose_window(window, self.app)

    def test_minimum_workspace_keeps_chart_column_dominant(self):
        from ui.main_window import MainWindow

        window = MainWindow()
        try:
            self.assertTrue(
                hasattr(window, "main_splitter"),
                "主工作区分栏应可被测试并在窄窗口中保持图表优先",
            )
            window.resize(1180, 700)
            window.show()
            self.app.processEvents()

            left, chart, right = window.main_splitter.sizes()
            self.assertGreaterEqual(chart, 500)
            self.assertGreater(chart, left)
            self.assertGreater(chart, right)
            self.assertLessEqual(right, 340)
        finally:
            _dispose_window(window, self.app)

    def test_left_panel_splitter_has_a_usable_drag_target(self):
        from PyQt6.QtCore import QPoint, Qt
        from PyQt6.QtTest import QTest
        from PyQt6.QtWidgets import QSplitter

        from ui.main_window import MainWindow

        window = MainWindow()
        try:
            window.resize(1600, 900)
            window.show()
            self.app.processEvents()

            left_splitter = next(
                splitter for splitter in window.findChildren(QSplitter)
                if splitter.orientation() == Qt.Orientation.Vertical
            )
            handles = [
                left_splitter.handle(index)
                for index in range(1, left_splitter.count())
            ]
            for handle in handles:
                self.assertGreaterEqual(
                    handle.height(),
                    10,
                    "左侧面板分割线需要至少 10px 的垂直命中区域，不能只靠精确点中细线",
                )

            before = left_splitter.sizes()
            handle = handles[0]
            start = handle.rect().center()
            QTest.mousePress(
                handle, Qt.MouseButton.LeftButton, pos=start)
            QTest.mouseMove(handle, start + QPoint(0, 48), delay=10)
            QTest.mouseRelease(
                handle, Qt.MouseButton.LeftButton,
                pos=start + QPoint(0, 48),
            )
            self.app.processEvents()

            self.assertNotEqual(
                left_splitter.sizes(),
                before,
                "拖动左侧面板分割线后，面板高度应实际发生变化",
            )
        finally:
            _dispose_window(window, self.app)

    def test_result_scroll_does_not_require_horizontal_panning(self):
        from PyQt6.QtCore import Qt

        from ui.main_window import MainWindow

        window = MainWindow()
        try:
            self.assertEqual(
                window.result_scroll.horizontalScrollBarPolicy(),
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff,
            )
        finally:
            _dispose_window(window, self.app)

    def test_result_table_replaces_the_card_stack(self):
        """U1：结果区是可排序表格 + 跨电池汇总行，不再是卡片竖排。"""
        from ui.main_window import MainWindow

        window = MainWindow()
        detail = {
            "battery": "cell_with_a_long_identifier",
            "cycles": 120,
            "model": "RNN",
            "rmse": 0.10,
            "mae": 0.08,
            "r2": 0.95,
            "pearson": 0.98,
            "re": None,
            "n_seeds": 3,
            "primary_start_frac": 0.5,
            "rolling_rows": [
                {"start_frac": 0.5, "start": 60, "battery":
                 "cell_with_a_long_identifier", "rmse": 0.10, "mae": 0.08,
                 "true_rul": 40, "pred_rul": 42, "rul_err": 2,
                 "rul_rel_err": 0.05, "within_20pct": True, "status": "ok"},
            ],
            "ci": {
                "rmse": {
                    "mean": 0.1,
                    "std": 0.01,
                    "lower": 0.08,
                    "upper": 0.12,
                }
            },
        }
        try:
            window.metric_combo.setCurrentText("RMSE")
            window.update_result_table([detail], elapsed=2.0)

            # 表格就位、可排序、用原始值排序
            self.assertTrue(window.result_view.isSortingEnabled())
            self.assertEqual(
                window.result_view.model().sortRole(),
                __import__("PyQt6.QtCore", fromlist=["Qt"]).Qt
                .ItemDataRole.UserRole,
            )
            # 汇总行在最后一行（跨电池 mean ± std）
            model = window.result_model
            rows = model.display_rows()
            self.assertTrue(rows)
            self.assertTrue(rows[-1].get("is_summary"))
            self.assertEqual(rows[-1]["n_batteries"], 1)
            # 置信区间口径必须写清楚，不能被藏起来
            self.assertIn("同一留一折", window.result_notes.text())
            # 结果表可横向滚动，不需要用户手动平移（列宽自适应内容）
            self.assertFalse(window.result_scroll.horizontalScrollBar().isVisible())
        finally:
            _dispose_window(window, self.app)

    def test_result_rows_wrap_long_confidence_intervals(self):
        """置信区间口径说明必须换行显示，不能被截断。"""
        from ui.main_window import MainWindow

        window = MainWindow()
        detail = {
            "battery": "cell_with_a_long_identifier",
            "cycles": 120,
            "model": "RNN",
            "rmse": 0.10,
            "mae": 0.08,
            "r2": 0.95,
            "pearson": 0.98,
            "re": None,
            "n_seeds": 3,
            "ci": {
                "rmse": {
                    "mean": 0.1,
                    "std": 0.01,
                    "lower": 0.08,
                    "upper": 0.12,
                }
            },
        }
        try:
            window.metric_combo.setCurrentText("RMSE")
            window.update_result_table([detail], elapsed=2.0)

            self.assertTrue(window.result_notes.wordWrap())
            self.assertIn("随机种子", window.result_notes.text())
        finally:
            _dispose_window(window, self.app)

    def test_terminal_state_returns_attention_to_results(self):
        from ui.main_window import MainWindow

        window = MainWindow()
        try:
            window.right_tabs.setCurrentIndex(window.log_tab_index)
            window._show_result_state("评估未完成", "请检查数据和参数。")

            self.assertEqual(
                window.right_tabs.currentIndex(),
                window.result_tab_index,
            )
        finally:
            _dispose_window(window, self.app)


if __name__ == "__main__":
    unittest.main()
