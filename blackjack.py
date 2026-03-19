from __future__ import annotations

import curses
from dataclasses import dataclass, field
import random
import sys
import time
from typing import Iterable

SUITS = ("♠", "♥", "♦", "♣")
RANKS = ("2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A")
FACE_CARD_VALUE = 10
BLACKJACK = 21
DEALER_STAND_VALUE = 17
DEFAULT_BANKROLL = 100
BLACKJACK_PAYOUT = 1.5
RESHUFFLE_THRESHOLD = 15
CARD_HEIGHT = 6
TABLE_MIN_HEIGHT = 24
TABLE_MIN_WIDTH = 70
ANIMATION_DELAY = 0.14


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

    def needs_reshuffle(self) -> bool:
        return len(self.cards) < RESHUFFLE_THRESHOLD


@dataclass
class RoundResult:
    message: str
    bankroll_change: int


class CursesRenderer:
    def __init__(self, screen: curses.window, animation_delay: float = ANIMATION_DELAY) -> None:
        self.screen = screen
        self.animation_delay = animation_delay
        curses.curs_set(0)
        curses.noecho()
        curses.cbreak()
        self.screen.keypad(True)
        self.screen.nodelay(False)

    def pause(self, factor: float = 1.0) -> None:
        time.sleep(self.animation_delay * factor)

    def require_size(self) -> None:
        height, width = self.screen.getmaxyx()
        if height < TABLE_MIN_HEIGHT or width < TABLE_MIN_WIDTH:
            raise RuntimeError(
                f"Terminal too small for animation. Need at least {TABLE_MIN_WIDTH}x{TABLE_MIN_HEIGHT}."
            )

    def center_x(self, text: str) -> int:
        _, width = self.screen.getmaxyx()
        return max(0, (width - len(text)) // 2)

    def safe_addstr(self, y: int, x: int, text: str, attr: int = 0) -> None:
        height, width = self.screen.getmaxyx()
        if y < 0 or y >= height or x >= width:
            return
        trimmed = text[: max(0, width - x - 1)]
        if trimmed:
            self.screen.addstr(y, x, trimmed, attr)

    def draw_frame(self) -> None:
        self.screen.erase()
        height, width = self.screen.getmaxyx()
        horizontal = "═" * (width - 2)
        self.safe_addstr(0, 0, f"╔{horizontal}╗")
        for row in range(1, height - 1):
            self.safe_addstr(row, 0, "║")
            self.safe_addstr(row, width - 1, "║")
        self.safe_addstr(height - 1, 0, f"╚{horizontal}╝")

    def draw_header(self, bankroll: int, bet: int | None) -> None:
        _, width = self.screen.getmaxyx()
        title = "♠ ♥ ♦ ♣  ANIMATED TERMINAL BLACKJACK  ♣ ♦ ♥ ♠"
        details = f"Bankroll: ${bankroll}"
        if bet is not None:
            details += f"   Current bet: ${bet}"
        self.safe_addstr(1, max(2, (width - len(title)) // 2), title, curses.A_BOLD)
        self.safe_addstr(3, max(2, (width - len(details)) // 2), details)
        self.safe_addstr(4, 2, "─" * (width - 4))

    def draw_hand(self, y: int, label: str, hand: Hand, *, reveal: bool) -> int:
        if reveal:
            summary_value = str(hand.value)
        elif len(hand.cards) > 1:
            summary_value = f"showing {hand.cards[1].value}"
        elif len(hand.cards) == 1:
            summary_value = "showing ?"
        else:
            summary_value = "waiting..."
        summary = f"{label} [{summary_value}]"
        cards_line = f"Cards: {hand.display(hide_first_card=not reveal)}"
        self.safe_addstr(y, 4, summary, curses.A_BOLD)
        self.safe_addstr(y + 1, 4, cards_line)
        for offset, line in enumerate(hand.render(hide_first_card=not reveal).splitlines()):
            self.safe_addstr(y + 3 + offset, 6, line)
        return y + 3 + CARD_HEIGHT

    def draw_status(self, message: str, prompt: str | None = None) -> None:
        height, width = self.screen.getmaxyx()
        self.safe_addstr(height - 5, 2, "─" * (width - 4))
        self.safe_addstr(height - 4, 4, message[: width - 8], curses.A_BOLD)
        if prompt:
            self.safe_addstr(height - 3, 4, prompt[: width - 8])

    def render_table(
        self,
        player: Hand,
        dealer: Hand,
        *,
        bankroll: int,
        bet: int | None,
        reveal_dealer: bool,
        message: str,
        prompt: str | None = None,
    ) -> None:
        self.require_size()
        self.draw_frame()
        self.draw_header(bankroll, bet)
        next_y = self.draw_hand(6, "Dealer", dealer, reveal=reveal_dealer)
        self.safe_addstr(next_y + 1, 2, "─" * (self.screen.getmaxyx()[1] - 4))
        self.draw_hand(next_y + 3, "Player", player, reveal=True)
        self.draw_status(message, prompt)
        self.screen.refresh()

    def splash(self) -> None:
        self.require_size()
        self.draw_frame()
        title = "WELCOME TO ANIMATED TERMINAL BLACKJACK"
        subtitle = "Watch cards deal onto the table and play with H / S / D."
        hint = "Press any key to start."
        self.safe_addstr(8, self.center_x(title), title, curses.A_BOLD)
        self.safe_addstr(10, self.center_x(subtitle), subtitle)
        self.safe_addstr(12, self.center_x(hint), hint)
        self.screen.refresh()
        self.screen.getch()

    def prompt_bet(self, bankroll: int) -> int:
        curses.echo()
        while True:
            self.draw_frame()
            self.draw_header(bankroll, None)
            self.draw_status("Place your bet for the next hand.", "Enter a whole number, or Q to quit: ")
            height, _ = self.screen.getmaxyx()
            self.safe_addstr(height - 2, 4, "Bet: $")
            self.screen.refresh()
            raw = self.screen.getstr(height - 2, 10, 10).decode("utf-8", errors="ignore").strip()
            if raw.lower() in {"q", "quit", "exit"}:
                curses.noecho()
                raise SystemExit
            if raw.isdigit() and 0 < int(raw) <= bankroll:
                curses.noecho()
                return int(raw)
            self.draw_status("Invalid bet. It must be a whole number within your bankroll.")
            self.screen.refresh()
            self.pause(1.3)

    def prompt_action(self, *, can_double: bool, player: Hand, dealer: Hand, bankroll: int, bet: int) -> str:
        prompt = "Choose [H]it or [S]tand"
        if can_double:
            prompt += ", or [D]ouble down"
        prompt += "."
        self.render_table(
            player,
            dealer,
            bankroll=bankroll,
            bet=bet,
            reveal_dealer=False,
            message="Your move.",
            prompt=prompt,
        )
        while True:
            key = self.screen.getkey().lower()
            if key in {"h", "s"}:
                return key
            if can_double and key == "d":
                return key

    def prompt_continue(self, bankroll: int) -> bool:
        self.draw_frame()
        self.draw_header(bankroll, None)
        self.draw_status("Play another round?", "Press Y to continue, N to leave the table.")
        self.screen.refresh()
        while True:
            key = self.screen.getkey().lower()
            if key in {"y", "n"}:
                return key == "y"

    def announce(self, player: Hand, dealer: Hand, *, bankroll: int, bet: int | None, reveal_dealer: bool, message: str) -> None:
        self.render_table(
            player,
            dealer,
            bankroll=bankroll,
            bet=bet,
            reveal_dealer=reveal_dealer,
            message=message,
        )


class BlackjackGame:
    def __init__(self, bankroll: int = DEFAULT_BANKROLL) -> None:
        self.bankroll = bankroll
        self.deck = Deck()

    def resolve_natural_blackjack(self, player: Hand, dealer: Hand, bet: int) -> RoundResult | None:
        if player.is_blackjack and dealer.is_blackjack:
            return RoundResult("Both you and the dealer have blackjack. Push!", 0)
        if player.is_blackjack:
            winnings = int(bet * BLACKJACK_PAYOUT)
            return RoundResult(f"Blackjack! You win ${winnings}.", winnings)
        if dealer.is_blackjack:
            return RoundResult("Dealer has blackjack. You lose.", -bet)
        return None

    def deal_opening_hands(self, renderer: CursesRenderer, bet: int) -> tuple[Hand, Hand]:
        player = Hand()
        dealer = Hand()
        sequence = [
            (player, "Dealing your first card..."),
            (dealer, "Dealer draws a card..."),
            (player, "Dealing your second card..."),
            (dealer, "Dealer takes the hole card..."),
        ]
        for hand, message in sequence:
            hand.add(self.deck.deal())
            renderer.announce(
                player,
                dealer,
                bankroll=self.bankroll,
                bet=bet,
                reveal_dealer=False,
                message=message,
            )
            renderer.pause()
        return player, dealer

    def player_turn(self, renderer: CursesRenderer, player: Hand, dealer: Hand, bet: int) -> int:
        while True:
            can_double = len(player.cards) == 2 and self.bankroll >= bet * 2
            choice = renderer.prompt_action(
                can_double=can_double,
                player=player,
                dealer=dealer,
                bankroll=self.bankroll,
                bet=bet,
            )

            if choice == "h":
                player.add(self.deck.deal())
                renderer.announce(
                    player,
                    dealer,
                    bankroll=self.bankroll,
                    bet=bet,
                    reveal_dealer=False,
                    message="You take a hit.",
                )
                renderer.pause()
                if player.is_bust:
                    return bet
            elif choice == "s":
                renderer.announce(
                    player,
                    dealer,
                    bankroll=self.bankroll,
                    bet=bet,
                    reveal_dealer=False,
                    message="You stand.",
                )
                renderer.pause(0.8)
                return bet
            elif choice == "d" and can_double:
                bet *= 2
                player.add(self.deck.deal())
                renderer.announce(
                    player,
                    dealer,
                    bankroll=self.bankroll,
                    bet=bet,
                    reveal_dealer=False,
                    message="Double down! One final card slides your way.",
                )
                renderer.pause(1.2)
                return bet

    def settle_round(
        self,
        player: Hand,
        dealer: Hand,
        bet: int,
        renderer: CursesRenderer | None = None,
    ) -> RoundResult:
        if player.is_bust:
            return RoundResult("You busted. Dealer wins.", -bet)

        if renderer is not None:
            renderer.announce(
                player,
                dealer,
                bankroll=self.bankroll,
                bet=bet,
                reveal_dealer=True,
                message="Dealer reveals the hole card.",
            )
            renderer.pause()

        while dealer.value < DEALER_STAND_VALUE:
            dealer.add(self.deck.deal())
            if renderer is not None:
                renderer.announce(
                    player,
                    dealer,
                    bankroll=self.bankroll,
                    bet=bet,
                    reveal_dealer=True,
                    message="Dealer hits...",
                )
                renderer.pause()

        if dealer.is_bust:
            return RoundResult(f"Dealer busts. You win ${bet}!", bet)
        if player.value > dealer.value:
            return RoundResult(f"You win ${bet}!", bet)
        if player.value < dealer.value:
            return RoundResult("Dealer wins.", -bet)
        return RoundResult("Push! Your bet is returned.", 0)

    def play_round(self, renderer: CursesRenderer) -> None:
        if self.deck.needs_reshuffle():
            self.deck.reset()
            empty = Hand()
            renderer.announce(
                empty,
                empty,
                bankroll=self.bankroll,
                bet=None,
                reveal_dealer=True,
                message="The shoe is low. Shuffling fresh cards...",
            )
            renderer.pause(1.5)

        bet = renderer.prompt_bet(self.bankroll)
        player, dealer = self.deal_opening_hands(renderer, bet)

        natural_result = self.resolve_natural_blackjack(player, dealer, bet)
        if natural_result is None:
            bet = self.player_turn(renderer, player, dealer, bet)
            result = self.settle_round(player, dealer, bet, renderer)
        else:
            renderer.announce(
                player,
                dealer,
                bankroll=self.bankroll,
                bet=bet,
                reveal_dealer=True,
                message="Natural blackjack check.",
            )
            renderer.pause(1.1)
            result = natural_result

        self.bankroll += result.bankroll_change
        renderer.announce(
            player,
            dealer,
            bankroll=self.bankroll,
            bet=bet,
            reveal_dealer=True,
            message=result.message,
        )
        renderer.pause(1.8)

    def run_animated(self, screen: curses.window) -> None:
        renderer = CursesRenderer(screen)
        renderer.splash()

        while self.bankroll > 0:
            self.play_round(renderer)
            if self.bankroll <= 0:
                empty = Hand()
                renderer.announce(
                    empty,
                    empty,
                    bankroll=self.bankroll,
                    bet=None,
                    reveal_dealer=True,
                    message="You're out of money. Game over!",
                )
                renderer.pause(2.0)
                break
            if not renderer.prompt_continue(self.bankroll):
                break

        empty = Hand()
        renderer.announce(
            empty,
            empty,
            bankroll=self.bankroll,
            bet=None,
            reveal_dealer=True,
            message=f"Thanks for playing! You leave with ${self.bankroll}.",
        )
        renderer.pause(2.0)

    def play(self) -> None:
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            raise RuntimeError("Animated mode requires an interactive terminal.")
        curses.wrapper(self.run_animated)


def simulate_hand(cards: Iterable[tuple[str, str]]) -> Hand:
    """Helper for tests and quick experiments."""
    return Hand([Card(rank, suit) for rank, suit in cards])


if __name__ == "__main__":
    try:
        BlackjackGame().play()
    except (KeyboardInterrupt, EOFError, SystemExit):
        print("\nGoodbye!")
    except RuntimeError as error:
        print(error)
