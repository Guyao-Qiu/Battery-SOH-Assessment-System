# Battery SOH Assessment System

> 电池健康状态评估系统

语言：中文 · [English](README_EN.md)

基于马里兰大学 CALCE 锂电池充放电数据集，采用 PyQt6 设计 UI 界面，利用 RNN/GRU/LSTM 及 XGBoost、Random Forest 共 5 种模型，构建了该系统，对锂离子电池循环充放电数据进行容量退化趋势预测，计算剩余使用寿命（RUL）。采用留一法（Leave-One-Out）跨电池验证，并提供多种评估指标与 95% 置信区间分析。

浅色（宣纸）与深色（墨夜）两套主题，颜色集中在 [`theme_tokens.py`](theme_tokens.py)。**默认深色（墨夜）**，右上角按钮一键切换（快捷键 `Ctrl+T`），选择会被记住：

| 深色 · 墨夜（默认） | 浅色 · 宣纸 |
|---|---|
| ![深色主题](assets/screenshots/main-dark.png) | ![浅色主题](assets/screenshots/main-light.png) |

截图由 `python tools/render_screenshots.py` 重新生成（真实主界面渲染，非示意图）。中文字体由 `ui/fonts.py` 在启动时显式注册——PyQt6 的 offscreen 平台插件不使用系统字体引擎，不注册就会满屏方框。

> [!IMPORTANT]
> 本项目是面向教学、科研与离线算法验证的 Research Preview。当前严格零样本基准显示一步容量预测较稳定，但递归 RUL 外推误差仍然很大；结果不得直接用于 BMS 安全保护、质保、报废或其他安全关键决策。TCP 实时接入属于实验功能，请勿暴露到不可信网络。

## 评估协议（请先读这一节）

这一节说明结果是怎么算出来的、哪些数字可以信、哪些不能信。**评估路径与部署路径共用同一套流程**，因此你看到的指标就是最终模型的表现。

### 外层：留一电池（LOBO）

对每块目标电池建一折：目标电池**全程不参与**任何拟合、scaler 拟合、超参选择、早停或种子选择，只在模型定型后评估一次。scaler 只用训练电池拟合。

### 内层：留一电池交叉验证选超参

在训练电池内部再做一次留一电池交叉验证，用**多步滚动预测误差**选超参。验证对象是一块**没见过的电池**，与最终使用场景一致。

> 这一点很关键：早期实现把每块训练电池切成「前 80% 训练 + 后 20% 验证」，而电池寿命末段（膝点）恰好落在后 20% —— 模型从没见过寿命末段，却被要求预测「什么时候越过失效阈值」。修正后，定型用的是**全部训练电池的全部窗口**。

### 定型：全量重训

选定超参后用全部训练电池的全部窗口重训一次。评估与部署（`core/protocol.py::fit_final`）调用的是**同一个函数**。

### 预测起点与头条指标

头条指标是**滚动预测起点**上的递归预测误差，起点取寿命的 40% / 50% / 60% / 70%：

- **递归预测**才是真实使用场景：只给起点之前的实测值，之后把模型自己的输出回填进窗口；
- **一步预测**（每一步都用真实历史）误差不累积、天然接近「平推」的好成绩，**区分不出模型好坏**，因此降级为诊断信息。

结果表默认展示 RMSE、MAE、相对平推的**技能分**、预测 RUL、真实 RUL 与 RUL 误差，并用下拉框切换起点。

### 基线：任何模型都必须先赢过它们

结果表并排列出三条经验基线：**平推**（下一个循环 = 上一个循环）、**线性外推**、**双指数** `C(k)=a·e^{bk}+c·e^{dk}`。

技能分 = `1 − RMSE模型 / RMSE平推`。技能分 < 0.05 的单元格会显示 ⚠ 并提示「模型未超越持久性基线」。

### 持久性混合系数 α

α 在 `[0, 1]` 之间，把预测向「上一循环容量」收缩。**α 用多步滚动误差标定，且只用没见过该验证电池的内层折模型**，避免「一步标定、多步使用」造成的坍缩。

