"""
电池数据适配器模块

通过适配器模式将不同来源、不同格式的电池循环数据统一为标准输出：
  DataFrame(cycle, capacity, dq_v, resistance, CCCT, CVCT)

其中 dq_v 是电压窗口 [voltage_lower, voltage_upper] 内的放电容量差，属于
健康指标 HI，不是 SOH（SOH = C / C_rated）；旧列名 'SoH' 仍作为别名保留。

内置两种适配器：
  1. CALCEAdapter  — CALCE 数据集格式（xlsx/csv），工步可配置（默认 2/4/7）
  2. NASAAdapter   — NASA 数据集格式（.mat），容量直接从结构体提取

所有适配器返回相同的 (battery_dict, battery_list) 结构，
下游 preprocess / train / evaluate 无需感知数据来源。
"""
import os
import glob
import numpy as np
import pandas as pd
from abc import ABC, abstractmethod

from .preprocess import OUTLIER_MODES, filter_capacity_outliers
from .validation import normalize_column_names, _read_data_file


def _read_data_sort_date(path):
    """Read only the first row needed to sort a CALCE source file."""
    extension = os.path.splitext(path)[1].lower()
    if extension == '.csv':
        header = pd.read_csv(path, nrows=1)
    elif extension == '.xlsx':
        with pd.ExcelFile(path) as workbook:
            sheet = 1 if len(workbook.sheet_names) > 1 else 0
            header = pd.read_excel(workbook, sheet_name=sheet, nrows=1)
    else:
        raise ValueError(f'不支持的数据文件格式: {extension}')
    normalize_column_names(header)
    if len(header) == 0 or 'Date_Time' not in header.columns:
        raise ValueError('缺少可用于排序的 Date_Time 首行')
    return header['Date_Time'].iloc[0]


def split_cc_cv(t, v, v_cv=4.2, tol=0.02):
    """从一次充电记录里分出恒流(CC)与恒压(CV)的时长（秒）。

    判据：电压第一次到达 v_cv - tol 就认为 CC 结束、进入 CV。
    NASA 电池充电协议是 1.5 A 恒流充到 4.2 V 再恒压（v_cv 做成参数，换电池体系时可调）。
    返回 (ccct, cvct)；数据太短返回 (nan, nan)；从未进入恒压则 cvct = 0。
    """
    t = np.asarray(t, dtype=float).reshape(-1)
    v = np.asarray(v, dtype=float).reshape(-1)
    if len(t) < 2 or len(t) != len(v):
        return (np.nan, np.nan)
    hit = np.flatnonzero(v >= v_cv - tol)
    if len(hit) == 0:
        return (float(t[-1] - t[0]), 0.0)
    k = int(hit[0])
    return (float(t[k] - t[0]), float(t[-1] - t[k]))


class BatteryDataAdapter(ABC):
    """电池数据适配器基类"""

    @classmethod
    @abstractmethod
    def name(cls) -> str:
        """适配器唯一标识（用于配置序列化）"""

    @classmethod
    @abstractmethod
    def display_name(cls) -> str:
        """UI 显示名称"""

    @classmethod
    @abstractmethod
    def extensions(cls) -> tuple:
        """支持的文件扩展名，如 ('.xlsx', '.csv')"""

    @classmethod
    @abstractmethod
    def needs_step_config(cls) -> bool:
        """是否需要用户配置工步序号"""

    @classmethod
    @abstractmethod
    def needs_voltage_config(cls) -> bool:
        """是否需要用户配置 SOH 上下电压"""

    @abstractmethod
    def load_battery_data(self, paths, voltage_upper, voltage_lower,
                          cc_step, cv_step, discharge_step,
                          log_callback, stop_flag, outlier_mode='mark') -> tuple:
        """
        加载电池数据，返回 (battery_dict, battery_list)

        参数:
            paths           : 导入路径列表（文件或文件夹）
            voltage_upper   : SOH 上电压 (V)
            voltage_lower   : SOH 下电压 (V)
            cc_step         : 恒流充电工步序号
            cv_step         : 恒压充电工步序号
            discharge_step  : 放电工步序号
            log_callback    : 日志回调函数
            stop_flag       : 停止标志函数（返回 True 时中止）
            outlier_mode    : 异常容量点处理（'mark' / 'delete' / 'off'）

        返回:
            battery_dict[name] = pd.DataFrame(cycle, capacity, dq_v, resistance, CCCT, CVCT)
            battery_list = [name1, name2, ...]

        说明:
            dq_v 是电压窗口内的放电容量差（健康指标 HI），'SoH' 仅作为它的
            兼容别名列保留，含义与 dq_v 完全相同。
        """


