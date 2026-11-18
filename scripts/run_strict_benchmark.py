"""Run and record reproducible strict zero-shot CALCE benchmarks."""

from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.baselines import (  # noqa: E402
    double_exp_direct,
    linear_step,
    persistence_step,
)
from core.dataload import load_battery_from_paths  # noqa: E402
from core.evaluate import calc_all_metrics, confidence_interval  # noqa: E402
from core.model_factory import (  # noqa: E402
    config_default_hp,
    hparam_grid,
    make_fit_fn,
)
from core.prediction import predict_capacity_batch  # noqa: E402
from core.preprocess import (  # noqa: E402
    generate_one_step_predictions,
    generate_recursive_predictions,
)
from core.protocol import (  # noqa: E402
    DEFAULT_STARTS,
    fit_final,
    first_cross,
    rolling_origin_eval,
)
from core.train import _fit_scalers, _model_metadata, train  # noqa: E402
from models.rnn_model import Net  # noqa: E402
from utils.config import TrainConfig, setup_seed  # noqa: E402


PROTOCOL = "strict_zero_shot_leave_one_battery_out"
BATTERY_NAMES = ("CS2_35", "CS2_36", "CS2_37", "CS2_38")
ALL_MODELS = ("RNN", "GRU", "LSTM", "XGBoost", "RF", "DeTransformer")
ROLLING_STARTS = DEFAULT_STARTS
DEPENDENCIES = (
    "PyQt6",
    "numpy",
    "pandas",
    "matplotlib",
    "torch",
    "scikit-learn",
    "xgboost",
    "scipy",
    "joblib",
    "openpyxl",
)


def sha256_tree(path: Path) -> str:
    digest = hashlib.sha256()
    for file_path in sorted(item for item in path.rglob("*") if item.is_file()):
        digest.update(file_path.relative_to(ROOT).as_posix().encode("utf-8"))
        digest.update(b"\0")
        with file_path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def sha256_capacity(values) -> str:
    array = np.asarray(values, dtype="<f8")
    return hashlib.sha256(array.tobytes(order="C")).hexdigest()


def git_commit() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def git_short_commit() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True
    ).strip()


def driver_version() -> str:
    try:
        return subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=driver_version",
                "--format=csv,noheader",
            ],
            text=True,
        ).splitlines()[0].strip()
    except (OSError, subprocess.SubprocessError, IndexError):
        return "unavailable"


def finite_or_none(value):
    if value is None:
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def clean_ci(ci):
    return {
        metric: {
            key: (
                [finite_or_none(item) for item in value]
                if key == "values" else finite_or_none(value)
            )
            for key, value in interval.items()
        }
        for metric, interval in ci.items()
    }


def _load_base_config_dict() -> dict:
    config_path = ROOT / "config.json"
    if config_path.is_file():
        return json.loads(config_path.read_text(encoding="utf-8"))
    return {}


def build_model_config(
    model_label: str,
    *,
    base_dict: dict,
    n_seeds: int,
    seed: int | None = None,
    epochs_override: int | None = None,
    device: str = "cuda",
    threshold_ratio: float | None = None,
) -> TrainConfig:
    """Construct TrainConfig for a benchmark model from config.json defaults."""
    raw = dict(base_dict)
    raw["n_seeds"] = int(n_seeds)
    if seed is not None:
        raw["seed"] = int(seed)
    if threshold_ratio is not None:
        raw["threshold_ratio"] = float(threshold_ratio)

    if model_label == "DeTransformer":
        raw.update({
            "mode": "RNN",
            "backbone": "DeTransformer",
            "epochs": 500,
            "hidden_dim": 16,
            "num_layers": 3,
            "nhead": 1,
            "transformer_k": 16,
            "alpha": 0.1,
            "noise_level": 0.0,
            "weight_decay": 0.0,
            "device": device,
        })
    elif model_label in ("RNN", "GRU", "LSTM"):
        raw.update({
            "mode": model_label,
            "backbone": "default",
            "device": device,
        })
    elif model_label in ("XGBoost", "RF"):
        raw.update({
            "mode": model_label,
            "backbone": "default",
            "device": "cpu",
        })
    else:
        raise ValueError(f"不支持的基准模型: {model_label}")

    if epochs_override is not None and model_label in (
        "RNN", "GRU", "LSTM", "DeTransformer"
    ):
        raw["epochs"] = int(epochs_override)

    return TrainConfig.from_dict(raw)


