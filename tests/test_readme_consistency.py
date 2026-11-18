import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

from core import model_factory
from tools import render_benchmark_table, sync_readme_defaults


ROOT = Path(__file__).resolve().parents[1]


def _factory_model_tokens() -> set[str]:
    """收集 core/model_factory.py 实际支持的全部模型与主干名称。"""
    source = (ROOT / 'core' / 'model_factory.py').read_text(encoding='utf-8')
    tokens = set(model_factory.RECURRENT_MODES) | set(model_factory.TREE_MODES)
    for name in ('DeTransformer', 'Transformer', 'RandomForestRegressor', 'XGBRegressor'):
        if name in source:
            tokens.add(name)
    # 英文全称 Random Forest 对应工厂中的 RF
    if 'RF' in tokens and 'RandomForestRegressor' in tokens:
        tokens.add('Random Forest')
    return tokens


def _extract_readme_model_mentions(text: str) -> set[str]:
    """提取 README 正文所宣称支持的模型名称。"""
    pattern = re.compile(
        r'\b(RNN|GRU|LSTM|XGBoost|RF|Random Forest|DeTransformer|Transformer)\b'
    )
    mentions = set()
    # 跳过参考论文标题（References / 参考资料）与目录树代码块之外的纯代码标识符
    body = re.split(r'^##\s+(?:参考资料|References)\b', text, maxsplit=1, flags=re.MULTILINE)[0]
    for match in pattern.finditer(body):
        token = match.group(1)
        # 仅统计作为模型类型宣称的名称（Transformer 若在 "Transformer 编码器" 语境中出现仍可映射到工厂）
        mentions.add(token)
    return mentions


class ReadmeConsistencyTests(unittest.TestCase):
    def test_sync_readme_defaults_check_passes(self):
        self.assertEqual(sync_readme_defaults.check_readme_defaults(ROOT), [])
        result = subprocess.run(
            [sys.executable, '-X', 'utf8', 'tools/sync_readme_defaults.py', '--check'],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding='utf-8',
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_sync_readme_defaults_detects_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            cfg = json.loads((ROOT / 'config.json').read_text(encoding='utf-8'))
            cfg['threshold_ratio'] = 0.85
            (tmp_root / 'config.json').write_text(
                json.dumps(cfg, indent=2), encoding='utf-8')
            shutil.copy2(ROOT / 'README.md', tmp_root / 'README.md')
            shutil.copy2(ROOT / 'README_EN.md', tmp_root / 'README_EN.md')

            problems = sync_readme_defaults.check_readme_defaults(tmp_root)
            self.assertEqual(len(problems), 2)

    def test_readme_models_exist_in_model_factory(self):
        supported = _factory_model_tokens()
        for filename in ('README.md', 'README_EN.md'):
            text = (ROOT / filename).read_text(encoding='utf-8')
            mentions = _extract_readme_model_mentions(text)
            self.assertTrue(mentions, f'{filename} 未检测到模型列表')
            missing = mentions - supported
            self.assertFalse(
                missing,
                f'{filename} 提到的模型未在 core/model_factory.py 中找到: {sorted(missing)}',
            )

    def test_readme_protocol_and_outlier_semantics_match_code(self):
        zh = (ROOT / 'README.md').read_text(encoding='utf-8')
        en = (ROOT / 'README_EN.md').read_text(encoding='utf-8')

        self.assertNotIn('降级为诊断', zh)
        self.assertNotIn('demoted to diagnostics', en)
        self.assertIn('UI 默认显示一步预测', zh)
        self.assertIn('UI defaults to one-step prediction', en)
        self.assertIn("outlier_mode='chunked'", zh)
        self.assertIn("outlier_mode='chunked'", en)

        # 确认每个 mark / 0.8 出现处都有明确的“可选/签名/历史/回退”语境
        for idx, line in enumerate(zh.splitlines(), 1):
            if re.search(r'\bmark\b', line):
                self.assertTrue(
                    any(k in line for k in (
                        '可选', '签名', '仅当', 'TrainConfig', 'chunked/mark/delete/off',
                    )),
                    f'README.md 第 {idx} 行出现未标明语境的 mark: {line}',
                )
            if re.search(r'(?<![\d.])0\.8(?![\d.])', line):
                self.assertTrue(
                    any(k in line for k in ('历史', '回退', '80%', '0.80')),
                    f'README.md 第 {idx} 行出现未标明语境的 0.8: {line}',
                )

    def test_ci_workflow_checks_readme_defaults(self):
        workflow = (ROOT / '.github' / 'workflows' / 'quality.yml').read_text(encoding='utf-8')
        self.assertIn('python tools/sync_readme_defaults.py --check', workflow)

    def test_benchmark_tables_match_results_json(self):
        results_files = sorted((ROOT / 'benchmark').glob('results_*.json'))
        self.assertTrue(results_files, '缺少 benchmark/results_*.json')
        nasa_files = sorted(
            (ROOT / 'benchmark').glob('nasa_*.json'),
            key=lambda p: p.stat().st_mtime,
        )
        nasa_path = nasa_files[-1] if nasa_files else None
        ablation_files = sorted(
            (ROOT / 'benchmark').glob('ablation_*.json'),
            key=lambda p: p.stat().st_mtime,
        )
        ablation_path = ablation_files[-1] if ablation_files else None
        for path in results_files:
            self.assertEqual(
                render_benchmark_table.check_benchmark_tables(
                    path, ROOT, nasa_input=nasa_path, ablation_input=ablation_path),
                [],
            )


if __name__ == '__main__':
    unittest.main()
