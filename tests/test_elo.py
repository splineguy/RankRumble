"""
Unit tests for ELO rating functions.
"""
import pytest
from app.core.elo import expected_score, update_elo


class TestExpectedScore:
    """Tests for the expected_score function."""

    def test_equal_ratings(self):
        """Equal ratings should give 0.5 expected score."""
        assert expected_score(1000, 1000) == 0.5

    def test_higher_rating_favored(self):
        """Higher rated player should have expected score > 0.5."""
        score = expected_score(1200, 1000)
        assert score > 0.5
        assert score < 1.0

    def test_lower_rating_unfavored(self):
        """Lower rated player should have expected score < 0.5."""
        score = expected_score(1000, 1200)
        assert score < 0.5
        assert score > 0.0

    def test_symmetric(self):
        """Expected scores should sum to 1."""
        score_a = expected_score(1200, 1000)
        score_b = expected_score(1000, 1200)
        assert abs(score_a + score_b - 1.0) < 0.0001

    def test_large_rating_difference(self):
        """Large rating difference should give very high/low expected score."""
        score = expected_score(1400, 1000)
        assert score > 0.9


class TestUpdateElo:
    """Tests for the update_elo function."""

    def test_winner_gains_rating(self):
        """Winner should gain rating."""
        new_rating = update_elo(1000, 1000, 1.0)
        assert new_rating > 1000

    def test_loser_loses_rating(self):
        """Loser should lose rating."""
        new_rating = update_elo(1000, 1000, 0.0)
        assert new_rating < 1000

    def test_tie_with_equal_ratings(self):
        """Tie between equal ratings should result in no change."""
        new_rating = update_elo(1000, 1000, 0.5)
        assert new_rating == 1000

    def test_upset_causes_large_change(self):
        """Upset (lower rated beats higher rated) causes larger rating change."""
        # Lower rated wins
        upset_gain = update_elo(1000, 1200, 1.0) - 1000
        # Higher rated wins
        expected_gain = update_elo(1200, 1000, 1.0) - 1200

        assert upset_gain > expected_gain

    def test_k_factor_affects_change(self):
        """Higher K-factor should cause larger rating changes."""
        change_k16 = update_elo(1000, 1000, 1.0, k=16) - 1000
        change_k32 = update_elo(1000, 1000, 1.0, k=32) - 1000
        change_k64 = update_elo(1000, 1000, 1.0, k=64) - 1000

        assert change_k16 < change_k32 < change_k64

    def test_rating_changes_are_symmetric(self):
        """Rating gained by winner should equal rating lost by loser."""
        old_a, old_b = 1000, 1100
        new_a = update_elo(old_a, old_b, 1.0)
        new_b = update_elo(old_b, old_a, 0.0)

        gain_a = new_a - old_a
        loss_b = old_b - new_b

        assert abs(gain_a - loss_b) < 0.0001

    def test_default_k_factor(self):
        """Default K-factor should be 32."""
        # With equal ratings and a win, expected change is K/2 = 16
        new_rating = update_elo(1000, 1000, 1.0)
        assert new_rating == 1016