> 早期实现在合成数据上 4/4 折的 α 全是 `0.000`：模型被整个丢掉，界面上看到的 R² 0.98–0.99 其实是「平推」的得分。修正后同一批数据的 α 落在 0.72–0.80。

### 指标与失效语义

- RMSE / MAE / R² / Pearson 对输入长度、有限性与常数序列有保护；
- **右删失是显式状态**：区分 `observed` / `observed_censored` / `prediction_censored` / `both_censored` / `observed_initial_failure` / `prediction_initial_failure`，界面显示 `N/A（截尾）`，不把「没失效」硬当成 0 或 −1；
- **RUL** = 从当前预测起点到 EOL 还有多少个循环（真正的剩余寿命），不是「SOH 从 pct% 掉到 80% 需要多少个循环」；
- **SOH** 一律定义为 `C / C_rated`；
- **失效判定只有一处实现**（`core/result_semantics.py`），`core/protocol.py`、`core/evaluate.py`、`core/train.py` 全部委托到它，避免多份逻辑各自漂移；
- **失效判定去抖可选**（`config.json` 的 `eol_debounce`，默认 `1`）：设为 `3` 时要求**连续 3 个循环**低于阈值才算失效，避免单点噪声把 EOL 提前。返回值仍是首次下穿处，所以开启去抖不会让报告的失效循环偏晚；
- **离群点默认只标记不删除**（`outlier_mode='mark'`）：局部窗口均值对快速下降段和 NASA 的**容量再生**（真实物理，不是噪声）都会滞后，直接删会误伤。审计信息在 `frame.attrs['outlier_audit']`，需要清理时显式传 `clean_outliers=True`。

### 不确定性：n = 电池数，不是随机种子

- 多种子 95% CI 只反映**同一留一折内的随机种子波动**，它很窄，**不代表**泛化不确定性；
- 真正的不确定性来自「换一块电池会怎样」，因此跨电池汇总给出 mean ± std 与 **bootstrap 区间**（`n = 电池数`）。电池只有 4–5 块时区间会很宽——这是诚实的。

### 复现本节的对照实验

```powershell
python tools/repro_synthetic.py
```

在合成「NASA 风格」电池上复现「现有流程 vs 建议流程」的四方对比，输出 α 值、各起点的 RMSE 与 EOL 检出情况。数据是合成的，只验证**机制**；把脚本里的 `make_battery` 换成你的真实 `battery_dict` 就是真实数据上的对比。

### 局限

- 没有接触真实 BMS、CAN、HIL 或台架数据，软件测试证据不能替代安全认证证据；
- 一步容量拟合好**不等于** RUL 递归外推可靠；
- 对「训练集里没有的极端电池」做外推依然很难——协议修复不是万能的；
- 多特征递归预测时，非容量通道保持窗口末值（未来工况未知时的保守假设）。

### 质量门禁

```powershell
python tools/check_undefined.py core models ui utils   # 找"用了但从未定义"的全局名字
python tools/check_colors.py                          # 硬编码颜色必须只出现在 theme_tokens.py
python -m unittest discover -s tests                   # 回归测试
```

## 严格零样本基准（Benchmark）

本基准使用严格零样本跨电池评估（留一电池验证）：目标电池不参与训练、验证、早停、调参或种子选择。RMSE、MAE、R² 和 Pearson 来自一步预测；RE 来自仅以初始窗口起步、后续只回填模型输出的完全递归 RUL 路径。所有预定种子均计入均值，95% CI 只反映同一留一折内的随机种子波动。

下表是源提交 `5681172` 生成的历史基准（当时使用分箱异常值清洗，CALCE CS2_35~38 共 3,883 个循环）。当前版本已增加因果预处理和验证集防过拟合收缩，因此该表只用于追溯旧基线，不能代表修正后的最新性能：

