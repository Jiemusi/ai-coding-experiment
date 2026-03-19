# Animated Blackjack

A solo Blackjack game for Python with a real animated desktop interface built with `tkinter`.

## Features

- Standard 52-card deck with automatic reshuffling when the shoe gets low.
- Solo play against a dealer.
- Betting with bankroll tracking.
- Blackjack detection with a 3:2 payout.
- Hit, stand, and double-down actions.
- A desktop game table instead of a text terminal UI.
- Animated dealing where cards visibly travel from the deck to the dealer and player hands.
- Dealer reveal and dealer-hit animations.
- Round results stay visible on the table until you explicitly start the next round, so natural blackjacks and losses are easy to see.

## Requirements

- Python 3.10+
- A graphical desktop session.
- On Linux, a valid `DISPLAY` environment is required.

## Run the game

```bash
python3 blackjack.py
```

## Run the tests

```bash
python3 -m unittest discover -s tests
```
