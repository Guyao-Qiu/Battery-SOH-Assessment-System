import re
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class EngineeringHygieneTests(unittest.TestCase):
    def test_runtime_dependencies_are_exactly_locked(self):
        lock_path = ROOT / "requirements.lock"
        self.assertTrue(lock_path.is_file(), "缺少 requirements.lock")

        lines = [
            line.strip()
            for line in lock_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        expected = {
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
        }
        locked = {line.split("==", 1)[0] for line in lines if "==" in line}
        self.assertEqual(expected, locked)
        self.assertIn("torch==2.13.0", lines)
        self.assertTrue(
            all(re.fullmatch(r"[A-Za-z0-9_.-]+==[^\s]+", line) for line in lines),
            "运行依赖必须使用精确版本，不得使用范围约束",
        )
        self.assertEqual("-r requirements.lock", (ROOT / "requirements.txt").read_text(encoding="utf-8").strip())

    def test_cuda_environment_has_a_reproducible_lock(self):
        cuda_lock = ROOT / "requirements-cuda.lock"
        self.assertTrue(cuda_lock.is_file(), "缺少 CUDA 环境锁文件")
        text = cuda_lock.read_text(encoding="utf-8")
        self.assertIn("-r requirements.lock", text)
        self.assertIn("https://download.pytorch.org/whl/cu130", text)
        self.assertIn("torch==2.13.0+cu130", text)
        self.assertIn(
            "requirements-cuda.lock",
            (ROOT / "README.md").read_text(encoding="utf-8"),
        )

    def test_quality_dependencies_are_exactly_locked(self):
        lock_path = ROOT / "requirements-dev.lock"
        self.assertTrue(lock_path.is_file(), "缺少 requirements-dev.lock")
        text = lock_path.read_text(encoding="utf-8")
        for package in ("ruff", "bandit", "pip-audit", "coverage"):
            self.assertRegex(text, rf"(?m)^{re.escape(package)}==[^\s]+$")

    def test_ci_runs_static_security_audit_tests_and_coverage(self):
        workflow = ROOT / ".github" / "workflows" / "quality.yml"
        self.assertTrue(workflow.is_file(), "缺少质量门禁工作流")
        text = workflow.read_text(encoding="utf-8")
        required_commands = (
            "ruff check .",
            "bandit -r core models ui utils battery_soh_app.py theme_tokens.py --ini .bandit",
            "pip-audit -r requirements.lock",
            "python -m unittest discover -s tests -v",
            "coverage run --source=core,models,ui,utils -m unittest discover -s tests",
            "coverage report --fail-under=59",
            "--include=\"core/evaluate.py,core/result_semantics.py,core/run_snapshot.py,utils/config.py\"",
            "coverage report --fail-under=85",
            # 改进方案 §7.2：两道守卫脚本必须进 CI
            "python tools/check_undefined.py core models ui utils theme_tokens.py battery_soh_app.py",
            "python tools/check_colors.py",
        )
        for command in required_commands:
            self.assertIn(command, text)
        self.assertIn("3.10", text)

    def test_undefined_names_and_hardcoded_colors_are_gated(self):
        """A1 / C1 的守卫脚本必须存在且能独立运行。"""
        undefined = ROOT / "tools" / "check_undefined.py"
        colors = ROOT / "tools" / "check_colors.py"
        self.assertTrue(undefined.is_file(), "缺少 check_undefined.py")
        self.assertTrue(colors.is_file(), "缺少 check_colors.py")

        result = subprocess.run(
            [sys.executable, "-X", "utf8", str(undefined),
             "core", "models", "ui", "utils", "theme_tokens.py"],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        result = subprocess.run(
            [sys.executable, "-X", "utf8", str(colors)],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_ruff_enforces_undefined_names_repo_wide(self):
        """A1 修复后不应再为任何文件豁免 F821。"""
        config = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('"F821"', config)
        self.assertNotIn("per-file-ignores", config)

    def test_linux_ci_installs_pyqt_runtime_library(self):
        workflow = (
            ROOT / ".github" / "workflows" / "quality.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("runner.os == 'Linux'", workflow)
        self.assertIn("sudo apt-get install -y libegl1", workflow)

    def test_distribution_excludes_runtime_and_ide_artifacts(self):
        tracked = subprocess.run(
            ["git", "ls-files"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        ).stdout.splitlines()
        forbidden = re.compile(r"(^|/)(\.idea|__pycache__|outputs)(/|$)|\.pyc$")
        self.assertFalse([path for path in tracked if forbidden.search(path)])

    def test_readme_and_license_match_current_product(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertNotIn("Quantum Lab 暗色主题", readme)
        self.assertIn("宣纸水墨主题", readme)
        self.assertIn("MIT License", readme)

        license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("MIT License", license_text)
        self.assertIn("Permission is hereby granted", license_text)

    def test_bilingual_readme_pair_is_published(self):
        chinese = (ROOT / "README.md").read_text(encoding="utf-8")
        english_path = ROOT / "README_EN.md"
        self.assertTrue(english_path.is_file(), "缺少英文 README")
        english = english_path.read_text(encoding="utf-8")
        self.assertTrue(english.startswith("# Battery SOH Assessment System\n"))
        self.assertIn("严格零样本基准", chinese)
        self.assertIn("Strict Zero-Shot Benchmark", english)
        self.assertIn("README_EN.md", chinese)
        self.assertIn("README.md", english)
        self.assertIn("Research Preview", english)
        self.assertIn("MIT License", english)


if __name__ == "__main__":
    unittest.main()
