# Battery SOH Assessment System 项目记忆

> 用途：每次重新进入仓库时，先读本文，再读 `AGENTS.md` 和 `README.md`，即可快速恢复项目上下文。
>
> 快照日期：2026-10-14（Asia/Shanghai）  
> 项目路径：`E:\Google Chrome\Battery-SOH-Assessment-System-main`  
> 项目类型：PyQt6 桌面端 + 离线电池容量退化建模/评估工具

## 先看结论

- 项目名称：Battery SOH Assessment System（电池 SOH 评估系统）。
- 核心任务：从 CALCE/NASA 电池循环数据提取容量序列，使用 5 种模型预测下一循环容量，并以递归预测估算 RUL/失效循环。
- 产品边界：面向教学、科研和离线算法验证的 **Research Preview**，不是量产 BMS、功能安全、质保/报废判定或安全保护系统。
- 当前主协议：**评估与部署共用同一流程**。外层留一电池（LOBO）保证目标电池全程隔离；内层留一电池交叉验证选超参；定型用全部训练电池的**全部窗口**重训（`core/protocol.py::fit_final`）。
- 头条指标：**滚动预测起点（寿命 40%–70%）上的递归预测**。一步预测已降级为诊断信息。
- 关键口径：SOH = `C / C_rated`；RUL = 从预测起点到 EOL 的循环数；`dq_v` 是健康指标 HI，不是 SOH。
- TCP 默认**只监听 127.0.0.1**；开放局域网需显式勾选并走 token 握手。
- 2026-10-14 完成《改进方案》P0+P1 全量与 P2 主要项；`pytest`/`unittest` 233 项全绿。
- 当前工作区不是干净状态：`main` 分支、HEAD 为 `589c7ac`，有大量未提交改动（含本次改进）。不要 reset、覆盖或自动提交。

## 30 秒恢复流程

1. 确认当前目录为项目根目录，先查看 `git status --short --branch`。
2. 阅读 `AGENTS.md`：只有用户明确说“确认”“定稿”或“提交”时才创建提交；只 stage 本次确认的文件。
3. 优先使用 `D:\Anaconda3\envs\pytorch\python.exe`（Python 3.10.20）和 `pwsh -NoProfile`。
4. 运行可靠的基础回归：

   ```powershell
   $env:PYTHONUTF8 = '1'
   $env:QT_QPA_PLATFORM = 'offscreen'
   D:\Anaconda3\envs\pytorch\python.exe -X utf8 -m unittest discover -s tests
   D:\Anaconda3\envs\pytorch\python.exe -X utf8 tools/check_undefined.py core models ui utils theme_tokens.py battery_soh_app.py
   D:\Anaconda3\envs\pytorch\python.exe -X utf8 tools/check_colors.py
   D:\Anaconda3\envs\pytorch\python.exe -X utf8 -m compileall -q battery_soh_app.py theme_tokens.py core models ui utils
   ```

5. 开始任何行为、评估协议、数据处理或 TCP 访问方式的修改前，先检查当前 diff，并说明影响和验证方法。

## 2026-10-14 改进方案落地记录

按《Battery-SOH-Assessment-System 改进方案》在**多文件工程**中落地（不要直接改 `battery_soh_all_in_one.py`，它由 `scripts/build_all_in_one.py` 生成）。

### 新增模块

| 文件 | 作用 | 对应条目 |
| --- | --- | --- |
| `theme_tokens.py`（根目录） | 唯一的颜色真相来源（浅色宣纸 / 深色墨夜）+ WCAG 对比度函数 | C1/C3/C5/U7 |
| `core/protocol.py` | 统一协议：选超参 → 全量重训 → 滚动起点评估 | A2/A3/A4 |
| `core/baselines.py` | 经验基线（平推 / 线性外推 / 双指数） | A9 |
| `core/model_factory.py` | 模型构造与拟合的**唯一入口**（评估/部署共用） | A2/A5/A7/A8 |
| `core/stream_protocol.py` | TCP 的纯 Python 部分（解析 / 限流 / RUL），不依赖 Qt | A1/A10 |
| `utils/crash_guard.py` | 全局异常兜底（闪退 → 日志 + 非阻塞提示） | A1 |
| `ui/result_model.py` | 可排序结果表 + 跨电池汇总 + CSV 导出 | U1 |
| `tools/check_undefined.py` | 找“用了但从未定义”的全局名字（CI 门禁） | A1/E2 |
| `tools/check_colors.py` | 禁止 `theme_tokens.py` 之外出现硬编码颜色（CI 门禁） | C1/E2 |
| `tools/repro_synthetic.py` | 复现 §4 的四方对比 | §4 |
| `tools/send_demo.py` | TCP 演示客户端（含畸形输入） | A1 |
| `tests/test_core.py` | 最小回归测试集（30 项） | E1 |
| `tests/test_tcp_stream.py` | TCP 端到端测试（真实 socket + 线程，含「预测不阻塞接收」回归） | A1/A10 |

### 关键行为变化

