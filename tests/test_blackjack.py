import random
import unittest

from blackjack import BlackjackGame, Card, Deck, Hand, simulate_hand


class HandValueTests(unittest.TestCase):
    def test_ace_adjusts_to_prevent_bust(self) -> None:
        hand = simulate_hand([("A", "♠"), ("9", "♦"), ("5", "♣")])
        self.assertEqual(hand.value, 15)

    def test_blackjack_detected_for_two_card_twenty_one(self) -> None:
        hand = simulate_hand([("A", "♠"), ("K", "♦")])
        self.assertTrue(hand.is_blackjack)

    def test_three_card_twenty_one_is_not_blackjack(self) -> None:
        hand = simulate_hand([("A", "♠"), ("5", "♦"), ("5", "♣")])
        self.assertFalse(hand.is_blackjack)
        self.assertEqual(hand.value, 21)

    def test_hidden_hand_render_masks_first_card(self) -> None:
        hand = simulate_hand([("A", "♠"), ("K", "♦")])
        rendered = hand.render(hide_first_card=True)
        self.assertIn("BLACK", rendered)
        self.assertIn("K", rendered)

    def test_empty_hand_render_is_placeholder(self) -> None:
        self.assertEqual(Hand().render(), "(empty hand)")


class DeckTests(unittest.TestCase):
    def test_deck_reset_restores_full_size(self) -> None:
        deck = Deck(rng=random.Random(0))
        drawn = [deck.deal() for _ in range(52)]
        self.assertEqual(len(drawn), 52)
        self.assertEqual(len(deck.cards), 0)
        deck.reset()
        self.assertEqual(len(deck.cards), 52)

    def test_card_string_representation(self) -> None:
        self.assertEqual(str(Card("Q", "♥")), "Q♥")

    def test_card_render_contains_rank_and_suit(self) -> None:
        rendered = "\n".join(Card("Q", "♥").render())
        self.assertIn("Q", rendered)
        self.assertIn("♥", rendered)

    def test_reshuffle_threshold_detected(self) -> None:
        deck = Deck(rng=random.Random(0))
        deck.cards = deck.cards[:10]
        self.assertTrue(deck.needs_reshuffle())


class PayoutTests(unittest.TestCase):
    def test_player_blackjack_pays_three_to_two(self) -> None:
        game = BlackjackGame(bankroll=100)
        player = simulate_hand([("A", "♠"), ("K", "♣")])
        dealer = simulate_hand([("9", "♦"), ("7", "♥")])
        result = game.resolve_natural_blackjack(player, dealer, bet=20)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.bankroll_change, 30)

    def test_push_returns_zero_change(self) -> None:
        game = BlackjackGame(bankroll=100)
        player = simulate_hand([("10", "♠"), ("8", "♣")])
        dealer = simulate_hand([("9", "♦"), ("9", "♥")])
        result = game.settle_round(player, dealer, bet=15)
        self.assertEqual(result.bankroll_change, 0)


if __name__ == "__main__":
    unittest.main()
