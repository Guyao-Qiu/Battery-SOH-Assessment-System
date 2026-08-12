# Battery SOH Assessment System

> 电池健康状态评估系统

基于马里兰大学 CALCE 锂电池充放电数据集，采用 PyQt6 设计 UI 界面，利用 RNN/GRU/LSTM 及 XGBoost、Random Forest 共 5 种模型，构建了该系统，对锂离子电池循环充放电数据进行容量退化趋势预测，计算剩余使用寿命（RUL）。采用留一法（Leave-One-Out）跨电池验证，并提供多种评估指标与 95% 置信区间分析。

> [!IMPORTANT]
> 本项目是面向教学、科研与离线算法验证的 Research Preview。当前严格零样本基准显示一步容量预测较稳定，但递归 RUL 外推误差仍然很大；结果不得直接用于 BMS 安全保护、质保、报废或其他安全关键决策。TCP 实时接入属于实验功能，请勿暴露到不可信网络。

## 严格零样本基准（Benchmark）

本基准使用严格零样本跨电池评估（留一电池验证）：目标电池不参与训练、验证、早停、调参或种子选择。RMSE、MAE、R² 和 Pearson 来自一步预测；RE 来自仅以初始窗口起步、后续只回填模型输出的完全递归 RUL 路径。所有预定种子均计入均值，95% CI 只反映同一留一折内的随机种子波动。

CALCE CS2_35~38 经当前可审计异常值规则清洗后共 3,883 个循环，RNN 五种子结果如下：

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

## 功能特性

- **多模型支持**：RNN / GRU / LSTM（PyTorch 深度学习）+ XGBoost / Random Forest（scikit-learn 集成学习）
- **多数据格式**：支持 CALCE（.xlsx/.csv）和 NASA（.mat）数据集，适配器模式统一异构接口
- **严格零样本留一法验证**：目标电池不参与训练、验证、早停、调参或种子选择，只在模型固定后评估一次
- **预测口径分离**：一步预测使用截至当前点的实测历史；递归未来预测只使用起始窗口，后续将预测值回填，RUL 仅按递归结果计算
- **多种子评估**：多随机种子（默认 5 个）重复实验，计算均值 ± 标准差及 95% 置信区间
- **评估指标**：RMSE、MAE、R²、Pearson 相关系数、RE（寿命终止点预测相对误差）
- **交互式图表**：Matplotlib 预测曲线与实测值对比、失效阈值线、鼠标悬停实时数据提示
- **模型持久化**：PyTorch 以纯 state-dict + 哈希元数据清单安全保存；sklearn（.joblib）加载前必须确认代码执行风险；模型文件与同名 `.meta.json` 清单需一并保留
- **TCP 实时预测**：加载模型后可启动 TCP 服务（端口 8888），接收实时数据在线预测 SOH
- **报告导出**：评估结果导出为 Excel（.xlsx）+ JSON 配置 + 图表 PNG

## 项目结构

```
Battery-SOH-Assessment-System/
├── battery_soh_app.py        # 应用入口（含启动闪屏）
├── requirements.txt          # 依赖清单
├── config.json               # 默认配置
├── core/
│   ├── adapters.py           # 数据适配器（CALCE / NASA）
│   ├── dataload.py           # 数据加载统一接口
│   ├── evaluate.py           # 评估指标（RMSE/MAE/R²/Pearson/RE/置信区间）
│   ├── model_persistence.py  # 模型保存与加载
│   ├── preprocess.py         # 数据预处理（异常值剔除 + 滑动窗口）
│   ├── train.py              # 训练流程（多种子 + 留一法）
│   └── validation.py         # 数据校验与列名标准化
├── models/
│   ├── rnn_model.py          # RNN / GRU / LSTM 网络定义
│   ├── XGBoost.py            # XGBoost 训练与预测
│   └── RF.py                 # Random Forest 训练与预测
├── ui/
│   ├── main_window.py        # 主窗口布局与交互逻辑
│   ├── chart_show.py         # Matplotlib 图表渲染与悬停交互
│   ├── worker.py             # 训练评估工作线程
│   ├── predict_worker.py     # 预测工作线程
│   ├── tcp_server.py         # TCP 数据接入服务
│   ├── tcp_display.py        # TCP 实时数据展示窗口
│   ├── animated_button.py    # 动画按钮组件
│   └── style.py              # 宣纸水墨主题样式
├── utils/
│   ├── config.py             # 配置管理与持久化
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

局部滑动窗口 **2σ 原则**清洗容量序列，分箱剔除离群点。

### 容量预测

将容量退化建模为**时间序列监督学习**问题：
- 输入：连续 `window_size`（默认 64）个历史容量点
- 输出：下一个容量点
- 归一化：支持额定容量、MinMax、ZScore；参数只在训练折拟合并随模型元数据保存，预测后按同一 scaler 反归一化

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

- Tian, J., et al. (2021). "Deep learning framework for lithium-ion battery state of health estimation." *Energy*, 234, 121274.
- Lin, M., et al. (2022). "State of health estimation of lithium-ion batteries based on the CC-CV charging curve and LSTM." *Energy Reports*, 8, 500-510.
