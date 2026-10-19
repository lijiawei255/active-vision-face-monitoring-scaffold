from __future__ import annotations

from avfm.fatigue.perclos import PerclosWindow


def make_window() -> PerclosWindow:
    return PerclosWindow(
        10.0,
        min_coverage=0.5,
        warmup_s=1.0,
        max_gap_s=1.0,
        min_samples=3,
    )


def test_value_and_coverage() -> None:
    window = make_window()
    window.add(0.0, closed=True, valid=True)
    window.add(1.0, closed=False, valid=True)
    window.add(2.0, closed=True, valid=True)
    assert window.value(2.0) == 2 / 3
    assert window.coverage(2.0) == 1.0
    assert window.ready(2.0)


def test_invalid_samples_reduce_coverage() -> None:
    window = make_window()
    window.add(0.0, closed=True, valid=True)
    window.add(1.0, closed=False, valid=False)
    window.add(2.0, closed=False, valid=False)
    assert window.value(2.0) == 1.0
    assert window.coverage(2.0) == 1 / 3
    assert not window.ready(2.0)


def test_eviction() -> None:
    window = make_window()
    window.add(0.0, closed=True, valid=True)
    window.add(1.0, closed=True, valid=True)
    assert window.value(1.0) == 1.0
    assert window.value(20.0) == 0.0


def test_ready_requires_recent_sample() -> None:
    window = make_window()
    window.add(0.0, closed=False, valid=True)
    window.add(1.0, closed=False, valid=True)
    window.add(2.0, closed=False, valid=True)
    assert window.ready(2.0)
    assert not window.ready(5.0)  # last sample is too old


def test_reset() -> None:
    window = make_window()
    window.add(0.0, closed=True, valid=True)
    window.reset()
    assert window.total_samples() == 0
    assert window.value(0.0) == 0.0
