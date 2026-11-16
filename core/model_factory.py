"""模型构造与训练的**唯一入口**（评估与部署共用）。

改进方案 A2 的核心：旧流程里评估走 ``prepare_leave_one_out_split``（每块训练
电池只用前 80% 训练），部署走 ``_prepare_final_training_data``（全量重训），
于是「报告的评估指标评估的并不是最终部署的那个模型」。

这里把两者的拟合逻辑收敛到一处：

- :func:`make_fit_fn` 返回 ``fit_fn(X, y, hp) -> model``，供
  :func:`core.protocol.select_hparams` / :func:`core.protocol.fit_final` 使用；
- :func:`hparam_grid` 给出可搜索的超参网格；
- :func:`make_step_fn` 把已拟合模型包装成「一个窗口 → 下一个容量」的递归预测器。

输入约定：``X`` 形状为 ``(N, W, F)``（单特征时 ``(N, W)`` 亦可）。树模型内部
展平成 ``(N, W*F)``，循环模型直接使用 ``(N, W, F)``。
"""

import numpy as np
# 显式再导出：``fit_rf`` 在调用时通过 globals() 取这个名字，
# 测试与调用方也以 ``core.model_factory.RandomForestRegressor`` 为替换点。
from sklearn.ensemble import RandomForestRegressor as RandomForestRegressor

from core.batching import DEFAULT_BATCH_SIZE, make_tensor_loader
from core.cancellation import check_cancelled

RECURRENT_MODES = ('RNN', 'GRU', 'LSTM')
TREE_MODES = ('XGBoost', 'RF')


def as_3d(features):
    """把 ``(N, W)`` 或 ``(N, W, F)`` 统一成 ``(N, W, F)`` float32。"""
    array = np.asarray(features, dtype=np.float32)
    if array.ndim == 2:
        return array.reshape(array.shape[0], array.shape[1], 1)
    if array.ndim != 3:
        raise ValueError('特征必须是二维窗口或三维多特征窗口')
    return array


def n_features(features):
    """特征数 F；单特征窗口返回 1。"""
    array = np.asarray(features)
    if array.ndim == 2:
        return 1
    if array.ndim == 3:
        return int(array.shape[2])
    raise ValueError('特征必须是二维窗口或三维多特征窗口')


def flatten(features):
    """树模型用：``(N, W, F)`` -> ``(N, W*F)``。"""
    array = as_3d(features)
    return array.reshape(len(array), -1)


