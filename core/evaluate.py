from math import sqrt
import numpy as np
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score


def relative_error(y_test, y_predict, threshold):
    true_re, pred_re = None, None
    for i in range(len(y_test) - 1):
        if y_test[i] >= threshold > y_test[i + 1]:
            true_re = i + 1
            break
    for i in range(len(y_predict) - 1):
        if y_predict[i] >= threshold > y_predict[i + 1]:
            pred_re = i + 1
            break
    if true_re is None or pred_re is None or true_re == 0:
        return 1.0
    return abs(true_re - pred_re) / true_re


def evaluation(y_test, y_predict):
    """RMSE"""
    return sqrt(mean_squared_error(y_test, y_predict))


def calc_mae(y_test, y_predict):
    """平均绝对误差"""
    return mean_absolute_error(y_test, y_predict)


def calc_r2(y_test, y_predict):
    """决定系数 R²"""
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
    metrics = {
        'rmse': evaluation(y_test, y_predict),
        'mae': calc_mae(y_test, y_predict),
        'r2': calc_r2(y_test, y_predict),
        'pearson': calc_pearson(y_test, y_predict),
    }
    if rated_capacity is not None and threshold_ratio is not None:
        metrics['re'] = relative_error(
            y_test, y_predict, rated_capacity * threshold_ratio)
    return metrics


def confidence_interval(values, confidence=0.95):
    """计算置信区间 [mean - margin, mean + margin]

    values: 多次实验的指标值列表
    confidence: 置信水平，默认 0.95
    返回 (mean, lower, upper, std)
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
