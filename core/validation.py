import glob
import os

import numpy as np
import pandas as pd


DEFAULT_MAX_FILE_BYTES = 100 * 1024 * 1024
DEFAULT_MAX_ROWS = 2_000_000
DEFAULT_MAX_COLUMNS = 256
DEFAULT_MAX_SHEETS = 32
DEFAULT_MAX_STRUCTURE_DEPTH = 12

# 列名映射：标准英文名 → 可接受的中英文别名列表
COLUMN_NAME_MAP = {
    'Date_Time': [
        'Date_Time', '日期时间', '日期', '时间', '测试时间',
        'datetime', 'date_time'],
    'Cycle_Index': [
        'Cycle_Index', '循环序号', '循环索引', '循环次数', '循环',
        'cycle', 'cycle_index'],
    'Step_Index': [
        'Step_Index', '工步序号', '工步索引', '步序号', '工步',
        'step', 'step_index'],
    'Voltage(V)': ['Voltage(V)', '电压(V)', '电压', 'voltage', 'Voltage'],
    'Current(A)': ['Current(A)', '电流(A)', '电流', 'current', 'Current'],
    'Test_Time(s)': [
        'Test_Time(s)', '测试时间(s)', '测试时间', 'Test_Time',
        'test_time', 'test_time(s)'],
    'Internal_Resistance(Ohm)': [
        'Internal_Resistance(Ohm)', '内阻(Ohm)', '内阻', 'resistance',
        'internal_resistance'],
}

REQUIRED_COLUMNS = [
    'Date_Time', 'Cycle_Index', 'Step_Index', 'Voltage(V)',
    'Current(A)', 'Test_Time(s)']


def _build_reverse_map():
    reverse = {}
    for canonical, aliases in COLUMN_NAME_MAP.items():
        for alias in aliases:
            reverse[alias.lower()] = canonical
    return reverse


_REVERSE_COLUMN_MAP = _build_reverse_map()


def normalize_column_names(df):
    """将 DataFrame 中的中文或变体列名统一为标准英文列名。"""
    rename_dict = {}
    for column in df.columns:
        key = str(column).strip().lower()
        if key in _REVERSE_COLUMN_MAP:
            canonical = _REVERSE_COLUMN_MAP[key]
            if column != canonical:
                rename_dict[column] = canonical
    if rename_dict:
        df.rename(columns=rename_dict, inplace=True)
    return df


def validate_training_config(config):
    """Validate parameters that affect data interpretation and model inputs."""
    errors = []
    upper = getattr(config, 'voltage_upper', None)
    lower = getattr(config, 'voltage_lower', None)
    if (not _is_finite_number(upper) or not _is_finite_number(lower) or
            upper <= lower):
        errors.append('SOH 上电压必须是有限数值并且大于下电压')

    rated = getattr(config, 'rated_capacity', None)
    if not _is_finite_number(rated) or not 0.01 <= rated <= 1000:
        errors.append('额定容量必须是 0.01～1000 Ah 范围内的有限数值')

    threshold = getattr(config, 'threshold_ratio', None)
    if not _is_finite_number(threshold) or not 0.1 <= threshold <= 1.0:
        errors.append('失效阈值比例必须位于 0.1～1.0')

    window = getattr(config, 'window_size', None)
    if (isinstance(window, bool) or not isinstance(window, (int, np.integer)) or
            not 1 <= int(window) <= 10000):
        errors.append('窗口大小必须是 1～10000 的整数')

    if str(getattr(config, 'adapter_type', 'CALCE')).upper() == 'CALCE':
        steps = [
            getattr(config, 'cc_step', None),
            getattr(config, 'cv_step', None),
            getattr(config, 'discharge_step', None),
        ]
        if (any(isinstance(value, bool) or not isinstance(
                value, (int, np.integer)) for value in steps) or
                len(set(steps)) != 3):
            errors.append('恒流、恒压和放电工步必须是三个不同的整数')
    return errors


