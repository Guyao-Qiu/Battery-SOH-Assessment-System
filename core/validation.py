import os
import glob
import numpy as np
import pandas as pd

# 列名映射：标准英文名 → 可接受的中英文别名列表
COLUMN_NAME_MAP = {
    'Date_Time':                ['Date_Time', '日期时间', '日期', '时间', '测试时间', 'datetime', 'date_time'],
    'Cycle_Index':              ['Cycle_Index', '循环序号', '循环索引', '循环次数', '循环', 'cycle', 'cycle_index'],
    'Step_Index':               ['Step_Index', '工步序号', '工步索引', '步序号', '工步', 'step', 'step_index'],
    'Voltage(V)':               ['Voltage(V)', '电压(V)', '电压', 'voltage', 'Voltage'],
    'Current(A)':               ['Current(A)', '电流(A)', '电流', 'current', 'Current'],
    'Test_Time(s)':             ['Test_Time(s)', '测试时间(s)', '测试时间', 'Test_Time', 'test_time', 'test_time(s)'],
    'Internal_Resistance(Ohm)': ['Internal_Resistance(Ohm)', '内阻(Ohm)', '内阻', 'resistance', 'internal_resistance'],
}

REQUIRED_COLUMNS = ['Date_Time', 'Cycle_Index', 'Step_Index', 'Voltage(V)', 'Current(A)', 'Test_Time(s)']


def _build_reverse_map():
    """构建 别名 → 标准名 的反向映射"""
    reverse = {}
    for canonical, aliases in COLUMN_NAME_MAP.items():
        for alias in aliases:
            reverse[alias.lower()] = canonical
    return reverse


_REVERSE_COLUMN_MAP = _build_reverse_map()


def normalize_column_names(df):
    """将 DataFrame 中的中文或变体列名统一为标准英文列名"""
    rename_dict = {}
    for col in df.columns:
        key = str(col).strip().lower()
        if key in _REVERSE_COLUMN_MAP:
            canonical = _REVERSE_COLUMN_MAP[key]
            if col != canonical:
                rename_dict[col] = canonical
    if rename_dict:
        df.rename(columns=rename_dict, inplace=True)
    return df


def _read_data_file(filepath):
    """读取数据文件，支持 csv / xlsx / json / h5 格式"""
    ext = os.path.splitext(filepath)[1].lower()

    if ext == '.csv':
        for enc in ('utf-8', 'utf-8-sig', 'gbk', 'gb2312', 'latin-1'):
            try:
                df = pd.read_csv(filepath, encoding=enc)
                return df
            except (UnicodeDecodeError, UnicodeError):
                continue
        raise ValueError(f'无法读取CSV文件（编码不支持）')

    elif ext in ('.xlsx', '.xls'):
        # 尝试读取第2个 sheet（CALCE 惯例），失败则回退到第1个
        try:
            return pd.read_excel(filepath, sheet_name=1)
        except Exception:
            return pd.read_excel(filepath, sheet_name=0)

    elif ext == '.json':
        return pd.read_json(filepath)

    elif ext in ('.h5', '.hdf5'):
        try:
            return pd.read_hdf(filepath)
        except Exception:
            # 如果有多个 key，尝试读取第一个
            with pd.HDFStore(filepath, mode='r') as store:
                keys = store.keys()
                if keys:
                    return pd.read_hdf(filepath, key=keys[0])
            raise ValueError('HDF5 文件中未找到有效数据集')

    elif ext == '.mat':
        # 表格型 .mat（非 NASA 结构体格式）
        from scipy.io import loadmat
        mat = loadmat(filepath)
        for k, v in mat.items():
            if not k.startswith('__'):
                try:
                    return pd.DataFrame(v)
                except Exception:
                    continue
        raise ValueError('MAT 文件中未找到可转换为表格的数据')

    else:
        raise ValueError(f'不支持的文件格式: {ext}（支持 .csv / .xlsx / .json / .h5 / .mat）')


