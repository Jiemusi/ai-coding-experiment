# Terminal Blackjack

A simple solo blackjack game you can play in the terminal with Python, now with a more polished card-table presentation.

## Features

- Standard 52-card deck with automatic reshuffling when the shoe gets low.
- Solo play against a dealer.
- Betting with bankroll tracking.
- Blackjack detection with a 3:2 payout.
- Hit, stand, and double-down actions.
- ASCII-style playing cards rendered directly in the terminal.
- A more stylized table display that shows bankroll, current bet, visible dealer info, and full hands.
- Dealer reveals the full hand at settlement and stands on 17.
- Replay loop so you can keep playing until you quit or run out of chips.

## Requirements

- Python 3.10+
- A terminal with decent Unicode/box-drawing character support for the best visual result.

## Run the game

```bash
python3 blackjack.py
```

## Run the tests

```bash
python3 -m unittest discover -s tests
```