def _is_finite_number(value):
    return (not isinstance(value, (bool, np.bool_)) and
            isinstance(value, (int, float, np.integer, np.floating)) and
            np.isfinite(value))


def validate_file_resource_limits(
        filepath, max_file_bytes=DEFAULT_MAX_FILE_BYTES,
        max_sheets=DEFAULT_MAX_SHEETS):
    """Reject oversized files and workbooks before loading their data."""
    errors = []
    try:
        size = os.path.getsize(filepath)
    except OSError as exc:
        return [f'无法读取文件大小：{exc}']
    if size <= 0:
        errors.append('文件大小为 0，无法读取')
    elif size > max_file_bytes:
        errors.append(
            f'文件大小超过限制（{size} 字节 > {max_file_bytes} 字节）')
    if errors:
        return errors

    extension = os.path.splitext(filepath)[1].lower()
    if extension in ('.xlsx', '.xls'):
        try:
            with pd.ExcelFile(filepath) as workbook:
                if len(workbook.sheet_names) > max_sheets:
                    errors.append(
                        f'工作表数量超过限制（{len(workbook.sheet_names)} > '
                        f'{max_sheets}）')
        except Exception as exc:
            errors.append(f'无法读取工作表结构：{exc}')
    return errors


def _read_data_file(filepath, max_rows=DEFAULT_MAX_ROWS,
                    max_sheets=DEFAULT_MAX_SHEETS):
    """读取受支持的表格文件，限制一次读取的最大行数。"""
    extension = os.path.splitext(filepath)[1].lower()
    row_limit = max_rows + 1 if max_rows is not None else None

    if extension == '.csv':
        for encoding in ('utf-8', 'utf-8-sig', 'gbk', 'gb2312', 'latin-1'):
            try:
                return pd.read_csv(
                    filepath, encoding=encoding, nrows=row_limit)
            except (UnicodeDecodeError, UnicodeError):
                continue
        raise ValueError('无法读取 CSV 文件（编码不支持）')

    if extension in ('.xlsx', '.xls'):
        with pd.ExcelFile(filepath) as workbook:
            if len(workbook.sheet_names) > max_sheets:
                raise ValueError(
                    f'工作表数量超过限制（{len(workbook.sheet_names)} > '
                    f'{max_sheets}）')
            sheet = 1 if len(workbook.sheet_names) > 1 else 0
            return pd.read_excel(
                workbook, sheet_name=sheet, nrows=row_limit)

    if extension == '.json':
        return pd.read_json(filepath)

    if extension in ('.h5', '.hdf5'):
        try:
            return pd.read_hdf(filepath)
        except Exception:
            with pd.HDFStore(filepath, mode='r') as store:
                keys = store.keys()
                if keys:
                    return pd.read_hdf(filepath, key=keys[0])
            raise ValueError('HDF5 文件中未找到有效数据集')

    if extension == '.mat':
        from scipy.io import loadmat
        mat = loadmat(filepath)
        for key, value in mat.items():
            if not key.startswith('__'):
                try:
                    return pd.DataFrame(value)
                except Exception:
                    continue
        raise ValueError('MAT 文件中未找到可转换为表格的数据')

    raise ValueError(
        f'不支持的文件格式: {extension}'
        '（支持 .csv / .xlsx / .json / .h5 / .mat）')


