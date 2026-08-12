# SOH 评估系统漏洞与风险修复清单

> 供 Codex 直接读取和执行。审查日期：2026-08-11  
> 项目：Battery-SOH-Assessment-System  
> 当前技术栈：Python 3.10、PyQt6、PyTorch、scikit-learn、XGBoost、pandas、Matplotlib

## 给 Codex 的执行指令

请在当前项目中按本文顺序修复问题。开始前完整阅读本文及相关源文件，并使用项目内测试技能：

- `.agents/skills/qa-project-context/SKILL.md`
- `.agents/skills/test-strategy/SKILL.md`
- `.agents/skills/ai-bug-triage/SKILL.md`
- `.agents/skills/unit-testing/SKILL.md`

必须遵守以下约束：

1. 保持现有用户功能、中文界面、国风宣纸水墨配色、按钮效果、文件夹对话框汉化和图表全屏功能不变。
2. 先添加能复现问题的测试，再修改实现；修复后运行全部回归测试。
3. 不要一次性重写整个项目。按“阶段 1 → 阶段 5”做小范围、可验证修改。
4. 不要用测试集做早停、调参、选种子或选最佳模型。
5. 不要加载不可信的 pickle/joblib/PyTorch 对象。
6. 不得再使用 `QThread.terminate()` 强制结束工作线程。
7. 修改评估方法后，旧 README benchmark 必须标记为旧方法结果，重新运行后才能更新为新基准。
8. 每完成一个阶段，输出：修改文件、已修复编号、测试结果、仍存在的风险和下一阶段建议。
9. 遇到会改变产品行为、评估口径或 TCP 对外访问方式的选择时，先说明影响，再采用本文推荐的安全默认值。

## 完成定义

满足以下条件才可以宣告全部修复完成：

- 所有 P1 项都有自动化回归测试并通过。
- 单元、集成和 UI 测试均通过，Python 源码可以完整编译。
- 测试电池不参与训练、早停、调参、最佳种子或最佳轮次选择。
- 五种模型及三种归一化方式的配置导出、导入和重新运行保持一致。
- TCP 默认只监听本机，恶意或异常输入不会使线程退出或无限占用内存。
- 模型加载采用可信格式和完整元数据校验，CPU/GPU行为一致。
- 停止训练、关闭窗口和停止 TCP 不会使用强制终止线程。
- 报告只包含对应运行快照的数据，不会无提示覆盖旧报告。
- README、启动说明、评估方法和实际代码一致。

## 审查基线

审查时已验证：

- `python -m unittest discover -s tests -v`：17/17 通过。
- `python -m compileall -q battery_soh_app.py core models ui utils`：通过。
- `python -m pip check`：通过。
- 现有 17 项测试均为 UI 源码字符串契约测试，未覆盖训练、指标、模型加载、TCP、线程和导出流程。
- 当前环境未安装 pytest、Bandit、pip-audit、Ruff。
- 最小复现确认：TCP RUL 路径触发 `NameError: initial_capacity is not defined`。
- 最小复现确认：混合数据中的零方差 40 点窗口会被异常值清洗全部删除。
- 最小复现确认：真实值和预测值都未跨越阈值时，RE 返回 `1.0`。

建议优先使用 PyCharm 当前解释器：

```powershell
D:\Anaconda3\envs\pytorch\python.exe -m unittest discover -s tests -v
D:\Anaconda3\envs\pytorch\python.exe -m compileall -q battery_soh_app.py core models ui utils
D:\Anaconda3\envs\pytorch\python.exe -m pip check
```

---

## 阶段 1：修复评估可信度和算法错配

这是最高优先级。完成前不要把当前 benchmark 作为可靠的跨电池泛化结果。

### P1-01 测试集泄漏和乐观选模

- [x] RNN 不再使用被测电池 RMSE 早停或选择最佳 epoch。
- [x] XGBoost 的 `eval_set` 不再使用被测电池。
- [x] Random Forest 不再使用被测电池决定最佳树数。
- [x] 多种子评估不再按测试 RMSE 选择“最佳种子”作为主结果。
- [x] 主结果改为预先约定种子或所有种子的均值；置信区间说明统计对象。

