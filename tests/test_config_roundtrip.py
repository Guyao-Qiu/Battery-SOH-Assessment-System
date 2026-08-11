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


if __name__ == "__main__":
    unittest.main()
