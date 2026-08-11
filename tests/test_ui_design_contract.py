from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class UiDesignContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main_window = (ROOT / "ui" / "main_window.py").read_text(encoding="utf-8")
        cls.style = (ROOT / "ui" / "style.py").read_text(encoding="utf-8")
        cls.chart = (ROOT / "ui" / "chart_show.py").read_text(encoding="utf-8")
        cls.button = (ROOT / "ui" / "animated_button.py").read_text(encoding="utf-8")

    def test_parameters_are_grouped_and_advanced_section_is_collapsible(self):
        self.assertIn("class CollapsibleSection", self.main_window)
        self.assertIn("电池与失效判据", self.main_window)
        self.assertIn("评估与验证", self.main_window)
        self.assertIn("模型高级参数", self.main_window)
        self.assertIn("expanded=False", self.main_window)

    def test_running_state_has_progress_and_stop_control(self):
        self.assertIn("def _set_running_state", self.main_window)
        self.assertIn("self.progress_bar.setRange(0, 0)", self.main_window)
        self.assertIn("self.pause_btn.setEnabled(False)", self.main_window)
        self.assertIn("self._set_running_state(True", self.main_window)

    def test_empty_and_loading_result_states_are_present(self):
        self.assertIn("def _show_result_state", self.main_window)
        self.assertIn("等待评估结果", self.main_window)
        self.assertIn("正在分析电池数据", self.main_window)

    def test_keyboard_focus_is_visible_across_core_controls(self):
        self.assertNotIn("outline: 0;", self.style)
        self.assertIn("QPushButton:focus", self.style)
        self.assertIn("QToolButton:focus", self.style)
        self.assertIn("QListWidget:focus", self.style)

    def test_palette_uses_one_accent_with_accessible_foreground_tokens(self):
        self.assertIn("'on_accent'", self.style)
        self.assertIn("'on_danger'", self.style)
        self.assertIn("DESIGN_LANGUAGE = '宣纸水墨'", self.style)
        self.assertIn("'paper'", self.style)
        self.assertIn("'ink'", self.style)
        self.assertIn("'cinnabar'", self.style)
        self.assertNotIn("'accent_p'", self.style)
        self.assertNotIn("'accent_b'", self.style)

    def test_chart_series_do_not_rely_on_color_alone(self):
        self.assertIn("pred_c      = '#6F7770'", self.chart)
        self.assertIn("linestyle='--'", self.chart)
        self.assertIn("marker='o'", self.chart)

    def test_chart_supports_independent_fullscreen_view(self):
        self.assertIn("class ChartFullscreenDialog", self.chart)
        self.assertIn("def mouseDoubleClickEvent", self.chart)
        self.assertIn("showFullScreen()", self.chart)
        self.assertIn("QKeySequence('Escape')", self.chart)

    def test_button_motion_is_restrained_to_click_feedback(self):
        self.assertNotIn("QGraphicsDropShadowEffect", self.button)
        self.assertNotIn("glowRadius", self.button)
        self.assertIn("_INK_BLOOM_DURATION", self.button)
        self.assertNotIn("_RIPPLE_DURATION", self.button)

    def test_button_rows_share_non_overlapping_layout_policy(self):
        self.assertIn("def _configure_button_row", self.main_window)
        self.assertGreaterEqual(self.main_window.count("_configure_button_row("), 5)

    def test_splitter_handles_are_uniform_and_narrow(self):
        self.assertGreaterEqual(self.main_window.count("setHandleWidth(2)"), 3)
        self.assertIn("QSplitter::handle:horizontal {{ width: 2px; }}", self.style)
        self.assertIn("QSplitter::handle:vertical   {{ height: 2px; }}", self.style)

    def test_folder_dialog_labels_are_localized(self):
        self.assertIn(
            "QFileDialog.DialogLabel.LookIn, '查找范围：'", self.main_window)
        self.assertIn(
            "QFileDialog.DialogLabel.FileName, '文件夹：'", self.main_window)
        self.assertIn(
            "QFileDialog.DialogLabel.FileType, '文件类型：'", self.main_window)

    def test_folder_dialog_views_have_readable_ink_theme(self):
        self.assertIn(
            "QFileDialog QTreeView, QFileDialog QListView", self.style)
        self.assertIn("QFileDialog QHeaderView::section", self.style)
        self.assertIn("selection-color: {COLORS['on_accent']};", self.style)

    def test_folder_dialog_entire_client_area_uses_paper_theme(self):
        self.assertIn("QFileDialog QToolButton", self.style)
        self.assertIn(
            "QFileDialog QLineEdit, QFileDialog QComboBox", self.style)
        self.assertIn("QFileDialog QPushButton", self.style)

    def test_folder_dialog_toolbar_tooltips_are_localized(self):
        self.assertIn("_FOLDER_DIALOG_TOOLTIPS", self.main_window)
        for tooltip in (
                '后退', '前进', '返回上一级', '新建文件夹',
                '列表视图', '详细信息视图'):
            self.assertIn(f"'{tooltip}'", self.main_window)
        self.assertIn("button.setToolTip(tooltip)", self.main_window)
        self.assertIn("button.setAccessibleName(tooltip)", self.main_window)

    def test_folder_dialog_requests_paper_colored_windows_caption(self):
        self.assertIn("def _apply_windows_paper_caption", self.main_window)
        self.assertIn("DWMWA_CAPTION_COLOR", self.main_window)
        self.assertIn("DwmSetWindowAttribute", self.main_window)

    def test_primary_actions_have_keyboard_shortcuts(self):
        self.assertIn("QKeySequence('Ctrl+Return')", self.main_window)
        self.assertIn("QKeySequence('F1')", self.main_window)

    def test_result_cards_prioritize_failure_status(self):
        self.assertIn("battery_group.setProperty('role', 'resultCard')", self.main_window)
        self.assertIn("setProperty('role', 'resultStatus')", self.main_window)
        status_position = self.main_window.index("fc = item.get('failure_cycle')")
        metric_position = self.main_window.index("# RMSE", status_position)
        self.assertLess(status_position, metric_position)


if __name__ == "__main__":
    unittest.main()
