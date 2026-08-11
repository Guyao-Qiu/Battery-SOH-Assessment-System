import re
import subprocess
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
        self.assertTrue(
            all(re.fullmatch(r"[A-Za-z0-9_.-]+==[^\s]+", line) for line in lines),
            "运行依赖必须使用精确版本，不得使用范围约束",
        )
        self.assertEqual("-r requirements.lock", (ROOT / "requirements.txt").read_text(encoding="utf-8").strip())

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
            "bandit -r core models ui utils battery_soh_app.py",
            "pip-audit -r requirements.lock",
            "python -m unittest discover -s tests -v",
            "coverage run --source=core,models,ui,utils -m unittest discover -s tests",
            "coverage report --fail-under=85",
        )
        for command in required_commands:
            self.assertIn(command, text)
        self.assertIn("3.10", text)

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


if __name__ == "__main__":
    unittest.main()