def hparam_grid(config, mode=None):
    """可搜索的超参网格（内层留一电池交叉验证的候选集）。

    树模型搜「树数 / 深度」，循环模型搜「训练轮数」。网格保持很小：内层 CV 的
    计算量是 ``训练电池数 × 网格大小``。
    """
    mode = mode or config.mode
    if mode == 'RF':
        depths = sorted({int(getattr(config, 'max_depth', 6)), 8})
        return [{'n_estimators': int(getattr(config, 'n_estimators', 100)),
                 'max_depth': depth} for depth in depths]
    if mode == 'XGBoost':
        depths = sorted({int(getattr(config, 'max_depth', 6)), 4})
        return [{'n_estimators': int(getattr(config, 'n_estimators', 100)),
                 'max_depth': depth} for depth in depths]
    if mode in RECURRENT_MODES:
        epochs = int(getattr(config, 'epochs', 100))
        # 循环模型较贵：先用「固定轮数」的少量候选做快速模式
        candidates = sorted({max(1, epochs // 2), max(1, epochs)})
        return [{'epochs': value} for value in candidates]
    raise ValueError(f'不支持的模型类型: {mode}')


def config_default_hp(config, mode, grid):
    """最初样式：不做内层交叉验证，从网格里取与配置一致的那组超参。"""
    if not grid:
        return {}
    if (mode or config.mode) in RECURRENT_MODES:
        epochs = int(getattr(config, 'epochs', 100))
        for hp in grid:
            if hp.get('epochs') == epochs:
                return hp
        return grid[-1]
    depth = int(getattr(config, 'max_depth', 6))
    for hp in grid:
        if hp.get('max_depth') == depth:
            return hp
    return grid[-1]


def scale_training_input(x, y, rated, feature_scaler=None):
    """按与推理**完全一致**的规则归一化训练输入。

    单特征：``x / rated``、``y / rated``；
    多特征：容量通道 ``/ rated``，其余通道用 ``FeatureScaler``（z-score）。
    推理端由 :func:`core.prediction.scale_model_input` 做同一件事，两边必须同步，
    否则模型在训练时看到的量纲和预测时不同（多特征路径曾经就是这样）。
    """
    features = as_3d(x)
    targets = np.asarray(y, dtype=np.float32).reshape(-1)
    scaled = np.array(features, dtype=np.float32, copy=True)
    scaled[:, :, 0] = features[:, :, 0] / rated
    if features.shape[2] > 1 and feature_scaler is not None:
        scaled = feature_scaler.transform(scaled)
    return scaled, targets / rated


def make_fit_fn(config, *, stop_flag=None, log_callback=None, name='',
                net_class=None, progress_callback=None, feature_scaler=None):
    """返回 ``fit_fn(X, y, hp) -> model``；X、y 是**原始** Ah / 原始特征。

    内部会用 :func:`scale_training_input` 归一化，因此调用方传原始窗口即可，
    不必自己先除额定容量。

    对循环模型，``hp['epochs']`` 就是「内层 CV 选出的最佳轮数」——最终重训时
    固定该轮数，不再做早停（早停的验证集来自训练电池的寿命末段，正是 A2 的
    病根）。

    ``net_class`` 允许注入 ``Net``（便于测试与打包环境定位），默认取
    ``models.rnn_model.Net``。
    """
    mode = config.mode
    seed = int(getattr(config, 'seed', 2))
    device = getattr(config, 'device', 'cpu')
    rated = float(getattr(config, 'rated_capacity', 1.0))

    def _scale(x, y):
        return scale_training_input(x, y, rated, feature_scaler)

    if mode == 'RF':
        def fit_rf(x, y, hp):
            # 在**调用时**取 RandomForestRegressor（而不是在 make_fit_fn 里），
            # 这样测试与调用方 patch ``core.model_factory.RandomForestRegressor``
            # 才能生效。
            model_class = globals()['RandomForestRegressor']
            scaled_x, scaled_y = _scale(x, y)
            model = model_class(
                n_estimators=int(hp.get('n_estimators', 100)),
                max_depth=int(hp.get('max_depth', 6)),
                min_samples_leaf=int(getattr(config, 'min_samples_leaf', 1)),
                max_features=getattr(config, 'max_features', 1.0),
                random_state=seed,
                # n_jobs=1：递归预测每步只喂一个窗口，而 joblib 的并行调度开销
                # 远大于单棵树的预测成本（实测 1 行 predict：27 ms vs 2.6 ms）。
                n_jobs=1,
            )
            model.fit(flatten(scaled_x), scaled_y)
            return model

        return fit_rf

    if mode == 'XGBoost':
        from xgboost import XGBRegressor

        def fit_xgb(x, y, hp):
            scaled_x, scaled_y = _scale(x, y)
            model = XGBRegressor(
                n_estimators=int(hp.get('n_estimators', 100)),
                learning_rate=float(getattr(config, 'learning_rate', 0.1)),
                max_depth=int(hp.get('max_depth', 6)),
                subsample=float(getattr(config, 'subsample', 1.0)),
                colsample_bytree=float(getattr(config, 'colsample_bytree', 1.0)),
                random_state=seed,
                verbosity=0,
            )
            model.fit(flatten(scaled_x), scaled_y)
            return model

        return fit_xgb

    if mode in RECURRENT_MODES:
        import time

        import torch
        import torch.nn as nn

        from core.prediction import resolve_inference_device
        from core.progress import make_progress_event
        from utils.config import setup_seed

        if net_class is None:
            from models.rnn_model import Net as net_class  # noqa: N813

        backbone = str(getattr(config, 'backbone', 'default')).strip().lower()
        use_transformer = backbone in ('transformer', 'detransformer')
        alpha = float(getattr(config, 'alpha', 0.1))

        def _build_dl_model(window_size, features):
            hidden_dim = int(getattr(config, 'hidden_dim', 64))
            num_layers = max(1, int(getattr(config, 'num_layers', 1)))
            if use_transformer:
                from models.rnn_model import DeTransformer
                return DeTransformer(
                    feature_size=int(window_size),
                    hidden_dim=hidden_dim,
                    feature_num=max(1, int(getattr(config, 'transformer_k', 16))),
                    num_layers=num_layers,
                    nhead=max(1, int(getattr(config, 'nhead', 1))),
                    dropout=float(getattr(config, 'dropout', 0.0)),
                    noise_level=float(getattr(config, 'noise_level', 0.0)),
                    input_size=features,
                )
            # 只在多特征时传 input_size，保持与测试桩 RecordingNet / BatchGuardNet 三参签名兼容
            if features == 1:
                return net_class(
                    hidden_dim=hidden_dim, num_layers=num_layers, mode=mode)
            return net_class(
                hidden_dim=hidden_dim, num_layers=num_layers, mode=mode,
                input_size=features)

        def fit_rnn(x, y, hp, test_x=None, test_y=None):
            """训练深度学习模型（对齐 XiuzeZhou/RUL 协议，且严格无测试集泄漏）。

            使用 Adam 优化器与分片全批量梯度累积（每个前向/反向分片 ``<= DEFAULT_BATCH_SIZE``）：
            数学梯度与参考实现的全批量更新等价，同时严格限制峰值张量显存/内存。
            ``test_x`` / ``test_y`` 参数仅为兼容保留，不参与早停或轮次筛选。
            """
            del test_x, test_y  # 红线：绝不使用测试电池参与模型/轮次选择
            resolved = resolve_inference_device(device)
            setup_seed(seed)
            scaled_x, scaled_y = _scale(x, y)
            features = scaled_x.shape[2]
            window_size = scaled_x.shape[1]
            model = _build_dl_model(window_size, features).to(resolved)

            criterion = nn.MSELoss()
            optimizer = torch.optim.Adam(
                model.parameters(),
                lr=float(getattr(config, 'rnn_lr', 0.001)),
                weight_decay=float(getattr(config, 'weight_decay', 0.0)),
            )
            loader = make_tensor_loader(
                scaled_x,
                scaled_y.reshape(-1, 1),
                batch_size=DEFAULT_BATCH_SIZE,
                shuffle=False,
                seed=seed,
            )
            epochs = max(1, int(hp.get('epochs', 1)))
            total_samples = max(1, len(scaled_x))
            started_at = time.monotonic()

            for epoch in range(epochs):
                check_cancelled(stop_flag)
                model.train()
                optimizer.zero_grad()
                epoch_loss = 0.0
                for features_batch, targets_batch in loader:
                    check_cancelled(stop_flag)
                    features_batch = features_batch.to(resolved)
                    targets_batch = targets_batch.to(resolved).reshape(-1, 1)
                    if use_transformer:
                        output, decode, x_rep = model(
                            features_batch, return_decode=True)
                        output = output.reshape(-1, 1)
                        batch_loss = (
                            criterion(output, targets_batch)
                            + alpha * criterion(decode, x_rep)
                        )
                    else:
                        output = model(features_batch).reshape(-1, 1)
                        batch_loss = criterion(output, targets_batch)
                    weight = len(features_batch) / total_samples
                    (batch_loss * weight).backward()
                    epoch_loss += float(batch_loss.item()) * weight
                optimizer.step()

                if progress_callback:
                    progress_callback(make_progress_event(
                        'rnn_epoch', started_at=started_at, battery=name,
                        seed=seed, epoch=epoch + 1, current=epoch + 1,
                        total=epochs))
                if log_callback and ((epoch + 1) % 10 == 0 or epoch + 1 == epochs):
                    log_callback(
                        f'[{name}] 第{epoch + 1}/{epochs}轮 '
                        f'损失={epoch_loss:.6f}')

            model.eval()
            return model

        return fit_rnn

    raise ValueError(f'不支持的模型类型: {mode}')


def make_step_fn(model, metadata, device='cpu'):
    """把已拟合模型包装成递归预测器：``(1, W) 或 (1, W, F) -> (1,)`` 容量。

    对多特征模型，递归时**只有容量通道是自回归的**；其余特征按「持久性」保持
    为窗口内最后一个观测值（未来工况未知时的保守假设，已在结果里标注）。
    """
    from core.prediction import predict_capacity_batch

    def step(windows):
        return predict_capacity_batch(model, metadata, windows, device=device)

    return step


def state_dict_of(model):
    """循环模型的 CPU state_dict（用于最终模型保存）。"""
    return {
        key: value.detach().cpu().clone()
        for key, value in model.state_dict().items()
    }
