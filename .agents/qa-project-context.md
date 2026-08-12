# Battery SOH Assessment System QA Project Context

## Product

- 产品：电池 SOH 评估系统，本地 PyQt6 桌面应用。
- 目标：导入 CALCE 或 NASA 电池循环数据，以 RNN、GRU、LSTM、XGBoost、RF 进行跨电池 SOH 与 RUL 评估、模型保存加载、TCP 实时预测和报告导出。
- 关键用户流程：导入电池数据并完成校验；选择模型和参数并启动评估；查看单指标或全部指标；比较实测与预测曲线并全屏查看；导出配置、表格和图表；保存并重新加载模型后批量预测；加载模型后启动 TCP 实时预测；安全停止训练或关闭窗口。
- 发布节奏、外部生产地址及合规要求：仓库未记录；当前形态为本地研究与学习工具。

## Tech Stack

- Python 3.10.20。
- 桌面界面：PyQt6 6.11.0。
- 模型与数据：PyTorch 2.13.0+cu130（CPU/CI 锁为 2.13.0）、scikit-learn 1.7.2、XGBoost 3.0.2、pandas 2.3.3、NumPy 1.26.4、Matplotlib 3.10.9。
- 数据格式：CALCE CSV 或 XLSX、NASA MAT。
- 运行平台：当前验证环境为 Windows CPU 或 CUDA；项目声明兼容 Windows、macOS 和 Linux。

## Test Stack

- 测试框架：Python 标准库 unittest。
- 测试目录：tests。
- 当前基线：118 项 unittest；2026-08-12 在项目解释器中完成阶段 4 回归。
- 集成与端到端：已有真实离屏窗口状态测试，以及五模型小样本训练、保存、加载、预测覆盖；TCP 自动化按用户要求暂不补充。
- 覆盖率工具：Coverage.py 7.15.2；全仓防回退基线 59%，阶段 4 核心语义/快照/配置模块门禁 85%（当前实测 90%）。

## CI/CD

- GitHub Actions：`.github/workflows/quality.yml`，Windows 与 Linux、Python 3.10。
- 门禁：compileall、Ruff、Bandit、pip-audit、unittest、全仓覆盖率基线和阶段 4 核心模块 85% 覆盖率。
- 本地阶段 4 门禁另包含 `pip check`、RTX 4050 CUDA 张量运算和五模型保存/加载/预测 smoke test。

## Environments

- 开发与验证：Windows 11，pytorch Conda 解释器，NVIDIA RTX 4050 Laptop GPU，驱动 596.49，CUDA 13.0。
- CPU 是基础必测环境；CUDA 是独立兼容性环境，不阻塞 CPU 基础门禁。
- Staging、Production、托管服务和外部测试地址：仓库未配置。
- 测试数据应使用内存合成序列和最小黄金文件，不访问外部网络。

## Quality Goals

- 每个 P1 缺陷先有能正确失败的自动化测试，再做最小修复。
- 每阶段结束时 unittest 全量通过，Python 源码完整编译，pip check 无损坏依赖。
- 所有 P1 项最终具备自动化回归覆盖；核心算法与安全模块目标覆盖率不低于 85%。
- 单元测试目标少于 3 分钟；完整本地回归目标少于 15 分钟；不接受已知不稳定测试作为绿色门禁。
- 测试电池标签参与训练、验证、早停、调参或选种子的容忍度为零。

## Risk Areas

| Area | Risk Level | Business Impact | Notes |
|---|---|---|---|
| 评估数据隔离与选模 | Critical | 产生虚高且不可复现的跨电池指标 | 阶段 1 首要测试 |
| 归一化与模型元数据 | Critical | 保存加载、批量预测和 TCP 结果不一致 | 训练数据单独拟合 scaler |
| 配置模型规范化 | Critical | XGBoost 可被错误构建为其他模型 | 不支持模型必须拒绝 |
| 模型反序列化与 TCP 输入 | Critical | 代码执行、网络暴露或服务崩溃 | 阶段 2 处理 |
| 线程停止与报告快照 | High | 崩溃、残留线程或结果混用 | 阶段 3 处理 |
| 宣纸水墨界面与交互回归 | High | 破坏现有可用性与用户功能 | 保留现有 17 项契约测试 |

## Team

- 仓库未记录团队人数、专职 QA、负责人或缺陷跟踪平台。
- 当前修复采用单维护者、无专职 QA 的保守执行模型：代码贡献者负责单元、集成与回归测试；每阶段由用户确认后推进。
- team_maturity: startup。

## Conventions

- 测试集中放在 tests 目录，文件命名为 test_*.py，类和方法使用 unittest 约定。
- 测试遵循 Arrange、Act、Assert；每项测试描述一个可观察行为。
- 优先真实纯函数和内存小数据；只在训练框架、文件系统或 GUI 边界使用最小假对象。
- 生产代码必须在对应失败测试之后修改，并按 RED、GREEN、REFACTOR 留下运行证据。
- 保持中文界面、宣纸水墨主题、按钮反馈、文件夹对话框汉化和图表全屏功能不变。
- 不使用测试集进行训练、早停、调参、选择种子、选择 epoch 或选择树数。

## Current Stage Gate

- 阶段 4 的非 TCP 优化已实现；TCP 缓冲、TCP 2000 步递归频控及此前 TCP 缺陷继续按用户要求跳过。
- 严格零样本 RNN 基准已在 4 块 CALCE 电池、5 个预定种子上重跑；产物为 `benchmark/strict_zero_shot_rnn.json`。
- PyTorch 2.1.0+cu118、torchaudio 2.1.0+cu118、torchvision 0.16.0+cu118 已从验证环境移除；当前仅保留 PyTorch 2.13.0+cu130。
- 阶段 4 完整回归和标签完成后暂停，未经用户确认不进入阶段 5。