def _summarize_values(values: list[float]) -> dict | None:
    clean = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    if not clean:
        return None
    mean, lo, hi, std = confidence_interval(clean, confidence=0.95)
    return {
        "mean": finite_or_none(mean),
        "std": finite_or_none(std),
        "lower": finite_or_none(lo),
        "upper": finite_or_none(hi),
        "values": [finite_or_none(v) for v in clean],
    }


def _eol_cycle_from_index(index: int | None, offset: int = 0) -> int | None:
    if index is None:
        return None
    return int(offset + int(index) + 1)


def _evaluate_step_baseline(
    sequence: np.ndarray,
    window_size: int,
    step_fn,
    rated_capacity: float,
    threshold_ratio: float,
    battery_name: str,
    persistence_by_start: dict[float, float] | None = None,
) -> dict:
    threshold = rated_capacity * threshold_ratio
    one_truth, one_pred = generate_one_step_predictions(
        sequence, window_size, step_fn)
    one_metrics = calc_all_metrics(
        one_truth, one_pred, rated_capacity, threshold_ratio)
    rec_truth, rec_pred = generate_recursive_predictions(
        sequence, window_size, step_fn)
    rec_metrics = calc_all_metrics(
        rec_truth, rec_pred, rated_capacity, threshold_ratio)

    rolling_rows = rolling_origin_eval(
        sequence, window_size, step_fn, threshold,
        starts=ROLLING_STARTS, battery=battery_name,
    )
    rolling = {}
    skills = []
    for row in rolling_rows:
        frac = float(row["start_frac"])
        key = f"{int(round(frac * 100))}%"
        skill = None
        if persistence_by_start and persistence_by_start.get(frac, 0.0) > 1e-12:
            skill = 1.0 - float(row["rmse"]) / persistence_by_start[frac]
            skills.append(skill)
        rolling[key] = {
            "start_frac": frac,
            "start": int(row["start"]),
            "rmse": finite_or_none(row["rmse"]),
            "mae": finite_or_none(row["mae"]),
            "skill": finite_or_none(skill),
            "true_rul": row["true_rul"],
            "pred_rul": row["pred_rul"],
            "true_eol_cycle": _eol_cycle_from_index(row["true_rul"], row["start"]),
            "pred_eol_cycle": _eol_cycle_from_index(row["pred_rul"], row["start"]),
            "rul_err": row["rul_err"],
            "rul_rel_err": finite_or_none(row["rul_rel_err"]),
            "status": row["status"],
        }

    return {
        "cycles": int(len(sequence)),
        "one_step": {
            "rmse": finite_or_none(one_metrics["rmse"]),
            "mae": finite_or_none(one_metrics["mae"]),
            "r2": finite_or_none(one_metrics["r2"]),
            "pearson": finite_or_none(one_metrics["pearson"]),
        },
        "rolling": rolling,
        "rolling_mean_rmse": finite_or_none(
            float(np.mean([r["rmse"] for r in rolling_rows])) if rolling_rows else None
        ),
        "rolling_mean_skill": finite_or_none(
            float(np.mean(skills)) if skills else None
        ),
        "rul": {
            "true_eol_cycle": _eol_cycle_from_index(
                rec_metrics.get("true_eol_index"), window_size),
            "pred_eol_cycle": _eol_cycle_from_index(
                rec_metrics.get("predicted_eol_index"), window_size),
            "re": finite_or_none(rec_metrics.get("re")),
            "re_ref": finite_or_none(rec_metrics.get("re_ref")),
            "re_status": rec_metrics.get("re_status"),
        },
    }