- **A2**：`core/preprocess.py::prepare_leave_one_out_split` 仍保留（向后兼容、测试在用），但评估与部署都改走 `core/protocol.py` 的「内层 CV 选超参 → 全量窗口重训」。`core/model_persistence.py::train_model_on_all_data` 调用同一个 `fit_final`，不再自带 RNN/RF/XGB 训练循环。
- **A3**：`fit_persistence_blend`（一步标定）保留但评估不再使用；α 改由 `choose_blend_by_rollout` 用**多步滚动误差**标定，且只用内层折模型。合成数据上 α 从 0.000 变为 0.72–0.80。
- **A4**：`detail['rolling']` / `detail['rolling_rows']` 是头条指标；`detail['rul_protocol']` 由 `'recursive_future'` 变为 `'rolling_origin'`。
- **A5**：`TrainConfig.feature_columns`（默认 `('capacity',)`）。适配器列 `'SoH'` → `'dq_v'`（`'SoH'` 作为别名保留）。
- **A6**：NASA 适配器用 `split_cc_cv` 真实切分 CC/CV（不再 `总时长×0.4`）；`cycle` 改为有效放电序号，原始下标存 `raw_index`；`get_adapter` 未知类型抛 `ValueError`；新增 `extract_cycles_fast` / `detect_step_indices`。
- **A7**：`train_rf` 固定树数一次训练（早停与二次重训已删除）；`n_jobs=1`（递归预测单行 predict 快 10 倍）。
- **A8**：RNN 训练集 `shuffle=True`、`AdamW(weight_decay=1e-4)`、梯度裁剪 1.0、`ReduceLROnPlateau`；`Net` 支持 `input_size=F`。
- **A9**：`bootstrap_ci`（跨电池）+ 三条基线并排 + α<0.05 的 ⚠ 提示。
- **A10**：`TCPServerWorker` 默认绑 `127.0.0.1`；`allow_lan=True` 才监听 `0.0.0.0` 并自动生成 token；畸形输入只警告不崩溃；`deque(maxlen=5000)`；限流 + **独立预测线程**（`stream_protocol.LatestOnlyQueue` 只保留最新快照，最坏 1500 步预测不阻塞接收，实测 reset 延迟 ≈0 ms）；`forecast_eol` 越阈即停；RUL 改为真正的剩余寿命。
- **A11**：配置只存规范键（`'cuda'` / `'rated'` / `'mae'`）；`normalize_device` 兼容旧的界面文本。**导入自己保存的配置不再把 GPU 静默切回 CPU。**
- **U1**：结果区从卡片堆改为 `QTableView` + `QAbstractTableModel` + `QSortFilterProxyModel`。
- **U2**：主图含预测起点、递归预测、10–90% 区间、失效阈值、真实/预测 EOL、SOH% 副轴，y 轴自动聚焦退化区间，x 轴用真实循环号。
- **C1–C6**：颜色收敛到 `theme_tokens.py`；`check_colors.py` 退出码 0；浅/深主题可切换（含启动闪屏与图表）。
- **U4**：窗口几何用 `QSettings` 记忆，无记录时按可用屏幕自适应。
- **U7**：闪屏百分比移到条外；颜色走 token；重库逐个预导入并更新状态；主窗口构造纳入 `try` 保护。

### P2 已落地项（A12 / E2）

- **A12.1 离群点默认只标记不删除**：`filter_capacity_outliers(..., mode='mark'|'delete'|'off')`，`OutlierFilterResult` 新增 `marked_indices` / `marked_count` / `mode`。`_build_battery_dataframe` 默认 `outlier_mode='mark'`（数据一行不删），旧的 `clean_outliers=True/False` 仍分别映射到 `delete`/`off`。容量再生是真实物理，不该被窗口均值判成噪声。
- **A12.2 失效判定合并为一处**：`core.result_semantics.first_failure_index` 是唯一实现，`core/protocol.first_cross` 只是委托。
- **A12.3 失效判定去抖**：`first_failure_index(..., debounce=N)`，要求连续 N 个循环低于阈值；默认 `N=1`＝旧语义（向后兼容），`config.eol_debounce` 可配（别名 `failure_debounce` / `debounce`）。返回值是首次下穿处，不会偏晚。
- **A12.4 可复现性**：`setup_seed(seed, deterministic=None)` 现在**如实返回**是否达成严格确定性；`PYTHONHASHSEED` 的进程内赋值无效这件事写进了 docstring（需在启动前用环境变量设置）；`SOH_DETERMINISTIC=1` 可开启 `torch.use_deterministic_algorithms` + `CUBLAS_WORKSPACE_CONFIG`。
- **A12.5 窗口向量化**：`build_instances_fast`（`sliding_window_view`）已对拍并与参考实现逐位相等。
- **E2 质量门禁**：`.github/workflows/quality.yml` 增加 `tools/check_undefined.py` 与 `tools/check_colors.py` 两步；`pyproject.toml` 的 ruff 开启 `F821` 且**取消所有 per-file 豁免**（旧配置为 `ui/tcp_server.py` 豁免 F821，正是它掩盖了 A1）。
- **README 截图**：`assets/screenshots/main-dark.png` / `main-light.png`，由 `tools/render_screenshots.py` 生成（优先用原生窗口平台，无显示环境才退回 offscreen）。

### 界面三处调整（U8 / U9 / 字体，2026-10-15）

用户反馈「截图乱码 / 刻度太稀 / 要右上角主题按钮」，对应改动：

- **中文字体引导 `ui/fonts.py`（新增）**：PyQt6 的 **offscreen / minimal 平台插件不使用系统字体引擎**，只认 `PyQt6/Qt6/lib/fonts`；该目录在 pip/conda 安装里通常不存在，于是 `QFontDatabase.families()` 返回**空列表**，所有 Qt 文字渲染成方框（matplotlib 不受影响，它自己解析 `CJK_FONTS`）。
  实测本环境：`platform=windows` → 570 个字体族、中文正常；`platform=offscreen` → **0 个字体族**、满屏方框。
  `install_fonts(app)` 显式注册 `msyh.ttc / simhei.ttf / simsun.ttc / segoeui.ttf / consola.ttf` 等，并设为应用字体。**必须在创建任何控件之前调用**（`battery_soh_app.py` 在 QApplication 之后立刻调用）。
  - ⚠ **不要在 `MainWindow.__init__` 里调用 `install_fonts` / 任何 `QFontDatabase` 静态方法**：在控件已存在之后再调用它，会让本环境（字体目录缺失）的 PyQt6 在后续绘制时**段错误 0xC0000005**。已实测定位到「`QFontDatabase.families()` 单独一行就能触发」，并加了回归测试锁死这条约束。
