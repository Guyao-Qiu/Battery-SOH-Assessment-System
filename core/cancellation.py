class TrainingCancelled(RuntimeError):
    """Raised when a cooperative training stop reaches a safe checkpoint."""


def stop_requested(stop_flag):
    return bool(stop_flag is not None and stop_flag())


def check_cancelled(stop_flag):
    if stop_requested(stop_flag):
        raise TrainingCancelled('训练已由用户取消')


def xgboost_stop_callbacks(stop_flag):
    """Create an XGBoost per-iteration cooperative stop callback."""
    if stop_flag is None:
        return None
    from xgboost.callback import TrainingCallback

    class CooperativeStopCallback(TrainingCallback):
        def after_iteration(self, model, epoch, evals_log):
            return stop_requested(stop_flag)

    return [CooperativeStopCallback()]
