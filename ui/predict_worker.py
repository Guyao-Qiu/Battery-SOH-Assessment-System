from copy import deepcopy
import time
import numpy as np

from PyQt6.QtCore import QThread, pyqtSignal

from core.prediction import predict_capacity_batch
from core.train import evaluate_prediction_protocols


METRIC_LABELS = {
    'rmse': 'RMSE',
    'mae': 'MAE',
    'r2': 'R²',
    'pearson': 'Pearson',
    're': 'RE',
}


def evaluate_loaded_sequence(model, metadata, capacity, threshold_ratio,
                             device='cpu'):
    """Evaluate a loaded model with the same metrics and protocols as training."""
    capacity = np.asarray(capacity, dtype=np.float32).reshape(-1)
    window_size = int(metadata['window_size'])
    rated_capacity = float(metadata['rated_capacity'])

    def predict_batch(windows):
        return predict_capacity_batch(
            model, metadata, windows, device=device)

    protocols = evaluate_prediction_protocols(
        capacity, window_size, predict_batch,
        rated_capacity, threshold_ratio)
    one_step = protocols['one_step']
    recursive = protocols['recursive']
    metrics = dict(one_step['metrics'])
    metrics['re'] = protocols['rul_re']
    metrics['re_status'] = recursive['metrics'].get('re_status')
    prediction = capacity[:window_size].tolist()
    prediction.extend(one_step['prediction'].tolist())
    detail = {
        **metrics,
        'one_step_metrics': one_step['metrics'],
        'recursive_metrics': recursive['metrics'],
        'one_step_prediction': one_step['prediction'].tolist(),
        'recursive_prediction': recursive['prediction'].tolist(),
        'rul_protocol': 'recursive_future',
    }
    return prediction, detail


def summarize_selected_metrics(detail_list, metric):
    """Return means for the selected metric, or all five metric means."""
    if not detail_list:
        return {}
    if metric == 'all':
        keys = tuple(METRIC_LABELS)
    elif metric in METRIC_LABELS:
        keys = (metric,)
    else:
        raise ValueError(f'不支持的评估指标: {metric}')
    return {
        key: mean_available_metric([item.get(key) for item in detail_list])
        for key in keys
    }


def mean_available_metric(values):
    available = [
        float(value) for value in values
        if value is not None and np.isfinite(value)
    ]
    if not available:
        return None
    return float(np.mean(available))


def _format_metric(value):
    return 'N/A（截尾）' if value is None else f'{value:.6f}'


class PredictWorker(QThread):
    log_signal = pyqtSignal(str)
    result_signal = pyqtSignal(object, float)
    error_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, model, metadata, imported_paths, config, parent=None):
        super().__init__(parent)
        self._model = model
        self._metadata = metadata
        self.imported_paths = tuple(deepcopy(imported_paths))
        self.battery_dict = {}
        self.battery_list = []
        self.config = deepcopy(config)
        self._stop_requested = False

    def request_stop(self):
        self._stop_requested = True
        self.requestInterruption()

    def stop_requested(self):
        return self._stop_requested or self.isInterruptionRequested()

    def run(self):
        try:
            start_time = time.time()

            from core.dataload import load_battery_from_paths
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
                self.error_signal.emit('未成功加载任何有效电池数据。')
                self.finished_signal.emit()
                return

            mode = self._metadata['mode']
            window_size = self._metadata['window_size']
            rated_capacity = self._metadata.get('rated_capacity', self.config.rated_capacity)
            threshold_ratio = self.config.threshold_ratio
            device = self.config.device

            results = {}

            for name in self.battery_list:
                if self._stop_requested:
                    break
                if name not in self.battery_dict:
                    continue
                capacity = self.battery_dict[name]['capacity'].tolist()
                if len(capacity) <= window_size + 1:
                    self.log_signal.emit(f'跳过 {name}：循环数不足（需>{window_size}）')
                    continue

                self.log_signal.emit(
                    f'[{name}] 预测中，测试样本 {len(capacity) - window_size}...')

                try:
                    prediction, detail = evaluate_loaded_sequence(
                        self._model, self._metadata, capacity,
                        threshold_ratio=threshold_ratio, device=device)
                    detail.update({
                        'battery': name,
                        'cycles': len(capacity),
                        'model': mode,
                    })
                    selected_score = (
                        detail['rmse'] if self.config.metric == 'all'
                        else detail[self.config.metric]
                    )
                    results[name] = {
                        'score': (
                            float(selected_score)
                            if selected_score is not None else None),
                        'prediction': list(prediction),
                        'detail': detail,
                    }
                    self.log_signal.emit(
                        f'[{name}] RMSE={detail["rmse"]:.4f} '
                        f'MAE={detail["mae"]:.4f} R²={detail["r2"]:.4f} '
                        f'Pearson={detail["pearson"]:.4f} '
                        f'RE(递归)={_format_metric(detail["re"])}')
                except Exception as e:
                    self.log_signal.emit(f'[{name}] 预测异常：{e}')
                    continue

            detail_list = [
                result['detail'] for result in results.values()
            ]
            summaries = summarize_selected_metrics(
                detail_list, self.config.metric)
            if self.config.metric == 'all':
                self.log_signal.emit('各电池全部指标已计算：')
                for item in detail_list:
                    self.log_signal.emit(
                        f'  {item["battery"]}：' + '，'.join(
                            f'{METRIC_LABELS[key]}='
                            f'{_format_metric(item.get(key))}'
                            for key in METRIC_LABELS))
                for key, value in summaries.items():
                    self.log_signal.emit(
                        f'→ 平均 {METRIC_LABELS[key]}: '
                        f'{_format_metric(value)}')
            else:
                metric_name = METRIC_LABELS[self.config.metric]
                self.log_signal.emit(f'各电池 {metric_name} 分数：')
                for item in detail_list:
                    self.log_signal.emit(
                        f'  {item["battery"]}：'
                        f'{_format_metric(item.get(self.config.metric))}')
                if summaries:
                    self.log_signal.emit(
                        f'→ 平均 {metric_name}: '
                        f'{_format_metric(summaries[self.config.metric])}')

            elapsed = time.time() - start_time
            self.result_signal.emit(results, elapsed)
            self.finished_signal.emit()
        except Exception as e:
            import traceback
            self.error_signal.emit(f'{e}\n{traceback.format_exc()}')
            self.finished_signal.emit()
