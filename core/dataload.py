import os
import glob
import numpy as np
import pandas as pd
from .preprocess import drop_outlier
from .validation import normalize_column_names, _read_data_file
from .adapters import get_adapter


def load_battery_from_paths(imported_paths, log_callback=None, stop_flag=None,
                           voltage_upper=3.8, voltage_lower=3.4,
                           adapter_type='CALCE',
                           cc_step=2, cv_step=4, discharge_step=7):
    """加载电池数据，自动选择适配器处理不同格式。

    参数:
        imported_paths : 导入路径列表（文件或文件夹）
        log_callback   : 日志回调函数
        stop_flag      : 停止标志函数
        voltage_upper  : SOH 上电压 (V)
        voltage_lower  : SOH 下电压 (V)
        adapter_type   : 适配器类型（'CALCE' / 'NASA'）
        cc_step        : 恒流充电工步序号
        cv_step        : 恒压充电工步序号
        discharge_step : 放电工步序号

    返回:
        (battery_dict, battery_list)
    """
    adapter = get_adapter(adapter_type)
    return adapter.load_battery_data(
        imported_paths, voltage_upper, voltage_lower,
        cc_step, cv_step, discharge_step,
        log_callback, stop_flag
    )
