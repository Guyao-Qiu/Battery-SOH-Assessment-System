from xgboost import XGBRegressor


def train_xgboost(train_x, train_y, val_x, val_y, n_estimators=100,
                  learning_rate=0.1, max_depth=6, subsample=1.0,
                  colsample_bytree=1.0, patience=20, seed=2,
                  log_callback=None, name=''):
    model = XGBRegressor(
        n_estimators=n_estimators,
        learning_rate=learning_rate,
        max_depth=max_depth,
        subsample=subsample,
        colsample_bytree=colsample_bytree,
        early_stopping_rounds=patience,
        random_state=seed,
        verbosity=0
    )
    if log_callback:
        log_callback(f'[{name}] 训练中...')
    model.fit(train_x, train_y, eval_set=[(val_x, val_y)], verbose=False)

    best_iteration = model.get_booster().best_iteration
    actual_trees = best_iteration if best_iteration is not None else n_estimators

    if log_callback:
        log_callback(f'[{name}] 训练完成，树数={n_estimators}（验证选择{actual_trees}）')

    return model