# ─── 通用容量提取逻辑（CALCE 适配器使用） ────────────────────────

def _extract_capacity_from_tabular(df, voltage_upper, voltage_lower,
                                   cc_step, cv_step, discharge_step,
                                   log_callback, name):
    """
    从标准化 DataFrame 中提取每循环的容量、SOH、内阻、充放电时间。

    这是 CALCE 适配器使用的核心逻辑，
    工步序号由参数传入而非硬编码。
    """
    cycles = sorted(list(set(df['Cycle_Index'])))
    discharge_cycles = []
    discharge_capacities = []
    health_indicator = []
    internal_resistance = []
    CCCT = []
    CVCT = []

    for c in cycles:
        df_lim = df[df['Cycle_Index'] == c]

        # 充电阶段：恒流 + 恒压
        df_cc = df_lim[df_lim['Step_Index'] == cc_step]
        df_cv = df_lim[df_lim['Step_Index'] == cv_step]

        if len(df_cc) != 0:
            ccct = np.max(df_cc['Test_Time(s)']) - np.min(df_cc['Test_Time(s)'])
        else:
            ccct = 0

        if len(df_cv) != 0:
            cvct = np.max(df_cv['Test_Time(s)']) - np.min(df_cv['Test_Time(s)'])
        else:
            cvct = 0

        # 放电阶段
        df_d = df_lim[df_lim['Step_Index'] == discharge_step]
        d_v = df_d['Voltage(V)']
        d_c = df_d['Current(A)']
        d_t = df_d['Test_Time(s)']
        d_im = df_d['Internal_Resistance(Ohm)'] if 'Internal_Resistance(Ohm)' in df_d.columns else pd.Series(dtype=float)

        if (len(list(d_c)) != 0) and (len(list(d_t)) > 1):
            time_diff = np.diff(list(d_t))
            d_c_arr = np.array(list(d_c))[1:]
            instant_cap = time_diff * d_c_arr / 3600
            if len(instant_cap) == 0:
                continue
            discharge_cycles.append(c)
            discharge_capacities.append(-1 * np.sum(instant_cap))
            CCCT.append(ccct)
            CVCT.append(cvct)

            cum_cap = np.cumsum(instant_cap)
            dec = np.abs(np.array(d_v) - voltage_upper)[1:]
            if len(dec) == 0:
                health_indicator.append(np.nan)
            else:
                start = cum_cap[np.argmin(dec)]
                dec = np.abs(np.array(d_v) - voltage_lower)[1:]
                end = cum_cap[np.argmin(dec)] if len(dec) != 0 else start
                health_indicator.append(-1 * (end - start))

            if len(d_im) != 0:
                internal_resistance.append(np.mean(np.array(d_im)))
            else:
                internal_resistance.append(np.nan)

    return (discharge_cycles, discharge_capacities, health_indicator,
            internal_resistance, CCCT, CVCT)


def _extract_capacity_lists_fast(df, voltage_upper, voltage_lower,
                                 cc_step, cv_step, discharge_step):
    """与 :func:`_extract_capacity_from_tabular` 数值等价的单遍扫描实现。

    只对整表做一次 ``groupby``，不再逐循环布尔筛选；组内保持原始行顺序
    （groupby 不会重排组内行），所以积分、极值、均值结果与原实现逐位一致。
    返回同样的 6 个列表：
    ``(cycles, capacities, health_indicator, resistance, CCCT, CVCT)``。
    """
    has_ir = 'Internal_Resistance(Ohm)' in df.columns
    cycles, capacities, health_indicator = [], [], []
    internal_resistance, CCCT, CVCT = [], [], []

    for cyc, g in df.groupby('Cycle_Index', sort=True):
        step = g['Step_Index'].to_numpy()
        t = g['Test_Time(s)'].to_numpy(dtype=float)
        v = g['Voltage(V)'].to_numpy(dtype=float)
        i = g['Current(A)'].to_numpy(dtype=float)
        is_cc, is_cv, is_d = step == cc_step, step == cv_step, step == discharge_step
        ccct = float(t[is_cc].max() - t[is_cc].min()) if is_cc.any() else 0.0
        cvct = float(t[is_cv].max() - t[is_cv].min()) if is_cv.any() else 0.0
        td, vd, idd = t[is_d], v[is_d], i[is_d]
        if len(idd) == 0 or len(td) <= 1:
            continue
        inst = np.diff(td) * idd[1:] / 3600.0
        cum = np.cumsum(inst)
        start = cum[np.argmin(np.abs(vd - voltage_upper)[1:])]
        end = cum[np.argmin(np.abs(vd - voltage_lower)[1:])]
        ir = (float(np.mean(g['Internal_Resistance(Ohm)'].to_numpy()[is_d]))
              if has_ir else np.nan)
        cycles.append(cyc)
        capacities.append(float(-inst.sum()))
        health_indicator.append(float(-(end - start)))
        internal_resistance.append(ir)
        CCCT.append(ccct)
        CVCT.append(cvct)

    return (cycles, capacities, health_indicator,
            internal_resistance, CCCT, CVCT)


