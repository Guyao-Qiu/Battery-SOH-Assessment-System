import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np


os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')


def _chart_payload(names=('cell_a', 'cell_b')):
    battery_data = {
        name: {
            'capacity': np.asarray(
                [1.10 - 0.01 * index, 1.06 - 0.01 * index,
                 1.01 - 0.01 * index, 0.96 - 0.01 * index],
                dtype=np.float64,
            )
        }
        for index, name in enumerate(names)
    }
    predictions = {
        name: [1.10 - 0.01 * index, 1.05 - 0.01 * index,
               1.00 - 0.01 * index, 0.95 - 0.01 * index]
        for index, name in enumerate(names)
    }
    return list(names), battery_data, predictions


class FullscreenChartNavigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication

        cls.app = QApplication.instance() or QApplication([])

    def tearDown(self):
        from matplotlib import pyplot as plt

        plt.close('all')
        self.app.processEvents()

    def test_result_subplot_can_be_replayed_alone_in_fullscreen_canvas(self):
        from ui.chart_show import MplCanvas

        source = MplCanvas()
        names, battery_data, predictions = _chart_payload()
        source.plot_results(
            names, battery_data, predictions,
            rated_capacity=1.1, threshold_ratio=0.8,
        )
        target = MplCanvas(allow_fullscreen=False)

        source.replay_last_plot(target, subplot_key='cell_b')

        visible_axes = [axis for axis in target.fig.axes if axis.get_visible()]
        self.assertEqual(len(visible_axes), 1)
        self.assertIn('cell_b', visible_axes[0].get_title())
        self.assertNotIn('cell_a', visible_axes[0].get_title())

    def test_right_click_menu_offers_current_subplot_and_all_subplots(self):
        from ui.chart_show import MplCanvas

        canvas = MplCanvas()
        names, battery_data, predictions = _chart_payload()
        canvas.plot_results(
            names, battery_data, predictions,
            rated_capacity=1.1, threshold_ratio=0.8,
        )

        menu = canvas._build_fullscreen_menu('cell_b')
        actions = menu.actions()

        self.assertEqual(
            [action.text() for action in actions],
            ['全屏查看当前子图', '全屏查看全部子图'],
        )
        with patch.object(canvas, 'open_fullscreen') as open_fullscreen:
            actions[0].trigger()
            open_fullscreen.assert_called_once_with('cell_b')
            open_fullscreen.reset_mock()
            actions[1].trigger()
            open_fullscreen.assert_called_once_with(None)

    def test_chart_context_menu_uses_the_paper_ink_palette(self):
        from ui.style import GLOBAL_QSS

        self.assertIn('QMenu {', GLOBAL_QSS)
        self.assertIn('QMenu::item:selected', GLOBAL_QSS)
        self.assertIn('QMenu::item:disabled', GLOBAL_QSS)

    def test_fullscreen_wheel_zooms_around_pointer(self):
        from ui.chart_show import MplCanvas

        canvas = MplCanvas(
            allow_fullscreen=False, interactive_navigation=True)
        axis = canvas.ax
        axis.set_xlim(0.0, 10.0)
        axis.set_ylim(0.0, 10.0)
        before_x = axis.get_xlim()
        before_y = axis.get_ylim()

        canvas._on_scroll_zoom(SimpleNamespace(
            inaxes=axis, xdata=5.0, ydata=5.0, button='up'))

        after_x = axis.get_xlim()
        after_y = axis.get_ylim()
        self.assertLess(after_x[1] - after_x[0], before_x[1] - before_x[0])
        self.assertLess(after_y[1] - after_y[0], before_y[1] - before_y[0])
        self.assertAlmostEqual(sum(after_x) / 2.0, 5.0)
        self.assertAlmostEqual(sum(after_y) / 2.0, 5.0)

    def test_fullscreen_left_drag_pans_visible_region(self):
        from ui.chart_show import MplCanvas

        canvas = MplCanvas(
            allow_fullscreen=False, interactive_navigation=True)
        axis = canvas.ax
        axis.set_xlim(0.0, 10.0)
        axis.set_ylim(0.0, 10.0)
        canvas.draw()
        before_x = axis.get_xlim()
        before_y = axis.get_ylim()

        canvas._on_pan_press(SimpleNamespace(
            button=1, inaxes=axis, x=100.0, y=100.0))
        canvas._on_pan_motion(SimpleNamespace(
            inaxes=axis, x=150.0, y=130.0))
        canvas._on_pan_release(SimpleNamespace(button=1))

        self.assertNotEqual(axis.get_xlim(), before_x)
        self.assertNotEqual(axis.get_ylim(), before_y)
        self.assertIsNone(canvas._pan_state)


class RetrainingWindowWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication

        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from ui.main_window import MainWindow

        self.window = MainWindow()
        self.window.metric_combo.setCurrentText('RMSE')
        self.window.imported_paths = ['cell_a.csv']
        self.window.import_list.addItem('cell_a.csv')
        self.window._update_data_summary()

    def tearDown(self):
        from matplotlib import pyplot as plt

        windows = [self.window]
        windows.extend(getattr(self.window, '_child_training_windows', []))
        for window in windows:
            worker = getattr(window, 'worker', None)
            if worker is not None and worker.isRunning():
                worker.request_stop()
                worker.wait(5000)
            plt.close(window.canvas.fig)
            window.deleteLater()
        self.app.processEvents()

    def _complete_result(self, *, rmse, run_id):
        from core.run_snapshot import RunSnapshot

        config = self.window._build_config()
        self.window._active_run_snapshot = RunSnapshot.capture(
            config,
            self.window.imported_paths,
            run_id=run_id,
        )
        self.window._active_run_kind = 'training'
        capacity = np.asarray([1.10, 1.02, 0.94, 0.86])
        self.window.worker = SimpleNamespace(
            battery_dict={
                'cell_a': {
                    'capacity': capacity,
                    'cycle': np.asarray([1, 2, 3, 4]),
                }
            }
        )
        results = {
            'cell_a': {
                'score': rmse,
                'prediction': [1.10, 1.01, 0.93, 0.85],
                'detail': {
                    'battery': 'cell_a',
                    'cycles': 4,
                    'model': config.mode,
                    'rmse': rmse,
                    'mae': rmse / 2.0,
                    'r2': 0.9,
                    'pearson': 0.95,
                    're': 0.1,
                    'n_seeds': 1,
                },
            }
        }
        self.window.on_result(results, elapsed=1.5)
        self.window.worker = None

    def test_completed_runs_are_kept_as_separate_result_batches(self):
        self._complete_result(rmse=0.10, run_id='run-one')
        self._complete_result(rmse=0.20, run_id='run-two')

        self.assertEqual(self.window.result_batch_combo.count(), 2)
        self.assertEqual(self.window.result_batch_combo.currentIndex(), 1)
        self.assertIn('0.200000', self.window.result_summary_metric.text())

        self.window.result_batch_combo.setCurrentIndex(0)
        self.app.processEvents()

        self.assertIn('0.100000', self.window.result_summary_metric.text())
        self.assertEqual(self.window._last_run_snapshot.run_id, 'run-one')

    def test_current_window_retraining_clears_log_but_keeps_old_result(self):
        from ui.worker import EvalWorker

        self._complete_result(rmse=0.10, run_id='run-one')
        self.window.log_text.setPlainText('旧训练日志')
        config = self.window._build_config()

        with patch.object(EvalWorker, 'start', return_value=None):
            self.window._run_training(config)

        self.assertEqual(self.window.log_text.toPlainText(), '')
        self.assertEqual(self.window.result_batch_combo.count(), 1)
        # U1：旧结果仍保留在结果表里（结果表是常驻控件，不会被重建掉）
        self.assertEqual(len(self.window.result_model.rows()), 1)
        self.assertFalse(self.window.result_view.isHidden())

    def test_completed_training_prompts_before_reusing_current_window(self):
        self._complete_result(rmse=0.10, run_id='run-one')

        with patch.object(
                self.window, '_ask_training_destination',
                return_value='current') as ask_destination, patch.object(
                    self.window, '_run_training') as run_training:
            self.window.start_evaluation()

        ask_destination.assert_called_once_with()
        run_training.assert_called_once()

    def test_new_window_copies_inputs_and_parameters_then_starts_training(self):
        from ui.worker import EvalWorker

        self.window.select_mode('RF')
        self.window.epochs_spin.setValue(7)
        self.window.seed_spin.setValue(29)
        self._complete_result(rmse=0.10, run_id='run-one')
        expected_config = self.window._build_config().to_dict()

        with patch.object(
                self.window, '_ask_training_destination',
                return_value='new'), patch.object(
                    EvalWorker, 'start', return_value=None):
            self.window.start_evaluation()

        self.assertEqual(len(self.window._child_training_windows), 1)
        child = self.window._child_training_windows[0]
        self.assertIsNot(child, self.window)
        self.assertEqual(child.imported_paths, self.window.imported_paths)
        self.assertEqual(child.import_list.count(), 1)
        self.assertEqual(child._build_config().to_dict(), expected_config)
        self.assertEqual(child.result_batch_combo.count(), 0)
        self.assertIsNotNone(child.worker)
        self.assertIsNone(self.window.worker)
        self.assertTrue(hasattr(child, 'save_model_btn'))
        self.assertTrue(hasattr(child, 'export_btn'))

    def test_second_start_cannot_replace_worker_before_completion(self):
        from ui.worker import EvalWorker

        config = self.window._build_config()
        with patch.object(EvalWorker, 'start', return_value=None):
            self.window._run_training(config)
            first_worker = self.window.worker
            with patch('ui.main_window.show_message'):
                self.window.start_evaluation()

        self.assertIs(self.window.worker, first_worker)


if __name__ == '__main__':
    unittest.main()
