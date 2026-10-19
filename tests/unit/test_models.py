from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from avfm import models
from avfm.errors import ModelNotFoundError, ModelVerificationError
from avfm.models import ModelSpec, model_root, resolve_model_path, verify_model


def tiny_spec() -> ModelSpec:
    data = b"abc"
    return ModelSpec(
        name="tiny",
        subdir="tiny",
        filename="tiny.bin",
        url="https://example.invalid/tiny.bin",
        sha256=hashlib.sha256(data).hexdigest(),
        size=len(data),
        license_name="MIT",
        license_url="https://example.invalid/license",
    )


def test_verify_model(tmp_path: Path) -> None:
    spec = tiny_spec()
    path = tmp_path / "tiny.bin"
    path.write_bytes(b"abc")
    assert verify_model(spec, path)
    path.write_bytes(b"abd")
    assert not verify_model(spec, path)


def test_download_model_monkeypatched(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    spec = tiny_spec()
    dest = tmp_path / "tiny.bin"

    def fake_download(spec, target, timeout):
        target.write_bytes(b"abc")

    monkeypatch.setattr(models, "_download_once", fake_download)
    result = models.download_model(spec, dest)
    assert result == dest
    assert verify_model(spec, dest)


def test_download_rejects_mismatch_without_force(tmp_path: Path) -> None:
    spec = tiny_spec()
    dest = tmp_path / "tiny.bin"
    dest.write_bytes(b"wrong")
    with pytest.raises(ModelVerificationError):
        models.download_model(spec, dest)


def test_resolve_model_path(tmp_path: Path) -> None:
    spec = tiny_spec()
    root = tmp_path / "models"
    configured = Path("models") / spec.subdir / spec.filename
    path = resolve_model_path(spec, configured, root)
    assert path == root / spec.subdir / spec.filename


def test_model_root_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AVFM_MODEL_DIR", str(tmp_path))
    assert model_root() == tmp_path


def test_verify_model_or_raise(tmp_path: Path) -> None:
    spec = tiny_spec()
    with pytest.raises(ModelNotFoundError):
        models.verify_model_or_raise(spec, tmp_path / "missing.bin")