def _evaluate_double_exp_baseline(
    sequence: np.ndarray,
    window_size: int,
    rated_capacity: float,
    threshold_ratio: float,
    persistence_by_start: dict[float, float],
) -> dict:
    threshold = rated_capacity * threshold_ratio
    rec_truth = sequence[window_size:]
    rec_pred = double_exp_direct(sequence[:window_size], len(rec_truth))
    rec_metrics = calc_all_metrics(
        rec_truth, rec_pred, rated_capacity, threshold_ratio)

    rolling = {}
    rmses = []
    skills = []
    for frac in ROLLING_STARTS:
        start = int(len(sequence) * frac)
        if start < window_size or start >= len(sequence) - 1:
            continue
        truth = sequence[start:]
        pred = double_exp_direct(sequence[:start], len(truth))
        rmse = float(np.sqrt(np.mean((pred - truth) ** 2)))
        mae = float(np.mean(np.abs(pred - truth)))
        true_rul = first_cross(truth, threshold)
        pred_rul = first_cross(pred, threshold)
        status = (
            "true_censored" if true_rul is None
            else ("pred_censored" if pred_rul is None else "ok")
        )
        rul_err = (int(pred_rul - true_rul) if status == "ok" else None)
        rul_rel_err = (
            abs(pred_rul - true_rul) / max(true_rul, 1)
            if status == "ok" else None
        )
        base_rmse = persistence_by_start.get(float(frac))
        skill = (
            1.0 - rmse / base_rmse
            if base_rmse is not None and base_rmse > 1e-12 else None
        )
        rmses.append(rmse)
        if skill is not None:
            skills.append(skill)
        key = f"{int(round(frac * 100))}%"
        rolling[key] = {
            "start_frac": float(frac),
            "start": int(start),
            "rmse": finite_or_none(rmse),
            "mae": finite_or_none(mae),
            "skill": finite_or_none(skill),
            "true_rul": true_rul,
            "pred_rul": pred_rul,
            "true_eol_cycle": _eol_cycle_from_index(true_rul, start),
            "pred_eol_cycle": _eol_cycle_from_index(pred_rul, start),
            "rul_err": rul_err,
            "rul_rel_err": finite_or_none(rul_rel_err),
            "status": status,
        }

    return {
        "cycles": int(len(sequence)),
        "one_step": {
            "rmse": None,
            "mae": None,
            "r2": None,
            "pearson": None,
            "note": "直接多步经验拟合基线，不定义单步滑窗预测",
        },
        "rolling": rolling,
        "rolling_mean_rmse": finite_or_none(float(np.mean(rmses)) if rmses else None),
        "rolling_mean_skill": finite_or_none(float(np.mean(skills)) if skills else None),
        "rul": {
            "true_eol_cycle": _eol_cycle_from_index(
                rec_metrics.get("true_eol_index"), window_size),
            "pred_eol_cycle": _eol_cycle_from_index(
                rec_metrics.get("predicted_eol_index"), window_size),
            "re": finite_or_none(rec_metrics.get("re")),
            "re_ref": finite_or_none(rec_metrics.get("re_ref")),
            "re_status": rec_metrics.get("re_status"),
        },
    }


def evaluate_baselines(
    battery_dict: dict,
    battery_names: tuple[str, ...],
    window_size: int,
    rated_capacity: float,
    threshold_ratio: float,
) -> dict:
    """Compute persistence, linear extrapolation, and double-exponential baselines."""
    baselines: dict[str, dict] = {
        "平推基线": {"batteries": {}},
        "线性外推": {"batteries": {}},
        "双指数": {"batteries": {}},
    }
    persistence_rmse_map: dict[str, dict[float, float]] = {}

    for name in battery_names:
        seq = np.asarray(battery_dict[name]["capacity"], dtype=np.float64).reshape(-1)
        p_res = _evaluate_step_baseline(
            seq, window_size, persistence_step,
            rated_capacity, threshold_ratio, name,
        )
        persistence_rmse_map[name] = {
            row["start_frac"]: float(row["rmse"])
            for row in p_res["rolling"].values()
        }
        # 平推相对自身技能分为 0.0
        for row in p_res["rolling"].values():
            row["skill"] = 0.0
        p_res["rolling_mean_skill"] = 0.0
        baselines["平推基线"]["batteries"][name] = p_res

        baselines["线性外推"]["batteries"][name] = _evaluate_step_baseline(
            seq, window_size, linear_step,
            rated_capacity, threshold_ratio, name,
            persistence_by_start=persistence_rmse_map[name],
        )
        baselines["双指数"]["batteries"][name] = _evaluate_double_exp_baseline(
            seq, window_size, rated_capacity, threshold_ratio,
            persistence_by_start=persistence_rmse_map[name],
        )

    for b_name, entry in baselines.items():
        b_rows = entry["batteries"]
        entry["macro_average"] = {
            "one_step_rmse": finite_or_none(
                _safe_mean([r["one_step"]["rmse"] for r in b_rows.values()])
            ),
            "one_step_mae": finite_or_none(
                _safe_mean([r["one_step"]["mae"] for r in b_rows.values()])
            ),
            "one_step_r2": finite_or_none(
                _safe_mean([r["one_step"]["r2"] for r in b_rows.values()])
            ),
            "rolling_mean_rmse": finite_or_none(
                _safe_mean([r["rolling_mean_rmse"] for r in b_rows.values()])
            ),
            "rolling_mean_skill": finite_or_none(
                _safe_mean([r["rolling_mean_skill"] for r in b_rows.values()])
            ),
            "re": finite_or_none(
                _safe_mean([r["rul"]["re"] for r in b_rows.values()])
            ),
            "rolling_by_start": _macro_rolling_by_start(
                [r["rolling"] for r in b_rows.values()]
            ),
        }
    return baselines, persistence_rmse_map


