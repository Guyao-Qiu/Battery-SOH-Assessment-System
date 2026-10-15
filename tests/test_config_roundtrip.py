import importlib
import os
import unittest

from models.rnn_model import Net
from utils.config import TrainConfig


config_module = importlib.import_module("utils.config")


class ModelNameTests(unittest.TestCase):
    def test_model_names_have_one_canonical_normalizer(self):
        normalize = getattr(config_module, "normalize_model_name", None)
        self.assertIsNotNone(normalize)

        cases = {
            "rnn": "RNN",
            "GRU": "GRU",
            "lStM": "LSTM",
            "XGBoost": "XGBoost",
            "xgboost": "XGBoost",
            "XGBOOST": "XGBoost",
            "rf": "RF",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(normalize(raw), expected)

    def test_unsupported_model_is_rejected_instead_of_falling_back(self):
        normalize = getattr(config_module, "normalize_model_name", None)
        self.assertIsNotNone(normalize)

        with self.assertRaises(ValueError):
            normalize("Transformer")
        with self.assertRaises(ValueError):
            Net(mode="XGBoost")


class TrainConfigRoundTripTests(unittest.TestCase):
    def test_all_five_models_round_trip_every_configuration_field(self):
        self.assertTrue(hasattr(TrainConfig, "from_dict"))
        self.assertTrue(hasattr(TrainConfig, "to_dict"))
        base = {
            "rated_capacity": 2.35,
            "threshold_ratio": 0.73,
            "voltage_upper": 4.15,
            "voltage_lower": 3.05,
            "window_size": 17,
            "epochs": 23,
            "hidden_dim": 19,
            "metric": "pearson",
            "device": "cpu",
            "seed": 41,
            "n_seeds": 7,
            "patience": 9,
            "norm_method": "zscore",
            "n_estimators": 37,
            "learning_rate": 0.07,
            "max_depth": 5,
            "subsample": 0.83,
            "colsample_bytree": 0.79,
            "min_samples_leaf": 3,
            "max_features": 0.66,
            "adapter_type": "NASA",
            "cc_step": 11,
            "cv_step": 13,
            "discharge_step": 17,
        }

        for mode in ("RNN", "GRU", "LSTM", "XGBoost", "RF"):
            with self.subTest(mode=mode):
                original = TrainConfig.from_dict({**base, "mode": mode})
                exported = original.to_dict()
                restored = TrainConfig.from_dict(exported)

                self.assertEqual(restored, original)
                self.assertEqual(exported, original.to_dict())
                self.assertEqual(exported["mode"], mode)
                self.assertEqual(exported["learning_rate"], 0.07)
                self.assertEqual(exported["n_seeds"], 7)
                self.assertEqual(exported["adapter_type"], "NASA")
                self.assertEqual(exported["cc_step"], 11)
                self.assertEqual(exported["cv_step"], 13)
                self.assertEqual(exported["discharge_step"], 17)

    def test_legacy_xgboost_alias_fields_import_without_algorithm_change(self):
        self.assertTrue(hasattr(TrainConfig, "from_dict"))

        config = TrainConfig.from_dict({
            "model": "XGBOOST",
            "xgb_learning_rate": 0.13,
            "xgb_n_estimators": 29,
            "random_seed": 5,
            "normalization": "minmax",
            "Feature Size": 12,
            "THRESHOLD_RATIO": 0.75,
        })

        self.assertEqual(config.mode, "XGBoost")
        self.assertEqual(config.learning_rate, 0.13)
        self.assertEqual(config.n_estimators, 29)
        self.assertEqual(config.seed, 5)
        self.assertEqual(config.norm_method, "minmax")
        self.assertEqual(config.window_size, 12)
        self.assertEqual(config.threshold_ratio, 0.75)

    def test_main_window_applies_imported_config_for_each_model(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        from ui.main_window import MainWindow

        self.assertTrue(hasattr(MainWindow, "_apply_train_config"))
        app = QApplication.instance() or QApplication([])
        window = MainWindow()
        common = {
            "rated_capacity": 2.2,
            "threshold_ratio": 0.72,
            "voltage_upper": 4.1,
            "voltage_lower": 3.1,
            "window_size": 16,
            "epochs": 22,
            "hidden_dim": 18,
            "metric": "mae",
            "device": "cpu",
            "seed": 31,
            "n_seeds": 6,
            "patience": 8,
            "norm_method": "minmax",
            "adapter_type": "NASA",
            "cc_step": 9,
            "cv_step": 10,
            "discharge_step": 12,
        }

        try:
            for mode in ("RNN", "GRU", "LSTM", "XGBoost", "RF"):
                with self.subTest(mode=mode):
                    expected = TrainConfig.from_dict({**common, "mode": mode})
                    window._apply_train_config(expected)
                    actual = window._build_config()

                    self.assertEqual(actual, expected)
        finally:
            window.deleteLater()
            app.processEvents()


class CanonicalConfigKeyTests(unittest.TestCase):
    """A11：配置里只存规范键，界面文本只在界面层转换。"""

    def test_device_normalization_accepts_ui_text_and_canonical_keys(self):
        normalize = config_module.normalize_device
        for raw, expected in (
                ("GPU (CUDA)", "cuda"), ("gpu", "cuda"), ("cuda", "cuda"),
                ("CPU", "cpu"), ("cpu", "cpu")):
            with self.subTest(raw=raw):
                self.assertEqual(normalize(raw), expected)
        # 未知值安全回退，不抛异常
        self.assertEqual(normalize("nonsense"), "cpu")
        self.assertEqual(normalize(None), "cpu")

    def test_legacy_config_written_with_ui_text_still_loads_as_canonical(self):
        """旧版本把界面文本直接写进 JSON，导致 GPU 被静默切回 CPU。"""
        legacy = {
            "device": "GPU (CUDA)",
            "norm_method": "额定容量归一化",
            "metric": "MAE",
            "mode": "RF",
            "adapter_type": "NASA",
        }
        config = TrainConfig.from_dict(legacy)
        self.assertEqual(config.device, "cuda")
        self.assertEqual(config.norm_method, "rated")
        self.assertEqual(config.metric, "mae")

    def test_save_import_save_round_trip_is_field_identical(self):
        import json

        original = TrainConfig(
            mode="RF", window_size=16, rated_capacity=2.0,
            threshold_ratio=0.7, device="cuda", norm_method="rated",
            metric="mae", adapter_type="NASA",
            feature_columns=("capacity", "dq_v", "CCCT"),
        )
        first = original.to_dict()
        reloaded = TrainConfig.from_dict(json.loads(json.dumps(first)))
        self.assertEqual(first, reloaded.to_dict())
        # 存进去的必须是规范键，不是界面文本
        self.assertEqual(first["device"], "cuda")
        self.assertEqual(first["norm_method"], "rated")
        self.assertEqual(first["metric"], "mae")

    def test_feature_list_always_contains_capacity_first(self):
        normalize = config_module.normalize_feature_list
        self.assertEqual(normalize(None), ("capacity",))
        self.assertEqual(normalize("dq_v"), ("capacity", "dq_v"))
        self.assertEqual(normalize(("CCCT", "capacity")),
                         ("capacity", "CCCT"))
        # 未知列被丢弃
        self.assertEqual(normalize("capacity,dq_v,bogus"),
                         ("capacity", "dq_v"))
        self.assertEqual(normalize([]), ("capacity",))

    def test_unsupported_adapter_is_rejected(self):
        with self.assertRaises(ValueError):
            TrainConfig(adapter_type="Bogus")


if __name__ == "__main__":
    unittest.main()
