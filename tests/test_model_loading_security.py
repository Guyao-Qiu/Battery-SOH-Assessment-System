import json
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import torch

import core.model_persistence as persistence
from core.preprocess import CapacityScaler
from models.rnn_model import Net


def _metadata():
    scaler = CapacityScaler(
        method="minmax", rated_capacity=1.1).fit([0.7, 0.8, 0.9, 1.0])
    return {
        "mode": "RNN",
        "model_type": "RNN",
        "window_size": 3,
        "hidden_dim": 4,
        "rated_capacity": 1.1,
        "threshold_ratio": 0.8,
        "scaler": scaler.to_dict(),
    }


class SafeModelLoadingTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(11)
        self.model = Net(hidden_dim=4, num_layers=1, mode="RNN")

    def test_pytorch_file_contains_only_state_dict_and_validated_sidecar(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "model.pt"
            persistence.save_model(self.model, _metadata(), str(path))

            payload = torch.load(path, map_location="cpu", weights_only=True)
            self.assertNotIn("metadata", payload)
            self.assertNotIn("state_dict", payload)
            self.assertTrue(all(torch.is_tensor(value) for value in payload.values()))

            sidecar = Path(str(path) + ".meta.json")
            self.assertTrue(sidecar.is_file())
            saved_metadata = json.loads(sidecar.read_text(encoding="utf-8"))
            self.assertEqual(saved_metadata["format_version"], 2)
            self.assertEqual(saved_metadata["model_type"], "RNN")
            self.assertRegex(saved_metadata["file_sha256"], r"^[0-9a-f]{64}$")
            self.assertIn("feature_schema", saved_metadata)
            self.assertIn("training_params", saved_metadata)
            self.assertIn("library_versions", saved_metadata)
            self.assertIn("data_hash", saved_metadata)
            self.assertIn("created_at", saved_metadata)

    def test_tampered_file_is_rejected_before_torch_deserialization(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "model.pt"
            persistence.save_model(self.model, _metadata(), str(path))
            with path.open("ab") as stream:
                stream.write(b"tampered")

            with patch.object(persistence.torch, "load") as torch_load:
                with self.assertRaisesRegex(ValueError, "哈希"):
                    persistence.load_model(str(path))
                torch_load.assert_not_called()

    def test_missing_metadata_and_oversized_files_are_rejected_before_load(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "model.pt"
            torch.save(self.model.state_dict(), path)

            with patch.object(persistence.torch, "load") as torch_load:
                with self.assertRaisesRegex(ValueError, "元数据"):
                    persistence.load_model(str(path))
                torch_load.assert_not_called()

            persistence.save_model(self.model, _metadata(), str(path))
            real_getsize = persistence.os.path.getsize

            def oversized_model_only(candidate):
                if Path(candidate) == path:
                    return persistence.MAX_MODEL_FILE_BYTES + 1
                return real_getsize(candidate)

            with patch.object(
                    persistence.os.path, "getsize",
                    side_effect=oversized_model_only), patch.object(
                        persistence.torch, "load") as torch_load:
                with self.assertRaisesRegex(ValueError, "过大"):
                    persistence.load_model(str(path))
                torch_load.assert_not_called()

    def test_pickle_is_forbidden_and_joblib_requires_explicit_opt_in(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            for suffix, error_type in ((".pkl", ValueError),
                                       (".joblib", PermissionError)):
                with self.subTest(suffix=suffix):
                    path = Path(temp_dir) / f"model{suffix}"
                    path.write_bytes(b"not a trusted model")
                    with patch("joblib.load") as joblib_load:
                        with self.assertRaises(error_type):
                            persistence.load_model(str(path))
                        joblib_load.assert_not_called()

    def test_fake_extension_and_mismatched_metadata_are_safely_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "fake.pt"
            persistence.save_model(self.model, _metadata(), str(path))
            sidecar = Path(str(path) + ".meta.json")
            metadata = json.loads(sidecar.read_text(encoding="utf-8"))
            metadata["model_type"] = "RF"
            metadata["mode"] = "RF"
            sidecar.write_text(
                json.dumps(metadata, ensure_ascii=False), encoding="utf-8")

            with patch.object(persistence.torch, "load") as torch_load:
                with self.assertRaisesRegex(ValueError, "不匹配"):
                    persistence.load_model(str(path))
                torch_load.assert_not_called()

    def test_missing_state_dict_key_is_rejected_without_partial_model(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "model.pt"
            persistence.save_model(self.model, _metadata(), str(path))
            state_dict = torch.load(
                path, map_location="cpu", weights_only=True)
            state_dict.pop(next(iter(state_dict)))
            torch.save(state_dict, path)

            sidecar = Path(str(path) + ".meta.json")
            metadata = json.loads(sidecar.read_text(encoding="utf-8"))
            metadata["file_sha256"] = hashlib.sha256(
                path.read_bytes()).hexdigest()
            sidecar.write_text(
                json.dumps(metadata, ensure_ascii=False), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "权重键"):
                persistence.load_model(str(path))

    def test_explicitly_approved_joblib_round_trip_still_checks_type(self):
        from sklearn.ensemble import RandomForestRegressor

        model = RandomForestRegressor(n_estimators=1, random_state=7)
        model.fit([[0.9, 0.8], [0.8, 0.7]], [0.7, 0.6])
        metadata = _metadata()
        metadata.update({"mode": "RF", "model_type": "RF"})
        metadata.pop("hidden_dim")

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "model.joblib"
            persistence.save_model(model, metadata, str(path))
            loaded, loaded_metadata = persistence.load_model(
                str(path), allow_unsafe_joblib=True)

        self.assertEqual(type(loaded).__name__, "RandomForestRegressor")
        self.assertEqual(loaded_metadata["model_type"], "RF")


if __name__ == "__main__":
    unittest.main()