def _safe_mean(values) -> float | None:
    clean = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    return float(np.mean(clean)) if clean else None


def _macro_rolling_by_start(battery_rolling_dicts: list[dict]) -> dict:
    keys = []
    for d in battery_rolling_dicts:
        for k in d:
            if k not in keys:
                keys.append(k)
    summary = {}
    for k in keys:
        items = [d[k] for d in battery_rolling_dicts if k in d]
        summary[k] = {
            "rmse": finite_or_none(_safe_mean([it.get("rmse") for it in items])),
            "mae": finite_or_none(_safe_mean([it.get("mae") for it in items])),
            "skill": finite_or_none(_safe_mean([it.get("skill") for it in items])),
        }
    return summary


def evaluate_model(
    model_label: str,
    cfg: TrainConfig,
    battery_dict: dict,
    battery_names: tuple[str, ...],
    persistence_rmse_map: dict[str, dict[float, float]],
    *,
    log_callback=print,
) -> dict:
    """Run strict zero-shot LOBO evaluation across all seeds for one model."""
    started_at = time.perf_counter()
    window = int(cfg.window_size)
    rated = float(cfg.rated_capacity)
    threshold_ratio = float(cfg.threshold_ratio)
    threshold = rated * threshold_ratio
    device = str(cfg.device)
    seeds = [int(cfg.seed) + idx for idx in range(int(cfg.n_seeds))]

    batteries_out = {}
    for target_name in battery_names:
        train_names = [n for n in battery_names if n != target_name]
        target_seq = np.asarray(
            battery_dict[target_name]["capacity"], dtype=np.float64
        ).reshape(-1)
        p_by_start = persistence_rmse_map[target_name]

        seed_records = []
        for s_idx, sd in enumerate(seeds):
            setup_seed(sd)
            fit_cfg = replace(cfg, seed=sd)
            scaler, feature_scaler, _ = _fit_scalers(
                fit_cfg, battery_dict, train_names, window,
                ('capacity',), False, rated,
            )
            fit_fn = make_fit_fn(
                fit_cfg,
                name=f"{model_label}/{target_name}",
                net_class=Net,
                feature_scaler=feature_scaler,
            )
            grid = hparam_grid(fit_cfg, fit_cfg.mode)
            hp = config_default_hp(fit_cfg, fit_cfg.mode, grid)
            fitted = fit_final(
                battery_dict, train_names, window, fit_fn, hp, rated,
            )
            metadata = _model_metadata(
                fit_cfg, window, rated, scaler, feature_scaler,
                ('capacity',), False, hp,
            )

            def step_fn(windows, _m=fitted, _meta=metadata, _dev=device):
                return predict_capacity_batch(_m, _meta, windows, device=_dev)

            one_truth, one_pred = generate_one_step_predictions(
                target_seq, window, step_fn)
            one_metrics = calc_all_metrics(
                one_truth, one_pred, rated, threshold_ratio)

            rec_truth, rec_pred = generate_recursive_predictions(
                target_seq, window, step_fn)
            rec_metrics = calc_all_metrics(
                rec_truth, rec_pred, rated, threshold_ratio)

            rolling_rows = rolling_origin_eval(
                target_seq, window, step_fn, threshold,
                starts=ROLLING_STARTS, battery=target_name,
            )
            rolling_map = {}
            for row in rolling_rows:
                frac = float(row["start_frac"])
                key = f"{int(round(frac * 100))}%"
                base_rmse = p_by_start.get(frac)
                skill = (
                    1.0 - float(row["rmse"]) / base_rmse
                    if base_rmse is not None and base_rmse > 1e-12 else None
                )
                rolling_map[key] = {
                    "start_frac": frac,
                    "start": int(row["start"]),
                    "rmse": finite_or_none(row["rmse"]),
                    "mae": finite_or_none(row["mae"]),
                    "skill": finite_or_none(skill),
                    "true_rul": row["true_rul"],
                    "pred_rul": row["pred_rul"],
                    "true_eol_cycle": _eol_cycle_from_index(
                        row["true_rul"], row["start"]),
                    "pred_eol_cycle": _eol_cycle_from_index(
                        row["pred_rul"], row["start"]),
                    "rul_err": row["rul_err"],
                    "rul_rel_err": finite_or_none(row["rul_rel_err"]),
                    "status": row["status"],
                }

            seed_records.append({
                "seed": sd,
                "one_step": {
                    "rmse": finite_or_none(one_metrics["rmse"]),
                    "mae": finite_or_none(one_metrics["mae"]),
                    "r2": finite_or_none(one_metrics["r2"]),
                    "pearson": finite_or_none(one_metrics["pearson"]),
                },
                "recursive_full": {
                    "rmse": finite_or_none(rec_metrics["rmse"]),
                    "mae": finite_or_none(rec_metrics["mae"]),
                    "r2": finite_or_none(rec_metrics["r2"]),
                    "pearson": finite_or_none(rec_metrics["pearson"]),
                    "true_eol_cycle": _eol_cycle_from_index(
                        rec_metrics.get("true_eol_index"), window),
                    "pred_eol_cycle": _eol_cycle_from_index(
                        rec_metrics.get("predicted_eol_index"), window),
                    "re": finite_or_none(rec_metrics.get("re")),
                    "re_ref": finite_or_none(rec_metrics.get("re_ref")),
                    "re_status": rec_metrics.get("re_status"),
                },
                "rolling": rolling_map,
            })
            log_callback(
                f"[{model_label}][{target_name}] seed {s_idx + 1}/{len(seeds)} "
                f"(sd={sd}) 1step_rmse={one_metrics['rmse']:.4f} "
                f"full_re={rec_metrics.get('re')}"
            )

        # Aggregate across all seeds
        one_step_agg = {
            k: _summarize_values([r["one_step"][k] for r in seed_records])
            for k in ("rmse", "mae", "r2", "pearson")
        }
        rec_full_agg = {
            "rmse": _summarize_values(
                [r["recursive_full"]["rmse"] for r in seed_records]),
            "mae": _summarize_values(
                [r["recursive_full"]["mae"] for r in seed_records]),
            "re": _summarize_values(
                [r["recursive_full"]["re"] for r in seed_records]),
            "re_ref": _summarize_values(
                [r["recursive_full"]["re_ref"] for r in seed_records]),
            "true_eol_cycle": seed_records[0]["recursive_full"]["true_eol_cycle"],
            "pred_eol_cycle_mean": finite_or_none(_safe_mean(
                [r["recursive_full"]["pred_eol_cycle"] for r in seed_records]
            )),
            "re_status": _aggregate_status(
                [r["recursive_full"]["re_status"] for r in seed_records]
            ),
        }

        rolling_agg = {}
        start_keys = list(seed_records[0]["rolling"].keys())
        for sk in start_keys:
            rmse_ci = _summarize_values(
                [r["rolling"][sk]["rmse"] for r in seed_records])
            mae_ci = _summarize_values(
                [r["rolling"][sk]["mae"] for r in seed_records])
            skill_ci = _summarize_values(
                [r["rolling"][sk]["skill"] for r in seed_records])
            rul_err_ci = _summarize_values(
                [r["rolling"][sk]["rul_err"] for r in seed_records])
            statuses = [r["rolling"][sk]["status"] for r in seed_records]
            rolling_agg[sk] = {
                "start_frac": seed_records[0]["rolling"][sk]["start_frac"],
                "start": seed_records[0]["rolling"][sk]["start"],
                "rmse": rmse_ci,
                "mae": mae_ci,
                "skill": skill_ci,
                "true_rul": seed_records[0]["rolling"][sk]["true_rul"],
                "pred_rul_mean": finite_or_none(_safe_mean(
                    [r["rolling"][sk]["pred_rul"] for r in seed_records]
                )),
                "true_eol_cycle": seed_records[0]["rolling"][sk]["true_eol_cycle"],
                "pred_eol_cycle_mean": finite_or_none(_safe_mean(
                    [r["rolling"][sk]["pred_eol_cycle"] for r in seed_records]
                )),
                "rul_err": rul_err_ci,
                "status": _aggregate_status(statuses),
                "observed_count": sum(1 for st in statuses if st == "ok"),
                "n_seeds": len(statuses),
            }

        rolling_mean_rmse = finite_or_none(_safe_mean(
            [rolling_agg[sk]["rmse"]["mean"] for sk in start_keys
             if rolling_agg[sk]["rmse"] is not None]
        ))
        rolling_mean_skill = finite_or_none(_safe_mean(
            [rolling_agg[sk]["skill"]["mean"] for sk in start_keys
             if rolling_agg[sk]["skill"] is not None]
        ))

        batteries_out[target_name] = {
            "cycles": int(len(target_seq)),
            "one_step": one_step_agg,
            "rolling": rolling_agg,
            "rolling_mean_rmse": rolling_mean_rmse,
            "rolling_mean_skill": rolling_mean_skill,
            "rul": rec_full_agg,
            "seeds": seed_records,
        }

    # Macro average across batteries
    macro_rolling = {}
    if batteries_out:
        sample_keys = list(next(iter(batteries_out.values()))["rolling"].keys())
        for sk in sample_keys:
            macro_rolling[sk] = {
                "rmse": finite_or_none(_safe_mean([
                    b["rolling"][sk]["rmse"]["mean"]
                    for b in batteries_out.values()
                    if b["rolling"][sk]["rmse"] is not None
                ])),
                "mae": finite_or_none(_safe_mean([
                    b["rolling"][sk]["mae"]["mean"]
                    for b in batteries_out.values()
                    if b["rolling"][sk]["mae"] is not None
                ])),
                "skill": finite_or_none(_safe_mean([
                    b["rolling"][sk]["skill"]["mean"]
                    for b in batteries_out.values()
                    if b["rolling"][sk]["skill"] is not None
                ])),
            }

    macro_avg = {
        "one_step_rmse": finite_or_none(_safe_mean([
            b["one_step"]["rmse"]["mean"] for b in batteries_out.values()
            if b["one_step"]["rmse"] is not None
        ])),
        "one_step_mae": finite_or_none(_safe_mean([
            b["one_step"]["mae"]["mean"] for b in batteries_out.values()
            if b["one_step"]["mae"] is not None
        ])),
        "one_step_r2": finite_or_none(_safe_mean([
            b["one_step"]["r2"]["mean"] for b in batteries_out.values()
            if b["one_step"]["r2"] is not None
        ])),
        "one_step_pearson": finite_or_none(_safe_mean([
            b["one_step"]["pearson"]["mean"] for b in batteries_out.values()
            if b["one_step"]["pearson"] is not None
        ])),
        "rolling_mean_rmse": finite_or_none(_safe_mean([
            b["rolling_mean_rmse"] for b in batteries_out.values()
        ])),
        "rolling_mean_skill": finite_or_none(_safe_mean([
            b["rolling_mean_skill"] for b in batteries_out.values()
        ])),
        "re": finite_or_none(_safe_mean([
            b["rul"]["re"]["mean"] for b in batteries_out.values()
            if b["rul"]["re"] is not None
        ])),
        "re_ref": finite_or_none(_safe_mean([
            b["rul"]["re_ref"]["mean"] for b in batteries_out.values()
            if b["rul"]["re_ref"] is not None
        ])),
        "rolling_by_start": macro_rolling,
    }

    return {
        "elapsed_seconds": time.perf_counter() - started_at,
        "parameters": cfg.to_dict(),
        "seeds": seeds,
        "seed_policy": "all_seed_mean",
        "ci_statistical_object": "同一留一折内的随机种子波动",
        "batteries": batteries_out,
        "macro_average": macro_avg,
    }