| 电池 | 循环数 | RMSE ↓ (Ah) | MAE ↓ (Ah) | R² ↑ | Pearson ↑ | 递归 RE ↓ | RE 状态 |
|------|-------:|------------:|-----------:|-----:|----------:|------------:|---------|
| CS2_35 | 896 | 0.0340 | 0.0300 | 0.9737 | 0.9981 | 97.69% | 已观测 |
| CS2_36 | 941 | 0.0381 | 0.0329 | 0.9780 | 0.9984 | 97.53% | 已观测 |
| CS2_37 | 1,008 | 0.0383 | 0.0340 | 0.9720 | 0.9986 | 97.46% | 已观测 |
| CS2_38 | 1,038 | 0.0375 | 0.0331 | 0.9684 | 0.9984 | 97.32% | 已观测 |
| **宏平均** | **970.8** | **0.0370** | **0.0325** | **0.9730** | **0.9984** | **97.50%** | — |

该结果说明一步容量拟合较稳定，但当前 RNN 的完全递归寿命外推误差很大；不能用一步预测指标替代 RUL 结论。机器可读的逐种子 CI、最佳 epoch、完整参数和哈希见 [`benchmark/strict_zero_shot_rnn.json`](benchmark/strict_zero_shot_rnn.json)，复跑入口为 `python scripts/run_strict_benchmark.py`。

复现实验信息：

- 源提交：`568117273798a983c8485c4b49abc60e28ae4464`
- 总耗时：246.515 秒，包含 106 个源文件加载、哈希与 20 次训练
- 硬件：AMD64 Family 25 Model 117 CPU；NVIDIA GeForce RTX 4050 Laptop GPU；驱动 596.49；CUDA 13.0
- 软件：Python 3.10.20；PyQt6 6.11.0；NumPy 1.26.4；pandas 2.3.3；Matplotlib 3.10.9；PyTorch 2.13.0+cu130；scikit-learn 1.7.2；XGBoost 3.0.2；SciPy 1.15.3；joblib 1.5.3；openpyxl 3.1.5
- 完整参数：`mode=RNN`，`window_size=64`，`epochs=100`，`hidden_dim=64`，`seed=1`，`n_seeds=5`（种子 1–5），`patience=20`，`norm_method=rated`，`rated_capacity=1.1`，`threshold_ratio=0.8`，`device=cuda`，`voltage_upper=3.8`，`voltage_lower=3.4`，`cc_step=2`，`cv_step=4`，`discharge_step=7`；树模型参数也随配置快照完整记录在基准 JSON 中

数据哈希（SHA-256）：

| 电池 | 原始源文件树 | 清洗后容量序列 |
|------|--------------|----------------|
| CS2_35 | `dfeda906c01c37161cc569fdc41c11e0aed00f675c32c4a000fa845791d810f8` | `811bf49f66363ca9ca30af570ba87a6dc39bdf9158913780d02274467ee94a85` |
| CS2_36 | `bee2c8e094f05feed6c53bab3ba930ca9580e436e41431ddd3b17e905a99aa4a` | `4e649c53b89bf545d6a284fb8cce05f0feff8b3e8e5a24e27093cce20a9e83bb` |
| CS2_37 | `dacc6cf5cd04e147afac28051917564ab204bce48810919a896e8e85cfb4e5ee` | `c123db2c3db2664e01b2563a419b1e041426867bfbbac84ad1097b0ca1367960` |
| CS2_38 | `39ed8e425eb5155835d08e3aadaf588ef4321f57f2d7e5eabb19e1e41f956760` | `8c91320c5a75e1760f5a6d66d631e67615d43cf1cad0a80ddb18d5e24a8fc423` |

### DeTransformer 对齐基准（CALCE.npy，零目标电池泄漏，5 种子）

在严格零目标电池泄漏的留一交叉验证下（仅用其余 3 节电池训练，`window_size=64`、`threshold_ratio=0.7`、`epochs=500`、`hidden_dim=16`、`num_layers=3`、`K=16`、`alpha=0.1`），新增 `DeTransformer` 的自回归滚动预测（`rolling`）与单步预测（`one_step`）结果如下：

