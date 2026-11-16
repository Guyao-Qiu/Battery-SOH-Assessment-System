from math import sqrt
import numpy as np
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

from core.result_semantics import first_failure_index


def _first_failure_index(values, threshold):
    """失效判定委托给 ``core.result_semantics``，全工程只有一处实现。"""
    return first_failure_index(values, threshold)


def relative_error_details(y_test, y_predict, threshold):
    """Return RE with an explicit observed/censored status."""
    true_re = _first_failure_index(y_test, threshold)
    pred_re = _first_failure_index(y_predict, threshold)

    if true_re == 0:
        status = 'observed_initial_failure'
        value = None
    elif true_re is None and pred_re is None:
        status = 'both_censored'
        value = None
    elif true_re is None:
        status = 'observed_censored'
        value = None
    elif pred_re is None:
        status = 'prediction_censored'
        value = None
    elif pred_re == 0:
        status = 'prediction_initial_failure'
        value = None
    else:
        status = 'observed'
        value = abs(true_re - pred_re) / true_re

    return {
        'value': value,
        'status': status,
        'true_crossing_index': true_re,
        'predicted_crossing_index': pred_re,
    }


def relative_error(y_test, y_predict, threshold):
    return relative_error_details(y_test, y_predict, threshold)['value']


def relative_error_reference(y_test, y_predict, threshold):
    """参考仓库（XiuzeZhou/RUL）公式计算的相对误差 RE：``abs(true - pred) / true``，上限 1.0。"""
    y_test = np.asarray(y_test, dtype=np.float64).reshape(-1)
    y_predict = np.asarray(y_predict, dtype=np.float64).reshape(-1)
    if len(y_test) == 0 or len(y_predict) == 0:
        return None
    true_re, pred_re = len(y_test), 0
    for i in range(len(y_test) - 1):
        if y_test[i] <= threshold >= y_test[i + 1]:
            true_re = i - 1
            break
    for i in range(len(y_predict) - 1):
        if y_predict[i] <= threshold:
            pred_re = i - 1
            break
    if true_re <= 0:
        return None
    val = abs(true_re - pred_re) / true_re
    return float(val if val <= 1.0 else 1.0)


def evaluation(y_test, y_predict):
    """RMSE"""
    return sqrt(mean_squared_error(y_test, y_predict))


def calc_mae(y_test, y_predict):
    """平均绝对误差"""
    return mean_absolute_error(y_test, y_predict)


def calc_r2(y_test, y_predict):
    """决定系数 R²"""
    if len(y_test) < 2:
        return 0.0
    return r2_score(y_test, y_predict)


def calc_pearson(y_test, y_predict):
    """Pearson 相关系数"""
    y_test = np.asarray(y_test, dtype=np.float64)
    y_predict = np.asarray(y_predict, dtype=np.float64)
    if len(y_test) < 2:
        return 0.0
    std_t = np.std(y_test)
    std_p = np.std(y_predict)
    if std_t < 1e-12 or std_p < 1e-12:
        return 0.0
    return float(np.corrcoef(y_test, y_predict)[0, 1])


def calc_all_metrics(y_test, y_predict, rated_capacity=None, threshold_ratio=None):
    """一次性计算全部指标，返回 dict"""
    y_test = np.asarray(y_test, dtype=np.float64).reshape(-1)
    y_predict = np.asarray(y_predict, dtype=np.float64).reshape(-1)
    if len(y_test) == 0 or len(y_predict) == 0:
        raise ValueError('真实值和预测值必须为非空序列')
    if len(y_test) != len(y_predict):
        raise ValueError('真实值和预测值长度必须一致')
    if not np.all(np.isfinite(y_test)) or not np.all(np.isfinite(y_predict)):
        raise ValueError('真实值和预测值必须全部为有限数值')
    metrics = {
        'rmse': evaluation(y_test, y_predict),
        'mae': calc_mae(y_test, y_predict),
        'r2': calc_r2(y_test, y_predict),
        'pearson': calc_pearson(y_test, y_predict),
    }
    if rated_capacity is not None and threshold_ratio is not None:
        threshold = rated_capacity * threshold_ratio
        re_result = relative_error_details(
            y_test, y_predict, threshold)
        metrics['re'] = re_result['value']
        metrics['re_status'] = re_result['status']
        metrics['true_eol_index'] = re_result['true_crossing_index']
        metrics['predicted_eol_index'] = re_result[
            'predicted_crossing_index']
        metrics['re_ref'] = relative_error_reference(
            y_test, y_predict, threshold)
    return metrics


def confidence_interval(values, confidence=0.95):
    """计算置信区间 [mean - margin, mean + margin]

    values: 多次实验的指标值列表
    confidence: 置信水平，默认 0.95
    返回 (mean, lower, upper, std)

    注意：这是**同一留一折内、不同随机种子**之间的区间，它不代表泛化不确定性。
    跨电池的泛化不确定性请用 :func:`bootstrap_ci`。
    """
    values = np.asarray(values, dtype=np.float64)
    n = len(values)
    if n == 0:
        return 0.0, 0.0, 0.0, 0.0
    mean = float(np.mean(values))
    std = float(np.std(values, ddof=1)) if n > 1 else 0.0
    if n > 1 and std > 1e-12:
        # 使用 t 分布
        from scipy import stats
        t_val = stats.t.ppf((1 + confidence) / 2, df=n - 1)
        margin = t_val * std / sqrt(n)
    else:
        margin = 0.0
    return mean, mean - margin, mean + margin, std


def bootstrap_ci(values, n_boot=2000, level=0.95, seed=0):
    """对「每块电池一个数」的指标做 bootstrap，返回 (均值, 下界, 上界)。

    ``n = 电池数`` 才是泛化不确定性的来源（而不是随机种子）。电池只有 4–5 块
    时区间会很宽——这是诚实的，也正是读者最想看到的。
    """
    array = np.asarray(
        [value for value in values
         if value is not None and np.isfinite(value)],
        dtype=np.float64)
    if len(array) == 0:
        return float('nan'), float('nan'), float('nan')
    if len(array) == 1:
        value = float(array[0])
        return value, value, value
    rng = np.random.default_rng(seed)
    means = rng.choice(
        array, size=(int(n_boot), len(array)), replace=True).mean(axis=1)
    lo, hi = np.percentile(
        means, [(1 - level) / 2 * 100, (1 + level) / 2 * 100])
    return float(array.mean()), float(lo), float(hi)
