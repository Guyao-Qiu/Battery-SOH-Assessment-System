"""随机森林训练。

改进方案 A7：旧实现用「分批加树 + 验证 RMSE 早停」来选树数，但这在统计上
没有意义——随机森林的方差随树数增加而单调下降，不会过拟合；而且旧代码里
``batch_size = max(1, min(10, n_estimators // 10))`` 只有 10 个批次，``patience=20``
的早停永远不会触发（计数器最大只能到 9），选出来的其实是噪声，之后还要**从头
重训**一遍。

现在：固定树数、一次训练。用于选超参的验证集交给 ``core.protocol`` 的
内层留一电池交叉验证。
"""

import numpy as np
from sklearn.ensemble import RandomForestRegressor

from core.cancellation import check_cancelled
from core.progress import make_progress_event


def train_rf(train_x, train_y, val_x=None, val_y=None, *, n_estimators=100,
             max_depth=6, min_samples_leaf=1, max_features=1.0, seed=2,
             n_jobs=1, log_callback=None, name='', stop_flag=None,
             progress_callback=None, patience=None, **_ignored):
    """训练一个随机森林。

    ``val_x`` / ``val_y`` / ``patience`` 保留在签名里以兼容旧调用方，但不再用于
    早停（随机森林不需要早停）。``train_x`` 可以是 ``(N, W)`` 或 ``(N, W, F)``。

    ``n_jobs`` 默认 1：递归预测每步只喂一个窗口，而 joblib 的并行调度开销远大于
    单棵树的预测成本（实测 1 行 predict：``n_jobs=-1`` 27 ms vs ``n_jobs=1`` 2.6 ms）。
    """
    check_cancelled(stop_flag)
    train_x = np.asarray(train_x)
    if train_x.ndim == 3:
        train_x = train_x.reshape(len(train_x), -1)
    train_y = np.asarray(train_y, dtype=np.float32).reshape(-1)
    if len(train_x) == 0:
        raise ValueError('随机森林训练集不能为空')

    if progress_callback:
        progress_callback(make_progress_event(
            'rf_trees', started_at=0.0, battery=name, seed=seed,
            epoch=None, current=1, total=1))

    model = RandomForestRegressor(
        n_estimators=int(n_estimators),
        max_depth=int(max_depth),
        min_samples_leaf=int(min_samples_leaf),
        max_features=max_features,
        random_state=seed,
        n_jobs=n_jobs,
    )
    if log_callback:
        log_callback(f'[{name}] 随机森林训练中（树数={int(n_estimators)}）...')
    model.fit(train_x, train_y)
    check_cancelled(stop_flag)

    if log_callback:
        log_callback(f'[{name}] 随机森林训练完成，树数={int(n_estimators)}')
    return model