证据：

- `core/train.py:111-154`
- `core/train.py:195-245`
- `models/XGBoost.py:17-28`
- `models/RF.py:31-56`

推荐修复：每个留一折仅从训练电池中划分验证电池或验证时段；被测电池只在模型和超参数确定后评估一次。

验收测试：构造带唯一哨兵值的测试电池，断言训练、早停和选模调用中从未出现该哨兵标签。

### P1-02 当前并非严格的跨电池留一法

- [x] 明确选择并实现一种协议：
  - 推荐默认：严格零样本跨电池评估，目标电池不生成任何训练标签；或
  - 显式命名为“前 N 循环微调”，并与零样本结果分开报告。
- [x] 一步预测和递归未来预测分开计算、分开命名。
- [x] RUL 指标不得用整个测试期的真实历史滚动输入冒充起点预测。

证据：

- `core/preprocess.py:31-39`
- `core/train.py:31-33`
- `README.md:23-30`

验收测试：严格模式下，移除测试电池早期标签不会改变训练模型；一步预测和递归预测使用不同函数与结果字段。

### P1-03 归一化选项无效

- [x] 实现 `rated`、`minmax`、`zscore` 三种真实训练路径。
- [x] MinMax/ZScore 只能在训练数据上拟合，禁止使用测试数据统计量。
- [x] scaler 参数随模型元数据保存和加载。
- [x] TCP、加载模型预测与批量评估使用同一 scaler。

证据：

- `core/preprocess.py:42-50`
- `core/train.py:98-100`
- `ui/main_window.py:936-979`

验收测试：同一数据选择三种归一化方式时，传入模型的张量符合各自公式；保存加载后预测一致。

### P1-04 JSON 导入可能把 XGBoost 变成 LSTM

- [x] 建立唯一的模型枚举/规范化函数。
- [x] 接受 `XGBoost`、`xgboost`、`XGBOOST`，内部统一为 `XGBoost`。
- [x] 不支持的模型必须拒绝并提示，禁止回退到其他算法。
- [x] 修复学习率、`n_seeds`、适配器和工步等配置字段的导入导出不对称。

证据：

- `ui/main_window.py:31-67`
- `ui/main_window.py:869-907`
- `models/rnn_model.py:5-12`

验收测试：五种模型分别执行“导出 → 导入 → 构建配置”，模型类型和全部参数完全一致。

### P1-05 加载模型后的指标路径不完整

- [x] `PredictWorker` 使用与训练相同的 `calc_all_metrics()`。
- [x] MAE、R²、Pearson、RE 和“全部”均可正常显示。
- [x] 平均指标必须取对应指标，不得始终使用 RMSE。

证据：

- `ui/predict_worker.py:97-126`
- `ui/worker.py:98-138`

验收测试：五个单指标和“全部”逐一运行，无 KeyError，平均值与逐电池结果一致。

---

## 阶段 2：修复 TCP 与模型加载安全

> 2026-08-11 用户明确要求跳过 TCP 有关部分。本阶段仅完成 P1-08～P1-10；P1-06、P1-07 保持未修复，不计入本阶段通过范围。

### P1-06 TCP RUL 未定义变量和输入崩溃

- [ ] 修复 `initial_capacity` 未定义问题，明确 RUL 基准使用额定容量还是首个有效容量。
- [ ] `capacity` 只接受有限浮点数，拒绝字符串、布尔值、NaN、Inf、负值和明显超范围值。
- [ ] 单条坏消息只返回错误，不得结束服务线程。
- [ ] `_run_prediction()` 的异常必须可观测并通过 `error_signal` 或结构化响应反馈。

证据：`ui/tcp_server.py:95-174`

验收测试：覆盖正常阈值交叉、无交叉、字符串、null、NaN、Inf、超大值、reset和连续坏消息。