| 电池 | 滚动 RMSE ↓ | 滚动 MAE ↓ | 滚动 RE (`re` / `re_ref`) ↓ | 单步 RMSE ↓ | 单步 MAE ↓ |
|---|---:|---:|---:|---:|---:|
| CS2_35 | 0.0402 ± 0.0082 | 0.0301 ± 0.0081 | 0.0528 / 0.0529 | 0.0229 ± 0.0021 | 0.0145 ± 0.0014 |
| CS2_36 | 0.0609 ± 0.0111 | 0.0474 ± 0.0060 | 0.3557 / 0.0703 | 0.0199 ± 0.0018 | 0.0135 ± 0.0013 |
| CS2_37 | 0.1188 ± 0.0336 | 0.0854 ± 0.0263 | 0.1291 / 0.1293 | 0.0164 ± 0.0007 | 0.0106 ± 0.0007 |
| CS2_38 | 0.1367 ± 0.0438 | 0.0946 ± 0.0327 | 0.1360 / 0.1512 | 0.0182 ± 0.0014 | 0.0110 ± 0.0007 |
| **宏平均** | **0.0892 ± 0.0186** | **0.0644 ± 0.0153** | **0.1684 / 0.1009** | **0.0194 ± 0.0014** | **0.0124 ± 0.0010** |

![四电池真实推理对比图](prediction_chart.png)

## 功能特性

- **多模型支持**：RNN / GRU / LSTM（PyTorch 深度学习）+ XGBoost / Random Forest（scikit-learn 集成学习）
- **多数据格式**：支持 CALCE（.xlsx/.csv）和 NASA（.mat）数据集，适配器模式统一异构接口
- **严格零样本留一法验证**：目标电池不参与训练、验证、早停、调参或种子选择，只在模型固定后评估一次
- **评估/部署同一协议**：内层留一电池交叉验证选超参 → 全量窗口重训，评估的模型就是部署的模型（见「评估协议」）
- **滚动起点递归评估**：头条指标是寿命 40%–70% 处的**真正未来预测**，一步指标降级为诊断信息
- **经验基线并排**：平推 / 线性外推 / 双指数，并给出相对平推的技能分；技能分 < 0.05 会显示 ⚠
- **防过拟合校准**：α 用**多步滚动误差**标定，且只用没见过该验证电池的内层折模型
- **多特征输入**：可选 capacity / dq_v / CCCT / CVCT / resistance（默认只用容量，保持纯自回归）
- **不确定性分层**：多种子 CI（折内种子波动）+ 跨电池 bootstrap 区间（`n = 电池数`）
- **可排序结果表**：点列头排序、跨电池汇总行、基线行、复制 / 导出 CSV
- **主图讲清全貌**：预测起点、递归预测、10–90% 区间、失效阈值、真实/预测 EOL、SOH% 副轴，y 轴自动聚焦退化区间；
- **刻度密到能直接读数**：主刻度按 1 / 2 / 2.5 / 5 × 10ⁿ 的友好步长铺满，中间再插 4 条次刻度（周期数是整数、容量保留必要小数位），不必在网格线之间目测估读；
- **浅色 / 深色主题**：宣纸水墨主题的浅色（宣纸）与深色（墨夜）两套 token，颜色集中在 `theme_tokens.py`，切换后图表与启动闪屏同步
- **模型持久化**：PyTorch 以纯 state-dict + 哈希元数据清单安全保存；sklearn（.joblib）加载前必须确认代码执行风险；模型文件与同名 `.meta.json` 清单需一并保留
- **TCP 实时预测（实验）**：默认**只监听本机**；可选局域网模式（自动生成 token 握手）；19 种畸形输入只产生警告不崩溃；缓冲有硬上限；限流 + **独立预测线程**（最坏 1500 步的递归预测不会阻塞接收）；RUL 为真正的剩余寿命
- **报告导出**：评估结果导出为 Excel（.xlsx）+ JSON 配置 + 图表 PNG

## 项目结构