def validate_calce_dataframe(
        dataframe, discharge_step=7, window_size=64, rated_capacity=1.1,
        max_rows=DEFAULT_MAX_ROWS, max_columns=DEFAULT_MAX_COLUMNS):
    """Validate one normalized CALCE table without mutating the caller."""
    errors = []
    if not isinstance(dataframe, pd.DataFrame):
        return ['CALCE 数据必须是表格结构']
    df = dataframe.copy()
    normalize_column_names(df)

    if len(df) > max_rows:
        errors.append(f'数据行数超过限制（{len(df)} > {max_rows}）')
    if len(df.columns) > max_columns:
        errors.append(f'数据列数超过限制（{len(df.columns)} > {max_columns}）')
    duplicated = [
        str(name) for name in df.columns[df.columns.duplicated()].unique()]
    if duplicated:
        errors.append(f'存在重复列：{", ".join(duplicated)}')
        return errors

    actual_columns = [str(column).strip() for column in df.columns]
    missing = [
        column for column in REQUIRED_COLUMNS if column not in actual_columns]
    if missing:
        errors.append(f'缺少必要列：{", ".join(missing)}')
        return errors

    parsed_time = pd.to_datetime(df['Date_Time'], errors='coerce')
    if parsed_time.isna().any():
        errors.append('日期时间列包含无法解析的值')
    elif not parsed_time.is_monotonic_increasing:
        errors.append('日期时间必须按时间单调递增')

    numeric = {}
    for column in (
            'Cycle_Index', 'Step_Index', 'Voltage(V)', 'Current(A)',
            'Test_Time(s)'):
        values = pd.to_numeric(df[column], errors='coerce')
        numeric[column] = values
        array = values.to_numpy(dtype=np.float64, na_value=np.nan)
        if not np.all(np.isfinite(array)):
            errors.append(f'{column} 必须全部是有限数值')
    if any('有限数值' in error for error in errors):
        return errors

    cycle_values = numeric['Cycle_Index'].to_numpy(dtype=np.float64)
    if np.any(np.diff(cycle_values) < 0):
        errors.append('循环顺序必须单调递增，不能回退')

    step_values = numeric['Step_Index']
    discharge_mask = step_values == discharge_step
    if not discharge_mask.any():
        errors.append(f'未找到放电工步（Step_Index={discharge_step}）')
        return errors
    discharge_cycles = numeric['Cycle_Index'][discharge_mask].nunique()
    if discharge_cycles <= window_size:
        errors.append(
            f'有效放电循环数 {discharge_cycles} 必须大于窗口大小 '
            f'{window_size}')

    test_times = numeric['Test_Time(s)']
    group_frame = pd.DataFrame({
        'cycle': numeric['Cycle_Index'],
        'step': step_values,
        'time': test_times,
    })
    if any(not group['time'].is_monotonic_increasing
           for _, group in group_frame.groupby(['cycle', 'step'], sort=False)):
        errors.append('同一循环和工步内的测试时间必须单调递增')

    discharge_current = numeric['Current(A)'][discharge_mask]
    if len(discharge_current) == 0 or float(discharge_current.median()) >= 0:
        errors.append('放电工步电流方向异常，应以负电流为主')

    for cycle in numeric['Cycle_Index'][discharge_mask].drop_duplicates():
        mask = discharge_mask & (numeric['Cycle_Index'] == cycle)
        times = test_times[mask].to_numpy(dtype=np.float64)
        currents = numeric['Current(A)'][mask].to_numpy(dtype=np.float64)
        if len(times) < 2:
            continue
        capacity = -float(np.sum(np.diff(times) * currents[1:]) / 3600)
        if (not np.isfinite(capacity) or capacity <= 0 or
                capacity > rated_capacity * 5):
            errors.append(
                f'循环 {cycle:g} 的放电容量 {capacity:.6g} Ah 超出合理范围')
            break
    return errors


def _structure_depth(value, depth=1, seen=None):
    if seen is None:
        seen = set()
    if isinstance(value, (dict, list, tuple, np.ndarray, np.void)):
        identity = id(value)
        if identity in seen:
            return depth
        seen.add(identity)
    if isinstance(value, dict):
        children = value.values()
    elif isinstance(value, (list, tuple)):
        children = value
    elif isinstance(value, np.ndarray) and value.dtype == object:
        children = value.flat
    elif isinstance(value, np.void) and value.dtype.names:
        children = (value[name] for name in value.dtype.names)
    else:
        return depth
    child_depths = [
        _structure_depth(child, depth + 1, seen) for child in children]
    return max([depth, *child_depths])


