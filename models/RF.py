import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error
from math import sqrt


def train_rf(train_x, train_y, val_x, val_y, n_estimators=100,
             max_depth=10, min_samples_leaf=1, max_features=1.0,
             patience=20, seed=2,
             log_callback=None, name=''):
    batch_size = max(1, min(10, n_estimators // 10))
    best_score = float('inf')
    best_n_trees = n_estimators
    counter = 0
    total_trees = 0

    model = RandomForestRegressor(
        n_estimators=batch_size,
        max_depth=max_depth,
        min_samples_leaf=min_samples_leaf,
        max_features=max_features,
        random_state=seed,
        n_jobs=-1,
        warm_start=True
    )

    if log_callback:
        log_callback(f'[{name}] 开始训练...')

    while total_trees < n_estimators:
        model.n_estimators = total_trees + batch_size
        model.fit(train_x, train_y)

        val_pred = np.asarray(model.predict(val_x)).reshape(-1)
        rmse = sqrt(mean_squared_error(val_y, val_pred))

        if rmse < best_score:
            best_score = rmse
            best_n_trees = total_trees + batch_size
            counter = 0
        else:
            counter += 1

        total_trees += batch_size

        if log_callback:
            log_callback(f'[{name}] 树数={total_trees}/{n_estimators}，rmse={rmse:.4f}')

        if counter >= patience:
            if log_callback:
                log_callback(f'[{name}] 第{total_trees}棵树早停')
            break

    final_model = RandomForestRegressor(
        n_estimators=best_n_trees,
        max_depth=max_depth,
        min_samples_leaf=min_samples_leaf,
        max_features=max_features,
        random_state=seed,
        n_jobs=-1,
    )
    final_model.fit(train_x, train_y)
    if log_callback:
        log_callback(f'[{name}] 训练完成，树数={n_estimators}（验证选择{best_n_trees}）')

    return final_model
