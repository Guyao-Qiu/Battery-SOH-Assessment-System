# Battery SOH Assessment System

> Lithium-ion battery state-of-health assessment and degradation analysis

Language: [中文 README](README.md) · English

> [!IMPORTANT]
> This project is a Research Preview for teaching, research, and offline algorithm validation. The strict zero-shot benchmark shows stable one-step capacity fitting, but recursive RUL extrapolation error is still very large. Results must not be used directly for BMS safety protection, warranty, retirement, or any other safety-critical decision. TCP real-time ingestion is experimental; do not expose it to untrusted networks.

## Strict Zero-Shot Benchmark

The benchmark uses strict zero-shot leave-one-battery-out evaluation: the target battery is excluded from training, validation, early stopping, hyperparameter tuning, and seed selection. RMSE, MAE, R², and Pearson are reported for one-step prediction. RE is computed from a fully recursive RUL path that starts from an initial measured window and feeds predictions back into the model. All preselected seeds are included in the mean; the 95% CI describes random-seed variation within the same fold, not population-wide uncertainty across batteries.

The table below is a historical benchmark generated at source commit `5681172` with the earlier binned outlier cleaning rule (3,883 CALCE CS2_35–38 cycles). The current version adds causal preprocessing and validation-only anti-overfitting shrinkage, so this table is retained for traceability and is not a current post-fix performance claim:

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
- **One protocol for evaluation and deployment:** hyperparameters come from an inner leave-one-battery-out cross-validation, then the final model is refit on every window of every training battery — the metrics describe the model you actually ship.
- **Rolling-origin recursive evaluation:** the headline metrics are true future forecasts at 40%–70% of life; one-step metrics are demoted to diagnostics.
- **Empirical baselines side by side:** persistence, linear extrapolation, and double-exponential, plus a skill score against persistence. Cells below 0.05 are flagged ⚠.
- **Anti-overfitting calibration:** the shrinkage coefficient α is fitted on **multi-step rollout** error using inner-fold models that never saw the validation battery.
- **Optional multi-feature input:** capacity / dq_v / CCCT / CVCT / resistance (capacity-only autoregression by default).
- **Layered uncertainty:** within-fold seed variation plus a cross-battery bootstrap interval (n = number of batteries).
- **Sortable result table:** click-to-sort columns, cross-battery summary row, baseline rows, copy / CSV export.
- **Self-explanatory main chart:** prediction start, recursive forecast, 10–90% band, failure threshold, true/predicted EOL markers, SOH% secondary axis, and a y-axis focused on the degradation band.
- **Readable tick density:** major ticks fill the visible range on human-friendly 1 / 2 / 2.5 / 5 × 10ⁿ steps, with four minor ticks between them; cycle numbers stay integers and capacity keeps only as many decimals as the step needs, so values can be read directly instead of estimated.
- **Light and dark themes (dark by default):** paper (light) and ink-night (dark) tokens centralized in `theme_tokens.py`. A button in the top-right corner switches between them (also `Ctrl+T`) and the choice is remembered; charts and the startup splash follow the switch.
- **CJK font bootstrap:** `ui/fonts.py` registers system Chinese fonts explicitly at startup — PyQt6's offscreen platform plugin does not use the system font engine and would otherwise render every Qt label as tofu boxes (matplotlib resolves its own fonts and is unaffected).
- **Model persistence:** PyTorch state-dict artifacts with metadata and hashes; `.joblib` loading requires explicit user confirmation because deserialization may execute code.
- **TCP real-time prediction (experimental):** binds to localhost only by default; optional LAN mode with a generated token handshake; malformed input produces a warning instead of a crash; RUL is a true remaining-life count.
- **Report export:** Excel (`.xlsx`), JSON configuration, and PNG charts.

## Evaluation Protocol

This section explains how the numbers are produced and which of them you may trust. The evaluation path and the deployment path share one implementation, so the reported metrics describe the final model.

### Outer loop: leave-one-battery-out (LOBO)

Each target battery forms one fold. It contributes nothing to fitting, scaler fitting, hyperparameter selection, early stopping, or seed selection, and is evaluated exactly once after the model is frozen. Scalers are fitted on training batteries only.

### Inner loop: leave-one-battery-out cross-validation

Inside the training batteries, another leave-one-battery-out pass selects hyperparameters using **multi-step rollout** error. The validation subject is a battery the model has never seen, matching the final use case.