def extract_cycles_fast(df, voltage_upper, voltage_lower, cc_step, cv_step, discharge_step):
    """与 _extract_capacity_from_tabular 数值等价，但只扫描一遍整表。

    组内保持原始行顺序（groupby 不会重排组内行），所以积分结果与原实现逐位一致。
    返回 DataFrame：cycle, capacity, dq_v(原 SoH), resistance, CCCT, CVCT
    """
    (cycles, capacities, health_indicator,
     internal_resistance, CCCT, CVCT) = _extract_capacity_lists_fast(
        df, voltage_upper, voltage_lower, cc_step, cv_step, discharge_step)
    return pd.DataFrame({
        'cycle': cycles,
        'capacity': capacities,
        'dq_v': health_indicator,
        'resistance': internal_resistance,
        'CCCT': CCCT,
        'CVCT': CVCT,
    }, columns=['cycle', 'capacity', 'dq_v', 'resistance', 'CCCT', 'CVCT'])


def _build_battery_dataframe(cycle_indices, discharge_capacities, health_indicator,
                             internal_resistance, CCCT, CVCT,
                             name, log_callback, clean_outliers=None,
                             protect_knees=True, raw_index=None,
                             outlier_mode='mark'):
    """将提取数组组装为 DataFrame；默认保留有限原始容量以避免评估泄漏。

    参数:
        raw_index : 可选，与 capacities 等长的原始循环索引（如 NASA 原始工步序号）。
                    提供时输出额外的 'raw_index' 列，便于回溯到源文件中的位置。
        outlier_mode : ``'mark'``（默认，A12）/ ``'delete'`` / ``'off'``。
                    默认只**标记**可疑点并保留数据：局部窗口均值对快速下降段和
                    NASA 的容量再生（真实物理）都会滞后，直接删会误伤。
        clean_outliers : 旧参数，保持向后兼容。显式传 ``True``/``False`` 时分别
                    等价于 ``outlier_mode='delete'`` / ``'off'``；传 ``None``
                    （默认）则使用 ``outlier_mode``。
    """
    count = len(discharge_capacities)
    if count == 0:
        return None

    if clean_outliers is not None:
        outlier_mode = 'delete' if clean_outliers else 'off'
    if outlier_mode not in OUTLIER_MODES:
        raise ValueError(
            f'不支持的离群点模式: {outlier_mode}（可选 {OUTLIER_MODES}）')

    discharge_capacities = np.array(discharge_capacities)
    cycle_indices = np.asarray(cycle_indices)

    def aligned(values):
        result = np.full(count, np.nan, dtype=float)
        values = np.asarray(values).reshape(-1)
        available = min(count, len(values))
        if available:
            result[:available] = values[:available]
        return result

    if len(cycle_indices) != count:
        raise ValueError('原始循环编号与有效放电容量数量不一致')
    health_indicator = aligned(health_indicator)
    internal_resistance = aligned(internal_resistance)
    CCCT = aligned(CCCT)
    CVCT = aligned(CVCT)
    if raw_index is not None:
        raw_index = aligned(raw_index)

    filter_result = filter_capacity_outliers(
        discharge_capacities, bins=40, protect_knees=protect_knees,
        mode=outlier_mode)
    idx = filter_result.indices

    if log_callback:
        if outlier_mode == 'chunked':
            log_callback(
                '数据筛选原则：将容量序列按每 40 个循环划分为局部窗口，'
                '窗口内计算均值 μ 与标准差 σ，剔除超出 μ±2σ 范围的点。'
                '边界点和稳定窗口保留，持续退化膝点受到保护。')
        elif outlier_mode == 'delete':
            log_callback(
                '数据筛选原则：每个容量点只参考此前最多 40 个有效循环，'
                '按历史均值 μ 与标准差 σ 剔除异常点。'
                '不读取未来循环，初始稳定段和退化膝点受到保护。'
            )
        elif outlier_mode == 'mark':
            log_callback(
                '数据筛选原则：只**标记**可疑点、不删除（容量再生是真实物理；'
                '局部窗口均值对快速下降段会滞后）。'
                '判定只用此前最多 40 个有效循环，不读取未来循环。'
            )
        else:
            log_callback(
                '数据筛选原则：为避免使用完整测试轨迹造成评估泄漏，'
                '默认保留所有有限容量点；仅剔除 NaN/Inf。')
        log_callback(
            f'{name} 异常值审计：输入 {count}，保留 {len(idx)}，'
            f'剔除 {filter_result.removed_count}，'
            f'标记 {filter_result.marked_count}，'
            f'保护膝点 {len(filter_result.protected_indices)}。')
        log_callback('─' * 40)

    filtered_cycles = cycle_indices[idx]
    has_cycle_reset = (
        len(filtered_cycles) > 1 and
        np.any(np.diff(filtered_cycles.astype(np.float64)) <= 0)
    )
    display_cycles = (
        np.arange(1, len(filtered_cycles) + 1)
        if has_cycle_reset else filtered_cycles
    )
    result_data = {
        'cycle': display_cycles,
        'capacity': discharge_capacities[idx],
        'dq_v': health_indicator[idx],
        'resistance': internal_resistance[idx],
        'CCCT': CCCT[idx],
        'CVCT': CVCT[idx],
    }
    # 兼容别名：dq_v 即电压窗口内的放电容量差（健康指标 HI），不是 SOH。
    # 保留 'SoH' 键名，避免旧代码 / 旧 notebook 读取 df['SoH'] 时 KeyError。
    result_data['SoH'] = result_data['dq_v']
    if raw_index is not None:
        result_data['raw_index'] = raw_index[idx]
    if has_cycle_reset:
        if log_callback:
            log_callback(
                f'{name} 检测到分文件循环号重复或回退；结果已按有效放电记录'
                '连续编号。')
    df_result = pd.DataFrame(result_data)
    # raw_index 是原始序号，能完整取整时转成整数列（更贴近源文件里的编号）
    if raw_index is not None and len(df_result) and \
            np.all(np.isfinite(df_result['raw_index'])) and \
            np.all(df_result['raw_index'] == np.floor(df_result['raw_index'])):
        df_result['raw_index'] = df_result['raw_index'].astype(np.int64)
    df_result.attrs['outlier_audit'] = {
        'mode': outlier_mode,
        'enabled': outlier_mode != 'off',
        'protect_knees': bool(protect_knees),
        'input_count': count,
        'kept_count': int(len(idx)),
        'removed_count': filter_result.removed_count,
        'marked_count': filter_result.marked_count,
        'mask': filter_result.mask.tolist(),
        'marked_indices': filter_result.marked_indices.tolist(),
        'removed_indices': filter_result.removed_indices.tolist(),
        'protected_indices': filter_result.protected_indices.tolist(),
        'reasons': dict(filter_result.reasons),
    }

    return df_result


