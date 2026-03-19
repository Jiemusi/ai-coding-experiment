from __future__ import annotations

from dataclasses import dataclass, field
import os
import random
import sys
import tkinter as tk
from typing import Callable, Iterable

SUITS = ("♠", "♥", "♦", "♣")
RANKS = ("2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A")
RED_SUITS = {"♥", "♦"}
FACE_CARD_VALUE = 10
BLACKJACK = 21
DEALER_STAND_VALUE = 17
DEFAULT_BANKROLL = 100
BLACKJACK_PAYOUT = 1.5
RESHUFFLE_THRESHOLD = 15
CANVAS_WIDTH = 980
CANVAS_HEIGHT = 640
CARD_WIDTH = 96
CARD_HEIGHT = 136
CARD_GAP = 28
DECK_X = 80
DECK_Y = 225
PLAYER_Y = 390
DEALER_Y = 120
HAND_START_X = 280
ANIMATION_FRAMES = 18
ANIMATION_DELAY_MS = 16


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

    def display(self, *, hide_hole_card: bool = False) -> str:
        if hide_hole_card and len(self.cards) >= 2:
            visible_cards = [str(self.cards[0]), "??", *(str(card) for card in self.cards[2:])]
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


@dataclass
class MovingCard:
    card: Card
    owner: str
    index: int
    hidden: bool
    x: float
    y: float


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

    def settle_round(self, player: Hand, dealer: Hand, bet: int) -> RoundResult:
        if player.is_bust:
            return RoundResult("You busted. Dealer wins.", -bet)

        while dealer.value < DEALER_STAND_VALUE:
            dealer.add(self.deck.deal())

        if dealer.is_bust:
            return RoundResult(f"Dealer busts. You win ${bet}!", bet)
        if player.value > dealer.value:
            return RoundResult(f"You win ${bet}!", bet)
        if player.value < dealer.value:
            return RoundResult("Dealer wins.", -bet)
        return RoundResult("Push! Your bet is returned.", 0)


