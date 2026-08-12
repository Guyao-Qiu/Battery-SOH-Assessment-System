"""Run and record the strict zero-shot CALCE RNN benchmark."""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.dataload import load_battery_from_paths  # noqa: E402
from core.train import train  # noqa: E402
from utils.config import TrainConfig  # noqa: E402


PROTOCOL = "strict_zero_shot_leave_one_battery_out"
BATTERY_NAMES = ("CS2_35", "CS2_36", "CS2_37", "CS2_38")
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


def main() -> int:
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


if __name__ == "__main__":
    raise SystemExit(main())
