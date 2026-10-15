#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""在合成「NASA 风格」电池上复现改进方案 §4 的四方对比。

运行（在工程根目录）::

    python tools/repro_synthetic.py

数据是合成的，只验证**机制**（例如：训练集少了寿命末段会怎样），不是真实指标。
把 ``make_battery`` 换成你的真实 ``battery_dict``（``{名字: {'capacity': 数组}}``
或带 ``capacity`` 列的 DataFrame）就是真实数据上的对比。

四种做法，在 40 / 50 / 60 / 70% 四个预测起点上做递归预测：

1. ``平推基线``            —— 持久性，任何模型都必须先赢过它；
2. ``现有流程+α混合``      —— 每块训练电池只用前 80% 训练，后 20% 标定 α；
3. ``现有训练，α=1``       —— 同上但关掉混合，暴露「树模型无法外推」的饱和；
4. ``建议流程``            —— 内层留一电池选超参 + 全量窗口重训（A2/A3/A4）。
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sklearn.ensemble import RandomForestRegressor            # noqa: E402

from core.prediction import predict_capacity_batch             # noqa: E402
from core.preprocess import (                                  # noqa: E402
    CapacityScaler,
    fit_persistence_blend,
    prepare_leave_one_out_split,
)
from core.protocol import fit_final, rolling_origin_eval, select_hparams  # noqa: E402
from models.RF import train_rf                                 # noqa: E402


RATED, RATIO, W = 2.0, 0.7, 16
THRESHOLD = RATED * RATIO
STARTS = (0.4, 0.5, 0.6, 0.7)


def make_battery(seed, n, c0, c_end):
    """衰减 + 加速膝点 + 容量再生尖峰 + 噪声。"""
    rng = np.random.default_rng(seed)
    k = np.arange(n) / (n - 1)
    shape = 0.55 * k + 0.45 * (np.exp(3.2 * k) - 1) / (np.exp(3.2) - 1)
    capacity = c0 - (c0 - c_end) * shape
    for _ in range(max(3, n // 25)):
        index, amplitude = rng.integers(10, n - 3), rng.uniform(0.02, 0.05)
        for offset, decay in enumerate((1.0, 0.5, 0.2)):
            if index + offset < n:
                capacity[index + offset] += amplitude * decay
    return (capacity + rng.normal(0, 0.008, n)).astype(np.float32)


def synthetic_data():
    return {
        'S05': {'capacity': make_battery(1, 168, 1.86, 1.29)},
        'S06': {'capacity': make_battery(2, 168, 2.04, 1.18)},
        'S07': {'capacity': make_battery(3, 168, 1.89, 1.43)},   # 观测期内不失效
        'S18': {'capacity': make_battery(4, 132, 1.86, 1.34)},
    }


def rf_fit(x, y, hp):
    """旧流程用的裸 sklearn 拟合（不做归一化，调用方已归一化）。"""
    return RandomForestRegressor(
        n_estimators=hp['n'], max_depth=hp['d'], random_state=3, n_jobs=1,
    ).fit(x, y)


def current_flow_models(data, target, seed=3):
    """复现项目旧流程：前 80% 训练 + 后 20% 标定 α。"""
    split = prepare_leave_one_out_split(data, target, window_size=W)
    scaler = CapacityScaler('rated', RATED).fit(
        np.concatenate((split.train_x.reshape(-1), split.train_y)))
    train_x = scaler.transform(split.train_x)
    train_y = scaler.transform(split.train_y)
    val_x = scaler.transform(split.val_x)
    val_y = scaler.transform(split.val_y)
    model = train_rf(
        train_x, train_y, val_x, val_y, n_estimators=100, max_depth=6,
        min_samples_leaf=1, max_features=1.0, patience=20, seed=seed,
        log_callback=None, name=target)
    metadata = {
        'mode': 'RF', 'window_size': W, 'rated_capacity': RATED,
        'scaler': scaler.to_dict(),
    }
    alpha = fit_persistence_blend(
        split.val_x, split.val_y,
        predict_capacity_batch(model, metadata, split.val_x))
    return model, metadata, alpha


def main():
    data = synthetic_data()
    # 建议流程：用 core.model_factory 的 fit_fn（内部负责归一化），
    # 与评估/部署路径完全一致。
    from core.model_factory import make_fit_fn
    from core.protocol import model_step_for
    from utils.config import TrainConfig

    config = TrainConfig(
        mode='RF', window_size=W, rated_capacity=RATED,
        threshold_ratio=RATIO, device='cpu', seed=3,
        n_estimators=100, max_depth=6, feature_columns=('capacity',))
    fit_fn = make_fit_fn(config, feature_scaler=None)
    grid = [{'n_estimators': 100, 'max_depth': depth}
            for depth in (4, 6, 8)]
    keys = ('平推基线', '现有流程+α混合', '现有训练，α=1', '建议流程')
    results = {key: [] for key in keys}
    alphas = {}

    for target in data:
        train_names = [name for name in data if name != target]
        sequence = data[target]['capacity']

        model, metadata, alpha = current_flow_models(data, target)
        alphas[target] = alpha
        step_current = lambda w, m=model, me=dict(          # noqa: E731
            metadata, persistence_blend=alpha): predict_capacity_batch(m, me, w)
        step_raw = lambda w, m=model, me=dict(               # noqa: E731
            metadata, persistence_blend=1.0): predict_capacity_batch(m, me, w)

        hp, _ = select_hparams(
            data, train_names, W, fit_fn, grid, RATED, start_frac=0.5)
        new_model = fit_final(data, train_names, W, fit_fn, hp, RATED)
        step_new = model_step_for(new_model, RATED)

        for key, step in (('平推基线', lambda w: w[:, -1]),
                          ('现有流程+α混合', step_current),
                          ('现有训练，α=1', step_raw),
                          ('建议流程', step_new)):
            rows = rolling_origin_eval(
                sequence, W, step, THRESHOLD, STARTS, battery=target)
            for row in rows:
                row['method'] = key
            results[key] += rows

    print('合成数据（4 块电池，额定 2.0 Ah，失效阈值 1.4 Ah，窗口 16，随机森林）')
    print('每折标定的持久性混合系数 α：'
          + '，'.join(f'{k}={v:.3f}' for k, v in alphas.items()))
    print()
    header = f"{'起点':>6} {'方法':<16} {'RMSE(Ah)':>9} {'EOL 检出':>10} {'平均|RUL误差|':>13}"
    print(header)
    print('-' * len(header))
    for frac in STARTS:
        for key in keys:
            rows = [r for r in results[key] if r['start_frac'] == frac]
            if not rows:
                continue
            need = [r for r in rows if r['true_rul'] is not None]
            ok = [r for r in rows if r['status'] == 'ok']
            error = (f"{np.mean([abs(r['rul_err']) for r in ok]):.1f}"
                     if ok else '—')
            print(f"{frac:6.0%} {key:<16} "
                  f"{np.mean([r['rmse'] for r in rows]):9.4f} "
                  f"{len(ok):>5}/{len(need):<4} {error:>13}")
        print()

    print('怎么读：')
    print('  * 「现有流程+α混合」若与「平推基线」逐位相同，说明 α 坍缩为 0（A3），')
    print('    界面上的高 R² 其实是平推的得分。')
    print('  * 「现有训练，α=1」关掉混合后 RMSE 下降但仍检不出失效，说明训练集')
    print('    没见过寿命末段，树模型物理上无法输出低于训练目标最小值的预测（A2）。')
    print('  * 「建议流程」用全部训练电池的全部窗口重训，才可能越过阈值。')


if __name__ == '__main__':
    main()
