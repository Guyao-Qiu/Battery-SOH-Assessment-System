# Battery SOH Assessment System

> Lithium-ion battery state-of-health assessment and degradation analysis

Language: [中文 README](README.md) · English

> [!IMPORTANT]
> This project is a Research Preview for teaching, research, and offline algorithm validation. The strict zero-shot benchmark shows stable one-step capacity fitting, while recursive RUL extrapolation error on vanilla RNN remains large. Results must not be used directly for BMS safety protection, warranty, retirement, or any other safety-critical decision. TCP real-time ingestion is experimental; do not expose it to untrusted networks.

## Evaluation Protocol (Read First)

This section explains how metrics are produced and which numbers to trust. **Evaluation and deployment share the same fitting implementation** (`core/protocol.py::fit_final`), so reported model behavior matches the exported model.

### Outer loop: leave-one-battery-out (LOBO)

Each target battery forms one fold. It contributes nothing to fitting, scaler fitting, hyperparameter selection, or seed selection, and is evaluated once after the model is frozen. Scalers are fitted on training batteries only.

### Refit on all training windows (no target leakage)

An earlier implementation split every training battery into "first 80% train + last 20% validate". Because the end-of-life knee falls in the last 20%, models never saw end-of-life during training yet were asked to predict when capacity crosses the failure threshold. Now evaluation and deployment share `core/protocol.py::fit_final`, training on **every window of every training battery**.

- The default UI evaluation loop (`core/train.py`) fits directly with the configured hyperparameters (skipping inner CV and α shrinkage, aligned with the original project and `XiuzeZhou/RUL`);
- For rolling-origin protocol evaluation and persistence-blend calibration, `core/protocol.py` also provides inner LOBO cross-validation (`select_hparams`) and multi-step rollout calibration (`choose_blend_by_rollout`), reproducible via `python tools/repro_synthetic.py`.

### Prediction modes and metric semantics (one-step vs. recursive)

**The UI defaults to one-step prediction; RUL / RE use recursive extrapolation; benchmarks report both** (`core/train.py::evaluate_prediction_protocols`):

- **One-step prediction (`prediction_mode='one_step'`, UI default):** feeds observed history up to each step, yielding stable RMSE / MAE / R² / Pearson capacity-fit metrics consistent with the original project and `XiuzeZhou/RUL`. Users may switch `prediction_mode` to `rolling` in configuration;
- **Recursive prediction (`recursive` / `rolling`):** provides only the initial measured window and feeds the model's own predictions back into subsequent windows to measure error accumulation; **RUL and failure relative error (RE) are always computed from recursive future rollout** (`rul_protocol='recursive_future'`), never from one-step predictions;
- **Rolling-origin helper (`core/protocol.py::rolling_origin_eval`):** supports multi-origin recursive evaluation at 40% / 50% / 60% / 70% of battery life for benchmark comparisons and protocol studies.

### Baselines: a model must beat them first

`core/baselines.py` and `ui/result_model.py` list three empirical baselines alongside the model: **persistence** (next cycle = last cycle), **linear extrapolation**, and the **double exponential** `C(k)=a·e^{bk}+c·e^{dk}`.

Skill = `1 − RMSE_model / RMSE_persistence`. Cells below 0.05 show ⚠ and a "model did not beat the persistence baseline" note.

### Persistence blend coefficient α (optional rolling-protocol mechanism)

In the rolling-origin protocol (`core/protocol.py::choose_blend_by_rollout`), α ∈ `[0, 1]` shrinks predictions toward the last observed capacity using **multi-step rollout** error on inner-fold models that never saw the validation battery, avoiding the "fit on one step, use on many" collapse (the default UI path in `core/train.py` fixes `persistence_blend=1.0`).

> In synthetic data (`tools/repro_synthetic.py`), the earlier one-step calibration produced α = `0.000` in 4/4 folds (discarding the model entirely); after switching to multi-step rollout calibration, α lands at 0.72–0.80.

### Metrics and failure semantics