### P1-07 TCP 默认对局域网暴露且没有资源限制

- [ ] 默认监听 `127.0.0.1`，局域网模式必须由用户显式开启。
- [ ] 局域网模式增加访问令牌；敏感场景增加 TLS 或由安全网关代理。
- [ ] 设置最大单行报文、最大缓冲区、最大容量历史和请求频率。
- [ ] 未换行数据超过限制后主动断开连接。
- [ ] 避免每个输入都复制完整历史并执行最多 2000 次同步递归预测。
- [ ] TCP 状态只能在成功 bind 后显示“已启动”，启动失败要恢复按钮状态。

证据：`ui/tcp_server.py:43-125`、`ui/main_window.py:1111-1160`

验收测试：端口冲突、超长报文、慢速发送、连接中断、重复连接和高频输入不会造成无限内存增长或错误运行状态。

### P1-08 不安全模型反序列化

- [x] PyTorch 仅加载 state-dict，使用 `weights_only=True`；旧混合格式默认拒绝并提示先安全迁移。
- [x] 默认不接受 `.pkl`。
- [x] joblib 模型默认拒绝；界面在加载前明确警告可能执行代码，仅在用户确认后放行。
- [x] 校验扩展名、文件大小、元数据 schema、模型类型和文件哈希。
- [x] 后缀、元数据和 SHA-256 清单共同校验，PyTorch 仍由 `weights_only=True` 限制反序列化对象。

证据：`core/model_persistence.py:23-45`

验收测试：损坏模型、缺少键、伪造扩展名、超大文件和不匹配元数据均被安全拒绝，旧状态不受影响。

### P1-09 模型加载状态、设备和元数据不完整

- [x] 在临时变量中完成加载和全部校验，成功后一次性替换当前模型。
- [x] 加载失败后 `loaded_model`、`loaded_metadata` 保持原状态。
- [x] 模型与输入统一迁移到同一 CPU/CUDA 设备，CUDA 不可用时共同回落到 CPU。
- [x] 元数据加入格式版本、模型类型、窗口、额定容量、阈值、scaler、特征 schema、训练参数、库版本、数据哈希和创建时间。
- [x] 增加“卸载模型/切回训练”操作。

证据：

- `core/model_persistence.py:23-43`
- `ui/main_window.py:981-1037`
- `ui/main_window.py:1080-1097`

### P1-10 “全部数据模型”没有使用全部电池

- [x] 验证集仅用于确定最佳 epoch/树数。
- [x] 确定训练长度后，使用所有有效电池重新训练最终导出模型。
- [x] 元数据记录最终训练样本数和电池名称/哈希。

证据：`core/model_persistence.py:48-234`

验收测试：最终拟合调用中包含所有有效电池，验证电池没有被永久排除。

---

## 阶段 3：数据质量、线程与结果完整性

### P1-11 数据校验没有接入主流程

- [x] 导入后或启动前调用统一验证器。
- [x] 校验电压上限大于下限、三个工步不冲突、额定容量和阈值合理。
- [x] 校验每块电池数据长度大于窗口要求，而不是仅检查至少 3 个循环。
- [x] 校验列唯一性、数值有限性、时间单调性、循环顺序、电流方向和容量合理区间。
- [x] 为 CSV/XLSX/MAT 设置文件大小、行列数、sheet数量和结构深度限制。
- [x] NASA `.mat` 使用独立校验器，不能套用 CALCE 表格列检查。

证据：

- `core/validation.py:46-197`
- `ui/main_window.py:981-992`

### P1-12 异常值清洗会删除稳定段并丢失循环编号

- [x] `sigma≈0` 的窗口保留全部有限值。
- [x] 明确边界点是否保留，避免严格不等号误删。
- [x] 保留原始 `Cycle_Index`，不得用 `linspace` 重新编号。
- [x] 输出剔除掩码、数量和原因，便于审计。
- [x] 对电池退化膝点建立保护或提供关闭清洗的选项。
- [x] 修正 CCCT/CVCT 与有效放电循环的对齐关系。