def _find_named_value(value, target, depth=0, max_depth=12):
    if depth > max_depth:
        return None
    if isinstance(value, dict):
        if target in value:
            return value[target]
        for child in value.values():
            found = _find_named_value(child, target, depth + 1, max_depth)
            if found is not None:
                return found
    elif isinstance(value, (list, tuple)):
        for child in value:
            found = _find_named_value(child, target, depth + 1, max_depth)
            if found is not None:
                return found
    elif isinstance(value, np.ndarray) and value.dtype == object:
        for child in value.flat:
            found = _find_named_value(child, target, depth + 1, max_depth)
            if found is not None:
                return found
    return None


def _as_scalar(value):
    array = np.asarray(value).reshape(-1)
    return array[0] if len(array) else None


def validate_nasa_structure(
        structure, window_size=64, rated_capacity=1.1,
        max_structure_depth=DEFAULT_MAX_STRUCTURE_DEPTH):
    """Validate NASA MAT semantics without applying CALCE column rules."""
    errors = []
    depth = _structure_depth(structure)
    if depth > max_structure_depth:
        errors.append(
            f'NASA MAT 结构深度超过限制（{depth} > {max_structure_depth}）')
        return errors

    cycles = _find_named_value(
        structure, 'cycle', max_depth=max_structure_depth)
    if cycles is None:
        return ['NASA MAT 中未找到 cycle 结构']
    if isinstance(cycles, dict):
        cycle_items = [cycles]
    elif isinstance(cycles, np.ndarray):
        cycle_items = list(cycles.reshape(-1))
    else:
        cycle_items = list(cycles) if isinstance(
            cycles, (list, tuple)) else [cycles]

    capacities = []
    invalid_capacity = False
    for cycle in cycle_items:
        if not isinstance(cycle, dict):
            continue
        cycle_type = str(_as_scalar(cycle.get('type', ''))).lower()
        if cycle_type != 'discharge':
            continue
        data = cycle.get('data', {})
        if not isinstance(data, dict):
            continue
        capacity = _as_scalar(data.get('Capacity'))
        if capacity is None and {'Current_measured', 'Time'}.issubset(data):
            current = np.asarray(data['Current_measured'], dtype=float).reshape(-1)
            times = np.asarray(data['Time'], dtype=float).reshape(-1)
            if len(times) > 1 and len(current) == len(times):
                capacity = -np.sum(np.diff(times) * current[1:]) / 3600
        if not _is_finite_number(capacity):
            invalid_capacity = True
            continue
        capacity = float(capacity)
        if capacity <= 0 or capacity > rated_capacity * 5:
            errors.append(f'NASA 放电容量 {capacity:.6g} Ah 超出合理范围')
        else:
            capacities.append(capacity)
    if invalid_capacity:
        errors.append('NASA 放电容量必须全部是有限数值')
    if len(capacities) <= window_size:
        errors.append(
            f'NASA 有效放电循环数 {len(capacities)} 必须大于窗口大小 '
            f'{window_size}')
    return errors


def _validate_calce_file(
        filepath, discharge_step, window_size, rated_capacity,
        max_file_bytes, max_rows, max_columns, max_sheets):
    errors = validate_file_resource_limits(
        filepath, max_file_bytes=max_file_bytes, max_sheets=max_sheets)
    if errors:
        return errors
    try:
        dataframe = _read_data_file(
            filepath, max_rows=max_rows, max_sheets=max_sheets)
    except Exception as exc:
        return [f'文件无法读取：{exc}']
    return validate_calce_dataframe(
        dataframe, discharge_step=discharge_step,
        window_size=window_size, rated_capacity=rated_capacity,
        max_rows=max_rows, max_columns=max_columns)


def _load_nasa_structure(filepath):
    from scipy.io import loadmat
    raw = loadmat(filepath, simplify_cells=True)
    return {
        key: value for key, value in raw.items() if not key.startswith('__')}