```
Battery-SOH-Assessment-System/
├── battery_soh_app.py        # 应用入口（含启动闪屏 + 全局异常兜底）
├── theme_tokens.py           # 唯一的颜色真相来源（浅色宣纸 / 深色墨夜）
├── requirements.txt          # 依赖清单
├── config.json               # 默认配置
├── core/
│   ├── adapters.py           # 数据适配器（CALCE / NASA；真实 CC/CV 切分）
│   ├── baselines.py          # 经验基线（平推 / 线性外推 / 双指数）
│   ├── batching.py           # RNN 小批量训练（含梯度裁剪）
│   ├── dataload.py           # 数据加载统一接口
│   ├── evaluate.py           # 指标、右删失语义、bootstrap 区间
│   ├── model_factory.py      # 模型构造与拟合的**唯一入口**（评估/部署共用）
│   ├── model_persistence.py  # 模型保存与加载
│   ├── prediction.py         # 共用预测入口（含多特征）
│   ├── preprocess.py         # 因果预处理、滑窗（单/多特征）、scaler
│   ├── protocol.py           # 统一协议：选超参 → 全量重训 → 滚动起点评估
│   ├── stream_protocol.py    # TCP 的纯 Python 部分（解析 / 限流 / RUL）
│   ├── train.py              # 留一电池评估主循环
│   └── validation.py         # 数据校验与列名标准化
├── models/
│   ├── rnn_model.py          # RNN / GRU / LSTM 网络定义（支持多特征 input_size）
│   ├── XGBoost.py            # XGBoost 训练与预测
│   └── RF.py                 # Random Forest（固定树数、一次训练）
├── ui/
│   ├── main_window.py        # 主窗口布局与交互逻辑
│   ├── chart_show.py         # Matplotlib 图表（预测起点/区间/EOL/SOH% 轴）
│   ├── result_model.py       # 可排序结果表 + 跨电池汇总
│   ├── worker.py             # 训练评估工作线程
│   ├── predict_worker.py     # 预测工作线程
│   ├── tcp_server.py         # TCP 数据接入服务（默认仅本机）
│   ├── tcp_display.py        # TCP 实时数据展示窗口
│   ├── animated_button.py    # 动画按钮组件
│   └── style.py              # 主题 QSS（颜色来自 theme_tokens）
├── tools/
│   ├── check_undefined.py    # 找"用了但从未定义"的全局名字
│   ├── check_colors.py       # 禁止 theme_tokens.py 之外出现硬编码颜色
│   ├── repro_synthetic.py    # 复现「现有流程 vs 建议流程」四方对比
│   └── send_demo.py          # TCP 演示客户端（含畸形输入）
├── utils/
│   ├── config.py             # 配置管理与持久化（只存规范键）
│   ├── crash_guard.py        # 全局异常兜底（闪退 → 日志 + 非阻塞提示）
│   ├── icon_generator.py     # 图标生成
│   └── logger.py             # 日志工具
└── dataset/                  # 数据集目录
    ├── CS2_35/               # 25 个 .xlsx 循环文件
    ├── CS2_36/               # 26 个 .xlsx 循环文件
    ├── CS2_37/               # 27 个 .xlsx 循环文件
    ├── CS2_38/               # 28 个 .xlsx 循环文件
    └── CALCE.npy             # 预处理后的 NumPy 数组
```

## 快速开始

### 环境要求

- Python 3.10+
- Windows / macOS / Linux
- NVIDIA GPU（可选，仅深度学习模型可加速）

### 安装

```bash
git clone https://github.com/Guyao-Qiu/Battery-SOH-Assessment-System.git
cd Battery-SOH-Assessment-System
pip install -r requirements.txt
```

`requirements.txt` 会引用项目验证过的精确版本锁文件；开发与质量门禁工具另见 `requirements-dev.lock`。当前锁定组合以 Python 3.10 为基准。

Windows + NVIDIA 显卡使用已验证的 CUDA 13.0 环境：

```bash
pip install -r requirements-cuda.lock
```

该组合在 RTX 4050 Laptop GPU、驱动 596.49 上以 `torch 2.13.0+cu130` 完成了实际 CUDA 张量运算验证。普通 `requirements.lock` 保留 PyPI 的 `torch 2.13.0`，供 CPU 环境和 CI 使用。

### 启动应用

