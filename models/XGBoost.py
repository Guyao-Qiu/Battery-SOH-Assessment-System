import numpy as np
import time

from xgboost import XGBRegressor
from core.cancellation import check_cancelled, xgboost_stop_callbacks


def _flatten(features):
    array = np.asarray(features)
    if array.ndim == 3:
        return array.reshape(len(array), -1)
    return array


def train_xgboost(train_x, train_y, val_x, val_y, n_estimators=100,
                  learning_rate=0.1, max_depth=6, subsample=1.0,
                  colsample_bytree=1.0, patience=20, seed=2,
                  log_callback=None, name='', stop_flag=None,
                  progress_callback=None):
    """在**训练电池**的验证集上做 early stopping。

    ``val_x`` / ``val_y`` 绝不能来自目标电池。改进方案 A2 修好后，这里的验证集
    由 ``core.protocol`` 的内层留一电池交叉验证提供，因此它是一块**没见过的
    电池**，和最终使用场景一致。
    """
    check_cancelled(stop_flag)
    progress_started_at = time.monotonic()
    train_x = _flatten(train_x)
    val_x = _flatten(val_x)
    train_y = np.asarray(train_y, dtype=np.float32).reshape(-1)
    val_y = np.asarray(val_y, dtype=np.float32).reshape(-1)
    options = dict(
        n_estimators=n_estimators,
        learning_rate=learning_rate,
        max_depth=max_depth,
        subsample=subsample,
        colsample_bytree=colsample_bytree,
        early_stopping_rounds=patience,
        random_state=seed,
        verbosity=0,
    )
    callbacks = xgboost_stop_callbacks(
        stop_flag,
        progress_callback,
        battery=name,
        seed=seed,
        total=n_estimators,
        started_at=progress_started_at,
    )
    if callbacks is not None:
        options['callbacks'] = callbacks
    model = XGBRegressor(**options)
    if log_callback:
        log_callback(f'[{name}] 训练中...')
    model.fit(train_x, train_y, eval_set=[(val_x, val_y)], verbose=False)
    check_cancelled(stop_flag)

    best_iteration = model.get_booster().best_iteration
    actual_trees = best_iteration if best_iteration is not None else n_estimators

    if log_callback:
        log_callback(f'[{name}] 训练完成，树数={n_estimators}（验证选择{actual_trees}）')

    return model