- **刻度密度（U9）**：`ui/chart_show.py` 新增 `nice_step`（1/2/2.5/5 × 10ⁿ）、`_ticks_in_range`、`_minor_ticks`、`_apply_ticks`、`_format_tick`、`_tick_decimals`。主刻度铺满可见区间 + 每两条之间 4 条次刻度；周期轴为整数，容量轴按步长保留必要小数位。
  - ⚠ **刻度必须用显式数组下发**（`axis.set_ticks(...)`），**不要用 `MultipleLocator` / `AutoMinorLocator`**：它们是有状态的 locator，每次绘制都会重新查询轴对象，与本环境组合会触发原生访问违例（单独开任一个都正常，`x major + y major` 一起就必崩）。这个坑同样用回归测试锁住了。
  - 另一个坑：格式化 lambda 必须用默认参数捕获当时的 `step`；两个轴共用同名局部变量时，闭包会让 x 轴读到 y 轴的步长（周期数曾被显示成 `20.00`）。
- **右上角主题按钮（U8）**：`build_top_bar()` 在 `centralWidget` 布局的**第 0 项**插入顶部条（左侧应用名 + 右侧主题按钮），按钮文案同时给出图标与当前主题名（`🌙 墨夜（深色）` / `☀ 宣纸（浅色）`），不只靠颜色。快捷键 `Ctrl+T`。
  - **默认深色**：`theme_tokens.DEFAULT_THEME = 'dark'`。
  - **设置键迁移**：改用 `THEME_SETTINGS_KEY = 'theme_v2'`。旧版本每次启动都把当时的默认值（浅色）写进 `theme`，不换键的话「默认改深色」对老用户不会生效；换键后新默认值能落到每个人身上，此后用户自己的选择照常被记住。

### 已知的有意取舍

- **多特征递归预测**：只有容量通道自回归，其余通道保持窗口末值（未来工况未知）。结果元数据里有 `multifeature_recursive_policy` 标注。
- **`fit_fn` 契约**：`make_fit_fn` 返回的函数接收**原始量纲** X/y，内部负责归一化。调用方**不要**再除 `rated`（曾经因此双重归一化，模型连训练集都拟合不上）。
- **`model_step_for`**：与 `fit_fn` 配对的 step_fn 工厂，单/多特征共用同一套映射，保证训练与推理量纲一致。
- **`n_jobs=1`**：随机森林训练略慢，但递归预测快约 10 倍——评估与实时预测都受益。
- **双指数基线**：外推出现负数或高于历史最大值 1.5 倍时自动回退为线性外推（避免发散）。

### 验证命令与结果（2026-10-14）

```powershell
$env:PYTHONUTF8 = '1'; $env:QT_QPA_PLATFORM = 'offscreen'
python -X utf8 -m unittest discover -s tests            # Ran 234 tests, OK
python -X utf8 tools/check_undefined.py core models ui utils theme_tokens.py battery_soh_app.py  # exit 0
python -X utf8 tools/check_colors.py                    # 没有硬编码颜色, exit 0
python -X utf8 -m ruff check .                          # All checks passed
python -X utf8 -m bandit -r core models ui utils battery_soh_app.py theme_tokens.py --ini .bandit  # 0 issues
python -X utf8 scripts/build_all_in_one.py              # 40 个内嵌模块
python -X utf8 battery_soh_all_in_one.py --check        # 全部通过
python -X utf8 tools/repro_synthetic.py                 # 复现方案 §4.2 表格
```

`tools/repro_synthetic.py` 在合成数据上逐位复现了方案 §4.2：α 全为 0.000（旧流程坍缩），建议流程 RMSE 0.0477–0.0677 Ah、EOL 检出 2/3–3/3。

### 质量门禁（`.github/workflows/quality.yml`）

compileall → ruff（含 F821 未定义名字，已取消所有 per-file 豁免）→ `tools/check_undefined.py` → `tools/check_colors.py` → bandit → pip-audit → unittest → coverage（总 ≥59%，四个核心文件合计 ≥85%）。


## 当前 Git 与工作区状态

### 已确认状态

- 分支：`main`。
- HEAD：`589c7ac`（`chore:checkpoint-current-project-settings`）。
- 当前没有为本次记忆文档创建提交。
- 当前工作树在本次快照时已有以下未提交内容：
  - 已修改：`README.md`、`README_EN.md`、`config.json`、`core/adapters.py`、`core/model_persistence.py`、`core/prediction.py`、`core/preprocess.py`、`core/result_semantics.py`、`core/train.py`、`core/validation.py`、多个测试文件，以及 `ui/chart_show.py`、`ui/main_window.py`、`ui/style.py`、`utils/config.py`。
  - 未跟踪：`dataset/NASA_PCoE/`（NASA MAT 数据及 README）、`.codex_tmp_fund_analysis/`（临时 Fund-Analysis 原型/虚拟环境，不属于本项目交付主线）、`tests/test_overfit_guard.py`、`tests/test_retraining_and_chart_navigation.py`、`tests/test_step_settings_ui.py`、`tests/test_ui_polish_layout.py`。
- 这些改动属于进入本任务前的用户工作。后续应保留、审阅并单独决定是否提交，不能把它们误判为本次工作产生的内容。

### Git 纪律

