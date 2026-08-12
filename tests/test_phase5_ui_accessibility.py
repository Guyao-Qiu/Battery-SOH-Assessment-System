import os
import unittest

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class Phase5RuntimeAccessibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from ui.main_window import MainWindow

        cls.app = QApplication.instance() or QApplication([])
        cls.window = MainWindow()
        cls.window.show()
        cls.app.processEvents()

    @classmethod
    def tearDownClass(cls):
        cls.window.deleteLater()
        cls.app.processEvents()

    def test_keyboard_focus_chain_reaches_primary_controls_in_actual_window(self):
        targets = {
            self.window.import_btn,
            self.window.import_list,
            self.window.adapter_combo,
            self.window.rated_capacity_spin,
            self.window.metric_combo,
            self.window.rnn_btn,
            self.window.load_model_btn,
            self.window.start_btn,
            self.window.save_chart_btn,
        }
        visited = set()
        self.window.import_btn.setFocus(Qt.FocusReason.TabFocusReason)
        self.app.processEvents()

        for _ in range(100):
            focused = self.app.focusWidget()
            if focused is not None:
                visited.add(focused)
            self.window.focusNextChild()
            self.app.processEvents()

        self.assertTrue(targets.issubset(visited),
                        f"焦点链遗漏：{targets - visited}")
        self.assertIn(":focus", self.app.styleSheet())

    def test_font_at_150_percent_keeps_core_controls_usable(self):
        original = QFont(self.app.font())
        scaled = QFont(original)
        base_size = original.pointSizeF()
        if base_size <= 0:
            base_size = 10.0
        scaled.setPointSizeF(base_size * 1.5)

        try:
            self.app.setFont(scaled)
            self.window.resize(1600, 900)
            self.app.processEvents()
            controls = (
                self.window.import_btn,
                self.window.rated_capacity_spin,
                self.window.metric_combo,
                self.window.start_btn,
                self.window.export_btn,
            )
            for control in controls:
                with self.subTest(control=control.__class__.__name__):
                    self.assertGreaterEqual(
                        control.height(), control.minimumSizeHint().height())
                    self.assertGreater(control.width(), 0)
        finally:
            self.app.setFont(original)
            self.app.processEvents()

    def test_window_uses_positive_device_pixel_ratio_for_high_dpi_rendering(self):
        screen = self.window.screen() or self.app.primaryScreen()

        self.assertIsNotNone(screen)
        self.assertGreater(screen.devicePixelRatio(), 0.0)
        self.assertGreater(screen.logicalDotsPerInch(), 0.0)
        self.assertGreater(self.window.devicePixelRatioF(), 0.0)


if __name__ == "__main__":
    unittest.main()
