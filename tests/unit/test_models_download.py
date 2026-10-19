from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from avfm import models
from avfm.errors import ModelVerificationError
from avfm.models import ModelSpec


def tiny_spec(data: bytes = b"abc") -> ModelSpec:
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


class FakeResponse:
    def __init__(self, data: bytes) -> None:
        self._data = data
        self._offset = 0
        self.headers = {"Content-Length": str(len(data))}

    def read(self, size: int = -1) -> bytes:
        if self._offset >= len(self._data):
            return b""
        end = len(self._data) if size < 0 else self._offset + size
        chunk = self._data[self._offset : end]
        self._offset = end
        return chunk

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_download_once_and_verify(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    spec = tiny_spec()
    monkeypatch.setattr(
        models.urllib.request,
        "urlopen",
        lambda request, timeout: FakeResponse(b"abc"),
    )
    target = tmp_path / "tiny.bin"
    result = models.download_model(spec, target, retries=1)
    assert result == target
    assert target.read_bytes() == b"abc"
    assert models.verify_model(spec, target)


def test_download_hash_mismatch_cleans_part(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec = tiny_spec()
    monkeypatch.setattr(
        models.urllib.request,
        "urlopen",
        lambda request, timeout: FakeResponse(b"wrong"),
    )
    target = tmp_path / "tiny.bin"
    with pytest.raises(ModelVerificationError):
        models.download_model(spec, target, retries=1)
    assert not target.exists()
    assert not (tmp_path / "tiny.bin.part").exists()


def test_download_all_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    spec = tiny_spec()
    monkeypatch.setattr(
        models.urllib.request,
        "urlopen",
        lambda request, timeout: FakeResponse(b"abc"),
    )
    original = models.MODELS
    monkeypatch.setattr(models, "MODELS", {"tiny": spec})
    try:
        paths = models.download_all(tmp_path, only="tiny")
    finally:
        models.MODELS = original
    assert paths == [tmp_path / "tiny" / "tiny.bin"]
