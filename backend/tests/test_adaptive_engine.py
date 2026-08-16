"""
Unit tests for the adaptive engine.
Run: pytest tests/test_adaptive_engine.py -v
"""
import pytest
from app.services.adaptive_engine import AdaptiveEngine


def test_strong_answer_increases_difficulty():
    engine = AdaptiveEngine(current_target=0.5)
    new_target, direction = engine.adjust("strong")
    assert new_target == pytest.approx(0.65, abs=0.001)
    assert direction == "up"


def test_weak_answer_decreases_difficulty():
    engine = AdaptiveEngine(current_target=0.5)
    new_target, direction = engine.adjust("weak")
    assert new_target == pytest.approx(0.35, abs=0.001)
    assert direction == "down"


def test_ok_answer_no_change():
    engine = AdaptiveEngine(current_target=0.5)
    new_target, direction = engine.adjust("ok")
    assert new_target == pytest.approx(0.5, abs=0.001)
    assert direction == "same"


def test_ceiling_clamped_at_1():
    engine = AdaptiveEngine(current_target=0.95)
    new_target, _ = engine.adjust("strong")
    assert new_target == 1.0


def test_floor_clamped_at_0():
    engine = AdaptiveEngine(current_target=0.05)
    new_target, _ = engine.adjust("weak")
    assert new_target == 0.0


def test_consecutive_strong_capped():
    engine = AdaptiveEngine(current_target=0.5)
    for _ in range(20):
        new_target, _ = engine.adjust("strong")
    assert new_target == 1.0


def test_consecutive_weak_floored():
    engine = AdaptiveEngine(current_target=0.5)
    for _ in range(20):
        new_target, _ = engine.adjust("weak")
    assert new_target == 0.0


def test_target_to_label_fundamentals():
    assert AdaptiveEngine.target_to_label(0.0) == "Fundamentals"
    assert AdaptiveEngine.target_to_label(0.2) == "Fundamentals"


def test_target_to_label_intermediate():
    assert AdaptiveEngine.target_to_label(0.4) == "Intermediate"
    assert AdaptiveEngine.target_to_label(0.5) == "Intermediate"


def test_target_to_label_advanced():
    assert AdaptiveEngine.target_to_label(0.7) == "Advanced"
    assert AdaptiveEngine.target_to_label(1.0) == "Advanced"
