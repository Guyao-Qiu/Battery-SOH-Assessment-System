from pathlib import Path
import tempfile
import unittest

import numpy as np
import torch

from core.adapters import CALCEAdapter
from core.evaluate import calc_all_metrics, relative_error_reference
from core.model_persistence import load_model, save_model, train_model_on_all_data
from core.prediction import predict_capacity_batch
from core.preprocess import drop_outlier_reference
from core.train import train
from models.rnn_model import Autoencoder, DeTransformer, Net, PositionalEncoding
from utils.config import TrainConfig


class XiuzeZhouAlignmentTests(unittest.TestCase):
    def test_detransformer_architecture_and_composite_decode_output(self):
        model = DeTransformer(
            feature_size=16, hidden_dim=8, feature_num=4,
            num_layers=2, nhead=1, dropout=0.0, noise_level=0.0, input_size=1,
        )
        x = torch.randn(5, 16, 1)
        out_only = model(x)
        out, decode, x_rep = model(x, return_decode=True)
        self.assertEqual(tuple(out_only.shape), (5, 1))
        self.assertEqual(tuple(out.shape), (5, 1))
        self.assertEqual(tuple(decode.shape), (5, 4, 16))
        self.assertEqual(tuple(x_rep.shape), (5, 4, 16))
        torch.testing.assert_close(out_only, out)

        net_t = Net(hidden_dim=8, num_layers=2, mode="Transformer",
                    window_size=16, nhead=1, feature_num=4)
        self.assertEqual(tuple(net_t(x).shape), (5, 1))
        self.assertIsInstance(model.autoencoder, Autoencoder)
        self.assertIsInstance(model.pos, PositionalEncoding)

    def test_config_roundtrip_preserves_alignment_fields(self):
        cfg = TrainConfig(
            mode="RNN",
            backbone="Transformer",
            num_layers=3,
            nhead=1,
            transformer_k=16,
            alpha=0.1,
            noise_level=0.0,
            weight_decay=1e-5,
            prediction_mode="rolling",
        )
        restored = TrainConfig.from_dict(cfg.to_dict())
        self.assertEqual(restored, cfg)
        self.assertEqual(restored.backbone, "Transformer")
        self.assertEqual(restored.prediction_mode, "rolling")

    def test_calce_adapter_loads_npy_and_reference_re_outlier_work(self):
        npy_path = Path(__file__).resolve().parents[1] / "dataset" / "CALCE.npy"
        self.assertTrue(npy_path.is_file())
        batteries, names = CALCEAdapter().load_battery_data(
            [str(npy_path)], 3.8, 3.4, 2, 4, 7,
            log_callback=None, stop_flag=lambda: False,
        )
        self.assertEqual(names, ["CS2_35", "CS2_36", "CS2_37", "CS2_38"])
        self.assertEqual(len(batteries["CS2_35"]), 882)
        self.assertIn("dq_v", batteries["CS2_35"].columns)

        arr = np.ones(90, dtype=np.float64)
        arr[20] = 5.0
        kept = drop_outlier_reference(arr, len(arr), bins=40)
        self.assertNotIn(20, kept)

        y_true = np.linspace(1.1, 0.6, 50)
        y_pred = np.linspace(1.1, 0.6, 50)
        re_val = relative_error_reference(y_true, y_pred, 0.77)
        metrics = calc_all_metrics(y_true, y_pred, rated_capacity=1.1, threshold_ratio=0.7)
        self.assertAlmostEqual(re_val, 0.0)
        self.assertIn("re_ref", metrics)

    def test_zero_leakage_training_supports_transformer_and_both_prediction_modes(self):
        # 即使目标电池前 window+1 个点被置为极端异常值 999.0，严格 LOO 训练也不受其任何影响
        base_a = np.linspace(1.1, 0.7, 30, dtype=np.float32)
        base_b = np.linspace(1.08, 0.68, 30, dtype=np.float32)
        target_clean = np.linspace(1.09, 0.69, 30, dtype=np.float32)
        target_poisoned = target_clean.copy()
        target_poisoned[:9] = 999.0

        data_clean = {"a": {"capacity": base_a}, "b": {"capacity": base_b}, "t": {"capacity": target_clean}}
        data_poisoned = {"a": {"capacity": base_a}, "b": {"capacity": base_b}, "t": {"capacity": target_poisoned}}

        cfg_roll = TrainConfig(
            mode="RNN", backbone="DeTransformer", window_size=8, hidden_dim=8,
            num_layers=2, nhead=1, transformer_k=4, alpha=0.1, epochs=3,
            n_seeds=1, seed=0, prediction_mode="rolling",
        )
        logs_roll = []
        res_clean = train(cfg_roll, data_clean, ["t"], log_callback=logs_roll.append)
        res_poison = train(cfg_roll, data_poisoned, ["t"])

        detail = res_clean["t"]["detail"]
        self.assertEqual(detail["prediction_mode"], "rolling")
        self.assertEqual(detail["prediction_mode_label"], "自回归滚动预测（起点后仅用模型自身输出）")
        self.assertTrue(any("自回归滚动预测（起点后仅用模型自身输出）" in m for m in logs_roll))
        # 验证训练期间未见过 target（后续 22 步推理完全相同或仅受目标窗口首段影响——此处验证前 8 点仅影响测试初始窗口）
        np.testing.assert_allclose(res_clean["t"]["prediction"][:8], target_clean[:8])
        np.testing.assert_allclose(res_poison["t"]["prediction"][:8], target_poisoned[:8])
        self.assertAlmostEqual(
            res_clean["t"]["detail"]["rmse"],
            res_clean["t"]["detail"]["recursive_metrics"]["rmse"],
            places=6,
        )

        # 验证单步模式标注及保存/加载闭环
        cfg_step = TrainConfig(
            mode="RNN", backbone="DeTransformer", window_size=8, hidden_dim=8,
            num_layers=2, nhead=1, transformer_k=4, alpha=0.1, epochs=3,
            n_seeds=1, seed=0, prediction_mode="one_step",
        )
        logs_step = []
        res_step = train(cfg_step, data_clean, ["t"], log_callback=logs_step.append)
        self.assertEqual(res_step["t"]["detail"]["prediction_mode_label"], "单步预测（基于真实历史窗口）")
        self.assertTrue(any("单步预测（基于真实历史窗口）" in m for m in logs_step))

        with tempfile.TemporaryDirectory() as tmp:
            pt_path = Path(tmp) / "detransformer.pt"
            model, meta = train_model_on_all_data(cfg_roll, data_clean, ["a", "b"])
            save_model(model, meta, str(pt_path))
            loaded_model, loaded_meta = load_model(str(pt_path))
            pred = predict_capacity_batch(loaded_model, loaded_meta, target_clean[:8])
            self.assertEqual(pred.shape, (1,))


if __name__ == "__main__":
    unittest.main()
