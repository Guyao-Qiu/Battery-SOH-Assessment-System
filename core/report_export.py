"""Snapshot-based, atomic report export."""

import errno
import json
import os
from pathlib import Path
from uuid import uuid4

import numpy as np
import pandas as pd

from core.run_snapshot import RunSnapshot


class ExportCancelled(RuntimeError):
    """The user declined to overwrite existing report artifacts."""


class ReportExportError(RuntimeError):
    """A report could not be written, with a user-actionable message."""


def friendly_export_error(error):
    error_number = getattr(error, 'errno', None)
    windows_error = getattr(error, 'winerror', None)
    if error_number == errno.ENOSPC:
        return '磁盘空间不足。请释放空间或选择其他磁盘后重试。'
    if (isinstance(error, PermissionError)
            or error_number in (errno.EACCES, errno.EPERM)
            or windows_error in (5, 32, 33)):
        return (
            '文件可能被占用或目录无写入权限。请关闭正在占用报告的 '
            'Excel/图片查看器，或选择有写入权限的目录后重试。'
        )
    return f'导出失败：{error}。请检查目标目录后重试。'


def _json_value(value):
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, np.ndarray):
        return [_json_value(item) for item in value.tolist()]
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    return value


def _report_payload(snapshot):
    return {
        'run': {
            'run_id': snapshot.run_id,
            'started_at': snapshot.started_at,
            'elapsed_seconds': snapshot.elapsed_seconds,
        },
        'imported_paths': list(snapshot.imported_paths),
        'config': snapshot.config_dict(),
        'results': snapshot.results_dict(),
    }


def _metrics_rows(snapshot):
    rows = []
    for name, result in snapshot.results_dict().items():
        item = result.get('detail', {})
        row = {
            'battery': item.get('battery', name),
            'cycles': item.get('cycles'),
            'model': item.get('model'),
            'rmse': item.get('rmse'),
            'mae': item.get('mae'),
            'r2': item.get('r2'),
            'pearson': item.get('pearson'),
            're': item.get('re'),
            'n_seeds': item.get('n_seeds', 1),
            'failure_cycle': item.get('failure_cycle'),
            'threshold': item.get('threshold'),
        }
        ci = item.get('ci', {})
        for key in ('rmse', 'mae', 'r2', 'pearson', 're'):
            if key in ci:
                values = ci[key]
                row[f'{key}_mean'] = values.get('mean')
                row[f'{key}_std'] = values.get('std')
                row[f'{key}_ci_lower'] = values.get('lower')
                row[f'{key}_ci_upper'] = values.get('upper')
        rows.append(row)
    return rows


def _temporary_path(target, token):
    return target.with_name(
        f'.{target.stem}.{token}.tmp{target.suffix}')


def _cleanup(paths):
    for path in paths:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


def export_run_report(snapshot, canvas, *, base_directory='outputs/runs',
                      confirm_overwrite=None):
    if not isinstance(snapshot, RunSnapshot):
        raise TypeError('报告导出必须使用 RunSnapshot')
    if not snapshot.results:
        raise ReportExportError('运行快照中没有可导出的评估结果。')

    run_directory = Path(base_directory) / snapshot.run_id
    targets = {
        'report_json': run_directory / 'report.json',
        'metrics_excel': run_directory / '评估结果.xlsx',
        'chart_image': run_directory / '评估结果.png',
    }
    existing = tuple(path for path in targets.values() if path.exists())
    if existing:
        if confirm_overwrite is None or not confirm_overwrite(existing):
            raise ExportCancelled('已取消覆盖现有报告。')

    temporary_paths = []
    try:
        run_directory.mkdir(parents=True, exist_ok=True)
        token = uuid4().hex
        temporary = {
            key: _temporary_path(path, token)
            for key, path in targets.items()
        }
        temporary_paths = list(temporary.values())

        with temporary['report_json'].open('w', encoding='utf-8') as handle:
            json.dump(
                _json_value(_report_payload(snapshot)), handle,
                ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())

        pd.DataFrame(_metrics_rows(snapshot)).to_excel(
            temporary['metrics_excel'], index=False)
        canvas.save_figure(str(temporary['chart_image']))
        if not temporary['chart_image'].is_file():
            raise OSError('图表临时文件未生成')

        for key, target in targets.items():
            os.replace(temporary[key], target)
    except ExportCancelled:
        raise
    except Exception as error:
        _cleanup(temporary_paths)
        raise ReportExportError(friendly_export_error(error)) from error
    finally:
        _cleanup(temporary_paths)

    return {
        'run_directory': str(run_directory),
        **{key: str(path) for key, path in targets.items()},
    }


def atomic_save_figure(canvas, target_path):
    target = Path(target_path)
    temporary = _temporary_path(target, uuid4().hex)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        canvas.save_figure(str(temporary))
        if not temporary.is_file():
            raise OSError('图表临时文件未生成')
        os.replace(temporary, target)
    except Exception as error:
        _cleanup([temporary])
        raise ReportExportError(friendly_export_error(error)) from error
    finally:
        _cleanup([temporary])
    return str(target)