def _validate_nasa_file(
        filepath, window_size, rated_capacity, max_file_bytes,
        max_sheets, max_structure_depth):
    errors = validate_file_resource_limits(
        filepath, max_file_bytes=max_file_bytes, max_sheets=max_sheets)
    if errors:
        return errors
    try:
        structure = _load_nasa_structure(filepath)
    except Exception as exc:
        return [f'NASA MAT 文件无法读取：{exc}']
    return validate_nasa_structure(
        structure, window_size=window_size, rated_capacity=rated_capacity,
        max_structure_depth=max_structure_depth)


def validate_imported_item(
        path, log_callback=None, discharge_step=7, extensions=None,
        adapter_type='CALCE', window_size=64, rated_capacity=1.1,
        max_file_bytes=DEFAULT_MAX_FILE_BYTES, max_rows=DEFAULT_MAX_ROWS,
        max_columns=DEFAULT_MAX_COLUMNS, max_sheets=DEFAULT_MAX_SHEETS,
        max_structure_depth=DEFAULT_MAX_STRUCTURE_DEPTH):
    """Validate one imported battery path with adapter-specific rules."""
    adapter_type = str(adapter_type).upper()
    if adapter_type not in ('CALCE', 'NASA'):
        return [f'不支持的数据适配器：{adapter_type}']
    if extensions is None:
        extensions = ('.mat',) if adapter_type == 'NASA' else ('.xlsx', '.csv')

    if os.path.isfile(path):
        file_list = [path]
        enforce_window_per_file = True
    elif os.path.isdir(path):
        file_list = []
        for extension in extensions:
            file_list.extend(glob.glob(os.path.join(path, f'*{extension}')))
        enforce_window_per_file = False
    else:
        return [f'路径不存在或不是有效的文件/文件夹：{path}']
    if not file_list:
        return [f'未找到支持的文件（{", ".join(extensions)}）']

    errors = []
    successful_cycle_count = 0
    for filepath in sorted(file_list):
        extension = os.path.splitext(filepath)[1].lower()
        if extension not in extensions:
            errors.append(f'不支持的文件类型：{os.path.basename(filepath)}')
            continue
        per_file_window = window_size if enforce_window_per_file else 0
        if adapter_type == 'NASA':
            file_errors = _validate_nasa_file(
                filepath, per_file_window, rated_capacity, max_file_bytes,
                max_sheets, max_structure_depth)
            if not file_errors and not enforce_window_per_file:
                structure = _load_nasa_structure(filepath)
                cycles = _find_named_value(
                    structure, 'cycle', max_depth=max_structure_depth)
                successful_cycle_count += len(cycles) if hasattr(
                    cycles, '__len__') else 1
        else:
            file_errors = _validate_calce_file(
                filepath, discharge_step, per_file_window, rated_capacity,
                max_file_bytes, max_rows, max_columns, max_sheets)
            if not file_errors and not enforce_window_per_file:
                frame = _read_data_file(
                    filepath, max_rows=max_rows, max_sheets=max_sheets)
                normalize_column_names(frame)
                step = pd.to_numeric(frame['Step_Index'], errors='coerce')
                cycle = pd.to_numeric(frame['Cycle_Index'], errors='coerce')
                successful_cycle_count += int(
                    cycle[step == discharge_step].nunique())
        if file_errors:
            filename = os.path.basename(filepath)
            if log_callback:
                log_callback(f'验证失败：{filename}')
            errors.extend(f'[{filename}] {error}' for error in file_errors)

    if (not enforce_window_per_file and not errors and
            successful_cycle_count <= window_size):
        errors.append(
            f'整块电池有效循环数 {successful_cycle_count} 必须大于窗口大小 '
            f'{window_size}')
    return errors


def validate_evaluation_request(config, imported_paths, log_callback=None):
    """Unified gate used immediately before starting a worker."""
    errors = validate_training_config(config)
    if errors:
        return errors
    if not imported_paths:
        return ['请先导入文件或文件夹']
    for path in imported_paths:
        errors.extend(validate_imported_item(
            path,
            log_callback=log_callback,
            adapter_type=config.adapter_type,
            window_size=config.window_size,
            rated_capacity=config.rated_capacity,
            discharge_step=config.discharge_step,
        ))
    return errors
