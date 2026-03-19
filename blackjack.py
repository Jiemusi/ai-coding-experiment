from __future__ import annotations

from dataclasses import dataclass, field
import random
from typing import Iterable

SUITS = ("♠", "♥", "♦", "♣")
RANKS = ("2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A")
FACE_CARD_VALUE = 10
BLACKJACK = 21
DEALER_STAND_VALUE = 17
DEFAULT_BANKROLL = 100
BLACKJACK_PAYOUT = 1.5
RESHUFFLE_THRESHOLD = 15
TABLE_WIDTH = 66


@dataclass(frozen=True)
class Card:
    rank: str
    suit: str

    @property
    def value(self) -> int:
        if self.rank in {"J", "Q", "K"}:
            return FACE_CARD_VALUE
        if self.rank == "A":
            return 11
        return int(self.rank)

    @property
    def short_name(self) -> str:
        return f"{self.rank}{self.suit}"

    def render(self, *, hidden: bool = False) -> list[str]:
        if hidden:
            return [
                "┌───────┐",
                "│░░░░░░░│",
                "│░ BLACK│",
                "│░ JACK░│",
                "│░░░░░░░│",
                "└───────┘",
            ]

        top_label = f"{self.rank:<2}"
        bottom_label = f"{self.rank:>2}"
        return [
            "┌───────┐",
            f"│{top_label:<7}│",
            f"│{' ':^7}│",
            f"│{self.suit:^7}│",
            f"│{bottom_label:>7}│",
            "└───────┘",
        ]

    def __str__(self) -> str:
        return self.short_name


@dataclass
class Hand:
    cards: list[Card] = field(default_factory=list)

    def add(self, card: Card) -> None:
        self.cards.append(card)

    @property
    def value(self) -> int:
        total = sum(card.value for card in self.cards)
        aces = sum(1 for card in self.cards if card.rank == "A")
        while total > BLACKJACK and aces:
            total -= 10
            aces -= 1
        return total

    @property
    def is_blackjack(self) -> bool:
        return len(self.cards) == 2 and self.value == BLACKJACK

    @property
    def is_bust(self) -> bool:
        return self.value > BLACKJACK

    def render(self, *, hide_first_card: bool = False) -> str:
        if not self.cards:
            return "(empty hand)"

        rendered_cards = [
            card.render(hidden=hide_first_card and index == 0)
            for index, card in enumerate(self.cards)
        ]
        return "\n".join("  ".join(parts) for parts in zip(*rendered_cards))

    def display(self, *, hide_first_card: bool = False) -> str:
        if hide_first_card and self.cards:
            visible_cards = ["??", *(str(card) for card in self.cards[1:])]
            return " ".join(visible_cards)
        return " ".join(str(card) for card in self.cards)