- 不自动 commit、push、rebase、reset 或丢弃改动。
- 需要提交时，只 stage 当前用户确认的文件，并报告 commit hash。
- `outputs/`、日志、模型文件和 `.meta.json` 被 `.gitignore` 忽略；不要为了“清理”而破坏性删除用户输出。

## 项目定位与证据边界

### 能做什么

- 读取 CALCE `.xlsx/.csv` 和 NASA `.mat` 电池循环数据。
- 通过适配器统一成电池 DataFrame 和容量序列。
- 训练/评估 RNN、GRU、LSTM、XGBoost、Random Forest。
- 计算 RMSE、MAE、R²、Pearson、RE，以及多种子均值/标准差/95% CI。
- 查看容量曲线、阈值线和失效循环；导出运行快照、Excel 指标和 PNG 图表。
- 保存/加载带元数据和 SHA-256 校验的模型；加载模型后可批量预测。

### 不能据此宣称什么

- 不能宣称已经完成实体 CAN、CANoe/CANape、HIL、台架或量产 BMS 验证。
- Virtual/offline/软件测试证据不能替代真实传感器、控制器、通信总线或安全认证证据。
- 一步容量拟合指标好，不等于 RUL 递归外推可靠。
- 当前模型结果不能直接用于安全保护、质保、报废、寿命承诺或其他安全关键决策。
- 当前 TCP 接入没有达到可暴露到不可信网络的安全标准。

## 端到端数据与计算链路

```text
导入路径
  -> 配置/数据校验
  -> CALCEAdapter 或 NASAAdapter
  -> 标准电池 DataFrame(cycle, capacity, SoH, resistance, CCCT, CVCT)
  -> capacity 序列 + window_size 滑动窗口
  -> 训练折 scaler
  -> 严格留一电池训练/验证/测试
  -> 一步预测 + 完全递归预测
  -> 指标/失效语义/结果快照
  -> PyQt 图表、结果卡片、Excel/JSON/PNG 报告
```

容量预测建模为：用前 `window_size` 个容量值预测下一个容量值。放电容量通常按安时积分计算：

```text
capacity = Σ(current × Δt / 3600)
```

## 代码入口与模块地图

| 路径 | 作用 | 进入时重点看什么 |
| --- | --- | --- |
| `battery_soh_app.py` | 应用入口、启动闪屏、导入 `MainWindow`、启动 Qt 事件循环 | 启动阶段和错误弹窗只显示简短信息，完整 traceback 写日志 |
| `ui/main_window.py` | 主窗口、数据导入、参数、模型生命周期、结果/报告交互 | 当前运行状态、结果批次、训练/预测分流、控件冻结 |
| `ui/worker.py` | 加载数据、跨电池训练评估、全量最终模型训练的 QThread | 合作式停止、阶段 progress、最终模型 signal |
| `ui/predict_worker.py` | 已加载模型的批量数据加载和预测 | 必须复用同一预测协议和 scaler |
| `ui/chart_show.py` | Matplotlib 画布、悬停、图例编辑、缩放/平移、全屏子图 | 预测与真实曲线使用不同线型/标记；右键进入当前/全部子图全屏 |
| `ui/style.py` | “宣纸水墨”主题、颜色 token、焦点和 QFileDialog 样式 | 不要随意改成旧的暗色/Quantum Lab 主题 |
| `ui/tcp_server.py` | 实验 TCP 接收服务 | 当前未完成安全修复，见 TCP 风险章节 |
| `ui/tcp_display.py` | TCP SOH/RUL 独立展示窗口 | 仅作为实验 UI |
| `core/adapters.py` | CALCE/NASA 适配器和容量/特征提取 | 统一输出字段、文件排序、无效文件跳过、循环对齐 |
| `core/dataload.py` | 根据 `adapter_type` 调用适配器 | `load_battery_from_paths()` 是 UI/脚本共用入口 |
| `core/validation.py` | 配置、文件资源、CALCE 表格、NASA 结构校验 | 资源限制和适配器专属规则 |
| `core/preprocess.py` | scaler、因果异常值审计、滑窗、留一法 split、一步/递归预测 | 训练统计量不得来自目标电池；清洗不得读未来 |
| `core/train.py` | 单电池留一折、多种子汇总、校准和协议指标 | 目标电池只在最终评估使用 |
| `core/evaluate.py` | 五种指标、RE 状态、t 分布 CI | 无阈值交叉时 RE 为 `None`/截尾状态 |
| `core/result_semantics.py` | 将失效位置映射回原始 `cycle` 编号 | 不要用预测数组位置冒充原始循环号 |
| `core/model_persistence.py` | 最终全量训练、模型保存/加载、安全元数据 | state-dict、sidecar、扩展名、版本、哈希一致性 |
| `core/run_snapshot.py` | 不可变单次运行快照 | 报告必须来自快照，不从导出时的 UI 重读参数 |
| `core/report_export.py` | JSON/Excel/PNG 原子导出 | 运行 ID 目录、覆盖确认、临时文件清理 |
| `core/batching.py` | RNN DataLoader 小批量训练 | 默认批次上限 64，避免一次性搬运全部样本 |
| `core/cancellation.py` / `core/progress.py` | 合作式停止和统一 progress event | 不得恢复 `QThread.terminate()` |
| `models/rnn_model.py` | 单层 RNN/GRU/LSTM `Net`，输入为单变量容量序列 | `input_size=1`，末端线性层输出下一容量 |
| `models/XGBoost.py` | XGBRegressor，训练电池验证集 early stopping | eval_set 不能使用目标电池 |
| `models/RF.py` | warm-start 分批加树，以验证 RMSE 选择树数 | 选完后再按选定树数重拟合 |
| `utils/config.py` | `TrainConfig`、模型/指标/scaler 规范化、配置保存 | 非法模型/指标/scaler 直接拒绝，不静默回退 |
| `utils/paths.py` | 以项目根目录为锚的 `CONFIG_FILE`、`OUTPUTS_DIR` 等 | 不依赖当前 IDE working directory |
| `utils/logger.py` | 项目日志 | 日志默认写 `outputs/` |

