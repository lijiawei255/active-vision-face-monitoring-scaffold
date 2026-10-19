"""Model download, checksum verification and path resolution.

Models are *not* committed to the repository. ``avfm models download`` fetches
them from pinned URLs and verifies SHA-256 before atomically installing them.
"""

from __future__ import annotations

import hashlib
import os
import sys
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from avfm.errors import ModelNotFoundError, ModelVerificationError


@dataclass(frozen=True, slots=True)
class ModelSpec:
    name: str
    subdir: str
    filename: str
    url: str
    sha256: str
    size: int
    license_name: str
    license_url: str


YUNET = ModelSpec(
    name="yunet",
    subdir="yunet",
    filename="face_detection_yunet_2026may.onnx",
    url=(
        "https://media.githubusercontent.com/media/opencv/opencv_zoo/"
        "26cc381e4d2594bb9f47a26eb8fd96c94a13660d/models/face_detection_yunet/"
        "face_detection_yunet_2026may.onnx"
    ),
    sha256="ebafce4e3c118d6554634be5c27ab333b4c047a9a8c3faf1d7cf93101c22f0f0",
    size=229_738,
    license_name="MIT",
    license_url="https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet",
)

MEDIAPIPE = ModelSpec(
    name="mediapipe",
    subdir="mediapipe",
    filename="face_landmarker.task",
    url=(
        "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
        "face_landmarker/float16/1/face_landmarker.task"
    ),
    sha256="64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff",
    size=3_758_596,
    license_name="Apache-2.0",
    license_url="https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker",
)

MODELS: dict[str, ModelSpec] = {spec.name: spec for spec in (YUNET, MEDIAPIPE)}


def model_root(cwd: str | Path | None = None) -> Path:
    configured = os.environ.get("AVFM_MODEL_DIR")
    if configured:
        return Path(configured).expanduser()
    base = Path(cwd) if cwd is not None else Path.cwd()
    return base / "models"


def default_path(spec: ModelSpec, root: Path | None = None) -> Path:
    base = root if root is not None else model_root()
    return base / spec.subdir / spec.filename


def resolve_model_path(
    spec: ModelSpec, configured: str | Path | None, root: Path | None = None
) -> Path:
    """Resolve a configured path, falling back to the model root.

    ``configured`` is usually something like ``models/yunet/x.onnx``. If it
    exists relative to the current directory we use it; otherwise we treat
    the leading ``models`` component as the model root.
    """
    base = root if root is not None else model_root()
    if not configured:
        return default_path(spec, base)
    path = Path(configured).expanduser()
    if path.is_absolute():
        return path
    if path.exists():
        return path
    parts = path.parts
    if parts and parts[0] == base.name:
        return base.joinpath(*parts[1:])
    return base / path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_model(spec: ModelSpec, path: Path) -> bool:
    if not path.exists() or not path.is_file():
        return False
    if path.stat().st_size != spec.size:
        return False
    return sha256_file(path) == spec.sha256


def verify_model_or_raise(spec: ModelSpec, path: Path) -> None:
    if not path.exists():
        raise ModelNotFoundError(
            f"Model '{spec.name}' not found at {path}. Run: avfm models download --only {spec.name}"
        )
    if not verify_model(spec, path):
        raise ModelVerificationError(
            f"Model '{spec.name}' at {path} failed SHA-256 verification. "
            f"Run: avfm models download --only {spec.name} --force"
        )


def _download_once(spec: ModelSpec, dest: Path, timeout: float) -> None:
    request = urllib.request.Request(spec.url, headers={"User-Agent": "avfm/0.1"})
    part = dest.with_name(dest.name + ".part")
    part.parent.mkdir(parents=True, exist_ok=True)
    if part.exists():
        part.unlink()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            total = int(response.headers.get("Content-Length", "0") or 0)
            written = 0
            digest = hashlib.sha256()
            with part.open("wb") as handle:
                while True:
                    chunk = response.read(1024 * 256)
                    if not chunk:
                        break
                    handle.write(chunk)
                    digest.update(chunk)
                    written += len(chunk)
                    if total and sys.stderr.isatty():
                        pct = min(100, int(written * 100 / total))
                        sys.stderr.write(f"\r{spec.name}: {pct:3d}%")
                        sys.stderr.flush()
            if total and written != total:
                raise ModelVerificationError(
                    f"Download for {spec.name} ended early ({written}/{total} bytes)"
                )
            if written != spec.size:
                raise ModelVerificationError(
                    f"Downloaded {spec.name} has unexpected size {written} (expected {spec.size})"
                )
            actual = digest.hexdigest()
            if actual != spec.sha256:
                raise ModelVerificationError(f"Downloaded {spec.name} failed SHA-256: {actual}")
        if sys.stderr.isatty():
            sys.stderr.write("\n")
        os.replace(part, dest)
    except Exception:
        if part.exists():
            part.unlink()
        raise


def download_model(
    spec: ModelSpec,
    dest: Path | None = None,
    *,
    force: bool = False,
    timeout: float = 60.0,
    retries: int = 3,
) -> Path:
    target = dest or default_path(spec)
    if target.exists() and not force:
        if verify_model(spec, target):
            return target
        raise ModelVerificationError(
            f"Model exists at {target} but failed verification. Run with --force to re-download."
        )
    last_error: Exception | None = None
    for attempt in range(1, max(1, retries) + 1):
        try:
            _download_once(spec, target, timeout)
            return target
        except Exception as exc:  # network errors are retried; hash errors are terminal
            last_error = exc
            if isinstance(exc, ModelVerificationError) and "SHA-256" in str(exc):
                break
            if attempt < max(1, retries):
                time.sleep(0.5)
    assert last_error is not None
    raise last_error


def download_all(
    root: Path | None = None,
    *,
    only: str | None = None,
    force: bool = False,
) -> list[Path]:
    base = root if root is not None else model_root()
    specs = [MODELS[only]] if only else list(MODELS.values())
    return [download_model(spec, default_path(spec, base), force=force) for spec in specs]


def verify_all(root: Path | None = None, *, only: str | None = None) -> dict[str, bool]:
    base = root if root is not None else model_root()
    specs = [MODELS[only]] if only else list(MODELS.values())
    return {spec.name: verify_model(spec, default_path(spec, base)) for spec in specs}