def _aggregate_status(statuses: list[str]) -> str:
    unique = set(statuses)
    if len(unique) == 1:
        return next(iter(unique))
    return "mixed"


def run_legacy_rnn() -> int:
    """Backward-compatible single-RNN runner writing strict_zero_shot_rnn.json."""
    if not torch.cuda.is_available():
        raise RuntimeError("严格基准要求可用的 NVIDIA CUDA 环境")

    parameters = TrainConfig(
        rated_capacity=1.1,
        threshold_ratio=0.8,
        voltage_upper=3.8,
        voltage_lower=3.4,
        window_size=64,
        epochs=100,
        hidden_dim=64,
        mode="RNN",
        metric="all",
        device="cuda",
        seed=1,
        n_seeds=5,
        patience=20,
        norm_method="rated",
        adapter_type="CALCE",
        cc_step=2,
        cv_step=4,
        discharge_step=7,
    )
    paths = [ROOT / "dataset" / name for name in BATTERY_NAMES]
    started_at = time.perf_counter()

    def log(message):
        print(message, flush=True)

    print(f"protocol={PROTOCOL}", flush=True)
    print(f"source_commit={git_commit()}", flush=True)
    battery_dict, battery_list = load_battery_from_paths(
        [os.fspath(path) for path in paths],
        log_callback=log,
        voltage_upper=parameters.voltage_upper,
        voltage_lower=parameters.voltage_lower,
        adapter_type=parameters.adapter_type,
        cc_step=parameters.cc_step,
        cv_step=parameters.cv_step,
        discharge_step=parameters.discharge_step,
        outlier_mode=parameters.outlier_mode,
    )
    if battery_list != list(BATTERY_NAMES):
        raise RuntimeError(f"电池加载不完整：{battery_list}")

    results = train(
        parameters,
        battery_dict,
        battery_list,
        log_callback=log,
    )
    if set(results) != set(BATTERY_NAMES):
        raise RuntimeError(f"基准结果不完整：{sorted(results)}")

    elapsed_seconds = time.perf_counter() - started_at
    dataset = {
        name: {
            "cycles": int(len(battery_dict[name]["capacity"])),
            "source_sha256": sha256_tree(ROOT / "dataset" / name),
            "capacity_sha256": sha256_capacity(
                battery_dict[name]["capacity"]),
        }
        for name in BATTERY_NAMES
    }
    benchmark_results = {}
    for name in BATTERY_NAMES:
        detail = results[name]["detail"]
        benchmark_results[name] = {
            "cycles": int(detail["cycles"]),
            "rmse": finite_or_none(detail["rmse"]),
            "mae": finite_or_none(detail["mae"]),
            "r2": finite_or_none(detail["r2"]),
            "pearson": finite_or_none(detail["pearson"]),
            "re": finite_or_none(detail.get("re")),
            "re_status": detail["re_status"],
            "ci": clean_ci(detail["ci"]),
            "ci_statistical_object": detail["ci_statistical_object"],
            "seed_policy": detail["seed_policy"],
            "best_epochs": [
                int(item["best_epoch"])
                for item in detail["run_details"]
                if "best_epoch" in item
            ],
        }

    cpu = platform.processor() or os.environ.get(
        "PROCESSOR_IDENTIFIER", "unknown")
    manifest = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "protocol": PROTOCOL,
        "source_commit": git_commit(),
        "elapsed_seconds": elapsed_seconds,
        "hardware": {
            "os": platform.platform(),
            "python": platform.python_version(),
            "cpu": cpu,
            "gpu": torch.cuda.get_device_name(0),
            "driver": driver_version(),
            "torch_cuda": str(torch.version.cuda),
        },
        "dependencies": {name: version(name) for name in DEPENDENCIES},
        "parameters": parameters.to_dict(),
        "seeds": [parameters.seed + index for index in range(parameters.n_seeds)],
        "dataset": dataset,
        "results": benchmark_results,
    }

    output_path = ROOT / "benchmark" / "strict_zero_shot_rnn.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(".json.tmp")
    temporary_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    os.replace(temporary_path, output_path)
    print(f"benchmark={output_path}", flush=True)
    print(f"elapsed_seconds={elapsed_seconds:.3f}", flush=True)
    return 0


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="运行严格零样本 CALCE 全模型基准")
    parser.add_argument(
        "--models",
        nargs="+",
        default=list(ALL_MODELS),
        choices=list(ALL_MODELS),
        help="要评估的模型列表",
    )
    parser.add_argument("--n-seeds", type=int, default=5, help="随机种子数（默认 5）")
    parser.add_argument("--seed", type=int, default=None, help="起始随机种子（默认取 config.json）")
    parser.add_argument("--epochs", type=int, default=None, help="覆盖深度学习训练轮数（用于冒烟测试）")
    parser.add_argument(
        "--device",
        default="cuda" if torch.cuda.is_available() else "cpu",
        help="深度学习设备（cuda / cpu）",
    )
    parser.add_argument(
        "--threshold-ratio",
        type=float,
        default=None,
        help="失效阈值比例（默认取 config.json）",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="输出 JSON 路径（默认 benchmark/results_<短commit>.json）",
    )
    parser.add_argument(
        "--legacy-rnn",
        action="store_true",
        help="兼容旧版：只跑 RNN 并写 benchmark/strict_zero_shot_rnn.json",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    if args.legacy_rnn:
        return run_legacy_rnn()

    base_dict = _load_base_config_dict()
    base_cfg = TrainConfig.from_dict(base_dict)
    if args.threshold_ratio is not None:
        base_cfg = replace(base_cfg, threshold_ratio=float(args.threshold_ratio))
    if args.seed is not None:
        base_cfg = replace(base_cfg, seed=int(args.seed))

    short_commit = git_short_commit()
    full_commit = git_commit()
    output_path = (
        args.output
        if args.output is not None
        else ROOT / "benchmark" / f"results_{short_commit}.json"
    )

    device = args.device
    if device == "cuda" and not torch.cuda.is_available():
        device = "cpu"

    paths = [ROOT / "dataset" / name for name in BATTERY_NAMES]
    started_at = time.perf_counter()

    def log(message):
        print(message, flush=True)

    print(f"protocol={PROTOCOL}", flush=True)
    print(f"source_commit={full_commit} ({short_commit})", flush=True)
    print(f"models={args.models} n_seeds={args.n_seeds} device={device}", flush=True)

    battery_dict, battery_list = load_battery_from_paths(
        [os.fspath(path) for path in paths],
        log_callback=log,
        voltage_upper=base_cfg.voltage_upper,
        voltage_lower=base_cfg.voltage_lower,
        adapter_type=base_cfg.adapter_type,
        cc_step=base_cfg.cc_step,
        cv_step=base_cfg.cv_step,
        discharge_step=base_cfg.discharge_step,
        outlier_mode=base_cfg.outlier_mode,
    )
    if battery_list != list(BATTERY_NAMES):
        raise RuntimeError(f"电池加载不完整：{battery_list}")

    dataset = {
        name: {
            "cycles": int(len(battery_dict[name]["capacity"])),
            "source_sha256": sha256_tree(ROOT / "dataset" / name),
            "capacity_sha256": sha256_capacity(battery_dict[name]["capacity"]),
        }
        for name in BATTERY_NAMES
    }

    baselines_out, persistence_rmse_map = evaluate_baselines(
        battery_dict,
        BATTERY_NAMES,
        int(base_cfg.window_size),
        float(base_cfg.rated_capacity),
        float(base_cfg.threshold_ratio),
    )

    models_out = {}
    for model_label in args.models:
        cfg = build_model_config(
            model_label,
            base_dict=base_dict,
            n_seeds=args.n_seeds,
            seed=args.seed,
            epochs_override=args.epochs,
            device=device,
            threshold_ratio=args.threshold_ratio,
        )
        models_out[model_label] = evaluate_model(
            model_label,
            cfg,
            battery_dict,
            BATTERY_NAMES,
            persistence_rmse_map,
            log_callback=log,
        )

    elapsed_seconds = time.perf_counter() - started_at
    cpu = platform.processor() or os.environ.get("PROCESSOR_IDENTIFIER", "unknown")
    gpu_name = (
        torch.cuda.get_device_name(0)
        if torch.cuda.is_available() else "unavailable"
    )
    manifest = {
        "schema_version": 2,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "protocol": PROTOCOL,
        "source_commit": full_commit,
        "short_commit": short_commit,
        "elapsed_seconds": elapsed_seconds,
        "hardware": {
            "os": platform.platform(),
            "python": platform.python_version(),
            "cpu": cpu,
            "gpu": gpu_name,
            "driver": driver_version(),
            "torch_cuda": str(torch.version.cuda) if torch.version.cuda else "unavailable",
        },
        "dependencies": {name: version(name) for name in DEPENDENCIES},
        "base_config": base_cfg.to_dict(),
        "rolling_starts": [float(s) for s in ROLLING_STARTS],
        "dataset": dataset,
        "baselines": baselines_out,
        "models": models_out,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(".json.tmp")
    temporary_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    os.replace(temporary_path, output_path)
    print(f"benchmark={output_path}", flush=True)
    print(f"elapsed_seconds={elapsed_seconds:.3f}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