# ─── 1. CALCE 适配器 ──────────────────────────────────────────────

def _load_calce_npy(filepath, log_callback=None):
    """读取预提取的 CALCE .npy 字典（对齐 XiuzeZhou/RUL CALCE.npy 格式）。"""
    raw = np.load(filepath, allow_pickle=True)
    payload = raw.item() if isinstance(raw, np.ndarray) and raw.ndim == 0 else raw
    if not isinstance(payload, dict):
        raise ValueError('CALCE .npy 文件必须包含以电池名为键的字典对象')

    battery_dict = {}
    battery_list = []
    for name, frame in payload.items():
        df = frame.copy() if isinstance(frame, pd.DataFrame) else pd.DataFrame(frame)
        if 'capacity' not in df.columns:
            continue
        cap = pd.to_numeric(df['capacity'], errors='coerce')
        valid = np.isfinite(cap.to_numpy(dtype=np.float64))
        df = df.loc[valid].reset_index(drop=True)
        if len(df) == 0:
            continue
        if 'cycle' not in df.columns:
            df['cycle'] = np.arange(1, len(df) + 1, dtype=np.float64)
        if 'dq_v' not in df.columns:
            df['dq_v'] = df['SoH'] if 'SoH' in df.columns else df['capacity']
        if 'SoH' not in df.columns:
            df['SoH'] = df['dq_v']
        for col in ('resistance', 'CCCT', 'CVCT'):
            if col not in df.columns:
                df[col] = np.nan
        df.attrs['outlier_audit'] = {
            'mode': 'pre_extracted_npy',
            'enabled': False,
            'protect_knees': True,
            'input_count': int(len(df)),
            'kept_count': int(len(df)),
            'removed_count': 0,
            'marked_count': 0,
            'mask': [True] * len(df),
            'marked_indices': [],
            'removed_indices': [],
            'protected_indices': [],
            'reasons': {},
        }
        battery_dict[str(name)] = df
        battery_list.append(str(name))
        if log_callback:
            log_callback(f'从 {os.path.basename(filepath)} 加载电池 {name}（{len(df)} 个循环）')
    return battery_dict, battery_list


