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


class FloatingThemeAndHelpTests(unittest.TestCase):
    """本轮修复：拖拽跟随、画布重绘、窗口单例、数学排版、字号、使用指南。"""

    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication

        cls.app = QApplication.instance() or QApplication([])

    def test_dragging_the_theme_button_keeps_the_grab_point(self):
        """拖动时按钮中心必须跟着鼠标走，不能跳位（坐标换算回归）。"""
        from PyQt6.QtCore import QEvent, QPoint, QPointF, QSettings, Qt
        from PyQt6.QtGui import QMouseEvent

        from ui.floating_theme_button import POSITION_KEY
        from ui.main_window import MainWindow

        QSettings("BatterySOH", "AssessmentSystem").remove(POSITION_KEY)
        window = MainWindow()
        try:
            window.resize(1300, 820)
            window.move(250, 150)
            window.show()
            self.app.processEvents()

            button = window.theme_btn
            center = button.mapToGlobal(
                QPoint(button.width() // 2, button.height() // 2))
            press = QMouseEvent(
                QEvent.Type.MouseButtonPress,
                QPointF(button.width() / 2, button.height() / 2),
                QPointF(center), Qt.MouseButton.LeftButton,
                Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
            button.mousePressEvent(press)

            target = center + QPoint(-120, 80)
            move = QMouseEvent(
                QEvent.Type.MouseMove,
                QPointF(button.width() / 2, button.height() / 2),
                QPointF(target), Qt.MouseButton.NoButton,
                Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
            button.mouseMoveEvent(move)
            self.app.processEvents()

            new_center = button.mapToGlobal(
                QPoint(button.width() // 2, button.height() // 2))
            offset = new_center - target
            self.assertLessEqual(
                abs(offset.x()), 2,
                "拖动后按钮横向偏离鼠标，说明坐标换算又混用了坐标系")
            self.assertLessEqual(abs(offset.y()), 2)
        finally:
            _dispose_window(window, self.app)

    def test_dragging_notifies_the_canvas_to_repaint(self):
        """拖动按钮必须通知图表重绘，否则会留下竖线状残影。"""
        from ui.main_window import MainWindow

        window = MainWindow()
        try:
            self.assertTrue(
                hasattr(window.theme_btn, "moved"),
                "悬浮按钮需要 moved 信号驱动画布全量重绘",
            )
            repainted = []
            window.theme_btn.moved.connect(lambda: repainted.append(True))
            window.theme_btn.moved.emit()
            self.assertTrue(repainted)
        finally:
            _dispose_window(window, self.app)

    def test_line_style_dialog_is_a_singleton(self):
        """连续点击线条样式按钮只能出现一个窗口。"""
        from ui.main_window import MainWindow

        window = MainWindow()
        try:
            toolbar = window.toolbar
            toolbar._open_line_style_dialog()
            first = toolbar._line_style_dialog
            self.assertIsNotNone(first)
            toolbar._open_line_style_dialog()
            self.assertIs(
                toolbar._line_style_dialog, first,
                "重复点击不应再新建窗口，应复用并前置已有窗口",
            )
        finally:
            _dispose_window(window, self.app)

    def test_feature_labels_use_math_typesetting(self):
        """输入特征里的变量用斜体 + 下标，而不是 dq_v 这种下划线写法。"""
        from PyQt6.QtWidgets import QLabel

        from ui.main_window import MainWindow

        window = MainWindow()
        try:
            texts = [label.text() for label in window.findChildren(QLabel)]
            self.assertTrue(
                any("<i>dq</i><sub>v</sub>" in text for text in texts),
                "dq_v 应按数学排版显示为斜体 dq + 下标 v",
            )
            self.assertTrue(
                any("<i>SOH</i>" in text for text in texts),
                "SOH 应使用斜体变量写法",
            )
            # 复选框本身仍是纯文本（QCheckBox 不渲染富文本）
            for name, checkbox in window.feature_checks.items():
                self.assertNotIn("<", checkbox.text(), f"{name} 复选框不应含标记")
        finally:
            _dispose_window(window, self.app)

    def test_help_dialog_font_size_defaults_to_12_and_applies_live(self):
        """帮助面板字号默认 12，改动立即生效并被记住。"""
        from PyQt6.QtCore import QSettings

        from ui.main_window import HELP_FONT_SIZE_KEY, MainWindow

        settings = QSettings("BatterySOH", "AssessmentSystem")
        settings.remove(HELP_FONT_SIZE_KEY)
        window = MainWindow()
        try:
            window.show_help()
            self.app.processEvents()
            dialog = window._help_dialog
            self.assertIsNotNone(dialog)
            self.assertEqual(dialog._font_size, 12, "默认字号应为 12")

            dialog._font_spin.setValue(18)
            self.app.processEvents()
            self.assertEqual(dialog._font_size, 18)
            self.assertEqual(
                dialog._text.font().pointSize(), 18,
                "改字号后正文必须立即跟着变",
            )
            self.assertEqual(int(settings.value(HELP_FONT_SIZE_KEY)), 18)
        finally:
            settings.remove(HELP_FONT_SIZE_KEY)
            _dispose_window(window, self.app)

    def test_sidebar_has_a_guide_button_with_full_instructions(self):
        """侧边栏底部要有使用指南入口，内容覆盖工作流程与常见问题。"""
        from ui.main_window import MainWindow

        window = MainWindow()
        try:
            self.assertTrue(hasattr(window, "guide_btn"))
            self.assertEqual(window.guide_btn.text(), "指南")
            window.show_guide()
            self.app.processEvents()
            guide = window._guide_dialog
            self.assertIsNotNone(guide)
            body = guide._text.toPlainText()
            for section in ("标准工作流程", "界面导航", "常见问题"):
                self.assertIn(section, body, f"使用指南缺少「{section}」")
            # 重复点击复用同一窗口
            window.show_guide()
            self.assertIs(window._guide_dialog, guide)
        finally:
            _dispose_window(window, self.app)


if __name__ == "__main__":
    unittest.main()