## 数据集与导入规则

### CALCE

- 内置目录：`dataset/CS2_35/`、`CS2_36/`、`CS2_37/`、`CS2_38/`，当前分别有 25、26、27、28 个文件；另有 `dataset/CALCE.npy`。
- 支持 `.xlsx` 和 `.csv`。表格列会先标准化，典型必需列为 `Date_Time`、`Cycle_Index`、`Step_Index`、`Voltage(V)`、`Current(A)`、`Test_Time(s)`。
- 文件夹导入时按每个文件数据表首行的 `Date_Time` 排序；正式数据读取避免重复完整读取。
- 工步必须由用户提供三个互不相同的非负整数：恒流充电、恒压充电、放电。内置严格基准显式使用 `2/4/7`；`TrainConfig` 默认值目前是 `None`，所以 CALCE UI 需要手动输入。
- 放电容量按放电工步的电流/时间积分；同时计算 `SoH`（上下电压之间容量差）、`CCCT`、`CVCT`，并尽量提取内阻。

### NASA PCoE

- 当前未跟踪目录：`dataset/NASA_PCoE/`，包含 `B0005.mat`、`B0006.mat`、`B0007.mat`、`B0018.mat` 和 README。
- 文件来源和校验信息写在 `dataset/NASA_PCoE/README.md`：NASA 官方说明页 + `USTC-AI4EEE/RUL-Mamba` 公开镜像；官方页面未明确附下载资源/许可证，重新分发前要再次确认。
- 2026-08-29 用当前 `NASAAdapter` 直接加载单文件时，得到的有效放电记录数为：B0005 168、B0006 168、B0007 168、B0018 132。原始 MAT `cycle` 结构包含充电和放电等全部周期，不能直接把结构长度当放电样本数。
- NASA 适配器优先读取 `data['Capacity']`，缺失时回退到 `Time`/`Current_measured` 积分；输出仍使用统一 DataFrame 字段。
- **严格留一电池时必须逐个导入四个 MAT 文件**。如果只导入整个 `dataset/NASA_PCoE` 文件夹，当前适配器会把其中所有 MAT 合并成一个名为 `NASA_PCoE` 的电池，无法建立 B0005/B0006/B0007/B0018 的严格跨电池折。
- NASA 常用额定容量为 2.0 Ah；系统 80% 阈值是 1.6 Ah。若复现 RUL-Mamba 实验的 EOL 定义，应显式使用 70%（1.4 Ah），不能把两种阈值混写。

### 输出标准

适配器返回：

```python
battery_dict[name] = DataFrame(
    cycle, capacity, SoH, resistance, CCCT, CVCT
)
battery_list = [name1, name2, ...]
```

只把真正成功加载且有可用放电容量的电池写入 `battery_list`。无效文件、空目录、重复名称和不足窗口的电池会被跳过并记录原因；结果、图表和预测均按电池名称对齐，不依赖列表位置。

## 评估协议与算法语义

### 严格留一法

`core.preprocess.prepare_leave_one_out_split()` 对每个目标电池建立一折：

- 目标电池不生成训练/验证样本，也不参与 scaler 拟合、早停、调参或种子选择。
- 其余每块训练电池按时间顺序生成滑窗，并将尾部约 20% 作为验证段；前段作为训练段。
- 目标电池的完整容量序列只用于一次最终测试。
- 训练结果以电池名称为键，目标电池序列中的哨兵值不会进入训练标签。

### 一步预测与递归预测

- 一步预测：每个窗口都使用该时刻可见的实测历史；用于 RMSE、MAE、R²、Pearson 等常规拟合指标。
- 递归未来预测：只从目标电池最初的 `window_size` 个实测值开始，后续把模型输出回填到窗口；用于 RUL/RE 和预测失效循环。
- `core/train.py` 的结果详情保留 `one_step_prediction`、`recursive_prediction`、`one_step_metrics`、`recursive_metrics` 和 `rul_protocol='recursive_future'`。

### 防过拟合收缩

- `fit_persistence_blend()` 只在训练电池验证段中比较模型和“上一循环容量”持久性基线。
- `persistence_blend` 在 `[0, 1]` 内：`0` 表示完全回退到上一循环，`1` 表示保留原模型预测。
- 预测统一经过 `core.prediction.predict_capacity_batch()`，先按模型保存的 scaler 反变换，再应用持久性收缩；批量预测、加载模型预测和 TCP 路径共用这一入口。
- 结果中保留 `persistence_baseline_metrics` 和 `rmse_skill_vs_persistence`，不能只看模型 RMSE 而忽略基线。

### 指标和失效语义

- RMSE、MAE、R²、Pearson 对输入长度、有限性和常数序列有明确保护。
- RE 取真实/预测序列首次低于 `rated_capacity × threshold_ratio` 的位置；真实或预测没有交叉、初始即失效等情况返回 `None` 并附 `re_status`，UI 显示 `N/A（截尾）`，不把缺失交叉伪装为 `1.0`。
- `analyze_failure_cycles()` 将预测/实测失效位置映射到原始 `cycle` 编号，并区分“实测失效”“模型预测失效”“观测期内未失效”。
- 多种子 95% CI 使用同一留一折内的随机种子波动；它不是跨电池总体不确定性，也不是安全置信度。

## 模型与最终模型生命周期

### 评估训练