class CALCEAdapter(BatteryDataAdapter):
    """CALCE 数据集适配器 — xlsx/csv 格式（亦兼容预提取 CALCE.npy），工步由用户配置"""

    @classmethod
    def name(cls):
        return 'CALCE'

    @classmethod
    def display_name(cls):
        return '.xlsx/.csv'

    @classmethod
    def extensions(cls):
        return ('.xlsx', '.csv')

    @classmethod
    def needs_step_config(cls):
        return True

    @classmethod
    def needs_voltage_config(cls):
        return True

    def load_battery_data(self, paths, voltage_upper, voltage_lower,
                          cc_step, cv_step, discharge_step,
                          log_callback, stop_flag, outlier_mode='mark'):
        battery_dict = {}
        battery_list = []

        for path in paths:
            if stop_flag is not None and stop_flag():
                break

            if os.path.isfile(path) and path.lower().endswith('.npy'):
                try:
                    npy_dict, npy_list = _load_calce_npy(path, log_callback=log_callback)
                    for npy_name in npy_list:
                        if npy_name in battery_dict:
                            if log_callback:
                                log_callback(f'跳过数据集 {npy_name}：电池名称重复')
                            continue
                        battery_dict[npy_name] = npy_dict[npy_name]
                        battery_list.append(npy_name)
                except Exception as exc:
                    if log_callback:
                        log_callback(f'跳过 {path}，原因：{exc}')
                continue

            if os.path.isfile(path):
                name = os.path.splitext(os.path.basename(path))[0]
                file_list = [path]
            elif os.path.isdir(path):
                name = os.path.basename(path.rstrip('/\\'))
                file_list = []
                for ext in self.extensions():
                    file_list.extend(glob.glob(os.path.join(path, f'*{ext}')))
                # 文件系统返回顺序不保证稳定；先排序，再按日期排序，
                # 保证同一目录在不同机器上得到一致的读取顺序。
                file_list = sorted(file_list)
                if not file_list:
                    npy_candidates = sorted(glob.glob(os.path.join(path, '*.npy')))
                    for npy_path in npy_candidates:
                        try:
                            npy_dict, npy_list = _load_calce_npy(
                                npy_path, log_callback=log_callback)
                            for npy_name in npy_list:
                                if npy_name not in battery_dict:
                                    battery_dict[npy_name] = npy_dict[npy_name]
                                    battery_list.append(npy_name)
                        except Exception as exc:
                            if log_callback:
                                log_callback(f'跳过 {npy_path}，原因：{exc}')
                    continue
            else:
                continue

            if not file_list:
                continue

            if log_callback:
                log_callback(f'加载数据集 {name} ...')

            # 按日期排序
            dates = []
            valid_path = []
            for p in file_list:
                try:
                    sort_date = _read_data_sort_date(p)
                    if log_callback:
                        log_callback(f'读取 {p} 的排序信息 ...')
                    dates.append(sort_date)
                    valid_path.append(p)
                except Exception as e:
                    if log_callback:
                        log_callback(f'跳过 {p}，原因：{e}')

            if len(valid_path) == 0:
                if log_callback:
                    log_callback(f'跳过数据集 {name}：没有可读取的有效文件')
                continue

            idx = np.argsort(dates)
            path_sorted = np.array(valid_path)[idx]

            all_cap = []
            all_cycles = []
            all_soh = []
            all_ir = []
            all_ccct = []
            all_cvct = []

            for p in path_sorted:
                if stop_flag is not None and stop_flag():
                    break
                df = _read_data_file(p)
                normalize_column_names(df)
                if log_callback:
                    log_callback(f'加载 {p} ...')

                cycles, cap, soh, ir, ccct, cvct = _extract_capacity_lists_fast(
                    df, voltage_upper, voltage_lower,
                    cc_step, cv_step, discharge_step
                )
                all_cycles.extend(cycles)
                all_cap.extend(cap)
                all_soh.extend(soh)
                all_ir.extend(ir)
                all_ccct.extend(ccct)
                all_cvct.extend(cvct)

            df_result = _build_battery_dataframe(
                all_cycles, all_cap, all_soh, all_ir, all_ccct, all_cvct,
                name, log_callback, outlier_mode=outlier_mode
            )
            if df_result is not None:
                if name in battery_dict:
                    if log_callback:
                        log_callback(f'跳过数据集 {name}：电池名称重复')
                    continue
                battery_dict[name] = df_result
                battery_list.append(name)
            elif log_callback:
                log_callback(f'跳过数据集 {name}：没有可用的放电循环')

        return battery_dict, battery_list