> This matters: an earlier implementation split every training battery into "first 80% train + last 20% validate". The end-of-life knee falls in that last 20%, so the model never saw end-of-life yet was asked to predict when the failure threshold is crossed. Now the final fit uses **every window of every training battery**.

### Freeze: refit on all data

After hyperparameters are chosen, the model is refit once on every window of every training battery. Evaluation and deployment call the same `core/protocol.py::fit_final`.

### Prediction origins and the headline metric

The headline metric is recursive forecast error at rolling origins of 40% / 50% / 60% / 70% of life:

- **Recursive** forecasting is the real use case: only measured values before the origin are given, then the model's own output is fed back into the window.
- **One-step** prediction (real history at every step) does not accumulate error and is naturally close to the persistence baseline, so it cannot distinguish good models from bad ones. It is reported as a diagnostic only.

The result table shows RMSE, MAE, skill against persistence, predicted RUL, true RUL, and RUL error, with a dropdown to switch origins.

### Baselines: a model must beat them first

Three empirical baselines are listed alongside the model: **persistence** (next cycle = last cycle), **linear extrapolation**, and the **double exponential** `C(k)=a·e^{bk}+c·e^{dk}`.

Skill = `1 − RMSE_model / RMSE_persistence`. Cells below 0.05 show ⚠ and a "model did not beat the persistence baseline" note.

### Persistence blend coefficient α

α lies in `[0, 1]` and shrinks predictions toward the last observed capacity. It is fitted on **multi-step rollout** error using inner-fold models that never saw the validation battery, avoiding the "fit on one step, use on many" collapse.

> In synthetic data the earlier implementation produced α = `0.000` in 4/4 folds: the model was discarded entirely and the R² of 0.98–0.99 shown in the UI was really the persistence score. After the fix, α on the same data lands at 0.72–0.80.

### Metrics and failure semantics

- RMSE / MAE / R² / Pearson guard against short, non-finite, or constant input.
- **Right-censoring is explicit:** `observed` / `observed_censored` / `prediction_censored` / `both_censored` / `observed_initial_failure` / `prediction_initial_failure`. The UI shows `N/A（截尾）` rather than pretending a missing crossing is 0 or −1.
- **RUL** is the number of cycles from the current origin to EOL — true remaining life, not "how many cycles for SOH to fall from pct% to 80%".
- **SOH** is always defined as `C / C_rated`.

### Uncertainty: n is the number of batteries, not seeds

- The multi-seed 95% CI reflects only **within-fold seed variation**. It is narrow and does **not** represent generalization uncertainty.
- Real uncertainty comes from "what if this were a different battery", so the cross-battery summary reports mean ± std and a **bootstrap interval** with `n = number of batteries`. With only 4–5 batteries the interval is wide — that is the honest answer.

### Reproduce the comparison

```powershell
python tools/repro_synthetic.py
```

This reproduces the four-way "current flow vs proposed flow" comparison on synthetic NASA-style batteries, printing α, per-origin RMSE, and EOL detection. The data is synthetic and validates the *mechanism* only; replace `make_battery` with your real `battery_dict` for a real comparison.

### Limitations

- No real BMS, CAN, HIL, or bench data was involved; software test evidence cannot substitute for safety certification.
- Good one-step capacity fitting does **not** imply reliable recursive RUL extrapolation.
- Extrapolating to an extreme battery absent from the training set remains hard; the protocol fix is not a cure-all.
- In multi-feature recursive forecasting, non-capacity channels are held at their last observed value (a conservative assumption when future operating conditions are unknown).

### Quality gates

```powershell
python tools/check_undefined.py core models ui utils   # used-but-never-defined globals
python tools/check_colors.py                           # colour literals only in theme_tokens.py
python -m unittest discover -s tests                   # regression tests
```

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

All finite raw capacity points are retained by default; only `NaN/Inf` values are removed. This prevents cleaning test labels after observing the complete target trajectory. The optional auditable 2σ filter is causal: it uses at most 40 preceding cycles, never future cycles, and conservatively preserves degradation knees.

### Capacity prediction

The degradation curve is treated as a supervised time-series problem:

- Input: the previous `window_size` capacity points, default 64.
- Output: the next capacity point.
- Scaling: rated-capacity, MinMax, and ZScore options. Scalers are fitted only on the training fold and stored with model metadata.
- Anti-overfitting shrinkage: `persistence_blend` is selected on training-battery validation periods against the last-cycle persistence baseline; `0` means full fallback and `1` keeps the raw model prediction.

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
