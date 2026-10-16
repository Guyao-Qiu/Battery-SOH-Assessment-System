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

    def test_workspace_groups_panels_behind_a_nav_rail(self):
        from ui.main_window import MainWindow

        window = MainWindow()
        try:
            self.assertEqual(
                window.sidebar_stack.count(),
                4,
                "数据/参数/结果/日志应合并为侧边栏页面栈",
            )
            self.assertEqual(
                window._sidebar_page_index,
                {"data": 0, "params": 1, "result": 2, "log": 3},
            )
            labels = [
                window._nav_group.button(index).text()
                for index in range(window.sidebar_stack.count())
            ]
            self.assertEqual(labels, ["数据", "参数", "结果", "日志"])
        finally:
            _dispose_window(window, self.app)

    def test_running_state_surfaces_the_training_log(self):
        from ui.main_window import MainWindow

        window = MainWindow()
        try:
            window._show_sidebar_page("result")
            window._set_running_state(True, "正在训练模型")

            self.assertEqual(
                window.sidebar_stack.currentIndex(),
                window._sidebar_page_index["log"],
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
                window.sidebar_stack.currentIndex(),
                window._sidebar_page_index["result"],
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

            sidebar, chart = window.main_splitter.sizes()
            self.assertGreaterEqual(chart, 500)
            self.assertGreater(chart, sidebar)
            self.assertLessEqual(sidebar, 470)

        finally:
            _dispose_window(window, self.app)

    def test_nav_rail_switches_pages_exclusively(self):
        from ui.main_window import MainWindow

        window = MainWindow()
        try:
            window._show_sidebar_page("params")
            window._nav_group.button(
                window._sidebar_page_index["log"]).click()

            self.assertEqual(
                window.sidebar_stack.currentIndex(),
                window._sidebar_page_index["log"],
                "点击轨道按钮应切换页面栈",
            )
            checked = [
                window._nav_group.button(index).isChecked()
                for index in range(window.sidebar_stack.count())
            ]
            self.assertEqual(checked.count(True), 1, "轨道按钮应互斥")

            # 再次点击当前页按钮 → 收起侧边栏（只剩导航轨道）
            window._nav_group.button(
                window._sidebar_page_index["log"]).click()
            self.assertTrue(
                window.sidebar_stack.isHidden(),
                "再次点击当前页应收起侧边栏",
            )
            # 收起状态下点击其他按钮 → 重新展开并切换页面
            window._nav_group.button(
                window._sidebar_page_index["result"]).click()
            self.assertFalse(window.sidebar_stack.isHidden())
            self.assertEqual(
                window.sidebar_stack.currentIndex(),
                window._sidebar_page_index["result"],
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
            window._show_sidebar_page("log")
            window._show_result_state("评估未完成", "请检查数据和参数。")

            self.assertEqual(
                window.sidebar_stack.currentIndex(),
                window._sidebar_page_index["result"],
            )
        finally:
            _dispose_window(window, self.app)


if __name__ == "__main__":
    unittest.main()