# ─── 2. NASA 适配器 ───────────────────────────────────────────────

class NASAAdapter(BatteryDataAdapter):
    """NASA 数据集适配器 — .mat 格式，容量直接从结构体提取"""

    @classmethod
    def name(cls):
        return 'NASA'

    @classmethod
    def display_name(cls):
        return '.mat'

    @classmethod
    def extensions(cls):
        return ('.mat',)

    @classmethod
    def needs_step_config(cls):
        return False

    @classmethod
    def needs_voltage_config(cls):
        return True

    def load_battery_data(self, paths, voltage_upper, voltage_lower,
                          cc_step, cv_step, discharge_step,
                          log_callback, stop_flag, v_cv=None,
                          outlier_mode='mark'):
        try:
            from scipy.io import loadmat
        except ImportError:
            raise ImportError(
                'NASA 数据集适配器需要 scipy 库。请在环境中安装：pip install scipy'
            )

        # CC/CV 分界电压：优先使用调用方显式传入的 v_cv；否则若 voltage_upper
        # 看起来是合理的充电截止电压（>= 3.0 V，例如 NASA 用户填 4.2），就用它；
        # 否则（例如沿用 CALCE 默认的 3.8 以下窗口电压）退回 4.2 V 默认值。
        if v_cv is None:
            if voltage_upper is not None and np.isfinite(voltage_upper) \
                    and voltage_upper >= 3.0:
                v_cv = float(voltage_upper)
            else:
                v_cv = 4.2
        else:
            v_cv = float(v_cv)

        battery_dict = {}
        battery_list = []

        for path in paths:
            if stop_flag is not None and stop_flag():
                break

            if os.path.isfile(path) and path.lower().endswith('.mat'):
                name = os.path.splitext(os.path.basename(path))[0]
                file_list = [path]
            elif os.path.isdir(path):
                name = os.path.basename(path.rstrip('/\\'))
                # 排序：glob 的返回顺序依赖文件系统，排序后读取顺序才可复现
                file_list = sorted(glob.glob(os.path.join(path, '*.mat')))
            else:
                continue

            if not file_list:
                continue

            if log_callback:
                log_callback(f'加载数据集 {name}...')

            discharge_capacities = []
            discharge_cycles = []
            discharge_raw_index = []
            health_indicator = []
            internal_resistance = []
            CCCT = []
            CVCT = []
            pending_ccct = np.nan
            pending_cvct = np.nan

            for p in file_list:
                if stop_flag is not None and stop_flag():
                    break
                try:
                    mat = loadmat(p, simplify_cells=True)
                except Exception as e:
                    if log_callback:
                        log_callback(f'跳过 {p}，原因：{e}')
                    continue

                # 找到电池结构体键（跳过 __header__ 等元数据键）
                battery_key = None
                for k in mat.keys():
                    if not k.startswith('__'):
                        battery_key = k
                        break
                if battery_key is None:
                    if log_callback:
                        log_callback(f'跳过 {p}，原因：未找到有效数据键')
                    continue

                battery_struct = mat[battery_key]
                try:
                    if not isinstance(battery_struct, dict):
                        raise ValueError('电池根节点必须是结构体')
                    cycles = battery_struct['cycle']
                    if isinstance(cycles, dict):
                        cycles = [cycles]
                    else:
                        cycles = np.asarray(
                            cycles, dtype=object).reshape(-1).tolist()
                except (KeyError, TypeError, ValueError) as e:
                    if log_callback:
                        log_callback(f'跳过 {p}，原因：数据结构异常 {e}')
                    continue

                for i in range(len(cycles)):
                    if stop_flag is not None and stop_flag():
                        break
                    try:
                        cycle = cycles[i]
                        if not isinstance(cycle, dict):
                            continue
                        cycle_type = str(cycle.get('type', ''))
                        data = cycle.get('data')
                        if not isinstance(data, dict):
                            continue

                        if cycle_type.lower() == 'discharge':
                            # NASA 数据集直接提供放电容量
                            if 'Capacity' in data:
                                cap = float(np.asarray(
                                    data['Capacity']).reshape(-1)[0])
                            else:
                                # 回退：从电流和时间积分
                                v = np.asarray(
                                    data['Voltage_measured']).reshape(-1)
                                c = np.asarray(
                                    data['Current_measured']).reshape(-1)
                                t = np.asarray(data['Time']).reshape(-1)
                                if len(t) > 1:
                                    dt = np.diff(t)
                                    c_arr = c[1:]
                                    cap = -np.sum(dt * c_arr / 3600)
                                else:
                                    continue

                            if cap > 0 and not np.isnan(cap):
                                # cycle 用「有效放电次数」编号（1,2,3,...），与文献里
                                # 的放电循环数一致；原始工步序号保留在 raw_index 列。
                                discharge_cycles.append(len(discharge_cycles) + 1)
                                discharge_raw_index.append(i + 1)
                                discharge_capacities.append(cap)

                                # SOH：从电压-容量曲线提取
                                v = np.asarray(
                                    data.get('Voltage_measured', [])).reshape(-1)
                                c_arr = np.asarray(
                                    data.get('Current_measured', [])).reshape(-1)
                                t = np.asarray(data.get('Time', [])).reshape(-1)
                                if len(t) > 1:
                                    dt = np.diff(t)
                                    instant_cap = dt * c_arr[1:] / 3600
                                    cum_cap = np.cumsum(instant_cap)
                                    dec_upper = np.abs(v[1:] - voltage_upper)
                                    if len(dec_upper) > 0:
                                        start = cum_cap[np.argmin(dec_upper)]
                                        dec_lower = np.abs(v[1:] - voltage_lower)
                                        end = cum_cap[np.argmin(dec_lower)] if len(dec_lower) > 0 else start
                                        health_indicator.append(-1 * (end - start))
                                    else:
                                        health_indicator.append(np.nan)
                                else:
                                    health_indicator.append(np.nan)

                                internal_resistance.append(np.nan)
                                CCCT.append(pending_ccct)
                                CVCT.append(pending_cvct)
                                pending_ccct = np.nan
                                pending_cvct = np.nan

                        elif cycle_type.lower() == 'charge':
                            # 从充电阶段提取 CCCT / CVCT：按电压是否到达充电截止
                            # 电压（v_cv）真实切分恒流段与恒压段，不再用固定比例估计。
                            t = np.asarray(data.get('Time', [])).reshape(-1)
                            v = np.asarray(
                                data.get('Voltage_measured', [])).reshape(-1)
                            pending_ccct, pending_cvct = split_cc_cv(
                                t, v, v_cv=v_cv)
                    except (IndexError, KeyError, ValueError):
                        continue

            df_result = _build_battery_dataframe(
                discharge_cycles, discharge_capacities, health_indicator,
                internal_resistance, CCCT, CVCT,
                name, log_callback, raw_index=discharge_raw_index,
                outlier_mode=outlier_mode
            )
            if df_result is not None:
                if name in battery_dict:
                    if log_callback:
                        log_callback(f'跳过数据集 {name}：电池名称重复')
                    continue
                battery_dict[name] = df_result
                battery_list.append(name)
            elif log_callback:
                log_callback(f'跳过数据集 {name}：没有可用的放电循环')

        return battery_dict, battery_list