class Deck:
    def __init__(self, num_decks: int = 1, *, rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()
        self.num_decks = num_decks
        self.cards: list[Card] = []
        self.reset()

    def reset(self) -> None:
        self.cards = [
            Card(rank=rank, suit=suit)
            for _ in range(self.num_decks)
            for suit in SUITS
            for rank in RANKS
        ]
        self._rng.shuffle(self.cards)

    def deal(self) -> Card:
        if not self.cards:
            self.reset()
        return self.cards.pop()

    def ensure_cards(self) -> None:
        if len(self.cards) < RESHUFFLE_THRESHOLD:
            print(f"\n{'=' * TABLE_WIDTH}")
            print(center_text("Not enough cards left in the shoe. Reshuffling..."))
            print(f"{'=' * TABLE_WIDTH}\n")
            self.reset()


@dataclass
class RoundResult:
    message: str
    bankroll_change: int


def center_text(text: str, fill: str = " ") -> str:
    return text.center(TABLE_WIDTH, fill)


def divider(char: str = "═") -> str:
    return char * TABLE_WIDTH


class BlackjackGame:
    def __init__(self, bankroll: int = DEFAULT_BANKROLL) -> None:
        self.bankroll = bankroll
        self.deck = Deck()

    def take_bet(self) -> int:
        print(divider("═"))
        print(center_text("PLACE YOUR BET"))
        print(divider("═"))
        while True:
            raw_bet = input(f"Bankroll ${self.bankroll} | Enter your bet: $").strip()
            if raw_bet.lower() in {"q", "quit", "exit"}:
                raise SystemExit
            if not raw_bet.isdigit():
                print("Please enter a whole-number bet.")
                continue
            bet = int(raw_bet)
            if bet <= 0:
                print("Your bet must be greater than zero.")
            elif bet > self.bankroll:
                print("You cannot bet more than your current bankroll.")
            else:
                return bet

    def initial_deal(self) -> tuple[Hand, Hand]:
        player = Hand([self.deck.deal(), self.deck.deal()])
        dealer = Hand([self.deck.deal(), self.deck.deal()])
        return player, dealer

    def show_table(self, player: Hand, dealer: Hand, *, reveal_dealer: bool = False, bet: int | None = None) -> None:
        dealer_value = str(dealer.value) if reveal_dealer else f"showing {dealer.cards[1].value}"
        bet_text = f" | Current bet: ${bet}" if bet is not None else ""

        print(f"\n╔{divider('═')}╗")
        print(f"║{center_text('♠ ♥ ♦ ♣  TERMINAL BLACKJACK  ♣ ♦ ♥ ♠')}║")
        print(f"║{center_text(f'Bankroll: ${self.bankroll}{bet_text}')}║")
        print(f"╠{divider('═')}╣")
        print(f"║ {('Dealer hand [' + dealer_value + ']'):<63}║")
        print(f"║ {('Cards: ' + dealer.display(hide_first_card=not reveal_dealer)):<63}║")
        for line in dealer.render(hide_first_card=not reveal_dealer).splitlines():
            print(f"║ {line:<63}║")
        print(f"╠{divider('─')}╣")
        print(f"║ {('Player hand [' + str(player.value) + ']'):<63}║")
        print(f"║ {('Cards: ' + player.display()):<63}║")
        for line in player.render().splitlines():
            print(f"║ {line:<63}║")
        print(f"╚{divider('═')}╝")

    def resolve_natural_blackjack(self, player: Hand, dealer: Hand, bet: int) -> RoundResult | None:
        if player.is_blackjack and dealer.is_blackjack:
            return RoundResult("Both you and the dealer have blackjack. Push!", 0)
        if player.is_blackjack:
            winnings = int(bet * BLACKJACK_PAYOUT)
            return RoundResult(f"Blackjack! You win ${winnings}.", winnings)
        if dealer.is_blackjack:
            return RoundResult("Dealer has blackjack. You lose.", -bet)
        return None

    def player_turn(self, player: Hand, dealer: Hand, bet: int) -> tuple[Hand, int, bool]:
        doubled_down = False
        while True:
            self.show_table(player, dealer, bet=bet)
            options = ["[H]it", "[S]tand"]
            can_double = len(player.cards) == 2 and self.bankroll >= bet * 2
            if can_double:
                options.append("[D]ouble down")
            choice = input(f"Choose an action: {', '.join(options)}: ").strip().lower()

            if choice in {"h", "hit"}:
                player.add(self.deck.deal())
                if player.is_bust:
                    self.show_table(player, dealer, bet=bet)
                    return player, bet, doubled_down
            elif choice in {"s", "stand"}:
                return player, bet, doubled_down
            elif can_double and choice in {"d", "double", "double down"}:
                bet *= 2
                player.add(self.deck.deal())
                doubled_down = True
                self.show_table(player, dealer, bet=bet)
                return player, bet, doubled_down
            else:
                print("Invalid choice. Please enter H, S, or D when available.")

    def dealer_turn(self, dealer: Hand) -> Hand:
        while dealer.value < DEALER_STAND_VALUE:
            dealer.add(self.deck.deal())
        return dealer

    def settle_round(self, player: Hand, dealer: Hand, bet: int) -> RoundResult:
        if player.is_bust:
            return RoundResult("You busted. Dealer wins.", -bet)

        self.dealer_turn(dealer)
        self.show_table(player, dealer, reveal_dealer=True, bet=bet)

        if dealer.is_bust:
            return RoundResult(f"Dealer busts. You win ${bet}!", bet)
        if player.value > dealer.value:
            return RoundResult(f"You win ${bet}!", bet)
        if player.value < dealer.value:
            return RoundResult("Dealer wins.", -bet)
        return RoundResult("Push! Your bet is returned.", 0)

    def play_round(self) -> None:
        self.deck.ensure_cards()
        bet = self.take_bet()
        player, dealer = self.initial_deal()

        self.show_table(player, dealer, bet=bet)
        natural_result = self.resolve_natural_blackjack(player, dealer, bet)
        if natural_result is None:
            player, final_bet, _ = self.player_turn(player, dealer, bet)
            result = self.settle_round(player, dealer, final_bet)
        else:
            self.show_table(player, dealer, reveal_dealer=True, bet=bet)
            result = natural_result

        self.bankroll += result.bankroll_change
        print(divider("═"))
        print(center_text(result.message))
        print(center_text(f"Bankroll: ${self.bankroll}"))
        print(divider("═"))
        print()

    def play(self) -> None:
        print(divider("═"))
        print(center_text("WELCOME TO TERMINAL BLACKJACK"))
        print(center_text("Try to get as close to 21 as possible without busting."))
        print(center_text("Enter 'q' at any bet prompt to quit."))
        print(divider("═"))
        print()

        while self.bankroll > 0:
            self.play_round()
            if self.bankroll <= 0:
                print(center_text("You're out of money. Game over!"))
                break

            again = input("Play another round? [Y/n]: ").strip().lower()
            if again in {"n", "no", "q", "quit"}:
                break

        print(center_text(f"Thanks for playing! You leave with ${self.bankroll}."))


def simulate_hand(cards: Iterable[tuple[str, str]]) -> Hand:
    """Helper for tests and quick experiments."""
    return Hand([Card(rank, suit) for rank, suit in cards])


if __name__ == "__main__":
    try:
        BlackjackGame().play()
    except (KeyboardInterrupt, EOFError, SystemExit):
        print("\nGoodbye!")
