import time
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

from core.dataload import load_battery_from_paths
from core.train import train
from utils.config import TrainConfig


class EvalWorker(QThread):
    log_signal = pyqtSignal(str)
    result_signal = pyqtSignal(list, list, list, float)
    error_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    progress_signal = pyqtSignal(int, int)
    final_model_signal = pyqtSignal(object, dict)

    def __init__(self, config, imported_paths, parent=None):
        super().__init__(parent)
        self.config = config
        self.imported_paths = imported_paths
        self._stop_requested = False
        self.battery_dict = {}
        self.battery_list = []

    def request_stop(self):
        self._stop_requested = True
        self.requestInterruption()

    def stop_requested(self):
        return self._stop_requested or self.isInterruptionRequested()

    def run(self):
        try:
            start_time = time.time()

            self.log_signal.emit('开始加载数据...')
            self.battery_dict, self.battery_list = load_battery_from_paths(
                self.imported_paths,
                log_callback=self.log_signal.emit,
                stop_flag=self.stop_requested,
                voltage_upper=self.config.voltage_upper,
                voltage_lower=self.config.voltage_lower,
                adapter_type=self.config.adapter_type,
                cc_step=self.config.cc_step,
                cv_step=self.config.cv_step,
                discharge_step=self.config.discharge_step,
            )

            if len(self.battery_dict) == 0:
                self.error_signal.emit('未成功加载任何有效电池数据，请检查所选路径中是否包含符合格式的 .xlsx 或 .csv 文件。')
                self.finished_signal.emit()
                return

            if self._stop_requested:
                self.log_signal.emit('数据加载已被用户停止。')
                self.finished_signal.emit()
                return

            self.log_signal.emit('────────────────────────────────────────')
            self.log_signal.emit('开始训练评估...')
            self.log_signal.emit(
                f"<span style='color:#FFD54F; font-weight:bold;'>"
                f'留一法验证：共 {len(self.battery_list)} 个电池，每次留 1 个作测试、其余训练，'
                f'随机种子固定为 {self.config.seed}，确保结果可复现'
                f'</span>'
            )

            score_list, pred_list, detail = train(
                config=self.config,
                battery_dict=self.battery_dict,
                battery_list=self.battery_list,
                stop_flag=self.stop_requested,
                log_callback=self.log_signal.emit
            )

            if self._stop_requested:
                self.log_signal.emit('训练已被用户停止。')
                self.finished_signal.emit()
                return

            self.log_signal.emit('────────────────────────────────────────')
            self.log_signal.emit('正在基于全部数据训练最终模型...')
            try:
                from core.model_persistence import train_model_on_all_data
                final_model, final_metadata = train_model_on_all_data(
                    config=self.config,
                    battery_dict=self.battery_dict,
                    battery_list=self.battery_list,
                    stop_flag=self.stop_requested,
                    log_callback=self.log_signal.emit
                )
                self.final_model_signal.emit(final_model, final_metadata)
                self.log_signal.emit('最终模型训练完成，可点击"保存模型"导出。')
            except Exception as e:
                from core.cancellation import TrainingCancelled
                if isinstance(e, TrainingCancelled):
                    raise
                self.log_signal.emit(f'最终模型训练失败：{e}')

            self.log_signal.emit('\n\n')
            metric_name = {
                'rmse': 'RMSE', 'mae': 'MAE', 'r2': 'R²',
                'pearson': 'Pearson', 're': 'RE', 'all': '全部'
            }.get(self.config.metric, self.config.metric)
            self.log_signal.emit(
                f"<span style='color:#FFD54F; font-weight:bold;'>"
                f'各电池 {metric_name} 分数：'
                f'</span>'
            )
            for i, name in enumerate(self.battery_list):
                if i >= len(detail):
                    break
                item = detail[i]
                ci = item.get('ci', {})
                n_seeds = item.get('n_seeds', 1)
                if n_seeds > 1 and 'rmse' in ci:
                    c = ci['rmse']
                    self.log_signal.emit(
                        f'  {name}：RMSE={c["mean"]:.6f} ± {c["std"]:.6f} '
                        f'95%CI=[{c["lower"]:.6f}, {c["upper"]:.6f}]')
                else:
                    score = score_list[i][0] if isinstance(score_list[i], list) else score_list[i]
                    self.log_signal.emit(f'  {name}：{score:.6f}')
            if len(score_list) != 0:
                avg = np.mean(np.array(score_list))
                self.log_signal.emit(f'→ 平均 {metric_name}: {avg:.6f}')
                hint_map = {
                    'rmse': 'RMSE 为均方根误差（Ah），越小越准，<0.02 优秀、<0.05 良好',
                    'mae': 'MAE 为平均绝对误差，越小越准，对离群点不敏感',
                    'r2': 'R² 为决定系数，越接近 1 越好，反映模型解释力',
                    'pearson': 'Pearson 相关系数衡量预测与真实值的线性相关度，越接近 1 越好',
                    're': 'RE 为寿命预测误差（0~1），越小越准',
                    'all': '已展示全部指标',
                }
                hint = hint_map.get(self.config.metric, '')
                if hint:
                    self.log_signal.emit(
                        "<span style='color:#FFD54F; font-weight:bold;'>"
                        + hint + '</span>')
            else:
                self.log_signal.emit(f'平均 {metric_name}: 0.0000')

            elapsed = time.time() - start_time
            hours, rem = divmod(elapsed, 3600)
            minutes, seconds = divmod(rem, 60)
            if hours > 0:
                time_str = f'{int(hours)}小时{int(minutes)}分{seconds:.1f}秒'
            elif minutes > 0:
                time_str = f'{int(minutes)}分{seconds:.1f}秒'
            else:
                time_str = f'{seconds:.1f}秒'
            self.log_signal.emit(f'训练总耗时：{time_str}')
            self.result_signal.emit(score_list, pred_list, detail, elapsed)
            self.finished_signal.emit()
        except Exception as e:
            from core.cancellation import TrainingCancelled
            if isinstance(e, TrainingCancelled):
                self.log_signal.emit('训练已在安全检查点停止。')
                self.finished_signal.emit()
                return
            import traceback
            self.error_signal.emit(f'{e}\n{traceback.format_exc()}')
            self.finished_signal.emit()
