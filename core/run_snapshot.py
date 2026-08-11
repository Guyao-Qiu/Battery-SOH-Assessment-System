"""Immutable snapshots for one evaluation or prediction run."""

from copy import deepcopy
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Mapping
from uuid import uuid4


def _freeze(value):
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item)
                                 for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, set):
        return frozenset(_freeze(item) for item in value)
    return value


def _thaw(value):
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    if isinstance(value, frozenset):
        return [_thaw(item) for item in value]
    return deepcopy(value)


@dataclass(frozen=True)
class RunSnapshot:
    """A deeply frozen record of inputs and outputs for exactly one run."""

    run_id: str
    started_at: str
    imported_paths: tuple[str, ...]
    config: Mapping[str, Any]
    results: Mapping[str, Any]
    elapsed_seconds: float | None = None

    @classmethod
    def capture(cls, config, imported_paths, *, now=None, run_id=None):
        captured_at = now or datetime.now(timezone.utc)
        if captured_at.tzinfo is None:
            captured_at = captured_at.replace(tzinfo=timezone.utc)
        captured_at = captured_at.astimezone(timezone.utc)
        if run_id is None:
            stamp = captured_at.strftime('%Y%m%dT%H%M%SZ')
            run_id = f'{stamp}-{uuid4().hex[:8]}'

        config_data = (
            config.to_dict() if hasattr(config, 'to_dict') else dict(config)
        )
        copied_paths = tuple(str(path) for path in deepcopy(imported_paths))
        return cls(
            run_id=str(run_id),
            started_at=captured_at.isoformat(),
            imported_paths=copied_paths,
            config=_freeze(deepcopy(config_data)),
            results=_freeze({}),
        )

    def with_results(self, results, *, elapsed_seconds):
        return replace(
            self,
            results=_freeze(deepcopy(results)),
            elapsed_seconds=float(elapsed_seconds),
        )

    def config_dict(self):
        return _thaw(self.config)

    def results_dict(self):
        return _thaw(self.results)
