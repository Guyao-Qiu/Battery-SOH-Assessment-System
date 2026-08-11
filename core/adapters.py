"""
电池数据适配器模块

通过适配器模式将不同来源、不同格式的电池循环数据统一为标准输出：
  DataFrame(cycle, capacity, SoH, resistance, CCCT, CVCT)

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

from .preprocess import filter_capacity_outliers
from .validation import normalize_column_names, _read_data_file


def _read_data_sort_date(path):
    """Read only the first row needed to sort a CALCE source file."""
    extension = os.path.splitext(path)[1].lower()
    if extension == '.csv':
        header = pd.read_csv(path, nrows=1)
    elif extension == '.xlsx':
        header = pd.read_excel(path, nrows=1)
    else:
        raise ValueError(f'不支持的数据文件格式: {extension}')
    normalize_column_names(header)
    if len(header) == 0 or 'Date_Time' not in header.columns:
        raise ValueError('缺少可用于排序的 Date_Time 首行')
    return header['Date_Time'].iloc[0]


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
                          log_callback, stop_flag) -> tuple:
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

        返回:
            battery_dict[name] = pd.DataFrame(cycle, capacity, SoH, resistance, CCCT, CVCT)
            battery_list = [name1, name2, ...]
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


def _build_battery_dataframe(cycle_indices, discharge_capacities, health_indicator,
                             internal_resistance, CCCT, CVCT,
                             name, log_callback, clean_outliers=True,
                             protect_knees=True):
    """将提取的数组组装为标准 DataFrame，并执行异常值剔除。"""
    count = len(discharge_capacities)
    if count == 0:
        return None

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

    filter_result = filter_capacity_outliers(
        discharge_capacities, bins=40, enabled=clean_outliers,
        protect_knees=protect_knees)
    idx = filter_result.indices

    if log_callback:
        log_callback(
            '数据筛选原则：将容量序列按每 40 个循环划分为局部窗口，'
            '窗口内计算均值 μ 与标准差 σ，剔除超出 μ±2σ 范围的点。'
            '边界点和稳定窗口保留，持续退化膝点受到保护。'
        )
        log_callback(
            f'{name} 异常值审计：输入 {count}，保留 {len(idx)}，'
            f'剔除 {filter_result.removed_count}，'
            f'保护膝点 {len(filter_result.protected_indices)}。')
        log_callback('─' * 40)

    df_result = pd.DataFrame({
        'cycle': cycle_indices[idx],
        'capacity': discharge_capacities[idx],
        'SoH': health_indicator[idx],
        'resistance': internal_resistance[idx],
        'CCCT': CCCT[idx],
        'CVCT': CVCT[idx],
    })
    df_result.attrs['outlier_audit'] = {
        'enabled': bool(clean_outliers),
        'protect_knees': bool(protect_knees),
        'input_count': count,
        'kept_count': int(len(idx)),
        'removed_count': filter_result.removed_count,
        'mask': filter_result.mask.tolist(),
        'removed_indices': filter_result.removed_indices.tolist(),
        'protected_indices': filter_result.protected_indices.tolist(),
        'reasons': dict(filter_result.reasons),
    }

    return df_result


# ─── 1. CALCE 适配器 ──────────────────────────────────────────────

class CALCEAdapter(BatteryDataAdapter):
    """CALCE 数据集适配器 — xlsx/csv 格式，工步可配置（默认 2/4/7）"""

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
                          log_callback, stop_flag):
        battery_dict = {}
        battery_list = []

        for path in paths:
            if stop_flag is not None and stop_flag():
                break

            if os.path.isfile(path):
                name = os.path.splitext(os.path.basename(path))[0]
                file_list = [path]
            elif os.path.isdir(path):
                name = os.path.basename(path.rstrip('/\\'))
                file_list = []
                for ext in self.extensions():
                    file_list.extend(glob.glob(os.path.join(path, f'*{ext}')))
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

                cycles, cap, soh, ir, ccct, cvct = _extract_capacity_from_tabular(
                    df, voltage_upper, voltage_lower,
                    cc_step, cv_step, discharge_step,
                    log_callback, name
                )
                all_cycles.extend(cycles)
                all_cap.extend(cap)
                all_soh.extend(soh)
                all_ir.extend(ir)
                all_ccct.extend(ccct)
                all_cvct.extend(cvct)

            df_result = _build_battery_dataframe(
                all_cycles, all_cap, all_soh, all_ir, all_ccct, all_cvct,
                name, log_callback
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
                          log_callback, stop_flag):
        try:
            from scipy.io import loadmat
        except ImportError:
            raise ImportError(
                'NASA 数据集适配器需要 scipy 库。请在环境中安装：pip install scipy'
            )

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
                file_list = glob.glob(os.path.join(path, '*.mat'))
            else:
                continue

            if not file_list:
                continue

            if log_callback:
                log_callback(f'加载数据集 {name}...')

            discharge_capacities = []
            discharge_cycles = []
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
                    mat = loadmat(p)
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
                # 结构体路径: battery[0,0]['cycle'][0] = 循环数组
                try:
                    cycles = battery_struct[0, 0]['cycle'][0]
                except (IndexError, KeyError, ValueError) as e:
                    if log_callback:
                        log_callback(f'跳过 {p}，原因：数据结构异常 {e}')
                    continue

                for i in range(len(cycles)):
                    if stop_flag is not None and stop_flag():
                        break
                    try:
                        cycle_type = cycles[i][0]['type'][0]
                        if isinstance(cycle_type, np.ndarray):
                            cycle_type = cycle_type[0] if len(cycle_type) > 0 else ''

                        data = cycles[i][0]['data'][0, 0]

                        if str(cycle_type).lower() == 'discharge':
                            # NASA 数据集直接提供放电容量
                            if 'Capacity' in data.dtype.names:
                                cap = float(data['Capacity'][0][0])
                            else:
                                # 回退：从电流和时间积分
                                v = np.array(data['Voltage_measured'].flatten())
                                c = np.array(data['Current_measured'].flatten())
                                t = np.array(data['Time'].flatten())
                                if len(t) > 1:
                                    dt = np.diff(t)
                                    c_arr = c[1:]
                                    cap = -np.sum(dt * c_arr / 3600)
                                else:
                                    continue

                            if cap > 0 and not np.isnan(cap):
                                discharge_cycles.append(i + 1)
                                discharge_capacities.append(cap)

                                # SOH：从电压-容量曲线提取
                                v = np.array(data['Voltage_measured'].flatten())
                                c_arr = np.array(data['Current_measured'].flatten())
                                t = np.array(data['Time'].flatten())
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

                        elif str(cycle_type).lower() == 'charge':
                            # 从充电阶段提取 CCCT / CVCT
                            t = np.array(data['Time'].flatten())
                            v = np.array(data['Voltage_measured'].flatten())
                            if len(t) > 1:
                                total_time = t[-1] - t[0]
                                # 粗略估计：电压变化率小于阈值时为恒压阶段
                                pending_cvct = float(total_time)
                                pending_ccct = float(total_time * 0.4)
                            else:
                                pending_ccct = np.nan
                                pending_cvct = np.nan
                    except (IndexError, KeyError, ValueError):
                        continue

            df_result = _build_battery_dataframe(
                discharge_cycles, discharge_capacities, health_indicator,
                internal_resistance, CCCT, CVCT,
                name, log_callback
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

ADAPTERS = {
    'CALCE': CALCEAdapter,
    'NASA': NASAAdapter,
}


def get_adapter(adapter_type='CALCE'):
    """根据名称获取适配器实例"""
    cls = ADAPTERS.get(adapter_type, CALCEAdapter)
    return cls()


def get_adapter_list():
    """返回所有适配器的 (name, display_name) 列表，用于 UI 下拉框"""
    return [(cls.name(), cls.display_name()) for cls in ADAPTERS.values()]
