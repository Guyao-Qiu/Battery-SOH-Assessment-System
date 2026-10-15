"""结果表的数据模型（U1）。

旧实现的「结果表」其实是 N 张卡片竖排：不能排序、不好对比、5 段指标代码
复制粘贴、数值用 ``.6f`` 打印、颜色内联写死。这里换成
``QTableView + QAbstractTableModel + QSortFilterProxyModel``：

- 点列头排序（用 ``UserRole`` 里的**原始值**排序，而不是格式化后的字符串）；
- 列包含滚动起点的 RMSE / MAE / 技能分 / 预测 RUL / 真实 RUL / RUL 误差；
- 末尾一行**汇总**：跨电池 mean ± std（n = 电池数）+ bootstrap 区间；
- 技能分 < 0.05 的单元格用 warning 色并加 ⚠（A3）；
- 数值保留 4 位小数并带单位。
"""

import numpy as np
from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PyQt6.QtGui import QBrush, QColor, QFont


#: (表头, 键, 数值格式)；``key`` 为 None 表示该列由 getter 计算
#:
#: 表头刻意用短名：结果面板只有约 300–400 px 宽，长表头会把数值挤出可视区。
#: 完整含义写在列的工具提示里（见 :meth:`ResultTableModel.headerData`）。
COLUMNS = (
    ('电池', 'name', '{}'),
    ('RMSE', 'rmse', '{:.4f}'),
    ('MAE', 'mae', '{:.4f}'),
    ('技能分', 'skill', '{:+.3f}'),
    ('预测RUL', 'pred_rul', '{}'),
    ('真实RUL', 'true_rul', '{}'),
    ('RUL误差', 'rul_err', '{:+d}'),
    ('状态', 'status', '{}'),
)

#: 每列的完整说明（工具提示）
COLUMN_HELP = {
    'name': '电池名称',
    'rmse': '滚动预测起点上的递归预测 RMSE（Ah）',
    'mae': '滚动预测起点上的递归预测 MAE（Ah）',
    'skill': '技能分 = 1 − RMSE模型 / RMSE平推；< 0.05 表示未超越平推基线',
    'pred_rul': '模型预测的剩余寿命（循环数）',
    'true_rul': '真实剩余寿命（循环数）',
    'rul_err': 'RUL 误差 = 预测 − 真实；正值表示预测偏保守',
    'status': '失效检出状态：EOL 是否落在预测期内',
}

#: 各列宽度（px）。结果面板默认约 480–560 px，用 `ResizeToContents` 会被
#: 汇总行的长文本撑到 1200 px 以上，因此这里显式给宽度，超出部分省略号 + 提示。
COLUMN_WIDTHS = {
    'name': 86, 'rmse': 62, 'mae': 62, 'skill': 66,
    'pred_rul': 62, 'true_rul': 62, 'rul_err': 66, 'status': 74,
}

#: 技能分低于此值时提示「模型未超越持久性基线」（A3）
SKILL_WARNING_THRESHOLD = 0.05

#: 状态列的短标签（含图标，满足「状态不能只靠颜色」的要求）；
#: 完整含义见 :data:`STATUS_HELP`，通过单元格工具提示给出。
STATUS_LABELS = {
    'ok': '✓ 检出',
    'pred_censored': '⚠ 未检出',
    'true_censored': '✓ 未失效',
    'unavailable': '— 不可用',
    'mixed': '— 种子不一致',
}

#: 状态列的完整解释（工具提示 / 无障碍文本）
STATUS_HELP = {
    'ok': '预测期内已检出失效，RUL 误差可计算',
    'pred_censored': '模型预测观测期内不会失效，但真实电池已失效',
    'true_censored': '真实电池在观测期内未失效（右删失）',
    'unavailable': '该指标当前不可用',
    'mixed': '多种子之间状态不一致',
}


def format_optional(value, fmt):
    """按格式渲染；None / 非有限值显示为 ``—``。"""
    if value is None:
        return '—'
    if isinstance(value, float) and not np.isfinite(value):
        return '—'
    try:
        return fmt.format(value)
    except (ValueError, TypeError):
        return str(value)


