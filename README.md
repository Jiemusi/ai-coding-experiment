# Terminal Blackjack

A solo Blackjack game for Python with an animated terminal interface powered by `curses`.

## Features

- Standard 52-card deck with automatic reshuffling when the shoe gets low.
- Solo play against a dealer.
- Betting with bankroll tracking.
- Blackjack detection with a 3:2 payout.
- Hit, stand, and double-down actions.
- ASCII-style playing cards rendered directly in the terminal.
- Animated dealing, dealer reveals, and dealer hit sequences using `curses`.
- A framed table layout that shows bankroll, current bet, visible dealer info, and full hands.
- Replay loop so you can keep playing until you quit or run out of chips.

## Requirements

- Python 3.10+
- An interactive terminal session with Unicode / box-drawing support.
- A terminal window at least 70 columns wide by 24 rows tall for the animated layout.

## Run the game

```bash
python3 blackjack.py
```

> Note: the game uses `curses`, so it must be launched in a real interactive terminal rather than a non-interactive pipe.

## Run the tests

```bash
python3 -m unittest discover -s tests
```
