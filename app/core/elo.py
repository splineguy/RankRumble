"""
Core ELO rating functions - preserved from original main.py
These are pure functions with no side effects.
"""


def expected_score(rating_a: float, rating_b: float) -> float:
    """
    Calculate expected score for rating_a vs rating_b.
    Returns probability that A wins (0.0 to 1.0).
    """
    return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400.0))


def update_elo(rating_a: float, rating_b: float, score_a: float, k: int = 32) -> float:
    """
    Update Elo rating for a single match.

    Args:
        rating_a: Current rating of item A
        rating_b: Current rating of item B
        score_a: 1.0 if A wins, 0.0 if A loses, 0.5 if tie
        k: K-factor controlling rating change magnitude

    Returns:
        New rating for item A
    """
    exp_a = expected_score(rating_a, rating_b)
    return rating_a + k * (score_a - exp_a)
