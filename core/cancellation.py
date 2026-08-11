import time

from core.progress import make_progress_event


class TrainingCancelled(RuntimeError):
    """Raised when a cooperative training stop reaches a safe checkpoint."""


def stop_requested(stop_flag):
    return bool(stop_flag is not None and stop_flag())


def check_cancelled(stop_flag):
    if stop_requested(stop_flag):
        raise TrainingCancelled('训练已由用户取消')


def xgboost_stop_callbacks(stop_flag, progress_callback=None, *,
                           battery=None, seed=None, total=None,
                           started_at=None):
    """Create an XGBoost per-iteration cooperative stop callback."""
    if stop_flag is None and progress_callback is None:
        return None
    from xgboost.callback import TrainingCallback
    progress_started_at = started_at or time.monotonic()

    class CooperativeStopCallback(TrainingCallback):
        def after_iteration(self, model, epoch, evals_log):
            if progress_callback:
                progress_callback(make_progress_event(
                    'xgboost_tree',
                    started_at=progress_started_at,
                    battery=battery,
                    seed=seed,
                    epoch=None,
                    current=epoch + 1,
                    total=total or epoch + 1,
                ))
            return stop_requested(stop_flag)

    return [CooperativeStopCallback()]