- `core.train.train()` 默认从 `config.seed` 开始生成连续 `n_seeds` 个种子，主结果为所有有效种子的均值，不按目标测试 RMSE 选“最佳种子”。
- RNN/GRU/LSTM 使用 PyTorch + Adam + MSELoss + DataLoader；验证损失早停，最佳 epoch 只由训练电池验证段决定。
- XGBoost 使用训练电池验证集 `eval_set` 和 early stopping。
- Random Forest 使用 warm-start 分批加树，以训练电池验证 RMSE 选择树数，再重新拟合选定树数。

### 全量最终模型

评估结束后，`ui/worker.py` 调用 `train_model_on_all_data()`：

- 先用保留的调参/验证数据确定 epoch 或树数；
- 再用全部有效电池的滑窗样本重训最终模型；
- 重新在全部最终训练数据上拟合最终 scaler；
- 元数据记录有效电池名、容量哈希、训练样本数、选定 epoch/树数和 `final_training_scope='all_valid_batteries'`。

## 模型保存、加载与安全

- RNN/GRU/LSTM：保存 `.pt/.pth`，文件内容必须是纯 tensor `state_dict`；加载使用 `torch.load(..., weights_only=True)`。
- RF/XGBoost：保存 `.joblib`；joblib 反序列化可能执行代码，UI 必须在用户明确确认后才加载。
- `.pkl` 默认禁止；缺少 sidecar、伪造后缀、格式版本不兼容、元数据缺字段、文件过大、SHA-256 不匹配、模型类型不匹配都会在反序列化前拒绝。
- 模型旁边必须保留同名 `.meta.json`。当前格式版本为 2，包含：模型类型、窗口、额定容量、阈值、scaler、特征 schema、训练参数、库版本、数据哈希、创建时间、文件哈希和训练电池信息。
- 限制：模型文件最大 512 MiB，元数据最大 1 MiB。
- UI 加载时先在临时变量完成校验和加载，成功后才一次性替换 `loaded_model/loaded_metadata`；失败不会破坏旧模型。卸载模型后回到训练模式。
- 循环模型与输入会统一到同一 CPU/CUDA 设备；CUDA 不可用时安全回落到 CPU。

## PyQt 工作流

### 启动与主窗口

- 入口：`python battery_soh_app.py`。
- 启动闪屏先显示，再导入重模块，阶段进度为 5%→80%→95%→100%；启动异常弹窗只显示简短错误，完整堆栈写日志。
- 主窗口默认约 1600×900，最小 1180×700；图标导航侧边栏 + 图表区两栏布局：左侧窄轨道（数据/参数/结果/日志，Ctrl+1~4 切换，再点当前页可收起侧栏）+ 页面栈，中间模型选择/图表/开始评估。
- 主题按钮是悬浮在右上角的**圆形图标按钮**（无文字，深色显示月/浅色显示日），可按住拖动到任意位置，位置按窗口比例记住；原顶部条已移除。
- 主题是“宣纸水墨”：暖宣纸底、黛青主强调、朱砂表示危险/阈值；保留可见焦点、键盘快捷键、文件夹对话框中文标签和图表全屏交互。

### 常用操作

- `Ctrl+O`：导入文件；`Ctrl+Shift+O`：导入文件夹；`Ctrl+Alt+O`：导入 JSON 配置；`Ctrl+Return`：开始评估；`Ctrl+L`：加载模型；`F1`：当前模型帮助。
- 支持模型：RNN、GRU、LSTM、XGBoost、RF；支持 RMSE、MAE、R²、Pearson、RE、全部。
- 参数区按“设置工步”“电池与失效判据”“评估与验证”“模型高级参数”折叠；运行期间冻结会影响结果的控件。
- 已完成训练后再次开始会询问“当前窗口训练”或“新窗口训练”；旧结果以结果批次保留，不要把结果批次混成一次运行。
- 结果卡片优先显示实测/预测失效状态，再显示指标；图表支持悬停、图例编辑、鼠标缩放/平移，以及右键选择当前子图/全部子图全屏。

### 训练/预测分流

- 未加载模型：`start_evaluation()` 启动 `EvalWorker`，执行加载→严格评估→全量最终模型训练→结果展示。
- 已加载模型：`start_evaluation()` 启动 `PredictWorker`，对导入电池做批量预测；指标和一步/递归协议应与训练一致。
- 当前 UI 启动前只调用 `validate_training_config()` 做配置校验；`validate_evaluation_request()` 存在但当前 `start_evaluation()` 未调用深度文件校验。深度数据读取/错误处理发生在 worker 中，这是现有行为，不要在没有确认的情况下改变启动流程。

### 快照与报告

- 每次运行开始时创建不可变 `RunSnapshot`，冻结配置和导入路径。
- 报告默认写入 `outputs/runs/<run_id>/`：`report.json`、`评估结果.xlsx`、`评估结果.png`。
- 导出采用临时文件 + `os.replace` 原子替换；已有目标必须确认覆盖；权限/占用/磁盘空间错误显示可执行的恢复建议。
- 报告必须从对应运行快照导出，不能从用户后来修改的当前 UI 重新拼参数。

## 当前 `config.json` 与“默认值”区别

`config.json` 是应用保存的最近一次界面状态，不是严格基准配置，也不是 `TrainConfig` 的代码默认值。当前文件记录的是：

```text
adapter_type = NASA
mode = RF
rated_capacity = 2.0 Ah
threshold_ratio = 0.7
window_size = 16
n_seeds = 1
metric = MAE
device = GPU (CUDA)
norm_method = 额定容量归一化
cc_step/cv_step/discharge_step = null
```

