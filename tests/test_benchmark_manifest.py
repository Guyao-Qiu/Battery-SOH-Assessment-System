import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class StrictBenchmarkManifestTests(unittest.TestCase):
    def test_manifest_records_reproducible_strict_protocol(self):
        manifest_path = ROOT / "benchmark" / "strict_zero_shot_rnn.json"
        self.assertTrue(manifest_path.is_file(), "缺少严格零样本基准产物")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        self.assertEqual(
            manifest["protocol"], "strict_zero_shot_leave_one_battery_out")
        self.assertRegex(manifest["source_commit"], r"^[0-9a-f]{40}$")
        self.assertGreater(manifest["elapsed_seconds"], 0)

        hardware = manifest["hardware"]
        for key in ("os", "python", "cpu", "gpu", "driver", "torch_cuda"):
            self.assertTrue(hardware[key])

        dependencies = manifest["dependencies"]
        for package in (
                "PyQt6", "numpy", "pandas", "matplotlib", "torch",
                "scikit-learn", "xgboost", "scipy", "joblib", "openpyxl"):
            self.assertIn(package, dependencies)
        self.assertEqual(dependencies["torch"], "2.13.0+cu130")

        parameters = manifest["parameters"]
        self.assertEqual(parameters["mode"], "RNN")
        self.assertEqual(parameters["window_size"], 64)
        self.assertEqual(parameters["epochs"], 100)
        self.assertEqual(parameters["hidden_dim"], 64)
        self.assertEqual(parameters["n_seeds"], 5)
        self.assertEqual(parameters["device"], "cuda")
        self.assertEqual(manifest["seeds"], [1, 2, 3, 4, 5])

        expected_batteries = {"CS2_35", "CS2_36", "CS2_37", "CS2_38"}
        self.assertEqual(set(manifest["dataset"]), expected_batteries)
        self.assertEqual(set(manifest["results"]), expected_batteries)
        for name in expected_batteries:
            data = manifest["dataset"][name]
            self.assertRegex(data["source_sha256"], r"^[0-9a-f]{64}$")
            self.assertRegex(data["capacity_sha256"], r"^[0-9a-f]{64}$")
            self.assertGreater(data["cycles"], 64)
            result = manifest["results"][name]
            for metric in ("rmse", "mae", "r2", "pearson"):
                self.assertIsInstance(result[metric], float)
            self.assertIn("re", result)
            self.assertIn("re_status", result)
            self.assertEqual(
                result["ci_statistical_object"],
                "同一留一折内的随机种子波动",
            )

    def test_readme_publishes_new_benchmark_and_manifest_link(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("严格零样本基准", readme)
        self.assertIn("benchmark/strict_zero_shot_rnn.json", readme)
        self.assertIn("RTX 4050", readme)
        self.assertNotIn("实验基准（旧方法结果", readme)

    def test_benchmark_runner_is_versioned(self):
        runner = ROOT / "scripts" / "run_strict_benchmark.py"
        self.assertTrue(runner.is_file(), "缺少可复现基准运行脚本")
        source = runner.read_text(encoding="utf-8")
        self.assertIn("strict_zero_shot_leave_one_battery_out", source)
        self.assertTrue(re.search(r"sha256", source, re.IGNORECASE))


if __name__ == "__main__":
    unittest.main()
