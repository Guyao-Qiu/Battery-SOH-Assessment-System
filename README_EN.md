# Battery SOH Assessment System

> Lithium-ion battery state-of-health assessment and degradation analysis

Language: [中文 README](README.md) · English

> [!IMPORTANT]
> This project is a Research Preview for teaching, research, and offline algorithm validation. The strict zero-shot benchmark shows stable one-step capacity fitting, but recursive RUL extrapolation error is still very large. Results must not be used directly for BMS safety protection, warranty, retirement, or any other safety-critical decision. TCP real-time ingestion is experimental; do not expose it to untrusted networks.

## Strict Zero-Shot Benchmark

The benchmark uses strict zero-shot leave-one-battery-out evaluation: the target battery is excluded from training, validation, early stopping, hyperparameter tuning, and seed selection. RMSE, MAE, R², and Pearson are reported for one-step prediction. RE is computed from a fully recursive RUL path that starts from an initial measured window and feeds predictions back into the model. All preselected seeds are included in the mean; the 95% CI describes random-seed variation within the same fold, not population-wide uncertainty across batteries.

After the current auditable outlier rules, CALCE CS2_35–38 contain 3,883 cycles in total. The five-seed RNN results are:

| Battery | Cycles | RMSE ↓ (Ah) | MAE ↓ (Ah) | R² ↑ | Pearson ↑ | Recursive RE ↓ | RE status |
|---------|-------:|------------:|-----------:|-----:|----------:|----------------:|-----------|
| CS2_35 | 896 | 0.0340 | 0.0300 | 0.9737 | 0.9981 | 97.69% | observed |
| CS2_36 | 941 | 0.0381 | 0.0329 | 0.9780 | 0.9984 | 97.53% | observed |
| CS2_37 | 1,008 | 0.0383 | 0.0340 | 0.9720 | 0.9986 | 97.46% | observed |
| CS2_38 | 1,038 | 0.0375 | 0.0331 | 0.9684 | 0.9984 | 97.32% | observed |
| **Macro average** | **970.8** | **0.0370** | **0.0325** | **0.9730** | **0.9984** | **97.50%** | — |

These results indicate that one-step capacity fitting is relatively stable, while the current RNN is not reliable for fully recursive lifetime extrapolation. One-step metrics must not be substituted for an RUL conclusion. Per-seed confidence intervals, best epochs, full parameters, and dataset hashes are available in [`benchmark/strict_zero_shot_rnn.json`](benchmark/strict_zero_shot_rnn.json). Re-run the benchmark with `python scripts/run_strict_benchmark.py`.

## Features

- **Five model families:** RNN / GRU / LSTM with PyTorch, plus XGBoost and Random Forest with scikit-learn.
- **Multiple data formats:** CALCE `.xlsx`/`.csv` and NASA `.mat`, normalized through adapter interfaces.
- **Strict validation:** leave-one-battery-out evaluation with no target-battery leakage into training, validation, tuning, or seed selection.
- **Separated prediction protocols:** one-step prediction uses measured history; recursive future prediction uses only the initial window and feeds predictions back for RUL.
- **Multi-seed evaluation:** configurable repeated runs with mean, standard deviation, and 95% confidence intervals.
- **Metrics:** RMSE, MAE, R², Pearson correlation, and RE (relative error at the predicted end-of-life point).
- **Interactive charts:** measured and predicted capacity curves, failure threshold, and hover data inspection.
- **Model persistence:** PyTorch state-dict artifacts with metadata and hashes; `.joblib` loading requires explicit user confirmation because deserialization may execute code.
- **TCP real-time prediction:** experimental port-8888 service for online SOH prediction after a model is loaded.
- **Report export:** Excel (`.xlsx`), JSON configuration, and PNG charts.

## Quick Start

### Requirements

- Python 3.10+
- Windows, macOS, or Linux
- NVIDIA GPU is optional; it accelerates deep-learning models when available.

### Install

```bash
git clone https://github.com/Guyao-Qiu/Battery-SOH-Assessment-System.git
cd Battery-SOH-Assessment-System
python -m pip install -r requirements.txt
```

The runtime dependencies are pinned in `requirements.lock`; development and quality-gate tools are pinned in `requirements-dev.lock`. The locks target Python 3.10.

For a verified Windows + NVIDIA CUDA 13.0 environment:

```bash
python -m pip install -r requirements-cuda.lock
```

The CUDA lock was validated on an RTX 4050 Laptop GPU with driver 596.49 and `torch 2.13.0+cu130`. The regular lock keeps the PyPI CPU build `torch 2.13.0` for CPU environments and CI.

### Run

```bash
python battery_soh_app.py
```

Basic workflow:

1. Select a data source format: CALCE `.xlsx`/`.csv` or NASA `.mat`.
2. Import battery files or a battery-data directory.
3. Select RNN, GRU, LSTM, XGBoost, or Random Forest.
4. Adjust parameters if needed and click **Start Evaluation**.
5. Inspect metrics, confidence intervals, failure-cycle predictions, and charts.
6. Export the Excel report, JSON snapshot, and PNG chart.

## Technical Overview

### Capacity extraction

Discharge capacity is extracted with the ampere-hour integration method:

```text
capacity = Σ(current × Δt / 3600)
```

### Outlier handling

Capacity sequences are cleaned with an auditable local sliding-window 2σ rule while preserving cycle alignment and stable segments.

### Capacity prediction

The degradation curve is treated as a supervised time-series problem:

- Input: the previous `window_size` capacity points, default 64.
- Output: the next capacity point.
- Scaling: rated-capacity, MinMax, and ZScore options. Scalers are fitted only on the training fold and stored with model metadata.

### Validation protocol

- **Strict leave-one-battery-out:** each target battery is held out from training and validation.
- **One-step vs. recursive prediction:** standard error metrics use one-step predictions; RUL RE uses recursive future prediction from the initial window.
- **Multiple seeds:** the default five seeds are repeated and summarized with mean, standard deviation, and a within-fold 95% confidence interval.

## Data

### CALCE

The project supports CS2 lithium-ion battery cycling data from the University of Maryland CALCE battery research center. Each battery is represented by multiple Excel files containing charge/discharge cycles.

Required columns include `Cycle_Index`, `Step_Index`, `Test_Time(s)`, `Voltage(V)`, and `Current(A)`.

### NASA

The adapter supports standard NASA PCoE MAT structures such as B0005, B0006, and B0018.

## Repository Layout

```text
Battery-SOH-Assessment-System/
├── battery_soh_app.py       # Application entry point and startup splash
├── core/                     # Adapters, validation, preprocessing, training, evaluation
├── models/                   # RNN-family, XGBoost, and Random Forest models
├── ui/                       # Main window, charts, workers, TCP display, theme
├── utils/                    # Configuration, paths, logging, icons
├── dataset/                  # Included sample data and preprocessed arrays
├── benchmark/                # Reproducible strict benchmark manifest
├── tests/                    # Regression and quality-contract tests
├── requirements*.lock       # Runtime, development, and CUDA locks
└── .github/workflows/        # Windows/Linux quality gates
```

## License and Data Notice

The project code is released under the [MIT License](LICENSE). The CALCE dataset is not covered by this code license; its copyright and usage conditions remain with the University of Maryland CALCE Battery Research Group. Check the dataset terms before redistribution.

## References

- Tian, J., et al. (2021). “Deep learning framework for lithium-ion battery state of health estimation.” *Energy*, 234, 121274.
- Lin, M., et al. (2022). “State of health estimation of lithium-ion batteries based on the CC-CV charging curve and LSTM.” *Energy Reports*, 8, 500–510.
