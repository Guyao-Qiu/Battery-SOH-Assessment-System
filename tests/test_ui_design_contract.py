from pathlib import Path
import unittest

from ui.style import COLORS, GLOBAL_QSS


ROOT = Path(__file__).resolve().parents[1]


def _relative_luminance(hex_color):
    channels = [int(hex_color[index:index + 2], 16) / 255
                for index in (1, 3, 5)]
    linear = [channel / 12.92 if channel <= 0.04045
              else ((channel + 0.055) / 1.055) ** 2.4
              for channel in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast_ratio(first, second):
    lighter, darker = sorted(
        (_relative_luminance(first), _relative_luminance(second)),
        reverse=True,
    )
    return (lighter + 0.05) / (darker + 0.05)


class ThemeToggleAndFontTests(unittest.TestCase):
    """U8：右上角主题切换 + 中文字体引导；默认深色（墨夜）。"""

    @classmethod
    def setUpClass(cls):
        import os

        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication

        cls.app = QApplication.instance() or QApplication([])

    def _dispose(self, window):
        """与其它 UI 测试一致：先关图，再删窗口（否则 matplotlib 留悬空引用）。"""
        import matplotlib.pyplot as plt

        try:
            plt.close(window.canvas.fig)
        except AttributeError:
            pass
        window.deleteLater()
        self.app.processEvents()

    def test_product_default_theme_is_dark(self):
        from theme_tokens import DEFAULT_THEME, THEMES
        from utils.config import THEME_UI

        self.assertEqual(DEFAULT_THEME, "dark")
        self.assertIn(DEFAULT_THEME, THEMES)
        # 界面上的主题名要有中文说法
        self.assertEqual(THEME_UI.get("dark"), "墨夜（深色）")
        self.assertEqual(THEME_UI.get("light"), "宣纸（浅色）")

    def test_theme_toggle_button_sits_in_the_top_right(self):
        from PyQt6.QtWidgets import QFrame

        from ui.main_window import MainWindow

        window = MainWindow()
        try:
            self.assertTrue(hasattr(window, "theme_btn"))
            bar = window.theme_btn.parentWidget()
            self.assertIsInstance(bar, QFrame)
            self.assertEqual(bar.property("role"), "topBar")
            self.assertEqual(window.theme_btn.objectName(), "themeToggle")
            # 顶部条必须在整个工作区之前（也就是视觉上的最上端）
            layout = window.centralWidget().layout()
            self.assertIs(layout.itemAt(0).widget(), bar)
            # 按钮靠右：顶部条里在它之前必须有一个 addStretch 产生的弹簧，
            # 且它是最后一个控件（结构上的右对齐，不依赖尚未完成布局的几何）。
            bar_layout = bar.layout()
            items = [bar_layout.itemAt(i) for i in range(bar_layout.count())]
            self.assertTrue(any(item.spacerItem() is not None
                                for item in items), '顶部条缺少弹簧，按钮不会靠右')
            last_widget = [item.widget() for item in items
                           if item.widget() is not None][-1]
            self.assertIs(last_widget, window.theme_btn)
        finally:
            self._dispose(window)

    def test_toggle_switches_between_the_two_themes(self):
        from ui.main_window import MainWindow

        window = MainWindow()
        try:
            window.apply_theme("dark")
            self.assertEqual(window._theme_mode, "dark")
            self.assertIn("墨夜", window.theme_btn.text())
            window.toggle_theme()
            self.assertEqual(window._theme_mode, "light")
            self.assertIn("宣纸", window.theme_btn.text())
            window.toggle_theme()
            self.assertEqual(window._theme_mode, "dark")
        finally:
            self._dispose(window)

    def test_theme_toggle_has_a_keyboard_shortcut_and_tooltip(self):
        window_source = (ROOT / "ui" / "main_window.py").read_text(
            encoding="utf-8")
        self.assertIn("QKeySequence('Ctrl+T')", window_source)
        self.assertIn("def toggle_theme", window_source)
        self.assertIn("_sync_theme_button", window_source)

    def test_fresh_install_defaults_to_dark_and_remembers_the_choice(self):
        """默认深色；用户切换后重启要沿用他自己的选择。

        用带版本号的设置键做一次性迁移：旧版本会把当时的默认值（浅色）
        自动写进 ``theme``，不换键的话「默认改深色」对老用户不会生效。
        """
        from PyQt6.QtCore import QSettings

        from theme_tokens import DEFAULT_THEME, THEME_SETTINGS_KEY
        from ui.main_window import MainWindow

        settings = QSettings("BatterySOH", "AssessmentSystem")
        saved = settings.value(THEME_SETTINGS_KEY)
        try:
            settings.remove(THEME_SETTINGS_KEY)
            settings.sync()
            window = MainWindow()
            try:
                self.assertEqual(window._theme_mode, DEFAULT_THEME)
                self.assertEqual(window._theme_mode, "dark")
                window.toggle_theme()
                self.assertEqual(window._theme_mode, "light")
            finally:
                self._dispose(window)

            reopened = MainWindow()
            try:
                self.assertEqual(reopened._theme_mode, "light",
                                 "用户显式选择的主题应当被记住")
            finally:
                self._dispose(reopened)
        finally:
            if saved is None:
                settings.remove(THEME_SETTINGS_KEY)
            else:
                settings.setValue(THEME_SETTINGS_KEY, saved)
            settings.sync()

    def test_chinese_font_is_installed_and_renders_glyphs(self):
        """中文必须真的有字形（不是方框）。

        在**子进程**里跑：``QFontDatabase`` 是本环境最脆弱的一环（Qt6/lib/fonts
        缺失），在已经建过控件的进程里调用它会让 PyQt6 段错误。子进程能拿到
        干净的解释器状态，同时不污染测试进程。
        """
        import subprocess
        import sys
        import textwrap

        script = textwrap.dedent(
            """
            import os, sys, warnings
            os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
            warnings.filterwarnings('ignore')
            sys.path.insert(0, r'%s')
            from PyQt6.QtWidgets import QApplication
            from PyQt6.QtGui import QFontMetrics
            app = QApplication([])
            from ui.fonts import install_fonts, diagnostics
            family = install_fonts(app)
            info = diagnostics()
            assert info['cjk_ok'], info
            assert family, '未能解析出 UI 字体族'
            metrics = QFontMetrics(app.font())
            missing = [c for c in '电池容量评估系统' if not metrics.inFont(c)]
            assert not missing, missing
            print('CJK_OK', family, info['family_count'])
            """
        ) % str(ROOT)
        result = subprocess.run(
            [sys.executable, '-X', 'utf8', '-c', script],
            capture_output=True, text=True, encoding='utf-8', timeout=180,
            cwd=str(ROOT),
        )
        self.assertEqual(result.returncode, 0,
                         result.stdout + result.stderr)
        self.assertIn('CJK_OK', result.stdout)

    def test_main_window_never_touches_the_font_database(self):
        """字体只在进程启动时装一次，窗口不得再碰 QFontDatabase。

        在控件已存在之后再调用 QFontDatabase 的静态方法，会让本环境里
        字体库缺失的 PyQt6 在后续绘制时段错误（0xC0000005）。
        """
        source = (ROOT / "ui" / "main_window.py").read_text(encoding="utf-8")
        # 只看代码，不看注释（注释里可以提到字体模块的名字）
        code = "\n".join(
            line for line in source.splitlines()
            if not line.lstrip().startswith("#"))
        self.assertNotIn("QFontDatabase", code)
        self.assertNotIn("ui.fonts", code)
        self.assertNotIn("install_fonts", code)
        # 启动入口负责装字体，且必须早于任何控件
        entry = (ROOT / "battery_soh_app.py").read_text(encoding="utf-8")
        self.assertIn("install_fonts(app)", entry)
        self.assertLess(entry.index("install_fonts(app)"),
                        entry.index("_StartupSplash()"))

    def test_font_candidates_cover_the_platforms_we_ship_on(self):
        from ui.fonts import (
            DISPLAY_FONT_FAMILIES,
            MONO_FONT_FAMILIES,
            UI_FONT_FAMILIES,
        )

        for chain in (UI_FONT_FAMILIES, DISPLAY_FONT_FAMILIES,
                      MONO_FONT_FAMILIES):
            self.assertTrue(chain)
            self.assertTrue(all(isinstance(name, str) for name in chain))
        joined = " ".join(UI_FONT_FAMILIES)
        # 三大平台的代表字体都要在候选链里
        for expected in ("Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC"):
            self.assertIn(expected, joined)

    def test_qss_gives_the_tab_bar_an_explicit_background(self):
        """页签栏空白区若不显式着色，浅色主题下会露出一块黑条。"""
        from ui.style import build_qss
        from theme_tokens import THEMES

        for name, tokens in THEMES.items():
            with self.subTest(theme=name):
                qss = build_qss(tokens)
                self.assertIn("QTabBar {", qss)
                tab_bar_rule = qss.split("QTabBar {", 1)[1].split("}", 1)[0]
                self.assertIn("background:", tab_bar_rule)
                self.assertIn("qproperty-drawBase: 0", tab_bar_rule)


class ChartTickDensityTests(unittest.TestCase):
    """U9：刻度要密到能直接读数，而不是靠目测估。"""

    def test_nice_step_is_human_friendly(self):
        from ui.chart_show import nice_step

        for span, divisions in ((1.0, 12), (0.72, 12), (140.0, 12),
                                (0.05, 12), (9.0, 12)):
            with self.subTest(span=span):
                step = nice_step(span, divisions)
                mantissa = step / 10 ** int(
                    __import__("math").floor(__import__("math").log10(step)))
                self.assertIn(round(mantissa, 6), (1.0, 2.0, 2.5, 5.0, 10.0))
                # 步长要真的把区间切到接近目标条数，不能太稀
                self.assertGreaterEqual(span / step, divisions * 0.5)

    def test_focused_ylim_returns_enough_ticks(self):
        import numpy as np

        from ui.chart_show import _focused_ylim

        series = [np.linspace(2.0, 1.29, 140), np.linspace(1.9, 1.35, 140)]
        y_lo, y_hi, ticks = _focused_ylim(series, 2.0, 1.4)
        self.assertGreaterEqual(len(ticks), 7)
        self.assertLessEqual(len(ticks), 20)
        # 所有刻度都必须落在可视区间内（否则会被裁掉，白占位置）
        self.assertTrue(all(y_lo - 1e-9 <= t <= y_hi + 1e-9 for t in ticks))
        # 步长均匀
        spans = np.diff(ticks)
        self.assertTrue(np.allclose(spans, spans[0]))

    def test_tick_labels_are_distinguishable_and_cycle_axis_is_integer(self):
        from ui.chart_show import _format_tick, _tick_decimals

        # 周期数是整数，不该显示成 "20.00"
        self.assertEqual(_format_tick(20.0, 20.0), "20")
        self.assertEqual(_format_tick(140.0, 20.0), "140")
        self.assertEqual(_format_tick(0.0, 20.0), "0")
        # 容量小结度按需保留小数位，且刚好够用
        self.assertEqual(_format_tick(1.3, 0.1), "1.3")
        self.assertEqual(_format_tick(1.25, 0.05), "1.25")
        self.assertEqual(_format_tick(2.5, 2.5), "2.5")
        # 关键：相邻刻度不能显示成同一个标签
        for step in (0.1, 0.05, 0.25, 2.5, 20.0, 0.02):
            with self.subTest(step=step):
                labels = [_format_tick(step * i, step) for i in range(1, 6)]
                self.assertEqual(len(set(labels)), len(labels), labels)
        self.assertEqual(_tick_decimals(20.0), 0)
        self.assertEqual(_tick_decimals(0.1), 1)
        self.assertEqual(_tick_decimals(0.05), 2)

    def test_chart_renders_dense_ticks_with_integer_cycles(self):
        import os

        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        import matplotlib.pyplot as plt
        import numpy as np
        import pandas as pd
        from PyQt6.QtWidgets import QApplication

        from ui.chart_show import MplCanvas
        from ui.fonts import install_fonts

        app = QApplication.instance() or QApplication([])
        install_fonts(app)

        n = 140
        progress = np.arange(n) / (n - 1)
        shape = 0.55 * progress + 0.45 * (
            np.exp(3.2 * progress) - 1) / (np.exp(3.2) - 1)
        capacity = 2.0 - 0.71 * shape
        frame = pd.DataFrame({
            'cycle': np.arange(1, n + 1),
            'capacity': capacity.astype(np.float32)})

        canvas = MplCanvas()
        try:
            canvas.plot_results(
                ['CS2_35'], {'CS2_35': frame},
                {'CS2_35': capacity.tolist()}, 2.0, 0.7)
            axis = canvas.figure.axes[0]
            canvas.figure.canvas.draw()

            x_labels = [t.get_text() for t in axis.get_xticklabels()
                        if t.get_text()]
            y_labels = [t.get_text() for t in axis.get_yticklabels()
                        if t.get_text()]
            # 周期轴：整数、且条数够密
            self.assertTrue(x_labels)
            for label in x_labels:
                self.assertNotIn('.', label, f'周期刻度不该有小数: {x_labels}')
            self.assertGreaterEqual(len(x_labels), 6)
            # 容量轴：至少 7 条主刻度，且能区分到 0.1 Ah
            self.assertGreaterEqual(len(y_labels), 7)
            self.assertGreaterEqual(
                len(set(y_labels)), len(y_labels), '刻度标签重复了')
            # 还有次刻度提供更细的读数
            self.assertGreater(len(axis.get_yticks(minor=True)), 0)
            self.assertGreater(len(axis.get_xticks(minor=True)), 0)
        finally:
            # 必须显式关掉图：matplotlib 的全局 figure 管理器会留下悬空引用，
            # 后续测试再触发一次 draw 就会访问已析构的 canvas（实测会段错误）。
            plt.close(canvas.figure)
            canvas.deleteLater()
            app.processEvents()


class UiDesignContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main_window = (ROOT / "ui" / "main_window.py").read_text(encoding="utf-8")
        cls.style = (ROOT / "ui" / "style.py").read_text(encoding="utf-8")
        cls.chart = (ROOT / "ui" / "chart_show.py").read_text(encoding="utf-8")
        cls.button = (ROOT / "ui" / "animated_button.py").read_text(encoding="utf-8")
        cls.readme = (ROOT / "README.md").read_text(encoding="utf-8")

    def test_project_name_is_consistent_in_window_and_readme(self):
        project_name = 'Battery SOH Assessment System'
        self.assertIn(f"self.setWindowTitle('{project_name}')", self.main_window)
        self.assertTrue(self.readme.startswith(f'# {project_name}\n'))
        self.assertIn(
            'github.com/Guyao-Qiu/Battery-SOH-Assessment-System.git',
            self.readme,
        )

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
        self.assertIn("QTextEdit:focus", self.style)
        self.assertIn("QPlainTextEdit:focus", self.style)

    def test_role_specific_disabled_buttons_are_visually_neutral(self):
        for role in ("primary", "success", "danger"):
            self.assertIn(
                f'QPushButton[role="{role}"]:disabled',
                GLOBAL_QSS,
            )

    def test_palette_uses_one_accent_with_accessible_foreground_tokens(self):
        # C1 后颜色收敛到 theme_tokens.py，ui/style.py 只渲染 QSS。
        self.assertIn("'on_accent'", self.style)
        self.assertIn("'on_danger'", self.style)
        self.assertIn("DESIGN_LANGUAGE = '宣纸水墨'", self.style)
        self.assertIn("from theme_tokens import", self.style)
        self.assertIn("def build_qss(", self.style)
        self.assertNotIn("'accent_p'", self.style)
        self.assertNotIn("'accent_b'", self.style)

    def test_numeric_wheel_selection_uses_readable_ochre_pair(self):
        # 默认主题改为深色（墨夜）后，COLORS 指向深色 token；
        # 这里断言的是**契约**（可读的赭石选中配对 + 足够对比度），
        # 而不是某一个写死的十六进制值。
        from theme_tokens import THEMES

        self.assertIn('spin_selection', COLORS)
        self.assertIn('on_selection', COLORS)
        self.assertIn('spin_selection', THEMES['light'])
        self.assertIn('spin_selection', THEMES['dark'])
        # C1 后 QSS 里的色值来自 token，因此断言渲染结果而不是源码字面量。
        self.assertIn(
            "QSpinBox, QDoubleSpinBox {\n"
            f"    selection-background-color: {COLORS['spin_selection']};\n"
            f"    selection-color: {COLORS['on_selection']};\n"
            "}",
            GLOBAL_QSS,
        )
        for name, tokens in THEMES.items():
            with self.subTest(theme=name):
                self.assertGreaterEqual(
                    _contrast_ratio(tokens['spin_selection'],
                                    tokens['on_selection']),
                    4.5,
                )

    def test_combo_box_uses_drawn_down_arrow_instead_of_border_trick(self):
        arrow_path = ROOT / 'assets' / 'icons' / 'combo-down-arrow.svg'
        self.assertTrue(arrow_path.is_file())
        arrow_svg = arrow_path.read_text(encoding='utf-8')
        self.assertIn('<path', arrow_svg)
        self.assertIn('stroke="#315B5A"', arrow_svg)
        self.assertIn('image: url(', GLOBAL_QSS)
        arrow_rule = GLOBAL_QSS.split(
            'QComboBox::down-arrow {', 1)[1].split('}', 1)[0]
        self.assertNotIn('border-top:', arrow_rule)

    def test_chart_series_do_not_rely_on_color_alone(self):
        # C2 后语义分层：事实用中性墨色，模型输出用强调色，失效用朱砂。
        # 三条线不再只靠颜色区分——同时用线型、标记和主题 token。
        self.assertIn("chart_measured", self.chart)
        self.assertIn("chart_forecast", self.chart)
        self.assertIn("chart_threshold", self.chart)
        self.assertIn("linestyle", self.chart)
        self.assertIn("marker=", self.chart)

    def test_chart_toolbar_keeps_only_high_frequency_actions(self):
        from ui.chart_show import CustomToolbar

        labels = [item[0] for item in CustomToolbar.toolitems if item[0]]
        self.assertEqual(labels, ['Home', 'Pan', 'Zoom', 'Save'])

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

    def test_splitter_lines_stay_narrow_with_a_usable_left_hit_target(self):
        self.assertIn("self.main_splitter.setHandleWidth(2)", self.main_window)
        self.assertIn("self.left_splitter.setHandleWidth(10)", self.main_window)
        self.assertIn("QSplitter::handle:horizontal {{ width: 2px; }}", self.style)
        self.assertIn("QSplitter::handle:vertical   {{ height: 2px; }}", self.style)
        self.assertIn(
            "QSplitter#leftPanelSplitter::handle:vertical {{",
            self.style,
        )
        self.assertIn("stop: 0.40 {COLORS['border']}", self.style)
        self.assertIn("stop: 0.60 {COLORS['border']}", self.style)

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

    def test_result_table_prioritizes_failure_status_and_is_sortable(self):
        """U1：结果区从「N 张卡片竖排」改为可排序表格 + 汇总行。"""
        self.assertIn("ResultTableModel", self.main_window)
        self.assertIn("QSortFilterProxyModel", self.main_window)
        self.assertIn("setSortRole(Qt.ItemDataRole.UserRole)", self.main_window)
        self.assertIn("setSortingEnabled(True)", self.main_window)
        self.assertIn("def _rebuild_result_rows", self.main_window)
        self.assertIn("def _copy_result_table", self.main_window)
        self.assertIn("def _export_result_csv", self.main_window)

    def test_result_table_marks_models_that_lose_to_persistence(self):
        """A3：技能分 < 0.05 必须有可见提示。"""
        from ui.result_model import SKILL_WARNING_THRESHOLD
        self.assertLessEqual(SKILL_WARNING_THRESHOLD, 0.05)
        result_source = (ROOT / "ui" / "result_model.py").read_text(
            encoding="utf-8")
        self.assertIn("未超越持久性基线", result_source)

    def test_theme_can_switch_between_light_and_dark(self):
        """C5：浅 / 深主题可切换。"""
        from theme_tokens import DARK, LIGHT, THEMES
        self.assertEqual(set(THEMES), {"light", "dark"})
        self.assertIn("def toggle_theme", self.main_window)
        self.assertIn("def apply_theme", self.style)
        self.assertNotEqual(DARK["bg_base"], LIGHT["bg_base"])
        self.assertNotEqual(DARK["text"], LIGHT["text"])

    def test_result_table_shows_baselines_summary_and_alpha_warning(self):
        """§8 验收：基线并排 + 汇总行 + α<0.05 可见提示。"""
        import os

        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication

        from ui.main_window import MainWindow
        from ui.result_model import COLUMNS, ResultTableModel

        app = QApplication.instance() or QApplication([])
        window = MainWindow()
        detail = {
            "battery": "cell", "cycles": 120, "model": "RF", "rmse": 0.2,
            "mae": 0.15, "r2": 0.5, "pearson": 0.9, "re": None,
            "n_seeds": 1, "persistence_blend": 0.0,
            "rmse_skill_vs_persistence": 0.0, "primary_start_frac": 0.5,
            "rolling_rows": [{
                "start_frac": 0.5, "start": 60, "battery": "cell",
                "rmse": 0.2, "mae": 0.15, "true_rul": 40, "pred_rul": None,
                "rul_err": None, "rul_rel_err": None, "within_20pct": None,
                "status": "pred_censored"}],
            "rolling": {"per_start": {0.5: {
                "n": 1, "rmse": 0.2, "mae": 0.15, "detected": 0,
                "needs_detection": 1, "mean_abs_rul_err": None, "skill": 0.0}},
                "overall": {"n": 1, "rmse": 0.2, "mae": 0.15, "detected": 0,
                            "needs_detection": 1, "mean_abs_rul_err": None,
                            "skill": 0.0}},
            "baselines": {"平推基线": {"rmse": 0.2}, "线性外推": {"rmse": 0.18},
                          "双指数": {"rmse": 0.25}},
        }
        try:
            window.metric_combo.setCurrentText("RMSE")
            window.update_result_table([detail], elapsed=1.0)

            # ① α < 0.05 必须有可见提示
            self.assertIn("未超越平推基线", window.result_notes.text())
            # ② 三条基线并排
            baselines = [row["name"] for row in window.result_model.rows()
                         if row.get("is_baseline")]
            self.assertEqual(baselines, ["平推基线", "线性外推", "双指数"])
            # ③ 汇总行：n = 电池数
            display = window.result_model.display_rows()
            self.assertTrue(display[-1].get("is_summary"))
            self.assertEqual(display[-1]["n_batteries"], 1)
            # ④ 技能分单元格带 ⚠
            skill_index = [i for i, column in enumerate(COLUMNS)
                           if column[1] == "skill"][0]
            text = window.result_model._display_text(
                display[0], "skill",
                ResultTableModel._cell_value(display[0], "skill"),
                COLUMNS[skill_index][2])
            self.assertTrue(text.startswith("⚠"), text)
            # ⑤ 可排序，且用原始值排序
            from PyQt6.QtCore import Qt
            self.assertTrue(window.result_view.isSortingEnabled())
            self.assertEqual(window.result_view.model().sortRole(),
                             Qt.ItemDataRole.UserRole)
        finally:
            # 先关掉 matplotlib 图，否则全局 figure 管理器会留下悬空 canvas 引用
            import matplotlib.pyplot as plt

            plt.close(window.canvas.fig)
            window.deleteLater()
            app.processEvents()


if __name__ == "__main__":
    unittest.main()
