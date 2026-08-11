"""Stable runtime paths independent of the process working directory."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_FILE = PROJECT_ROOT / 'config.json'
OUTPUTS_DIR = PROJECT_ROOT / 'outputs'
LOG_DIR = OUTPUTS_DIR
MODEL_DIR = OUTPUTS_DIR
FIGURE_DIR = OUTPUTS_DIR / 'figures'
REPORT_DIR = OUTPUTS_DIR / 'runs'