def rows_from_details(detail_list, start_frac=None, baselines=None):
    """把 ``detail`` 列表转成结果表行。

    ``start_frac`` 指定看哪个滚动起点（默认用每块电池的主起点）。
    ``baselines`` 是 ``{基线名: {'rmse': ...}}``，会作为额外的行插在后面。
    """
    rows = []
    for detail in detail_list or []:
        row = _row_from_detail(detail, start_frac)
        if row is not None:
            rows.append(row)
    for name, entry in (baselines or {}).items():
        rows.append({
            'name': name,
            'is_baseline': True,
            'rmse': entry.get('rmse'),
            'mae': entry.get('mae'),
            'skill': None,
            'pred_rul': None,
            'true_rul': None,
            'rul_err': None,
            'status': 'baseline',
            'status_label': f'基线 · {name}',
        })
    return rows


def _row_from_detail(detail, start_frac):
    if not isinstance(detail, dict):
        return None
    battery = detail.get('battery', '?')
    row = {
        'name': battery,
        'rmse': detail.get('rmse'),
        'mae': detail.get('mae'),
        'skill': detail.get('rmse_skill_vs_persistence'),
        'pred_rul': None,
        'true_rul': None,
        'rul_err': None,
        'status': detail.get('re_status', 'unavailable'),
    }

    # 优先用滚动起点里对应那一行
    target = start_frac if start_frac is not None else detail.get(
        'primary_start_frac', 0.5)
    rolling = detail.get('rolling') or {}
    per_start = rolling.get('per_start') or {}
    entry = None
    if per_start:
        if target is not None:
            for frac, value in per_start.items():
                if abs(float(frac) - float(target)) < 1e-9:
                    entry = value
                    break
        if entry is None:
            entry = next(iter(per_start.values()))
    if entry:
        row['rmse'] = entry.get('rmse', row['rmse'])
        row['mae'] = entry.get('mae', row['mae'])
        if entry.get('skill') is not None:
            row['skill'] = entry['skill']
        row['mean_abs_rul_err'] = entry.get('mean_abs_rul_err')
        row['detected'] = entry.get('detected')
        row['needs_detection'] = entry.get('needs_detection')
        if entry.get('detected'):
            row['status'] = 'ok'
        elif entry.get('needs_detection'):
            row['status'] = 'pred_censored'
        else:
            row['status'] = 'true_censored'

    # RUL 明细：优先取该起点的原始行
    rows = detail.get('rolling_rows') or []
    picked = None
    for item in rows:
        if target is not None and abs(
                float(item.get('start_frac', -1)) - float(target)) < 1e-9:
            picked = item
            break
    if picked is None and rows:
        picked = rows[0]
    if picked:
        row['true_rul'] = picked.get('true_rul')
        row['pred_rul'] = (
            None if picked.get('pred_rul') is None
            else int(round(picked['pred_rul'])))
        row['rul_err'] = (
            None if picked.get('rul_err') is None
            else int(round(picked['rul_err'])))
        if picked.get('status'):
            row['status'] = picked['status']
    if row.get('rul_err') is None:
        row['rul_err'] = detail.get('rul_err')

    row['status_label'] = STATUS_LABELS.get(
        row['status'], row.get('status') or '—')
    row['alpha'] = detail.get('persistence_blend')
    row['n_seeds'] = detail.get('n_seeds')
    row['cycles'] = detail.get('cycles')
    return row


def summary_row(rows):
    """跨电池汇总：mean ± std（n = 电池数）。基线行不参与。"""
    values = [row for row in rows if not row.get('is_baseline')]
    if not values:
        return None

    def stats(key):
        items = [
            float(row[key]) for row in values
            if row.get(key) is not None
            and isinstance(row[key], (int, float))
            and np.isfinite(row[key])
        ]
        if not items:
            return None, None
        return float(np.mean(items)), (
            float(np.std(items, ddof=1)) if len(items) > 1 else 0.0)

    rmse_mean, rmse_std = stats('rmse')
    mae_mean, mae_std = stats('mae')
    skill_mean, skill_std = stats('skill')
    rul_mean, rul_std = stats('rul_err')
    detected = sum(1 for row in values if row.get('status') == 'ok')
    needs = sum(1 for row in values
                if row.get('status') in ('ok', 'pred_censored'))
    return {
        # 「电池」列只有 86px，长标签会被省略号截断；完整说明放在工具提示里
        'name': f'汇总 n={len(values)}',
        'n_batteries': len(values),
        'is_summary': True,
        'rmse': rmse_mean,
        'rmse_std': rmse_std,
        'mae': mae_mean,
        'mae_std': mae_std,
        'skill': skill_mean,
        'skill_std': skill_std,
        'pred_rul': None,
        'true_rul': None,
        'rul_err': rul_mean,
        'rul_err_std': rul_std,
        'status': 'summary',
        'status_label': f'检出 {detected}/{needs}' if needs else '—',
    }


