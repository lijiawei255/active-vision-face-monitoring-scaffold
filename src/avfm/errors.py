"""Typed exceptions and actionable error helpers."""

from __future__ import annotations


class AvfmError(Exception):
    """Base class for errors that should be reported cleanly by the CLI."""


class ConfigError(AvfmError):
    """Invalid configuration value or unknown configuration key."""


class DependencyMissingError(AvfmError):
    """An optional runtime dependency is not installed."""


class ModelNotFoundError(AvfmError):
    """A required model file is missing."""


class ModelVerificationError(AvfmError):
    """A model file exists but its checksum does not match."""


class DetectorError(AvfmError):
    """A face detector failed to initialize or run."""


class CameraError(AvfmError):
    """A camera source could not be opened or read."""


class ActuatorError(AvfmError):
    """An actuator (servo) backend failed."""


class RecordingError(AvfmError):
    """A recorder could not write its output."""


def missing_dependency(package: str, hint: str) -> DependencyMissingError:
    """Build a consistent, copy-pasteable missing-dependency error."""
    return DependencyMissingError(f"{package} is not installed. {hint}")


def model_not_found(path: object, command: str) -> ModelNotFoundError:
    """Build a consistent, copy-pasteable missing-model error."""
    return ModelNotFoundError(f"Model file not found: {path}. Run: {command}")