证据：

- `core/preprocess.py:4-18`
- `core/adapters.py:86-179`

### P1-13 强制终止线程和关闭流程不安全

- [x] 删除 `QThread.terminate()`。
- [x] 使用 `request_stop()`、`requestInterruption()`、安全检查点和有限等待。
- [x] 数据读取、epoch、树批次和最终模型训练均检查停止状态。
- [x] 停止期间禁止开始新的训练、加载/保存模型或导出混合状态报告。
- [ ] 主窗口关闭时依次停止训练线程和 TCP 线程；超时要提示而不是假装已经停止。（非 TCP 的训练线程关闭流程已修复；TCP 部分按用户要求跳过）

证据：

- `ui/main_window.py:314-321`
- `ui/main_window.py:1039-1061`
- `ui/worker.py:26-79`

验收测试：分别在加载文件、RNN epoch、RF/XGB训练、最终模型训练和 TCP 预测期间停止或关闭窗口，进程无崩溃、无残留线程、无损坏文件。

### P1-14 跳过电池时结果可能错位

- [x] 训练结果改为以电池名称为键的结构，不再依赖多个列表的相同下标。
- [x] `battery_list` 只记录实际成功加载的数据。
- [x] 被跳过电池应显示原因，不能把后一块电池的预测画到前一块上。

证据：

- `core/adapters.py:215-290`
- `core/train.py:178-246`
- `ui/main_window.py:1409-1432`

### P1-15 报告可能混用参数并静默覆盖旧结果

- [x] 启动时深拷贝路径和配置，保存不可变 `RunSnapshot`。
- [x] 报告从运行快照导出，不从当前 UI 重新读取参数。
- [x] 运行期间冻结会影响结果的导入、删除、参数和模型控件。
- [x] 默认创建带时间戳或运行 ID 的目录。
- [x] 覆盖已有文件前确认；JSON、Excel和图片采用临时文件后原子替换。
- [x] 捕获文件占用、权限不足和磁盘空间错误，显示可执行的恢复建议。

证据：`ui/main_window.py:781-790`、`ui/main_window.py:1203-1280`

---

## 阶段 4：P2 优化清单

### 指标与结果语义

- [x] 无真实阈值交叉或无预测阈值交叉时，RE 返回 N/A/截尾状态，不再统一返回 `1.0`。证据：`core/evaluate.py`、`tests/test_metric_semantics.py`。
- [x] 失效循环使用真实原始循环编号，并区分“实测失效”“模型预测失效”“观测期内未失效”。证据：`core/result_semantics.py`、`ui/main_window.py`、`tests/test_metric_semantics.py`。
- [x] 置信区间明确仅反映随机种子波动，不冒充跨电池总体不确定性。证据：结果详情和 README 均标注“同一留一折内的随机种子波动”。
- [x] README 的 benchmark 在新验证协议下重新运行，记录硬件、数据哈希、依赖版本和完整参数。证据：`benchmark/strict_zero_shot_rnn.json`；RTX 4050 上完成 4 折 × 5 种子严格零样本 RNN 基准，总耗时 246.515 秒。

### 配置和交互

- [x] 修复配置恢复中不存在的 `model_combo`；使用统一模型状态。证据：`ui/main_window.py`、`tests/test_config_roundtrip.py`。
- [x] 配置保存失败不能静默 `pass`，应记录并提示。证据：`utils/config.py`、`tests/test_config_paths_progress.py`。
- [x] 配置、输出和日志路径基于项目目录或用户数据目录，不依赖 PyCharm 当前工作目录。证据：`utils/paths.py`、`tests/test_config_paths_progress.py`。
- [x] 连接并发送真实 `progress_signal`，显示当前阶段、电池、种子、epoch和耗时。证据：`core/progress.py`、`ui/worker.py`、`ui/predict_worker.py`、`tests/test_config_paths_progress.py`。
- [x] 保留现有无障碍焦点、宣纸水墨主题和图表全屏交互。证据：`tests/test_ui_design_contract.py` 全部通过。