```bash
python battery_soh_app.py
```

### 基本流程

1. 选择数据源格式（CALCE .xlsx/.csv 或 NASA .mat）
2. 导入电池数据文件夹（或直接使用内置 `dataset/` 目录）
3. 选择模型（RNN / GRU / LSTM / XGBoost / RF）
4. 调整参数（可选），点击"启动评估"
5. 查看右侧面板评估结果、置信区间、失效循环预测
6. 导出报告（Excel + JSON + 图表）

## 技术方案

### 容量提取

采用**安时积分法**从放电阶段提取每个循环的放电容量：

```
capacity = Σ(current × Δt / 3600)
```

### 异常值清洗

默认保留所有有限的原始容量点，只剔除 `NaN/Inf`，避免先观察完整目标电池轨迹再清洗测试标签。可审计的 **2σ** 清洗函数仅参考当前点之前最多 40 个循环，不读取未来循环；退化膝点采用保守保留策略。

### 容量预测

将容量退化建模为**时间序列监督学习**问题：
- 输入：连续 `window_size`（默认 64）个历史容量点
- 输出：下一个容量点
- 归一化：支持额定容量、MinMax、ZScore；参数只在训练折拟合并随模型元数据保存，预测后按同一 scaler 反归一化
- 防过拟合收缩：在训练电池验证段比较模型与“沿用上一循环容量”基线，学习 `persistence_blend`；`0` 表示完全回退到基线，`1` 表示保留原模型

### 验证策略

- **严格零样本留一法**（Leave-One-Out）：每次留 1 块电池做测试集；该目标电池不产生训练或验证标签，其余电池按时间划分训练和验证区间
- **一步预测与递归预测分离**：常规误差按一步预测统计，RUL 的 RE 只使用从初始窗口开始的递归未来预测
- **多种子重复实验**（默认 5 种子）：主结果取全部预定种子的均值；t 分布 95% 置信区间只描述同一留一折内的随机种子波动，不代表跨电池总体不确定性

### 评估指标

| 指标 | 全称 | 说明 |
|------|------|------|
| RMSE | Root Mean Square Error | 均方根误差（Ah），越小越准 |
| MAE | Mean Absolute Error | 平均绝对误差 |
| R² | Coefficient of Determination | 决定系数，越接近 1 越好 |
| Pearson | Pearson Correlation | 预测与真实值的线性相关性 |
| RE | Relative Error | 寿命终止点预测误差，衡量"何时报废"的准确度 |

## 数据说明

### CALCE 数据集

来源于马里兰大学 CALCE 电池研究中心，CS2 批次锂离子电池循环充放电数据。每块电池包含约 25-28 个 Excel 文件，每个文件记录一次完整的充放电循环。

文件需包含列：`Cycle_Index`、`Step_Index`、`Test_Time(s)`、`Voltage(V)`、`Current(A)`

### NASA 数据集

标准 NASA PCoE 数据集（B0005/B0006/B0018 等），MATLAB .mat 格式。

## 许可证

项目代码采用 [MIT License](LICENSE)。CALCE 数据集不包含在该代码许可证的授权范围内，其版权及使用条件归马里兰大学 CALCE 电池研究中心所有。

## 参考资料

- Chen, D., Hong, W., & Zhou, X. (2022). "Transformer network for remaining useful life prediction of lithium-ion batteries." *IEEE Access*, 10, 19621-19628. 参考开源实现：[XiuzeZhou/RUL](https://github.com/XiuzeZhou/RUL)（[CALCE 基线实现](https://github.com/XiuzeZhou/CALCE)；经核查，原仓库未附带 `LICENSE` 许可证文件，本研究/工程对齐实现以科研复现目的引用其论文与仓库地址并保留原作者署名声明，禁止用于未授权的商业再分发）。
- Tian, J., et al. (2021). "Deep learning framework for lithium-ion battery state of health estimation." *Energy*, 234, 121274.
- Lin, M., et al. (2022). "State of health estimation of lithium-ion batteries based on the CC-CV charging curve and LSTM." *Energy Reports*, 8, 500-510.