`TrainConfig` 代码默认值仍偏向 CALCE/RNN：额定容量 1.1 Ah、阈值 0.8、窗口 64、`n_seeds=5`、CPU、rated scaler、`adapter_type='CALCE'`，CALCE 工步默认为 `None`。需要复现实验时，以实验脚本/manifest 的显式参数为准，不要直接复用当前 `config.json`。

## 严格基准与可复现信息

### 复跑入口

```powershell
python scripts/run_strict_benchmark.py
```

脚本要求 NVIDIA CUDA 可用，固定使用 CALCE `CS2_35`～`CS2_38`、RNN、`window_size=64`、`epochs=100`、`hidden_dim=64`、`seed=1` 起的 5 个种子、`patience=20`、rated scaler、额定容量 1.1 Ah、阈值 0.8、工步 2/4/7，并写入 `benchmark/strict_zero_shot_rnn.json`。

### 基准性质

manifest 生成于 2026-08-12，源提交为 `568117273798a983c8485c4b49abc60e28ae4464`，硬件为 RTX 4050 Laptop GPU，Python 3.10.20，耗时约 246.515 秒。README 中的表是旧方法/历史追溯结果：当前版本新增了因果预处理和验证集持久性收缩，旧表不能当作当前修正代码的最新性能声明。

历史四折均值如下（Ah，RE 为递归寿命相对误差）：

| 目标电池 | RMSE | MAE | R² | Pearson | 递归 RE |
| --- | ---: | ---: | ---: | ---: | ---: |
| CS2_35 | 0.03396 | 0.03002 | 0.97372 | 0.99808 | 0.97688 |
| CS2_36 | 0.03806 | 0.03294 | 0.97797 | 0.99836 | 0.97529 |
| CS2_37 | 0.03831 | 0.03402 | 0.97204 | 0.99862 | 0.97465 |
| CS2_38 | 0.03747 | 0.03314 | 0.96836 | 0.99841 | 0.97323 |
| 宏平均 | 0.03700 | 0.03250 | 0.97300 | 0.99840 | 0.97500 |

解读：一步容量拟合相对稳定，但当前 RNN 的完全递归 RUL 外推误差很大；不能用一步 RMSE/R² 替代 RUL 结论。若修改评估协议或预处理，必须重新生成 manifest，并同步更新 README 的“历史/当前”说明。

## TCP 实验边界（当前不要误判为已修复）

当前 `ui/tcp_server.py` 的行为：

- 绑定 `0.0.0.0`，端口 `8888`，单连接监听；报文是换行分隔 JSON，主要字段为 `{"capacity": ...}` 和 `{"reset": true}`。
- 缓冲容量历史，达到窗口后执行预测；递归循环上限为 2000 步。
- 与离线预测共用 `predict_capacity_batch()`，但输入校验、资源上限、认证和网络暴露边界尚未完成。
- RUL 路径仍引用未定义的 `initial_capacity`，会触发 `NameError`；这是已知问题，不得宣称 TCP RUL 可用。
- 默认局域网暴露、无访问令牌、无最大报文/历史/频率限制；`main_window` 也会在异步线程真正 bind 成功前切换部分 UI 状态。
- 阶段修复清单中 P1-06、P1-07 标记为“已跳过（未修复）”；P1-13 仅完成非 TCP 合作式停止。TCP 测试和“加载模型→TCP→全屏→安全断开”端到端场景按用户要求未执行。

如果以后要处理 TCP，必须先重新确认范围和安全默认值，至少单独设计：本机默认绑定、显式局域网模式/认证、输入有限性与范围、报文/缓冲/频率上限、错误可观测性、RUL 基准语义和停止/关闭流程。

## 异常值、数据校验与已知行为

- 适配器默认 `clean_outliers=False`：保留所有有限容量点，只剔除 `NaN/Inf`，避免先观察完整目标轨迹再清洗测试标签。
- 可审计的 `filter_capacity_outliers()` 是因果局部 2σ 过滤，最多参考此前 40 个有效循环；稳定窗口、边界点和持续退化膝点有保护策略，输出 mask、原因、数量和 protected indices。
- 若跨文件循环编号重复/回退，展示序号可能改为有效放电记录的连续编号；原始编号语义和审计信息应保留。
- CALCE/NASA 有独立校验器；校验包含文件大小、行数/列数、sheet 数、MAT 结构深度、有限性、时间/循环顺序、电流方向、容量范围和窗口长度。
- `validate_evaluation_request()` 的深度校验目前不是启动按钮的前置步骤；不要把“存在校验函数”写成“所有导入都在点击前完成深度验证”。

## 测试、质量门禁与当前证据

### 当前已实际运行

2026-08-29 在 `D:\Anaconda3\envs\pytorch\python.exe`（Python 3.10.20）下执行：

- `python -m unittest discover -s tests -v`：**184 tests，全部通过**，耗时约 86.887 秒。
- `python -m compileall -q battery_soh_app.py core models ui utils`：通过。
- `python -m pip check`：`No broken requirements found.`。
- `git diff --check`：无 diff 错误；仅有 Git 关于 LF/CRLF 的提示。

### 环境陷阱

- 当前默认 `D:\Anaconda3\python.exe` 是 Python 3.12.7，安装的 pytest 为 7.4.4，但导入 PyQt6 时出现 `ImportError: DLL load failed while importing QtCore/QtWidgets`，并伴随 Windows `0xc0000139`；这次不能作为项目测试失败或通过的证据。
- 文档指定的 Python 3.10.20 `pytorch` 环境没有 pytest，但 unittest 回归可以运行。因此当前最稳妥的命令是上面的 3.10 `unittest`；若要跑 pytest/Ruff/Bandit/pip-audit，应在该环境按锁文件安装开发依赖后再记录结果。
- `requirements.lock`、`requirements-dev.lock`、`requirements-cuda.lock` 均以 Python 3.10 为基准；CUDA 锁针对 RTX 4050 / 驱动 596.49 / `torch 2.13.0+cu130`。

