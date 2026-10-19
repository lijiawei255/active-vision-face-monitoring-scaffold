"""EAR calibration: per-person, per-camera open-eye baseline."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True, slots=True)
class EarCalibration:
    baseline: float
    threshold: float
    samples: int
    ratio: float
    floor: float
    ceiling: float
    created_at: float
    source: str = ""
    frame_size: tuple[int, int] = (0, 0)
    model: str = "mediapipe"

    @classmethod
    def from_samples(
        cls,
        samples: list[float],
        *,
        ratio: float = 0.7,
        floor: float = 0.15,
        ceiling: float = 0.25,
        min_samples: int = 10,
        source: str = "",
        frame_size: tuple[int, int] = (0, 0),
        model: str = "mediapipe",
    ) -> EarCalibration:
        values = np.asarray([x for x in samples if np.isfinite(x) and x > 0], dtype=np.float64)
        if values.size < min_samples:
            raise ValueError(
                f"Not enough valid EAR samples: {values.size} (need at least {min_samples})"
            )
        baseline = float(np.median(values))
        threshold = float(np.clip(baseline * ratio, floor, ceiling))
        return cls(
            baseline=baseline,
            threshold=threshold,
            samples=int(values.size),
            ratio=ratio,
            floor=floor,
            ceiling=ceiling,
            created_at=time.time(),
            source=source,
            frame_size=frame_size,
            model=model,
        )

    def to_dict(self) -> dict:
        return {
            "baseline": self.baseline,
            "threshold": self.threshold,
            "samples": self.samples,
            "ratio": self.ratio,
            "floor": self.floor,
            "ceiling": self.ceiling,
            "created_at": self.created_at,
            "source": self.source,
            "frame_size": list(self.frame_size),
            "model": self.model,
        }

    @classmethod
    def from_dict(cls, data: dict) -> EarCalibration:
        return cls(
            baseline=float(data["baseline"]),
            threshold=float(data["threshold"]),
            samples=int(data["samples"]),
            ratio=float(data.get("ratio", 0.7)),
            floor=float(data.get("floor", 0.15)),
            ceiling=float(data.get("ceiling", 0.25)),
            created_at=float(data.get("created_at", 0.0)),
            source=str(data.get("source", "")),
            frame_size=tuple(data.get("frame_size", (0, 0))),
            model=str(data.get("model", "mediapipe")),
        )

    def save(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return target

    @classmethod
    def load(cls, path: str | Path) -> EarCalibration:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        calibration = cls.from_dict(data)
        if not 0 < calibration.threshold < 1:
            raise ValueError("Calibration threshold must be in (0, 1)")
        return calibration
