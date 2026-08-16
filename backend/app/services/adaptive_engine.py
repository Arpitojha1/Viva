"""
Viva — Adaptive Engine
Manages difficulty_target based on answer scores.
Pure business logic — no DB or LLM dependencies. Fully unit-testable.
"""
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


class AdaptiveEngine:
    """
    Adjusts the difficulty_target (0.0–1.0 float) based on answer quality.

    difficulty_target is a continuous proxy for chapter_position in the knowledge base:
        0.0 = very early chapters (fundamentals)
        0.5 = middle chapters (intermediate)
        1.0 = late chapters (advanced topics)

    Adjustment rules (from OD5 in implementation plan):
        strong → +0.15 (harder)
        ok     → +0.00 (no change)
        weak   → -0.15 (easier)

    Both floor (0.0) and ceiling (1.0) are hard-clamped.
    """

    STEP = 0.15

    # Maps difficulty_target float to display label
    @staticmethod
    def target_to_label(target: float) -> str:
        if target < 0.35:
            return "Fundamentals"
        elif target < 0.65:
            return "Intermediate"
        else:
            return "Advanced"

    def __init__(self, current_target: float = 0.5):
        self.difficulty_target = max(0.0, min(1.0, current_target))

    def adjust(self, score: str) -> Tuple[float, str]:
        """
        Adjust difficulty_target based on score.

        Args:
            score: One of 'weak', 'ok', 'strong'.

        Returns:
            Tuple of (new_difficulty_target, direction_str).
            direction_str is one of 'up', 'same', 'down'.
        """
        old_target = self.difficulty_target

        if score == "strong":
            self.difficulty_target = min(1.0, self.difficulty_target + self.STEP)
            direction = "up"
        elif score == "weak":
            self.difficulty_target = max(0.0, self.difficulty_target - self.STEP)
            direction = "down"
        else:  # 'ok'
            direction = "same"

        logger.debug(
            "AdaptiveEngine: score=%s | %.2f → %.2f (%s)",
            score, old_target, self.difficulty_target, direction
        )
        return self.difficulty_target, direction