### CI 门禁

`.github/workflows/quality.yml` 在 Windows/Linux、Python 3.10 上执行：

- 安装 runtime + dev lock；
- compileall；Ruff；Bandit；pip-audit；unittest；
- 总覆盖率至少 59%，`core/evaluate.py`、`core/result_semantics.py`、`core/run_snapshot.py`、`utils/config.py` 合计门禁至少 85%。

TCP 代码在 coverage 配置中排除，且 TCP 测试此前按用户要求跳过；不要把 CI 绿灯解释为 TCP 已安全。

## 测试文件分组入口

- 评估协议与隔离：`tests/test_evaluation_protocol.py`、`tests/test_final_model_training.py`、`tests/test_overfit_guard.py`。
- 指标与结果语义：`tests/test_metric_semantics.py`、`tests/test_named_results.py`。
- 数据与适配器：`tests/test_data_validation.py`、`tests/test_outlier_audit.py`、`tests/test_phase5_dataset_integration.py`、`tests/test_phase5_edge_cases.py`。
- scaler、模型和安全：`tests/test_scaling.py`、`tests/test_model_artifact_smoke.py`、`tests/test_model_loading_security.py`、`tests/test_model_session.py`、`tests/test_phase5_model_devices.py`。
- 线程、快照和导出：`tests/test_cooperative_stop.py`、`tests/test_run_snapshot_export.py`、`tests/test_resource_efficiency.py`、`tests/test_safe_logging.py`。
- UI、启动和重训：`tests/test_startup_loading_flow.py`、`tests/test_step_settings_ui.py`、`tests/test_phase5_ui_workflows.py`、`tests/test_phase5_ui_accessibility.py`、`tests/test_retraining_and_chart_navigation.py`、`tests/test_ui_design_contract.py`、`tests/test_ui_polish_layout.py`。
- 工程卫生和基准：`tests/test_engineering_hygiene.py`、`tests/test_benchmark_manifest.py`。
- 测试计划与阶段记录：`tests/phase5_test_plan.md`、`SOH_漏洞与风险修复清单.md`。

## 阶段完成度（以现有修复清单为准）

- P1-01～P1-05：评估隔离、严格留一法、scaler、配置规范化、加载模型指标路径，标记已修复。
- P1-08～P1-12：模型加载安全/元数据、全量最终模型、数据校验、异常值审计/循环对齐，标记已修复。
- P1-14～P1-15：按名称对齐结果、不可变运行快照、原子报告导出，标记已修复。
- P1-06/P1-07：TCP RUL/网络暴露与资源限制，标记已跳过（未修复）。
- P1-13：非 TCP 停止/关闭流程已修复，TCP 部分跳过，因此是部分修复。
- P2 阶段 4/5：非 TCP 指标、性能、日志、依赖、UI、数据集成回归标记完成；TCP 缓冲、2000 步频控和 TCP 端到端场景仍排除。

## 下一次工作建议

### 如果是普通维护/继续开发

1. 先确认 `git status` 和本文件中的 dirty 状态；不要覆盖现有用户 diff。
2. 先用小型合成数据或现有测试建立可重复 oracle，再改实现。
3. 只要改动评估口径、数据清洗、模型输入、持久化格式或 UI 运行状态，就补对应测试并运行 3.10 unittest 全套。
4. 新性能数字必须注明数据集、目标电池、窗口、阈值、种子、环境、协议和是否历史结果。

### 如果是复现 CALCE 严格基准

1. 使用 CUDA 环境和 `scripts/run_strict_benchmark.py`，不要直接读取当前 `config.json`。
2. 确认 `dataset/CS2_35`～`CS2_38` 的源文件和哈希没有变化。
3. 保存新的 manifest，再决定是否更新 README；旧表必须保留历史标记。

### 如果是跑 NASA 小样本烟测

1. 在 UI 中选择 `NASA (.mat)`。
2. 逐个导入 B0005/B0006/B0007/B0018，不要只导入整个文件夹。
3. 额定容量设 2.0 Ah；先用窗口 32、RF、单种子、CPU 烟测，再考虑窗口 64/多种子/深度模型。
4. 80% 是系统常用阈值；只有在复现实验 EOL 时才改成 70%，并在报告中明确写出。

### 如果是处理 TCP

先暂停实现，重新确认是否要扩大到 TCP 安全修复。需要先解决绑定地址、认证、输入校验、资源限制、RUL 初始容量语义、异常反馈和关闭流程，再补 TCP 测试；不能用当前离线测试结果替代。

## 参考文件索引

- 项目说明和运行方法：`README.md`、`README_EN.md`。
- 约束：`AGENTS.md`。
- 风险/阶段记录：`SOH_漏洞与风险修复清单.md`。
- NASA 数据说明：`dataset/NASA_PCoE/README.md`。
- 严格基准 manifest：`benchmark/strict_zero_shot_rnn.json`。
- 严格基准脚本：`scripts/run_strict_benchmark.py`。
- CI：`.github/workflows/quality.yml`。

## 维护说明

本文是“快速恢复上下文”的项目记忆，不替代当前代码、测试输出或正式实验报告。每次发生以下变化时应更新本文：

- 评估协议、阈值、数据集来源或模型输入改变；
- 模型持久化格式、UI 工作流、TCP 边界或安全策略改变；
- 测试环境/锁文件/CI 门禁改变；
- 当前工作区从 dirty 变为已确认提交，或出现新的未提交工作。

更新时保留事实、历史结果和待验证项的标签，不把推测写成已验证能力。