### 性能与资源

- [x] CALCE Excel 排序和正式提取不要重复完整读取，可缓存 DataFrame或只读日期列。证据：`core/adapters.py`、`tests/test_resource_efficiency.py`；真实 CALCE Excel 数据工作表回归通过，每个文件只完整读取一次。
- [x] 大数据训练使用 DataLoader/小批量，避免把全部样本一次搬入 GPU。证据：`core/batching.py`、`tests/test_resource_efficiency.py`，批次上限 64。
- [ ] TCP 只保留窗口所需历史和独立循环计数，避免每次复制全部缓冲区。（用户明确要求跳过 TCP 有关部分，未修改）
- [ ] 递归 RUL 预测加入批次、缓存或频率控制，不必每个容量点都重新预测 2000 步。（`2000` 步路径仅位于 TCP 实时预测，按用户要求跳过；离线评估不使用该循环）

### 日志、依赖和工程卫生

- [x] 不可信文件名、异常和网络内容使用纯文本插入，不能直接 `insertHtml()`。证据：`ui/main_window.py`、`tests/test_safe_logging.py`。
- [x] 用户弹窗不显示完整 traceback；完整堆栈只写入本地日志。证据：`battery_soh_app.py`、评估/预测 worker、`tests/test_safe_logging.py`。
- [x] 使用锁文件固定经过验证的依赖组合，并加入哈希或可重复环境文件。证据：`requirements.lock`、`requirements-cuda.lock`、`requirements-dev.lock`；PyTorch 2.13.0+cu130 在 RTX 4050 上完成 CUDA 运算验证。
- [x] CI 加入 Ruff、Bandit、pip-audit、测试和覆盖率门禁。证据：`.github/workflows/quality.yml`；全仓覆盖率基线 59%，阶段 4 核心模块覆盖率 90%。
- [x] 清理分发包中的 `.idea`、`__pycache__` 和运行输出。证据：`.gitignore` 和 `git ls-files` 验证这些路径均未进入 Git 分发内容；本地忽略的运行文件不做破坏性删除。
- [x] README 将“Quantum Lab 暗色主题”更新为当前宣纸水墨主题，并补充正式许可证文件。证据：`README.md`、MIT `LICENSE`、`tests/test_engineering_hygiene.py`。

---

## 阶段 5：必须补充的自动化测试

### 单元测试

- [x] 严格留一法数据隔离和训练/验证/测试边界。
- [x] `drop_outlier()`：常数窗口、边界值、NaN/Inf、真实退化膝点。
- [x] `relative_error()`：正常交叉、无交叉、多次交叉、初始失效、截尾数据。
- [x] 五种指标：空序列、短序列、常数序列和非法数值。
- [x] 三种 scaler 的 fit/transform/inverse_transform 和序列化。
- [x] 五种模型名称与全部配置字段的 round-trip。

### 数据集成测试

- [x] CALCE 最小黄金 Excel/CSV 样本。
- [x] NASA 最小黄金 MAT 样本。
- [x] 损坏文件、缺列、重复列、错误工步、时间倒序、超大文件。
- [x] 文件夹中混合有效文件、无效文件和空目录。
- [x] 短电池被跳过后结果仍与正确电池名称对应。

### 模型测试

- [x] 五种模型最小数据 smoke test。
- [x] 保存—加载—预测一致性。
- [x] 缺失/损坏/版本不兼容元数据。
- [x] CPU保存、CPU加载、GPU加载和无 GPU 回退。
- [x] 最终模型训练包含全部有效电池。
- [x] 不可信或伪造模型被安全拒绝。

### TCP 测试（用户明确要求跳过，未执行）

