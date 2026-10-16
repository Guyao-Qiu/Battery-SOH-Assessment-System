import inspect
import os
import unittest
from unittest.mock import patch


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _dispose_window(window, app):
    from matplotlib import pyplot as plt

    plt.close(window.canvas.fig)
    window.deleteLater()
    app.processEvents()


class StartupSplashProgressTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication

        cls.app = QApplication.instance() or QApplication([])

    def test_progress_shows_percentage_and_current_loading_stage(self):
        from battery_soh_app import _StartupSplash

        self.assertIn("status", inspect.signature(
            _StartupSplash.set_progress).parameters)
        splash = _StartupSplash()
        try:
            splash.set_progress(42, "正在加载计算组件…")

            self.assertEqual(splash._progress.value(), 42)
            self.assertEqual(splash._status_label.text(), "正在加载计算组件…")
            # U7②：百分比文字移到进度条**外**（条内文字压在填充块上
            # 只有 2.01:1，读不清），因此条内文字关闭、条外标签显示。
            self.assertFalse(splash._progress.isTextVisible())
            self.assertEqual(splash._percent_label.text(), "42%")
        finally:
            splash._programmatic_close = True
            splash.close()
            splash.deleteLater()
            self.app.processEvents()

    def test_splash_centers_identity_and_omits_extra_labels(self):
        from PyQt6.QtWidgets import QLabel
        from battery_soh_app import _StartupSplash

        splash = _StartupSplash()
        try:
            self.assertEqual(splash.objectName(), "startupSplash")
            self.assertEqual(splash.property("visualWorld"), "paperInk")
            self.assertEqual(splash._title_label.text(), "电池 SOH 评估系统")
            self.assertEqual(splash._identity_widget.objectName(), "splashIdentity")
            self.assertEqual(
                splash._identity_widget.geometry().center().x(),
                splash.rect().center().x(),
            )
            roles = {
                label.property("role") for label in splash.findChildren(QLabel)
            }
            self.assertNotIn("splashBadge", roles)
            self.assertNotIn("splashStage", roles)
        finally:
            splash._programmatic_close = True
            splash.close()
            splash.deleteLater()
            self.app.processEvents()


class EvaluationStartupFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication

        cls.app = QApplication.instance() or QApplication([])

    def test_start_evaluation_skips_deep_file_validation(self):
        from ui.main_window import MainWindow

        window = MainWindow()
        window.imported_paths = ["large-battery-folder"]
        started = []
        window._run_training = started.append

        try:
            with patch(
                    "core.validation.validate_evaluation_request",
                    return_value=[]) as deep_validation:
                window.start_evaluation()

            deep_validation.assert_not_called()
            self.assertEqual(len(started), 1)
        finally:
            _dispose_window(window, self.app)

    def test_main_window_starts_directly_with_sidebar_workspace(self):
        from PyQt6.QtWidgets import QLabel, QSplitter
        from ui.main_window import MainWindow

        window = MainWindow()
        try:
            central_layout = window.centralWidget().layout()
            # 工作区必须直接是「导航侧边栏 + 图表区」分栏，
            # 而不是落地页 / 向导；原先承载主题按钮的顶栏已移除。
            widgets = [
                central_layout.itemAt(index).widget()
                for index in range(central_layout.count())
            ]
            splitters = [w for w in widgets if isinstance(w, QSplitter)]
            self.assertEqual(len(splitters), 1)
            self.assertIs(splitters[0], window.main_splitter)
            self.assertIs(widgets[0], window.main_splitter)
            self.assertEqual(window.main_splitter.count(), 2)
            # 侧边栏 = 窄轨道 + 页面栈（数据/参数/结果/日志）
            self.assertEqual(window.sidebar_stack.count(), 4)
            # 主题按钮改为悬浮在中央控件上的圆形按钮（不再占一行顶栏）
            self.assertTrue(hasattr(window, 'theme_btn'))
            self.assertIs(window.theme_btn.parent(), window.centralWidget())
            self.assertFalse(hasattr(window, "workspace_header"))
            roles = {
                label.property("role") for label in window.findChildren(QLabel)
            }
            self.assertNotIn("workflowStep", roles)
            self.assertNotIn("topBarTitle", roles)
        finally:
            _dispose_window(window, self.app)

    def test_data_summary_tracks_imported_item_count(self):
        from ui.main_window import MainWindow

        window = MainWindow()
        try:
            self.assertIn("尚未导入", window.data_summary_label.text())
            window.imported_paths = ["cell-a.xlsx", "cell-b.xlsx"]
            window._update_data_summary()
            self.assertIn("2 项数据", window.data_summary_label.text())
        finally:
            _dispose_window(window, self.app)

    def test_run_indicator_follows_evaluation_state(self):
        from ui.main_window import MainWindow

        window = MainWindow()
        try:
            window._set_running_state(True, "正在训练模型")
            self.assertEqual(window.run_status_dot.property("state"), "running")
        finally:
            _dispose_window(window, self.app)

    def test_model_selection_surfaces_model_explanation(self):
        from ui.main_window import MainWindow

        window = MainWindow()
        try:
            window.select_mode("XGBoost")
            self.assertIn("梯度提升树", window.model_hint_label.text())
        finally:
            _dispose_window(window, self.app)

    def test_result_state_uses_structured_title_detail_and_guidance(self):
        from PyQt6.QtWidgets import QApplication, QFrame, QLabel
        from ui.main_window import MainWindow

        window = MainWindow()
        try:
            window._show_result_state("等待评估结果", "导入数据后显示。")
            roles = {
                label.property("role")
                for label in window.result_container.findChildren(QLabel)
            }
            self.assertTrue(
                {"resultStateTitle", "resultStateDetail", "resultStateGuide"}
                <= roles
            )
            frame_roles = {
                frame.property("role")
                for frame in window.result_container.findChildren(QFrame)
            }
            self.assertTrue(
                {"resultStateBattery", "resultStateBatteryFill"}
                <= frame_roles
            )
            self.assertEqual(
                window.result_container.property("role"), "resultContainer")
            self.assertIn(
                'QWidget[role="resultContainer"]',
                QApplication.instance().styleSheet(),
            )
        finally:
            _dispose_window(window, self.app)

    def test_result_state_guidance_matches_running_analysis(self):
        from PyQt6.QtWidgets import QLabel
        from ui.main_window import MainWindow

        window = MainWindow()
        try:
            window._show_result_state("正在分析电池数据", "训练日志持续更新。")
            guide = next(
                label for label in window.result_container.findChildren(QLabel)
                if label.property("role") == "resultStateGuide"
            )
            self.assertEqual(guide.text(), "读取数据 · 训练模型 · 生成指标")
        finally:
            _dispose_window(window, self.app)


if __name__ == "__main__":
    unittest.main()
