"""Fatigue detection and calibration."""

from avfm.fatigue.calibration import EarCalibration
from avfm.fatigue.monitor import FatigueMonitor
from avfm.fatigue.perclos import PerclosWindow

__all__ = ["EarCalibration", "FatigueMonitor", "PerclosWindow"]
