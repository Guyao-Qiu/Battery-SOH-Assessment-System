# NASA PCoE 锂离子电池老化数据

本目录保存 NASA Ames Prognostics Center of Excellence (PCoE) 的 18650 锂离子电池老化数据，用于本项目的跨电池 SOH 评估。

## 来源

- 官方说明：https://data.nasa.gov/dataset/li-ion-battery-aging-datasets
- 本次下载镜像：https://github.com/USTC-AI4EEE/RUL-Mamba/tree/main/Data/NASA_Data

NASA 官方页面目前保留数据结构、实验条件和 EOL 定义，但页面未附可下载资源，因此本目录中的原始 MAT 文件取自上述公开镜像。官方页面未指定许可证，使用或再分发前请自行确认适用条件。

## 文件校验

| 文件 | 大小（字节） | SHA-256 |
| --- | ---: | --- |
| `B0005.mat` | 15,956,874 | `0eae4585baf3f200c09fe24c5ab884f1889679fc75206ca1aa19da704104f0b0` |
| `B0006.mat` | 16,028,159 | `fa818ab4db5db8ab21e910b6dd6c3e20d3761bb9672089e1a4de8f96074616c5` |
| `B0007.mat` | 16,049,460 | `d022afa086efaf54ab5b63f05220f5be178c8027e2fa8d68589db0e85a441a3b` |
| `B0018.mat` | 8,502,218 | `d1e6c923a43ea1c9666b3a90bbb521757a067fd60b4d17dbfaa49c50b179da69` |

## 在本系统中训练

1. 运行 `python battery_soh_app.py`。
2. 数据源选择 `NASA (.mat)`。
3. 点击“导入文件”，一次选中本目录的四个 `.mat` 文件。
4. 将额定容量设为 `2.0 Ah`，归一化方式选择“额定容量归一化”。
5. 首次冒烟训练建议使用窗口 `32`、模型 `RF`、多种子数 `1`、设备 `CPU`。
6. 确认流程正常后，将窗口改为 `64`，多种子数改为 `5`，再比较 RF、RNN、GRU、LSTM 和 XGBoost。
7. 点击“启动评估”。系统会依次把一块电池作为完全未参与训练的目标电池，其余电池构成训练集和验证集。

失效阈值比例取 `0.8` 表示常用的 80% SOH 阈值；若要复现 NASA 本实验的 EOL 定义，则取 `0.7`，即容量由 2.0 Ah 衰减到 1.4 Ah。

> 必须通过“导入文件”分别选择四个 MAT 文件。不要只导入本目录；当前 NASA 适配器会把同一文件夹中的 MAT 文件合并成一块名为 `NASA_PCoE` 的电池，无法建立严格的留一电池验证。