class AnimatedBlackjackApp:
    def __init__(self, game: BlackjackGame) -> None:
        self.game = game
        self.root = tk.Tk()
        self.root.title("Animated Blackjack")
        self.root.geometry(f"{CANVAS_WIDTH}x{CANVAS_HEIGHT}")
        self.root.minsize(CANVAS_WIDTH, CANVAS_HEIGHT)
        self.root.configure(bg="#123524")

        self.bankroll_var = tk.StringVar()
        self.bet_var = tk.StringVar(value="10")
        self.status_var = tk.StringVar(value="Welcome! Choose your bet and click Deal Hand.")

        self.current_bet = 10
        self.player_hand = Hand()
        self.dealer_hand = Hand()
        self.reveal_dealer = False
        self.round_active = False
        self.awaiting_next_round = False
        self.animation_active = False
        self.moving_card: MovingCard | None = None

        self.build_ui()
        self.update_bankroll_label()
        self.update_controls()
        self.render_table()

    def build_ui(self) -> None:
        top_bar = tk.Frame(self.root, bg="#123524", pady=12)
        top_bar.pack(fill="x")

        tk.Label(
            top_bar,
            text="ANIMATED BLACKJACK",
            font=("Helvetica", 20, "bold"),
            fg="#f8f4e3",
            bg="#123524",
        ).pack(side="left", padx=18)

        self.bankroll_label = tk.Label(
            top_bar,
            textvariable=self.bankroll_var,
            font=("Helvetica", 14, "bold"),
            fg="#f8f4e3",
            bg="#123524",
        )
        self.bankroll_label.pack(side="left", padx=16)

        bet_frame = tk.Frame(top_bar, bg="#123524")
        bet_frame.pack(side="right", padx=18)
        tk.Label(bet_frame, text="Bet", font=("Helvetica", 12, "bold"), fg="#f8f4e3", bg="#123524").pack(side="left")
        self.bet_entry = tk.Entry(bet_frame, textvariable=self.bet_var, width=8, justify="center", font=("Helvetica", 12))
        self.bet_entry.pack(side="left", padx=8)

        self.deal_button = tk.Button(top_bar, text="Deal Hand", command=self.start_or_advance_round, width=12, font=("Helvetica", 12, "bold"))
        self.deal_button.pack(side="right", padx=8)

        self.canvas = tk.Canvas(
            self.root,
            width=CANVAS_WIDTH,
            height=CANVAS_HEIGHT - 150,
            bg="#1f6f43",
            highlightthickness=0,
        )
        self.canvas.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        controls = tk.Frame(self.root, bg="#123524", pady=10)
        controls.pack(fill="x")
        self.hit_button = tk.Button(controls, text="Hit", command=self.player_hit, width=10, font=("Helvetica", 12, "bold"))
        self.hit_button.pack(side="left", padx=12)
        self.stand_button = tk.Button(controls, text="Stand", command=self.player_stand, width=10, font=("Helvetica", 12, "bold"))
        self.stand_button.pack(side="left", padx=12)
        self.double_button = tk.Button(controls, text="Double", command=self.player_double, width=10, font=("Helvetica", 12, "bold"))
        self.double_button.pack(side="left", padx=12)
        self.status_label = tk.Label(
            controls,
            textvariable=self.status_var,
            font=("Helvetica", 12, "bold"),
            fg="#f8f4e3",
            bg="#123524",
            anchor="w",
        )
        self.status_label.pack(side="left", fill="x", expand=True, padx=18)

    def update_bankroll_label(self) -> None:
        self.bankroll_var.set(f"Bankroll: ${self.game.bankroll}    Current bet: ${self.current_bet}")

    def parse_bet(self) -> int | None:
        raw_bet = self.bet_var.get().strip()
        if not raw_bet.isdigit():
            self.status_var.set("Enter a whole-number bet before dealing.")
            return None
        bet = int(raw_bet)
        if bet <= 0:
            self.status_var.set("Your bet must be greater than zero.")
            return None
        if bet > self.game.bankroll:
            self.status_var.set("You cannot bet more than your bankroll.")
            return None
        return bet

    def update_controls(self) -> None:
        can_double = self.round_active and len(self.player_hand.cards) == 2 and self.game.bankroll >= self.current_bet * 2
        action_state = tk.NORMAL if self.round_active and not self.animation_active else tk.DISABLED
        self.hit_button.config(state=action_state)
        self.stand_button.config(state=action_state)
        self.double_button.config(state=tk.NORMAL if can_double and not self.animation_active else tk.DISABLED)

        can_deal = not self.round_active and not self.animation_active and self.game.bankroll > 0
        self.deal_button.config(state=tk.NORMAL if can_deal else tk.DISABLED)
        self.deal_button.config(text="Next Round" if self.awaiting_next_round else "Deal Hand")
        self.bet_entry.config(state=tk.NORMAL if can_deal else tk.DISABLED)

    def hand_card_position(self, owner: str, index: int) -> tuple[int, int]:
        x = HAND_START_X + index * (CARD_WIDTH + CARD_GAP)
        y = PLAYER_Y if owner == "player" else DEALER_Y
        return x, y

    def set_status(self, message: str) -> None:
        self.status_var.set(message)
        self.render_table()

    def start_or_advance_round(self) -> None:
        if self.awaiting_next_round:
            self.awaiting_next_round = False
        self.start_round()

    def start_round(self) -> None:
        if self.animation_active or self.game.bankroll <= 0:
            return

        bet = self.parse_bet()
        if bet is None:
            self.update_controls()
            self.render_table()
            return

        if self.game.deck.needs_reshuffle():
            self.game.deck.reset()
            self.status_var.set("Shoe was running low, so the deck was reshuffled.")

        self.current_bet = bet
        self.player_hand = Hand()
        self.dealer_hand = Hand()
        self.reveal_dealer = False
        self.round_active = False
        self.awaiting_next_round = False
        self.moving_card = None

        self.update_bankroll_label()
        self.update_controls()
        self.render_table()

        sequence = [
            ("player", False, "Dealing your first card..."),
            ("dealer", False, "Dealer takes the up card..."),
            ("player", False, "Dealing your second card..."),
            ("dealer", True, "Dealer takes the hole card..."),
        ]
        self.deal_sequence(sequence, 0)

    def deal_sequence(self, sequence: list[tuple[str, bool, str]], index: int) -> None:
        if index >= len(sequence):
            self.finish_opening_deal()
            return

        owner, hidden, message = sequence[index]
        target_hand = self.player_hand if owner == "player" else self.dealer_hand
        card = self.game.deck.deal()
        target_hand.add(card)
        card_index = len(target_hand.cards) - 1
        self.status_var.set(message)
        self.animate_card(
            card=card,
            owner=owner,
            index=card_index,
            hidden=hidden,
            on_complete=lambda: self.deal_sequence(sequence, index + 1),
        )

    def finish_opening_deal(self) -> None:
        result = self.game.resolve_natural_blackjack(self.player_hand, self.dealer_hand, self.current_bet)
        if result is not None:
            self.reveal_dealer = True
            self.game.bankroll += result.bankroll_change
            self.awaiting_next_round = True
            self.status_var.set(f"{result.message} Review the table, then click Next Round.")
            self.update_bankroll_label()
            self.update_controls()
            self.render_table()
            return

        self.round_active = True
        self.status_var.set("Your move. Choose Hit, Stand, or Double.")
        self.update_controls()
        self.render_table()

    def animate_card(
        self,
        *,
        card: Card,
        owner: str,
        index: int,
        hidden: bool,
        on_complete: Callable[[], None],
    ) -> None:
        target_x, target_y = self.hand_card_position(owner, index)
        self.animation_active = True

        def step(frame: int) -> None:
            progress = frame / ANIMATION_FRAMES
            current_x = DECK_X + (target_x - DECK_X) * progress
            current_y = DECK_Y + (target_y - DECK_Y) * progress
            self.moving_card = MovingCard(card=card, owner=owner, index=index, hidden=hidden, x=current_x, y=current_y)
            self.render_table()
            if frame < ANIMATION_FRAMES:
                self.root.after(ANIMATION_DELAY_MS, lambda: step(frame + 1))
            else:
                self.moving_card = None
                self.animation_active = False
                self.update_controls()
                self.render_table()
                on_complete()

        step(0)

    def player_hit(self) -> None:
        if not self.round_active or self.animation_active:
            return
        self.round_active = False
        self.update_controls()
        card = self.game.deck.deal()
        self.player_hand.add(card)
        self.status_var.set("You take a hit.")
        self.animate_card(
            card=card,
            owner="player",
            index=len(self.player_hand.cards) - 1,
            hidden=False,
            on_complete=self.after_player_hit,
        )

    def after_player_hit(self) -> None:
        if self.player_hand.is_bust:
            self.reveal_dealer = True
            self.finish_round(self.game.settle_round(self.player_hand, self.dealer_hand, self.current_bet))
            return
        self.round_active = True
        self.status_var.set("Your move. Choose another action.")
        self.update_controls()
        self.render_table()

    def player_stand(self) -> None:
        if not self.round_active or self.animation_active:
            return
        self.round_active = False
        self.reveal_dealer = True
        self.status_var.set("Dealer reveals the hole card.")
        self.update_controls()
        self.render_table()
        self.root.after(500, self.dealer_play_step)

    def player_double(self) -> None:
        if not self.round_active or self.animation_active:
            return
        if len(self.player_hand.cards) != 2 or self.game.bankroll < self.current_bet * 2:
            self.status_var.set("You can only double on your first decision and within your bankroll.")
            self.render_table()
            return
        self.round_active = False
        self.current_bet *= 2
        self.update_bankroll_label()
        self.update_controls()
        card = self.game.deck.deal()
        self.player_hand.add(card)
        self.status_var.set("Double down! One final card is on the way.")
        self.animate_card(
            card=card,
            owner="player",
            index=len(self.player_hand.cards) - 1,
            hidden=False,
            on_complete=self.after_double_down,
        )

    def after_double_down(self) -> None:
        if self.player_hand.is_bust:
            self.reveal_dealer = True
            self.finish_round(self.game.settle_round(self.player_hand, self.dealer_hand, self.current_bet))
            return
        self.reveal_dealer = True
        self.status_var.set("Dealer reveals the hole card.")
        self.render_table()
        self.root.after(500, self.dealer_play_step)

    def dealer_play_step(self) -> None:
        if self.dealer_hand.value >= DEALER_STAND_VALUE:
            self.finish_round(self.game.settle_round(self.player_hand, self.dealer_hand, self.current_bet))
            return

        card = self.game.deck.deal()
        self.dealer_hand.add(card)
        self.status_var.set("Dealer hits...")
        self.animate_card(
            card=card,
            owner="dealer",
            index=len(self.dealer_hand.cards) - 1,
            hidden=False,
            on_complete=self.dealer_play_step,
        )

    def finish_round(self, result: RoundResult) -> None:
        self.game.bankroll += result.bankroll_change
        self.round_active = False
        self.awaiting_next_round = self.game.bankroll > 0
        self.reveal_dealer = True
        if self.game.bankroll > 0:
            self.status_var.set(f"{result.message} The result stays on screen until you click Next Round.")
        else:
            self.status_var.set(f"{result.message} You are out of chips.")
        self.update_bankroll_label()
        self.update_controls()
        self.render_table()

    def draw_card(self, x: float, y: float, card: Card, *, hidden: bool = False) -> None:
        x1 = x + CARD_WIDTH
        y1 = y + CARD_HEIGHT
        if hidden:
            self.canvas.create_rectangle(x, y, x1, y1, fill="#19376d", outline="#f6f1d1", width=3)
            self.canvas.create_rectangle(x + 10, y + 10, x1 - 10, y1 - 10, outline="#f6f1d1", width=2)
            self.canvas.create_text((x + x1) / 2, (y + y1) / 2 - 12, text="BLACK", fill="#f6f1d1", font=("Helvetica", 15, "bold"))
            self.canvas.create_text((x + x1) / 2, (y + y1) / 2 + 12, text="JACK", fill="#f6f1d1", font=("Helvetica", 15, "bold"))
            return

        suit_color = "#b31312" if card.suit in RED_SUITS else "#111111"
        self.canvas.create_rectangle(x, y, x1, y1, fill="#fffdf7", outline="#222222", width=3)
        self.canvas.create_text(x + 18, y + 18, text=card.rank, fill=suit_color, font=("Helvetica", 16, "bold"))
        self.canvas.create_text((x + x1) / 2, (y + y1) / 2, text=card.suit, fill=suit_color, font=("Helvetica", 34, "bold"))
        self.canvas.create_text(x1 - 18, y1 - 18, text=card.rank, fill=suit_color, font=("Helvetica", 16, "bold"))

    def draw_hand(self, owner: str, hand: Hand) -> None:
        y = PLAYER_Y if owner == "player" else DEALER_Y
        title_y = y - 36
        if owner == "dealer":
            if self.reveal_dealer:
                value_text = str(hand.value)
            elif hand.cards:
                value_text = f"showing {hand.cards[0].value}"
            else:
                value_text = "waiting..."
            heading = f"Dealer [{value_text}]"
            cards_text = hand.display(hide_hole_card=not self.reveal_dealer)
        else:
            heading = f"Player [{hand.value if hand.cards else 0}]"
            cards_text = hand.display()

        self.canvas.create_text(HAND_START_X, title_y, text=heading, fill="#f8f4e3", font=("Helvetica", 18, "bold"), anchor="w")
        self.canvas.create_text(HAND_START_X, title_y + 24, text=cards_text or "(empty hand)", fill="#d7f9e9", font=("Helvetica", 12), anchor="w")

        for index, card in enumerate(hand.cards):
            if self.moving_card is not None and self.moving_card.owner == owner and self.moving_card.index == index:
                continue
            x, card_y = self.hand_card_position(owner, index)
            hidden = owner == "dealer" and not self.reveal_dealer and index == 1
            self.draw_card(x, card_y, card, hidden=hidden)

    def render_table(self) -> None:
        self.canvas.delete("all")
        self.canvas.create_rectangle(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT, fill="#1f6f43", outline="")
        self.canvas.create_oval(190, 40, 920, 600, outline="#d9b95b", width=4)
        self.canvas.create_text(CANVAS_WIDTH / 2, 34, text="BLACKJACK TABLE", fill="#f6e7b7", font=("Helvetica", 22, "bold"))

        self.canvas.create_rectangle(DECK_X, DECK_Y, DECK_X + CARD_WIDTH, DECK_Y + CARD_HEIGHT, fill="#7f1020", outline="#f6f1d1", width=3)
        self.canvas.create_text(DECK_X + CARD_WIDTH / 2, DECK_Y + CARD_HEIGHT / 2 - 10, text="DECK", fill="#f6f1d1", font=("Helvetica", 16, "bold"))
        self.canvas.create_text(DECK_X + CARD_WIDTH / 2, DECK_Y + CARD_HEIGHT / 2 + 16, text=str(len(self.game.deck.cards)), fill="#f6f1d1", font=("Helvetica", 12, "bold"))

        self.draw_hand("dealer", self.dealer_hand)
        self.draw_hand("player", self.player_hand)

        if self.moving_card is not None:
            self.draw_card(self.moving_card.x, self.moving_card.y, self.moving_card.card, hidden=self.moving_card.hidden)

        self.canvas.create_rectangle(24, 448, 250, 540, fill="#123524", outline="#f6e7b7", width=3)
        self.canvas.create_text(40, 474, text="Round status", fill="#f8f4e3", font=("Helvetica", 15, "bold"), anchor="w")
        self.canvas.create_text(40, 508, text=self.status_var.get(), fill="#e8fff5", font=("Helvetica", 11, "bold"), anchor="w", width=190)

    def run(self) -> None:
        self.root.mainloop()


def simulate_hand(cards: Iterable[tuple[str, str]]) -> Hand:
    """Helper for tests and quick experiments."""
    return Hand([Card(rank, suit) for rank, suit in cards])


def launch_game() -> None:
    if sys.platform != "win32" and not os.environ.get("DISPLAY"):
        raise RuntimeError("Animated mode requires a graphical desktop session with DISPLAY available.")
    AnimatedBlackjackApp(BlackjackGame()).run()


if __name__ == "__main__":
    try:
        launch_game()
    except (KeyboardInterrupt, EOFError, SystemExit):
        print("\nGoodbye!")
    except RuntimeError as error:
        print(error)