def bootstrap_summary(rows, key='rmse', n_boot=2000, level=0.95, seed=0):
    """对「每块电池一个数」的指标做 bootstrap（A9）。"""
    from core.evaluate import bootstrap_ci

    values = [
        row.get(key) for row in rows
        if not row.get('is_baseline') and not row.get('is_summary')
    ]
    return bootstrap_ci(values, n_boot=n_boot, level=level, seed=seed)


class ResultTableModel(QAbstractTableModel):
    """结果表模型；数值排序走 ``UserRole`` 里的原始值。"""

    def __init__(self, rows=None, tokens=None, parent=None):
        super().__init__(parent)
        self._rows = list(rows or [])
        self._tokens = tokens or {}
        self._show_summary = True

    # ── Qt 接口 ──────────────────────────────────────────────
    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return len(self._display_rows())

    def columnCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return len(COLUMNS)

    def headerData(self, section, orientation,
                   role=Qt.ItemDataRole.DisplayRole):
        if not (0 <= section < len(COLUMNS)):
            return None
        header, key, _ = COLUMNS[section]
        if orientation == Qt.Orientation.Horizontal:
            if role == Qt.ItemDataRole.DisplayRole:
                return header
            if role == Qt.ItemDataRole.ToolTipRole:
                return COLUMN_HELP.get(key, header)
        return None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        rows = self._display_rows()
        if not (0 <= index.row() < len(rows)):
            return None
        row = rows[index.row()]
        _, key, fmt = COLUMNS[index.column()]
        value = self._cell_value(row, key)

        if role == Qt.ItemDataRole.DisplayRole:
            return self._display_text(row, key, value, fmt)
        if role == Qt.ItemDataRole.UserRole:
            # 排序用的原始值；缺失值排到最后
            if value is None or (isinstance(value, float)
                                 and not np.isfinite(value)):
                return float('-inf')
            return value
        if role == Qt.ItemDataRole.TextAlignmentRole:
            if index.column() == 0:
                return int(Qt.AlignmentFlag.AlignLeft
                           | Qt.AlignmentFlag.AlignVCenter)
            return int(Qt.AlignmentFlag.AlignRight
                       | Qt.AlignmentFlag.AlignVCenter)
        if role == Qt.ItemDataRole.ForegroundRole:
            return self._foreground(row, key, value)
        if role == Qt.ItemDataRole.FontRole:
            if row.get('is_summary') or row.get('is_baseline'):
                font = QFont()
                font.setBold(True)
                return font
            return None
        if role == Qt.ItemDataRole.ToolTipRole:
            return self._tooltip(row)
        return None

    # ── 数据管理 ────────────────────────────────────────────
    def set_rows(self, rows):
        self.beginResetModel()
        self._rows = list(rows or [])
        self.endResetModel()

    def set_tokens(self, tokens):
        self._tokens = tokens or {}
        if self._rows:
            top = self.index(0, 0)
            bottom = self.index(len(self._display_rows()) - 1,
                                len(COLUMNS) - 1)
            self.dataChanged.emit(top, bottom)

    def set_show_summary(self, show):
        self.beginResetModel()
        self._show_summary = bool(show)
        self.endResetModel()

    def rows(self):
        return list(self._rows)

    def display_rows(self):
        return self._display_rows()

    # ── 内部 ────────────────────────────────────────────────
    def _display_rows(self):
        rows = list(self._rows)
        if self._show_summary and rows:
            summary = summary_row(rows)
            if summary is not None:
                rows.append(summary)
        return rows

    @staticmethod
    def _cell_value(row, key):
        if row.get('is_summary'):
            if key == 'name':
                return row.get('name')
            if key in ('rmse', 'mae', 'skill'):
                # 均值用作排序键；±std 由 _display_text 单独渲染
                return row.get(key)
            if key == 'rul_err':
                return row.get('rul_err')
            if key == 'status':
                return row.get('status_label')
            return None
        if key == 'status':
            return row.get('status_label')
        return row.get(key)

    def _display_text(self, row, key, value, fmt):
        if row.get('is_summary'):
            if key in ('rmse', 'mae', 'skill'):
                # 单元格只放均值，保证在窄面板里不被省略号截断；
                # 「mean ± std」写在工具提示与结果区下方的说明行里。
                return '—' if row.get(key) is None else fmt.format(row[key])
            if key == 'rul_err':
                mean = row.get('rul_err')
                return '—' if mean is None else f'{mean:+.1f}'
        if key == 'skill' and isinstance(value, (int, float)) \
                and np.isfinite(value) and value < SKILL_WARNING_THRESHOLD:
            return f'⚠ {value:+.3f}'
        return format_optional(value, fmt)

    def _foreground(self, row, key, value):
        tokens = self._tokens
        if row.get('is_summary'):
            color = tokens.get('primary_d') or tokens.get('primary')
            return QBrush(QColor(color)) if color else None
        if row.get('is_baseline'):
            color = tokens.get('text_muted')
            return QBrush(QColor(color)) if color else None
        if key == 'skill' and isinstance(value, (int, float)) \
                and np.isfinite(value) and value < SKILL_WARNING_THRESHOLD:
            color = tokens.get('warning')
            return QBrush(QColor(color)) if color else None
        if key == 'status':
            state = row.get('status')
            color = {
                'ok': tokens.get('success_d'),
                'true_censored': tokens.get('success_d'),
                'pred_censored': tokens.get('warning'),
                'unavailable': tokens.get('text_muted'),
            }.get(state)
            return QBrush(QColor(color)) if color else None
        return None

    @staticmethod
    def _tooltip(row):
        parts = []
        if row.get('is_summary'):
            parts.append(
                f'跨电池汇总，n={row.get("n_batteries")} 块电池。'
                'n = 电池数才是泛化不确定性的来源。')
            for key, label in (('rmse', 'RMSE'), ('mae', 'MAE'),
                               ('skill', '技能分')):
                mean, std = row.get(key), row.get(f'{key}_std')
                if mean is None:
                    continue
                if std is None:
                    parts.append(f'{label} 均值 = {mean:.4f}')
                else:
                    parts.append(f'{label} = {mean:.4f} ± {std:.4f}')
            if row.get('rul_err') is not None:
                std = row.get('rul_err_std')
                parts.append(
                    f'RUL 误差均值 = {row["rul_err"]:+.1f}'
                    + (f' ± {std:.1f}' if std is not None else ''))
        elif row.get('is_baseline'):
            parts.append('经验基线：任何模型都必须先赢过它。')
        else:
            alpha = row.get('alpha')
            if alpha is not None:
                parts.append(f'持久性混合系数 α={alpha:.3f}')
                if alpha < SKILL_WARNING_THRESHOLD:
                    parts.append('⚠ 模型未超越持久性基线（α≈0）')
            if row.get('detected') is not None:
                parts.append(
                    f'EOL 检出 {row.get("detected")}/'
                    f'{row.get("needs_detection")}')
            if row.get('n_seeds'):
                parts.append(f'{row["n_seeds"]} 个种子')
            help_text = STATUS_HELP.get(row.get('status'))
            if help_text:
                parts.append(help_text)
        return '\n'.join(parts) if parts else None


def to_csv(rows):
    """把结果行导出成 CSV 文本（Excel 可直接打开）。"""
    import csv
    import io

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([header for header, _, _ in COLUMNS])
    for row in rows:
        line = []
        for _, key, fmt in COLUMNS:
            value = ResultTableModel._cell_value(row, key)
            line.append(format_optional(value, fmt))
        writer.writerow(line)
    return buffer.getvalue()