- [ ] 本机默认绑定和显式局域网模式。
- [ ] 正常消息、reset、断线重连、端口冲突。
- [ ] 畸形 JSON、非法 UTF-8、字符串、NaN、Inf、负值、超长行。
- [ ] 缓冲区和请求频率上限。
- [ ] 80% 阈值交叉后的 SOH/RUL 结果。
- [ ] 停止和关闭时套接字、线程及时退出。

### PyQt 集成与端到端测试

- [x] 实际创建窗口和控件，不只搜索源码字符串。
- [x] 导入数据 → 选择模型 → 训练 → 查看结果 → 导出报告。
- [x] 加载模型 → 选择任意指标 → 批量预测。
- [ ] 加载模型 → TCP 接入 → 全屏图表 → 安全断开。（用户明确要求跳过，未执行）
- [x] 训练中停止、关闭窗口、文件被占用和错误恢复。
- [x] 键盘导航、焦点可见、缩放字体和高 DPI。

## 推荐 CI 门禁

最低建议：

```powershell
python -m compileall -q battery_soh_app.py core models ui utils
python -m unittest discover -s tests -v
python -m pip check
ruff check .
bandit -r core models ui utils battery_soh_app.py
pip-audit -r requirements.txt
```

建议测试矩阵：

- Python 3.10、3.11、3.12。
- Windows CPU 必测；Linux CPU 可作为兼容性测试。
- CUDA 测试单独运行，不阻塞纯 CPU 基础门禁。
- 核心算法与安全模块目标覆盖率不低于 85%。

## 修复记录

Codex 每完成一项，在此更新状态并记录验证证据：