def _validate_single_file(filepath, discharge_step=7):
    """校验单个数据文件，返回错误信息列表（空列表表示通过）

    参数:
        filepath       : 文件路径
        discharge_step : 放电工步序号（可配置，默认 7）
    """
    errors = []
    filename = os.path.basename(filepath)

    # 1. 可读性检查
    try:
        df = _read_data_file(filepath)
    except Exception as e:
        errors.append(f'文件无法读取：{e}')
        return errors

    # 2. 列名检查
    normalize_column_names(df)
    actual_cols = [str(c).strip() for c in df.columns]
    missing = [c for c in REQUIRED_COLUMNS if c not in actual_cols]
    if missing:
        errors.append(f'缺少必要列：{", ".join(missing)}，当前列名为：{", ".join(actual_cols)}')
        return errors  # 后续检查依赖必要列，提前返回

    # 3. 日期时间可解析性检查
    try:
        pd.to_datetime(df['Date_Time'])
    except Exception:
        errors.append('"日期时间"列无法解析，请检查数据格式（期望格式如 YYYY-MM-DD HH:MM:SS）')

    # 4. 数值列有效性检查
    for col in ['Voltage(V)', 'Current(A)', 'Test_Time(s)']:
        try:
            vals = pd.to_numeric(df[col], errors='coerce')
            if vals.isna().any():
                nan_count = vals.isna().sum()
                errors.append(f'"{col}"列包含 {nan_count} 个无效数值（非数字或为空）')
        except Exception:
            errors.append(f'"{col}"列无法转换为数值类型')

    # 5. 放电工步检查（使用可配置的工步序号）
    try:
        step_idx = pd.to_numeric(df['Step_Index'], errors='coerce')
        if not (step_idx == discharge_step).any():
            errors.append(f'未找到放电工步记录（Step_Index={discharge_step}），请检查"工步序号"列或在参数中调整放电工步号')
    except Exception:
        errors.append('"工步序号"列数据异常，无法识别放电工步')

    # 6. 最少循环数检查
    try:
        step_idx = pd.to_numeric(df['Step_Index'], errors='coerce')
        cycle_idx = pd.to_numeric(df['Cycle_Index'], errors='coerce')
        discharge_cycles = cycle_idx[step_idx == discharge_step].nunique()
        if discharge_cycles < 3:
            errors.append(f'有效放电循环数不足（当前 {discharge_cycles} 个循环，至少需要 3 个循环才能进行SOH评估）')
    except Exception:
        errors.append('"循环序号"列数据异常，无法统计放电循环数')

    return errors


def validate_imported_item(path, log_callback=None, discharge_step=7, extensions=None):
    """校验导入的路径（文件或文件夹），返回错误信息列表（空列表表示通过）

    参数:
        path           : 文件或文件夹路径
        log_callback   : 日志回调
        discharge_step : 放电工步序号（可配置）
        extensions     : 支持的扩展名元组，默认为 ('.xlsx', '.csv')
    """
    if extensions is None:
        extensions = ('.xlsx', '.csv')

    errors = []

    if os.path.isfile(path):
        ext = os.path.splitext(path)[1].lower()
        if ext not in extensions:
            errors.append(f'不支持的文件类型：{os.path.basename(path)}，支持的格式：{", ".join(extensions)}')
            return errors
        file_errors = _validate_single_file(path, discharge_step=discharge_step)
        errors.extend(file_errors)

    elif os.path.isdir(path):
        file_list = []
        for ext in extensions:
            file_list.extend(glob.glob(os.path.join(path, f'*{ext}')))
        if not file_list:
            errors.append(f'文件夹中未找到支持的文件（{", ".join(extensions)}）')
            return errors
        for f in sorted(file_list):
            file_errors = _validate_single_file(f, discharge_step=discharge_step)
            if file_errors:
                if log_callback:
                    log_callback(f'验证失败：{os.path.basename(f)}')
                for e in file_errors:
                    errors.append(f'[{os.path.basename(f)}] {e}')
    else:
        errors.append(f'路径不存在或不是有效的文件/文件夹：{path}')

    return errors