# ─── 适配器注册表 ─────────────────────────────────────────────────

def detect_step_indices(df):
    """从标准化后的 CALCE DataFrame 推断 (cc_step, cv_step, discharge_step)。

    判据（尽量保守，识别不出就返回 None）：
      * 放电：电流 < 0；
      * 恒流充电 CC：电流 > 0 且电压在上升；
      * 恒压充电 CV：电流 > 0 但在衰减，且电压接近本循环最大值。

    返回 {'cc_step', 'cv_step', 'discharge_step', 'confidence', 'summary'}，
    供 UI「自动识别工步」按钮使用；空表或缺少必需列时各项为 None。
    """
    result = {'cc_step': None, 'cv_step': None, 'discharge_step': None,
              'confidence': 0.0, 'summary': '无法识别'}
    required = ('Step_Index', 'Current(A)', 'Voltage(V)', 'Cycle_Index')
    if df is None or len(df) == 0:
        result['summary'] = '数据为空'
        return result
    if any(column not in df.columns for column in required):
        result['summary'] = '缺少必要列：' + ', '.join(
            column for column in required if column not in df.columns)
        return result

    try:
        frame = df.loc[:, list(required)].dropna()
        if len(frame) == 0:
            result['summary'] = '数据为空'
            return result
        step = frame['Step_Index'].to_numpy()
        current = frame['Current(A)'].to_numpy(dtype=float)
        voltage = frame['Voltage(V)'].to_numpy(dtype=float)
        cycle = frame['Cycle_Index'].to_numpy()

        discharge_votes = {}
        cc_votes = {}
        cv_votes = {}
        for cyc in pd.unique(cycle):
            mask = cycle == cyc
            group_step, group_current = step[mask], current[mask]
            group_voltage = voltage[mask]
            if len(group_step) == 0:
                continue
            max_voltage = float(np.nanmax(group_voltage))
            for value in pd.unique(group_step):
                cell = group_step == value
                cell_current, cell_voltage = group_current[cell], group_voltage[cell]
                if len(cell_current) == 0:
                    continue
                if np.all(cell_current < 0):
                    discharge_votes[value] = discharge_votes.get(value, 0) + 1
                    continue
                if not np.all(cell_current > 0):
                    continue
                # 恒压段：电压基本不变且贴住本循环最高电压；恒流段：电压仍在上升
                span = (float(np.nanmax(cell_voltage)) -
                        float(np.nanmin(cell_voltage))) if len(cell_voltage) else 0.0
                near_max = float(np.nanmax(cell_voltage)) >= max_voltage - 0.02
                if near_max and span <= 0.05:
                    cv_votes[value] = cv_votes.get(value, 0) + 1
                elif span > 0.05:
                    cc_votes[value] = cc_votes.get(value, 0) + 1

        def best(votes):
            if not votes:
                return None
            return int(max(votes.items(), key=lambda item: (item[1], -item[0]))[0])

        cc_step, cv_step = best(cc_votes), best(cv_votes)
        discharge_step = best(discharge_votes)
        if cc_step is None and cv_step is None and discharge_step is None:
            result['summary'] = '无法识别'
            return result

        cycle_count = max(len(pd.unique(cycle)), 1)
        hits = (cc_votes.get(cc_step, 0) + cv_votes.get(cv_step, 0) +
                discharge_votes.get(discharge_step, 0))
        detected = sum(1 for value in (cc_step, cv_step, discharge_step)
                       if value is not None)
        coverage = min(hits / (3.0 * cycle_count), 1.0)
        confidence = float(min(1.0, 0.5 * detected / 3.0 + 0.5 * coverage))
        result.update({
            'cc_step': cc_step,
            'cv_step': cv_step,
            'discharge_step': discharge_step,
            'confidence': confidence,
            'summary': (
                f'恒流 {cc_step}，恒压 {cv_step}，放电 {discharge_step}'
                f'（置信度 {confidence:.2f}）'),
        })
        return result
    except Exception as e:  # 防御：自动识别失败不应影响主流程
        result['summary'] = f'识别失败：{e}'
        return result


ADAPTERS = {
    'CALCE': CALCEAdapter,
    'NASA': NASAAdapter,
}


def get_adapter(adapter_type='CALCE'):
    """根据名称获取适配器实例。

    未知名称直接抛 ValueError 并列出支持的名字，避免静默回退到 CALCE
    导致后续出现难以定位的结构性错误。
    """
    key = adapter_type if adapter_type is not None else 'CALCE'
    if not isinstance(key, str):
        raise ValueError(
            f'数据适配器类型必须是字符串，收到 {type(adapter_type).__name__}；'
            f'支持的类型：{", ".join(ADAPTERS)}')
    normalized = key.strip().upper()
    if normalized not in ADAPTERS:
        raise ValueError(
            f'不支持的数据适配器：{adapter_type}；'
            f'支持的类型：{", ".join(ADAPTERS)}')
    return ADAPTERS[normalized]()


def get_adapter_list():
    """返回所有适配器的 (name, display_name) 列表，用于 UI 下拉框"""
    return [(cls.name(), cls.display_name()) for cls in ADAPTERS.values()]