| 编号 | 状态 | 修改文件 | 新增测试 | 验证结果 | 备注 |
|---|---|---|---|---|---|
| P1-01 | 已修复 | `core/preprocess.py`、`core/train.py`、`models/XGBoost.py`、`models/RF.py` | `tests/test_evaluation_protocol.py` | 目标哨兵隔离、多种子均值、独立验证集通过 | CI 仅表示同一留一折的随机种子波动 |
| P1-02 | 已修复 | `core/preprocess.py`、`core/train.py`、`ui/main_window.py`、`README.md` | `tests/test_evaluation_protocol.py`、`tests/test_benchmark_manifest.py` | 严格零样本、一步/递归分离、递归失效循环与 4 折 × 5 种子实测基准通过 | 新基准已发布至 `benchmark/strict_zero_shot_rnn.json` |
| P1-03 | 已修复 | `core/preprocess.py`、`core/prediction.py`、`core/train.py`、`core/model_persistence.py`、`ui/predict_worker.py`、`ui/tcp_server.py` | `tests/test_scaling.py` | 三种 scaler、训练集拟合、元数据往返、共享预测路径通过 | 兼容无 scaler 的旧树模型原始输入契约 |
| P1-04 | 已修复 | `utils/config.py`、`models/rnn_model.py`、`ui/main_window.py` | `tests/test_config_roundtrip.py` | 五模型全部配置字段 round-trip 与真实窗口重建通过 | 非法模型直接拒绝，不回退 |
| P1-05 | 已修复 | `ui/predict_worker.py` | `tests/test_predict_worker_metrics.py` | 五个单指标和“全部”均通过，平均值按所选指标计算 | RE 使用递归未来预测 |
| P1-06 | 已跳过（未修复） |  |  | 未执行 | 用户明确要求跳过 TCP 有关部分 |
| P1-07 | 已跳过（未修复） |  |  | 未执行 | 用户明确要求跳过 TCP 有关部分 |
| P1-08 | 已修复 | `core/model_persistence.py`、`ui/main_window.py` | `tests/test_model_loading_security.py`、`tests/test_model_artifact_smoke.py` | 破损、缺键、伪后缀、超大、元数据错配、默认拒绝 pickle/joblib 与五模型往返通过 | joblib 仅在用户明确确认后加载；旧 PyTorch 混合格式默认拒绝 |
| P1-09 | 已修复 | `core/model_persistence.py`、`core/prediction.py`、`ui/main_window.py` | `tests/test_model_session.py`、`tests/test_model_artifact_smoke.py` | 原子替换、失败保留旧状态、CPU 回落、卸载切回训练与完整元数据通过 | CUDA 硬件兼容性仍按独立门禁执行 |
| P1-10 | 已修复 | `core/model_persistence.py` | `tests/test_final_model_training.py`、`tests/test_model_artifact_smoke.py` | RNN/XGBoost/RF 最终拟合均包含全部有效电池；五模型真实小样本链路通过 | 验证集只选择 epoch/树数，最终 scaler 也在全量训练数据上重拟合 |
| P1-11 | 已修复 | `core/validation.py`、`ui/main_window.py` | `tests/test_data_validation.py` | 配置、CALCE/NASA结构、逐电池窗口长度及资源上限校验通过 | 启动评估前统一拦截 |
| P1-12 | 已修复 | `core/preprocess.py`、`core/adapters.py` | `tests/test_outlier_audit.py` | 稳定段、边界、非有限值、膝点、原始循环编号和充电特征对齐测试通过 | 清洗结果附带可审计掩码和原因 |
| P1-13 | 部分修复（TCP跳过） | `core/cancellation.py`、`core/train.py`、`core/model_persistence.py`、`models/`、`ui/worker.py`、`ui/predict_worker.py`、`ui/main_window.py` | `tests/test_cooperative_stop.py` | 文件加载、RNN、RF/XGB、最终训练与窗口关闭的非 TCP 停止流程通过 | TCP 停止与关闭流程按用户要求未修改 |
| P1-14 | 已修复 | `core/adapters.py`、`core/train.py`、`ui/worker.py`、`ui/predict_worker.py`、`ui/main_window.py`、`ui/chart_show.py` | `tests/test_named_results.py` | 无效/短电池跳过后，加载、预测、详情与图表均按电池名称对应 | 重复电池名称会记录跳过原因 |
| P1-15 | 已修复 | `core/run_snapshot.py`、`core/report_export.py`、`ui/main_window.py`、`ui/worker.py`、`ui/predict_worker.py` | `tests/test_run_snapshot_export.py`、`tests/test_cooperative_stop.py` | 不可变快照、运行期控件冻结、运行 ID 目录、覆盖确认、原子导出与错误恢复测试通过 | 报告不再读取导出时的实时 UI 参数 |
| P2-阶段4 | 已完成（TCP 项跳过） | `core/`、`ui/`、`utils/`、`README.md`、依赖锁和 CI | `tests/test_metric_semantics.py`、`tests/test_config_paths_progress.py`、`tests/test_resource_efficiency.py`、`tests/test_safe_logging.py`、`tests/test_engineering_hygiene.py`、`tests/test_benchmark_manifest.py` | 118 项回归目标、Ruff、Bandit、pip-audit、两级覆盖率和 CUDA 实测门禁 | TCP 缓冲与 TCP 2000 步频控按用户要求未修改 |
| P2-阶段5 | 已完成（TCP 项跳过） | `core/evaluate.py`、`core/adapters.py`、阶段 5 测试与测试计划 | `tests/test_phase5_edge_cases.py`、`tests/test_phase5_dataset_integration.py`、`tests/test_phase5_ui_workflows.py`、`tests/test_phase5_model_devices.py`、`tests/test_phase5_ui_accessibility.py` | 135 项非 TCP 回归通过；总覆盖率 64%，关键模块门禁 92%；Ruff、Bandit、pip check、pip-audit、CPU/CUDA 与真实 PyQt 流程通过 | 修复退化指标输入和 NASA MAT 校验/加载不一致；所有 TCP 测试按用户要求未执行 |

## 推荐执行顺序摘要

1. 评估泄漏、严格留一法、归一化和配置算法错配。
2. TCP 崩溃、网络暴露和模型反序列化安全。
3. 模型元数据、CPU/GPU一致性和全部数据最终训练。
4. 数据验证、异常值清洗、线程停止和报告快照。
5. 性能、日志、依赖锁定、CI、文档和完整回归测试。
