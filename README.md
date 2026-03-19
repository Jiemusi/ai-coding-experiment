# Terminal Blackjack

A simple solo blackjack game you can play in the terminal with Python.

## Features

- Standard 52-card deck with automatic reshuffling when the shoe gets low.
- Solo play against a dealer.
- Betting with bankroll tracking.
- Blackjack detection with a 3:2 payout.
- Hit, stand, and double-down actions.
- Dealer reveals the full hand at settlement and stands on 17.
- Replay loop so you can keep playing until you quit or run out of chips.

## Requirements

- Python 3.10+

## Run the game

```bash
python3 blackjack.py
```

## Run the tests

```bash
python3 -m unittest discover -s tests
```