- RMSE / MAE / R² / Pearson guard against short, non-finite, or constant input.
- **Right-censoring is explicit:** `observed` / `observed_censored` / `prediction_censored` / `both_censored` / `observed_initial_failure` / `prediction_initial_failure`. The UI shows `N/A（截尾）` rather than pretending a missing crossing is 0 or −1.
- **RUL** is the number of cycles from the prediction origin to EOL — true remaining life, not the legacy bug "how many cycles for SOH to fall from pct% to a threshold (e.g., historical 80%)".
- **SOH** is always defined as `C / C_rated`.
- **Single source of failure logic** (`core/result_semantics.py`): `core/protocol.py`, `core/evaluate.py`, and `ui/result_model.py` all delegate to it.
- **Optional failure debounce** (`TrainConfig.eol_debounce`, default `1`): setting it to `3` requires 3 consecutive cycles below the threshold while still returning the first crossing index.
- **Chunked 2σ outlier cleaning by default (`outlier_mode='chunked'`):** both `config.json` and `TrainConfig` default to `chunked` (40-cycle bins removing points outside `μ ± 2σ` while protecting persistent degradation knees). `mark` (optional; causal 40-cycle window marking without deletion — also the direct-call signature default in `core/adapters.py` and `core/dataload.py`), `delete` (optional; causal removal), and `off` (optional; `NaN`/`Inf` removal only) are kept as selectable modes, with full audit details stored in `frame.attrs['outlier_audit']`.

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
python tools/check_undefined.py core models ui utils theme_tokens.py battery_soh_app.py  # used-but-never-defined globals
python tools/check_colors.py                                                             # colour literals only in theme_tokens.py
python tools/sync_readme_defaults.py --check                                             # verify README defaults match code/config.json
python -m unittest discover -s tests                                                     # regression tests
```

## Default Parameters & Code Locations

The table below summarizes the active runtime defaults (`config.json`, loaded by the UI on startup) alongside `TrainConfig` class defaults (`utils/config.py`), noting any signature or historical differences:

<!-- DEFAULTS:BEGIN -->
> Auto-generated from `config.json` and `utils/config.py::TrainConfig` via `python tools/sync_readme_defaults.py` (`--check` enforced in CI).

| Parameter | Runtime Default (`config.json` / UI) | `TrainConfig` Default | Notes & Code Location |
|---|---|---|---|
| `rated_capacity` | `1.1` | `1.1` | Rated capacity (Ah) (`config.json`, `utils/config.py`) |
| `threshold_ratio` | `0.7` | `0.8` | Failure threshold ratio (UI loads `0.7` from `config.json`; `TrainConfig` / persistence fallback and historical `5681172` benchmark use `0.8`) (`config.json`, `utils/config.py`, `ui/main_window.py`) |
| `voltage_upper` | `3.8` | `3.8` | Upper voltage for `dq_v` (V) (`config.json`, `utils/config.py`) |
| `voltage_lower` | `3.4` | `3.4` | Lower voltage for `dq_v` (V) (`config.json`, `utils/config.py`) |
| `window_size` | `64` | `64` | Sliding input window length (cycles) (`config.json`, `utils/config.py`) |
| `epochs` | `100` | `100` | Deep-learning training epochs (`config.json`, `utils/config.py`) |
| `hidden_dim` | `64` | `64` | Hidden dimension for RNN / DeTransformer (`config.json`, `utils/config.py`) |
| `mode` | `RNN` | `RNN` | Default evaluation model (`config.json`, `utils/config.py`) |
| `metric` | `all` | `rmse` | Default display metric (`all` in `config.json`; `rmse` on `TrainConfig`) (`config.json`, `utils/config.py`) |
| `device` | `cpu` | `cpu` | Default compute device (`cpu` / `cuda`) (`config.json`, `utils/config.py`) |
| `seed` | `2` | `2` | Base random seed (`config.json`, `utils/config.py`) |
| `n_seeds` | `1` | `5` | Number of random seeds (UI loads `1` from `config.json`; `TrainConfig` defaults to `5`; benchmarks use `5`) (`config.json`, `utils/config.py`) |
| `patience` | `20` | `20` | XGBoost early-stopping rounds (`config.json`, `utils/config.py`) |
| `norm_method` | `rated` | `rated` | Capacity scaling method (`rated` / `minmax` / `zscore`) (`config.json`, `utils/config.py`) |
| `n_estimators` | `100` | `100` | Number of trees (XGBoost / RF) (`config.json`, `utils/config.py`) |
| `learning_rate` | `0.1` | `0.1` | XGBoost learning rate (`config.json`, `utils/config.py`) |
| `max_depth` | `6` | `6` | Maximum tree depth (XGBoost / RF) (`config.json`, `utils/config.py`) |
| `subsample` | `1.0` | `1.0` | XGBoost row subsample ratio (`config.json`, `utils/config.py`) |
| `colsample_bytree` | `1.0` | `1.0` | XGBoost column subsample ratio (`config.json`, `utils/config.py`) |
| `min_samples_leaf` | `1` | `1` | RF minimum samples per leaf (`config.json`, `utils/config.py`) |
| `max_features` | `1.0` | `1.0` | RF max features ratio (`config.json`, `utils/config.py`) |
| `rnn_lr` | `0.001` *(via `TrainConfig`)* | `0.001` | Deep-learning Adam learning rate (`TrainConfig` only) (`utils/config.py`) |
| `rnn_dropout` | `0.1` *(via `TrainConfig`)* | `0.1` | Deep-learning dropout rate (`TrainConfig` only) (`utils/config.py`) |
| `feature_columns` | `['capacity']` | `['capacity']` | Input feature columns (capacity-only autoregression by default) (`config.json`, `utils/config.py`) |
| `eol_debounce` | `1` *(via `TrainConfig`)* | `1` | Consecutive cycles below threshold for EOL confirmation (`TrainConfig` / `core/result_semantics.py`) (`utils/config.py`, `core/result_semantics.py`) |
| `adapter_type` | `CALCE` | `CALCE` | Default data adapter (`CALCE` / `NASA`) (`config.json`, `utils/config.py`) |
| `cc_step` | `2` | `None` | CALCE constant-current charge step index (`config.json`, `utils/config.py`) |
| `cv_step` | `4` | `None` | CALCE constant-voltage charge step index (`config.json`, `utils/config.py`) |
| `discharge_step` | `7` | `None` | CALCE discharge step index (`config.json`, `utils/config.py`) |
| `outlier_mode` | `chunked` | `chunked` | Outlier handling: UI/evaluation runtime passes `chunked` via `TrainConfig` and `ui/worker.py`; direct calls to `adapters.py`/`dataload.py` default to `mark` in function signatures (`config.json`, `utils/config.py`, `ui/worker.py`, `core/adapters.py`) |
| `backbone` | `default` | `default` | Neural backbone (`default` / `Transformer` / `DeTransformer`) (`config.json`, `utils/config.py`, `core/model_factory.py`) |
| `num_layers` | `1` | `1` | Number of recurrent / Transformer layers (`config.json`, `utils/config.py`) |
| `nhead` | `1` | `1` | Number of Transformer attention heads (`config.json`, `utils/config.py`) |
| `transformer_k` | `16` | `16` | DeTransformer univariate channel replication factor K (`config.json`, `utils/config.py`) |
| `alpha` | `0.1` | `0.1` | DeTransformer autoencoder reconstruction loss weight α (`config.json`, `utils/config.py`) |
| `noise_level` | `0.0` | `0.0` | DeTransformer autoencoder input noise level (`config.json`, `utils/config.py`) |
| `weight_decay` | `0.0` | `0.0` | Deep-learning Adam weight decay (`config.json`, `utils/config.py`) |
| `prediction_mode` | `one_step` | `one_step` | UI headline prediction mode: `one_step` (one-step fit metrics + recursive RUL/RE); optional `rolling` (`config.json`, `utils/config.py`, `core/train.py`) |

> **Note on `outlier_mode` runtime resolution**: `config.json` and `TrainConfig` default to `chunked`, and `ui/worker.py` passes `config.outlier_mode` (`chunked`) at runtime. Function signatures in `core/dataload.py` (`mark`), `core/adapters.py::CALCEAdapter` (`mark`), and `core/adapters.py::NASAAdapter` (`mark`) keep `mark` as their direct-call default.
<!-- DEFAULTS:END -->

## Strict Zero-Shot Benchmark

The benchmark uses strict zero-shot leave-one-battery-out evaluation: the target battery is excluded from training, scaling, hyperparameter tuning, and seed selection. Both **one-step prediction** (matching the UI default) and **rolling-origin recursive extrapolation** (at 40% / 50% / 60% / 70% of life, with skill vs. persistence flagged ⚠ when `< 0.05`) are reported alongside full-horizon recursive RUL / RE and explicit censoring states. All preselected seeds are included in every mean.

Re-run via `python scripts/run_strict_benchmark.py --n-seeds 5` (writes `benchmark/results_<short_commit>.json`, rendered below via `python tools/render_benchmark_table.py`).

<!-- BENCH:BEGIN -->
> Source: [`benchmark/results_cbcbfa9.json`](benchmark/results_cbcbfa9.json) · Commit: `cbcbfa9` · Protocol: `strict_zero_shot_leave_one_battery_out` · `threshold_ratio=0.7` · `outlier_mode=chunked`

### Macro Summary (6 Models + 3 Baselines, CALCE `CS2_35`–`CS2_38` LOBO, 5-Seed Mean)

| Model / Baseline | 1-Step RMSE ↓ | 1-Step MAE ↓ | 1-Step R² ↑ | 40% Roll RMSE | 50% Roll RMSE | 60% Roll RMSE | 70% Roll RMSE | Mean Skill ↑ | Rec. RE ↓ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **RNN** | 0.0205 | 0.0152 | 0.9916 | 0.2796 | 0.3115 | 0.3479 | 0.3948 | +0.028 ⚠ | 43.46% |
| **GRU** | 0.0820 | 0.0618 | 0.8700 | 0.2745 | 0.2976 | 0.3316 | 0.3819 | +0.061 | — |
| **LSTM** | 0.1036 | 0.0767 | 0.8040 | 0.2681 | 0.2897 | 0.3223 | 0.3715 | +0.086 | — |
| **XGBoost** | 0.0148 | 0.0084 | 0.9959 | 0.2813 | 0.1942 | 0.1085 | 0.1289 | +0.483 | — |
| **RF** | 0.0139 | 0.0074 | 0.9965 | 0.3428 | 0.3520 | 0.3173 | 0.3169 | +0.033 ⚠ | — |
| **DeTransformer** | 0.0191 | 0.0121 | 0.9931 | 0.1234 | 0.0929 | 0.0662 | 0.0595 | +0.752 | 17.79% |
| Persistence | 0.0132 | 0.0050 | 0.9969 | 0.3478 | 0.3554 | 0.3363 | 0.3329 | +0.000 (base) | — |
| Linear Extrap. | 0.0132 | 0.0049 | 0.9969 | 0.3272 | 0.2339 | 0.1435 | 0.1889 | +0.352 | 24.78% |
| Double Exp. | — | — | — | 0.2822 | 0.2680 | 0.2291 | 0.1634 | +0.312 | — |

### Per-Origin Skill vs. Persistence (`1 − RMSE_model / RMSE_persistence`; `< 0.05` flagged ⚠)

| Model / Baseline | 40% Origin | 50% Origin | 60% Origin | 70% Origin | Macro Skill |
|---|---:|---:|---:|---:|---:|
| **RNN** | +0.199 | +0.127 | -0.031 ⚠ | -0.184 ⚠ | +0.028 ⚠ |
| **GRU** | +0.210 | +0.164 | +0.016 ⚠ | -0.145 ⚠ | +0.061 |
| **LSTM** | +0.229 | +0.187 | +0.044 ⚠ | -0.114 ⚠ | +0.086 |
| **XGBoost** | +0.206 | +0.445 | +0.675 | +0.605 | +0.483 |
| **RF** | +0.016 ⚠ | +0.009 ⚠ | +0.057 | +0.050 ⚠ | +0.033 ⚠ |
| **DeTransformer** | +0.655 | +0.735 | +0.800 | +0.816 | +0.752 |
| Linear Extrap. | +0.054 | +0.343 | +0.571 | +0.438 | +0.352 |
| Double Exp. | +0.193 | +0.237 | +0.311 | +0.509 | +0.312 |

<details>
<summary>Expand per-(model × battery) details (1-step metrics, 40%–70% rolling RMSE/skill, EOL, RE & censoring)</summary>

| Model | Battery | Cycles | 1-Step RMSE | 1-Step MAE | 1-Step R² | 40% RMSE (Skill) | 50% RMSE (Skill) | 60% RMSE (Skill) | 70% RMSE (Skill) | Pred EOL | True EOL | Rec. RE | Status |
|---|---|---:|---:|---:|---:|---|---|---|---|---:|---:|---:|---|
| RNN | CS2_35 | 896 | 0.0205 ± 0.0069 | 0.0146 ± 0.0070 | 0.9900 ± 0.0072 | 0.2479 (+0.225) | 0.2750 (+0.161) | 0.3085 (+0.052) | 0.3519 (-0.142 ⚠) | 449 | 641 | 33.33% ± 0.00% | mixed |
| RNN | CS2_36 | 941 | 0.0222 ± 0.0059 | 0.0167 ± 0.0058 | 0.9926 ± 0.0041 | 0.3412 (+0.164) | 0.3731 (+0.039 ⚠) | 0.4135 (-0.144 ⚠) | 0.4625 (-0.303 ⚠) | N/A（截尾） | 517 | — | prediction_censored |
| RNN | CS2_37 | 1008 | 0.0204 ± 0.0058 | 0.0153 ± 0.0051 | 0.9921 ± 0.0045 | 0.2853 (+0.176) | 0.3181 (+0.127) | 0.3557 (-0.049 ⚠) | 0.4017 (-0.213 ⚠) | 388 | 715 | 50.31% ± 0.00% | mixed |
| RNN | CS2_38 | 1038 | 0.0190 ± 0.0070 | 0.0141 ± 0.0068 | 0.9918 ± 0.0065 | 0.2441 (+0.230) | 0.2799 (+0.180) | 0.3140 (+0.016 ⚠) | 0.3633 (-0.077 ⚠) | 431 | 752 | 46.72% ± 0.00% | mixed |
| GRU | CS2_35 | 896 | 0.0688 ± 0.0226 | 0.0529 ± 0.0185 | 0.8882 ± 0.0633 | 0.2457 (+0.232) | 0.2645 (+0.193) | 0.2939 (+0.097) | 0.3390 (-0.100 ⚠) | N/A（截尾） | 641 | — | prediction_censored |
| GRU | CS2_36 | 941 | 0.1039 ± 0.0255 | 0.0792 ± 0.0196 | 0.8401 ± 0.0725 | 0.3126 (+0.234) | 0.3398 (+0.125) | 0.3794 (-0.050 ⚠) | 0.4363 (-0.229 ⚠) | N/A（截尾） | 517 | — | prediction_censored |
| GRU | CS2_37 | 1008 | 0.0840 ± 0.0236 | 0.0614 ± 0.0178 | 0.8659 ± 0.0676 | 0.2830 (+0.182) | 0.3078 (+0.155) | 0.3430 (-0.012 ⚠) | 0.3950 (-0.193 ⚠) | N/A（截尾） | 715 | — | prediction_censored |
| GRU | CS2_38 | 1038 | 0.0714 ± 0.0230 | 0.0536 ± 0.0179 | 0.8859 ± 0.0638 | 0.2567 (+0.191) | 0.2783 (+0.184) | 0.3099 (+0.029 ⚠) | 0.3574 (-0.059 ⚠) | N/A（截尾） | 752 | — | prediction_censored |
| LSTM | CS2_35 | 896 | 0.0860 ± 0.0109 | 0.0649 ± 0.0121 | 0.8372 ± 0.0394 | 0.2392 (+0.252) | 0.2561 (+0.218) | 0.2839 (+0.128) | 0.3275 (-0.062 ⚠) | N/A（截尾） | 641 | — | prediction_censored |
| LSTM | CS2_36 | 941 | 0.1321 ± 0.0104 | 0.0996 ± 0.0066 | 0.7518 ± 0.0401 | 0.3067 (+0.249) | 0.3327 (+0.143) | 0.3714 (-0.028 ⚠) | 0.4274 (-0.204 ⚠) | N/A（截尾） | 517 | — | prediction_censored |
| LSTM | CS2_37 | 1008 | 0.1068 ± 0.0104 | 0.0764 ± 0.0082 | 0.7950 ± 0.0397 | 0.2764 (+0.202) | 0.2998 (+0.177) | 0.3338 (+0.015 ⚠) | 0.3847 (-0.162 ⚠) | N/A（截尾） | 715 | — | prediction_censored |
| LSTM | CS2_38 | 1038 | 0.0896 ± 0.0111 | 0.0659 ± 0.0111 | 0.8320 ± 0.0398 | 0.2500 (+0.212) | 0.2700 (+0.209) | 0.3001 (+0.060) | 0.3462 (-0.026 ⚠) | N/A（截尾） | 752 | — | prediction_censored |
| XGBoost | CS2_35 | 896 | 0.0161 ± 0.0000 | 0.0093 ± 0.0000 | 0.9944 ± 0.0000 | 0.3038 (+0.050 ⚠) | 0.3328 (-0.016 ⚠) | 0.1948 (+0.402) | 0.2091 (+0.322) | N/A（截尾） | 641 | — | prediction_censored |
| XGBoost | CS2_36 | 941 | 0.0160 ± 0.0000 | 0.0092 ± 0.0000 | 0.9964 ± 0.0000 | 0.3866 (+0.053) | 0.2069 (+0.467) | 0.0739 (+0.796) | 0.0837 (+0.764) | N/A（截尾） | 517 | — | prediction_censored |
| XGBoost | CS2_37 | 1008 | 0.0125 ± 0.0000 | 0.0067 ± 0.0000 | 0.9972 ± 0.0000 | 0.3454 (+0.002 ⚠) | 0.1255 (+0.655) | 0.1129 (+0.667) | 0.1179 (+0.644) | N/A（截尾） | 715 | — | prediction_censored |
| XGBoost | CS2_38 | 1038 | 0.0145 ± 0.0000 | 0.0084 ± 0.0000 | 0.9956 ± 0.0000 | 0.0893 (+0.719) | 0.1116 (+0.673) | 0.0525 (+0.836) | 0.1048 (+0.689) | N/A（截尾） | 752 | — | prediction_censored |
| RF | CS2_35 | 896 | 0.0136 ± 0.0002 | 0.0071 ± 0.0002 | 0.9960 ± 0.0001 | 0.3052 (+0.045 ⚠) | 0.3344 (-0.020 ⚠) | 0.2801 (+0.139) | 0.2773 (+0.100) | N/A（截尾） | 641 | — | prediction_censored |
| RF | CS2_36 | 941 | 0.0164 ± 0.0002 | 0.0089 ± 0.0001 | 0.9962 ± 0.0001 | 0.4080 (+0.001 ⚠) | 0.3858 (+0.006 ⚠) | 0.3397 (+0.060) | 0.3537 (+0.003 ⚠) | N/A（截尾） | 517 | — | prediction_censored |
| RF | CS2_37 | 1008 | 0.0125 ± 0.0001 | 0.0065 ± 0.0001 | 0.9972 ± 0.0000 | 0.3449 (+0.004 ⚠) | 0.3476 (+0.046 ⚠) | 0.3352 (+0.011 ⚠) | 0.3252 (+0.018 ⚠) | N/A（截尾） | 715 | — | prediction_censored |
| RF | CS2_38 | 1038 | 0.0130 ± 0.0001 | 0.0071 ± 0.0001 | 0.9965 ± 0.0001 | 0.3130 (+0.013 ⚠) | 0.3403 (+0.003 ⚠) | 0.3142 (+0.016 ⚠) | 0.3114 (+0.077) | N/A（截尾） | 752 | — | prediction_censored |
| DeTransformer | CS2_35 | 896 | 0.0218 ± 0.0008 | 0.0138 ± 0.0005 | 0.9896 ± 0.0008 | 0.0676 (+0.788) | 0.1637 (+0.500) | 0.0871 (+0.733) | 0.1154 (+0.626) | 686.4 | 641 | 7.88% ± 3.16% | observed |
| DeTransformer | CS2_36 | 941 | 0.0196 ± 0.0006 | 0.0128 ± 0.0006 | 0.9946 ± 0.0003 | 0.2229 (+0.454) | 0.1132 (+0.709) | 0.0444 (+0.877) | 0.0379 (+0.893) | 705.8 | 517 | 41.77% ± 1.36% | observed |
| DeTransformer | CS2_37 | 1008 | 0.0169 ± 0.0007 | 0.0107 ± 0.0006 | 0.9949 ± 0.0004 | 0.0728 (+0.790) | 0.0376 (+0.897) | 0.0564 (+0.833) | 0.0429 (+0.870) | 659.8 | 715 | 8.49% ± 2.46% | observed |
| DeTransformer | CS2_38 | 1038 | 0.0179 ± 0.0004 | 0.0110 ± 0.0004 | 0.9934 ± 0.0003 | 0.1304 (+0.589) | 0.0569 (+0.833) | 0.0771 (+0.758) | 0.0416 (+0.877) | 693 | 752 | 13.01% ± 3.54% | observed |
| Persistence | CS2_35 | 896 | 0.0121 | 0.0046 | 0.9968 | 0.3197 (+0.000 (base)) | 0.3277 (+0.000 (base)) | 0.3254 (+0.000 (base)) | 0.3083 (+0.000 (base)) | N/A（截尾） | 641 | — | prediction_censored |
| Persistence | CS2_36 | 941 | 0.0159 | 0.0060 | 0.9964 | 0.4082 (+0.000 (base)) | 0.3883 (+0.000 (base)) | 0.3615 (+0.000 (base)) | 0.3549 (+0.000 (base)) | N/A（截尾） | 517 | — | prediction_censored |
| Persistence | CS2_37 | 1008 | 0.0132 | 0.0050 | 0.9969 | 0.3462 (+0.000 (base)) | 0.3642 (+0.000 (base)) | 0.3389 (+0.000 (base)) | 0.3311 (+0.000 (base)) | N/A（截尾） | 715 | — | prediction_censored |
| Persistence | CS2_38 | 1038 | 0.0115 | 0.0045 | 0.9972 | 0.3172 (+0.000 (base)) | 0.3412 (+0.000 (base)) | 0.3192 (+0.000 (base)) | 0.3374 (+0.000 (base)) | N/A（截尾） | 752 | — | prediction_censored |
| Linear Extrap. | CS2_35 | 896 | 0.0121 | 0.0044 | 0.9968 | 0.3988 (-0.247 ⚠) | 0.1133 (+0.654) | 0.1978 (+0.392) | 0.0953 (+0.691) | 471 | 641 | 29.51% | observed |
| Linear Extrap. | CS2_36 | 941 | 0.0158 | 0.0059 | 0.9964 | 0.3601 (+0.118) | 0.2024 (+0.479) | 0.1529 (+0.577) | 0.1947 (+0.451) | 603 | 517 | 19.03% | observed |
| Linear Extrap. | CS2_37 | 1008 | 0.0132 | 0.0049 | 0.9969 | 0.2933 (+0.153) | 0.3088 (+0.152) | 0.0871 (+0.743) | 0.1579 (+0.523) | 460 | 715 | 39.23% | observed |
| Linear Extrap. | CS2_38 | 1038 | 0.0115 | 0.0044 | 0.9972 | 0.2565 (+0.191) | 0.3111 (+0.088) | 0.1364 (+0.573) | 0.3078 (+0.088) | 830 | 752 | 11.35% | observed |
| Double Exp. | CS2_35 | 896 | — | — | — | 0.2459 (+0.231) | 0.2993 (+0.087) | 0.3011 (+0.075) | 0.1033 (+0.665) | N/A（截尾） | 641 | — | prediction_censored |
| Double Exp. | CS2_36 | 941 | — | — | — | 0.3515 (+0.139) | 0.1899 (+0.511) | 0.2101 (+0.419) | 0.0410 (+0.884) | N/A（截尾） | 517 | — | prediction_censored |
| Double Exp. | CS2_37 | 1008 | — | — | — | 0.2883 (+0.167) | 0.3057 (+0.161) | 0.1140 (+0.664) | 0.0574 (+0.827) | N/A（截尾） | 715 | — | prediction_censored |
| Double Exp. | CS2_38 | 1038 | — | — | — | 0.2433 (+0.233) | 0.2772 (+0.188) | 0.2913 (+0.087) | 0.4520 (-0.340 ⚠) | N/A（截尾） | 752 | — | prediction_censored |

</details>

Reproducibility metadata & dataset hashes:

- Source commit: `cbcbfa949065a74d284475544bb0d79e22a36f8b`
- Elapsed seconds: 3363.00 s
- Hardware: AMD64 Family 25 Model 117 Stepping 2, AuthenticAMD; GPU: NVIDIA GeForce RTX 4050 Laptop GPU; Driver: 616.64; CUDA: 13.0
- Software: PyQt6 6.11.0; numpy 1.26.4; pandas 2.3.3; matplotlib 3.10.9; torch 2.13.0+cu130; scikit-learn 1.7.2; xgboost 3.0.2; scipy 1.15.3; joblib 1.5.3; openpyxl 3.1.5

| Battery | Cycles | Source Tree SHA-256 | Cleaned Capacity SHA-256 |
|---|---:|---|---|
| CS2_35 | 896 | `dfeda906c01c37161cc569fdc41c11e0aed00f675c32c4a000fa845791d810f8` | `811bf49f66363ca9ca30af570ba87a6dc39bdf9158913780d02274467ee94a85` |
| CS2_36 | 941 | `bee2c8e094f05feed6c53bab3ba930ca9580e436e41431ddd3b17e905a99aa4a` | `4e649c53b89bf545d6a284fb8cce05f0feff8b3e8e5a24e27093cce20a9e83bb` |
| CS2_37 | 1008 | `dacc6cf5cd04e147afac28051917564ab204bce48810919a896e8e85cfb4e5ee` | `c123db2c3db2664e01b2563a419b1e041426867bfbbac84ad1097b0ca1367960` |
| CS2_38 | 1038 | `39ed8e425eb5155835d08e3aadaf588ef4321f57f2d7e5eabb19e1e41f956760` | `8c91320c5a75e1760f5a6d66d631e67615d43cf1cad0a80ddb18d5e24a8fc423` |
<!-- BENCH:END -->

### Honest Takeaways

1. **Who beats persistence:** Under strict zero-shot LOBO evaluation, only **`DeTransformer`** (`+0.752` macro skill) and **`XGBoost`** (`+0.483`) consistently outperform all three empirical baselines (linear extrapolation `+0.352`, double-exponential `+0.312`, persistence `0.000`). `RF` (`+0.033 ⚠`) and vanilla `RNN` (`+0.028 ⚠`) fall below the `0.05` threshold, while `GRU` (`+0.061`) and `LSTM` (`+0.086`) drop behind persistence from the 60%–70% origins onward.
2. **Where recursive rollout becomes usable:** `DeTransformer` already provides strong recursive skill at the 40% origin (`0.1234` RMSE, `+0.655` skill) and improves to `0.0595`–`0.0662` RMSE (`+0.800`–`+0.816` skill) at the **60%–70% origins**, reaching a `17.79%` macro recursive RE. `XGBoost` is competitive from the **60% origin onward** (`+0.605`–`+0.675` skill), though early-origin tree rollouts often saturate and become `prediction_censored`.
3. **What cannot be claimed:** **Strong one-step R² does not imply reliable RUL extrapolation** — persistence itself achieves `0.9969` one-step R² (`0.0132` RMSE), and `RF` (`0.9965` 1-step R²) / `RNN` (`0.9916` 1-step R²) break down under multi-step recursion. Furthermore, these numbers cover only four same-chemistry CALCE cells (and `CS2_36`'s noisy early dip at cycle 517 inflates non-debounced EOL RE), so they cannot justify cross-chemistry generalization or BMS safety deployment.

![Four-Cell Prediction Chart](prediction_chart.png)

<details>
<summary>Historical Baseline (commit <code>5681172</code>, for traceability)</summary>

The table below is the **historical benchmark** generated at source commit `5681172` (historical parameters used `threshold_ratio=0.8` and chunked outlier cleaning across 3,883 CALCE CS2_35–38 cycles; current `config.json` defaults to `threshold_ratio=0.7`). Machine-readable details are preserved in [`benchmark/strict_zero_shot_rnn.json`](benchmark/strict_zero_shot_rnn.json) (`python scripts/run_strict_benchmark.py --legacy-rnn`):

| Battery | Cycles | RMSE ↓ (Ah) | MAE ↓ (Ah) | R² ↑ | Pearson ↑ | Recursive RE ↓ | RE status |
|---------|-------:|------------:|-----------:|-----:|----------:|----------------:|-----------|
| CS2_35 | 896 | 0.0340 | 0.0300 | 0.9737 | 0.9981 | 97.69% | observed |
| CS2_36 | 941 | 0.0381 | 0.0329 | 0.9780 | 0.9984 | 97.53% | observed |
| CS2_37 | 1,008 | 0.0383 | 0.0340 | 0.9720 | 0.9986 | 97.46% | observed |
| CS2_38 | 1,038 | 0.0375 | 0.0331 | 0.9684 | 0.9984 | 97.32% | observed |
| **Macro average** | **970.8** | **0.0370** | **0.0325** | **0.9730** | **0.9984** | **97.50%** | — |

> Note: an earlier `DeTransformer` alignment table used pre-extracted `CALCE.npy` (3,786 cycles; 5-seed rolling RMSE `0.0892 ± 0.0186`, 1-step RMSE `0.0194 ± 0.0014`). The new benchmark above evaluates all 6 models and 3 baselines on the exact same raw `CS2_35`–`CS2_38` dataset (3,883 cycles).

</details>

## Features

- **Six model options across PyTorch & scikit-learn:** **RNN / GRU / LSTM / DeTransformer** (`backbone='DeTransformer'` or `'Transformer'`, denoising autoencoder + Transformer encoder) in PyTorch, plus **XGBoost** and **RF (Random Forest)** in scikit-learn.
- **Multiple data formats:** CALCE `.xlsx`/`.csv` (plus pre-extracted `.npy`) and NASA `.mat`, normalized through adapter interfaces.
- **Strict validation:** leave-one-battery-out evaluation with no target-battery leakage into training, scaling, tuning, or seed selection.
- **One fitting entrypoint for evaluation and deployment:** `core/protocol.py::fit_final` refits on every window of every training battery; `core/protocol.py` also provides rolling-origin evaluation (40%–70%) and α calibration.
- **Dual-protocol reporting:** the UI defaults to one-step fit metrics while **always computing RUL / RE via recursive future rollout** (with optional `rolling` mode); benchmark tables report both one-step and rolling/recursive metrics.
- **Empirical baselines side by side:** persistence, linear extrapolation, and double-exponential, plus a skill score against persistence. Cells below 0.05 are flagged ⚠.
- **Optional multi-feature input:** `capacity` / `dq_v` / `CCCT` / `CVCT` / `resistance` (capacity-only autoregression by default).
- **Layered uncertainty:** within-fold seed variation plus a cross-battery bootstrap interval (n = number of batteries).
- **Sortable result table:** click-to-sort columns, cross-battery summary row, baseline rows, copy / CSV export.
- **Self-explanatory main chart:** prediction start, prediction curves, recursive extrapolation, 10–90% band, failure threshold, true/predicted EOL markers, SOH% secondary axis, and a y-axis focused on the degradation band.
- **Readable tick density:** major ticks fill the visible range on human-friendly 1 / 2 / 2.5 / 5 × 10ⁿ steps, with four minor ticks between them; cycle numbers stay integers and capacity keeps only as many decimals as the step needs.
- **Light and dark themes (dark by default):** paper (light) and ink-night (dark) tokens centralized in `theme_tokens.py`. A button in the top-right corner switches between them (also `Ctrl+T`) and the choice is remembered; charts and the startup splash follow the switch.
- **CJK font bootstrap:** `ui/fonts.py` registers system Chinese fonts explicitly at startup — PyQt6's offscreen platform plugin does not use the system font engine.
- **Model persistence:** PyTorch state-dict artifacts with metadata and hashes; `.joblib` loading requires explicit user confirmation because deserialization may execute code.
- **TCP real-time prediction (experimental):** binds to localhost only by default; optional LAN mode with a generated token handshake; malformed input produces a warning instead of a crash; RUL is a true remaining-life count.
- **Immutable run snapshots & atomic report export:** `core/run_snapshot.py` + `core/report_export.py` export Excel (`.xlsx`), JSON configuration, and PNG charts atomically.

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

1. Select a data source format: CALCE `.xlsx`/`.csv`/`.npy` or NASA `.mat`.
2. Import battery files or a battery-data directory.
3. Select `RNN`, `GRU`, `LSTM`, `XGBoost`, or `RF` (or enable `backbone='DeTransformer'` in config).
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

By default, `config.json` and `TrainConfig` run **`outlier_mode='chunked'`** (40-cycle bins filtering points outside local `μ ± 2σ` while protecting persistent degradation knees, keeping capacity curves smooth and aligned with the reference implementation).

Optional modes remain available:

- **`mark` (optional):** causal 40-cycle window that flags suspicious points without deleting them (preserving real physical capacity regeneration; also the direct-call signature default in `core/adapters.py` / `core/dataload.py`);
- **`delete` (optional):** causal sliding-window removal using at most 40 prior cycles;
- **`off` (optional):** retains all finite capacity points and drops only `NaN`/`Inf`.

Audit details are recorded in `frame.attrs['outlier_audit']`.

### Capacity prediction

The degradation curve is treated as a supervised time-series problem:

- Input: the previous `window_size` capacity points, default 64.
- Output: the next capacity point.
- Scaling: `rated` (default), `minmax`, and `zscore` options. Scalers are fitted only on the training fold and stored with model metadata.
- Anti-overfitting shrinkage: `core/protocol.py::choose_blend_by_rollout` learns `persistence_blend` on multi-step rollout error (`0` = full fallback to persistence, `1` = keep raw model prediction); the default UI path in `core/train.py` uses `persistence_blend=1.0`.

### Validation protocol

- **Strict leave-one-battery-out:** each target battery is held out from training, scaler fitting, and parameter selection.
- **One-step vs. recursive prediction:** both `one_step` and `recursive` protocols are evaluated; the UI defaults to `one_step` fit metrics (`rolling` selectable) while **RUL / RE always use recursive future rollout**.
- **Multiple seeds:** `config.json` defaults to `n_seeds=1` (`TrainConfig` defaults to `5`; UI allows 1–20; benchmarks use `5`), summarized with mean, standard deviation, and within-fold 95% confidence interval.

## Data

### CALCE

The project supports CS2 lithium-ion battery cycling data from the University of Maryland CALCE battery research center. Each battery is represented by multiple Excel files containing charge/discharge cycles (or pre-extracted `CALCE.npy`).

Required columns include `Cycle_Index`, `Step_Index`, `Test_Time(s)`, `Voltage(V)`, and `Current(A)`.

### NASA

The adapter supports standard NASA PCoE MAT structures such as B0005, B0006, and B0018.

## Repository Layout

```text
Battery-SOH-Assessment-System/
├── battery_soh_app.py       # Application entry point, startup splash, crash guard
├── theme_tokens.py          # Single source of truth for paper/ink-night color tokens
├── config.json              # Active runtime defaults loaded on UI startup
├── core/
│   ├── adapters.py          # CALCE / NASA data adapters, CC/CV split, step detection
│   ├── baselines.py         # Empirical baselines (persistence / linear / double-exp)
│   ├── batching.py          # Mini-batch DataLoader & recurrent training helpers
│   ├── cancellation.py      # Cooperative cancellation & XGBoost stop callbacks
│   ├── dataload.py          # Unified data-loading entrypoint
│   ├── evaluate.py          # Metrics, right-censoring semantics, CI & bootstrap
│   ├── model_factory.py     # Unified model creation & fitting (eval + deploy)
│   ├── model_persistence.py # Safe model save/load with SHA-256 sidecar validation
│   ├── prediction.py        # Shared inference & scaling path
│   ├── preprocess.py        # Outlier handling, sliding windows, CapacityScaler/FeatureScaler
│   ├── progress.py          # Shared progress event schema
│   ├── protocol.py          # fit_final, inner LOBO CV, rolling-origin eval & α blend
│   ├── report_export.py     # Snapshot-based atomic report export (Excel/JSON/PNG)
│   ├── result_semantics.py  # Single source of truth for EOL crossing & debounce
│   ├── run_snapshot.py      # Deeply frozen per-run snapshot records
│   ├── stream_protocol.py   # Pure-Python TCP stream parsing, throttling & RUL
│   ├── train.py             # Leave-one-battery-out evaluation loop
│   └── validation.py        # Config validation, resource limits & column normalization
├── models/                  # RNN/GRU/LSTM/DeTransformer, XGBoost, and RF models
├── ui/                      # MainWindow, chart, result table, workers, TCP server, theme
├── utils/                   # Config, paths, crash guard, icon generator, logging
├── tools/                   # Checkers (undefined/colors), screenshot, repro, README sync
├── scripts/                 # All-in-one packager and strict benchmark runner
├── dataset/                 # Included CALCE CS2_35–38 files and CALCE.npy
├── benchmark/               # Reproducible strict benchmark JSON manifest
├── tests/                   # Regression and quality-contract tests
├── requirements*.lock       # Runtime, development, and CUDA locks
└── .github/workflows/       # Windows/Linux quality gates
```

## License and Data Notice

The project code is released under the [MIT License](LICENSE). The CALCE dataset is not covered by this code license; its copyright and usage conditions remain with the University of Maryland CALCE Battery Research Group. Check the dataset terms before redistribution.

## References

- Chen, D., Hong, W., & Zhou, X. (2022). “Transformer network for remaining useful life prediction of lithium-ion batteries.” *IEEE Access*, 10, 19621–19628. Reference implementation: [XiuzeZhou/RUL](https://github.com/XiuzeZhou/RUL) ([CALCE baselines](https://github.com/XiuzeZhou/CALCE); verified that neither repository includes a `LICENSE` file—only the architectural alignment is re-implemented here for research/educational reproducibility with full author attribution retained).
- Tian, J., et al. (2021). “Deep learning framework for lithium-ion battery state of health estimation.” *Energy*, 234, 121274.
- Lin, M., et al. (2022). “State of health estimation of lithium-ion batteries based on the CC-CV charging curve and LSTM.” *Energy Reports*, 8, 500–510.
