# 🏀 NBA Player Card Bot

A Telegram bot for NBA fans. Get player cards with stats, photos, and fun facts — all in one chat.

## Features

- 🔍 **Player Card** — search any NBA player by name and get a full card: team, position, jersey number, height, weight, season averages, and a fun fact
- 🎲 **Random Player** — discover a random famous NBA player with their card and photo
- 🏆 **Top Scorers** — top 5 scorers of the 2024-25 season with the NBA logo
- ⚔️ **Compare** — compare two players head-to-head with stats side by side and photos of both

## Commands

| Command | Description |
|--------|-------------|
| `/start` | Show welcome message and command list |
| `/player LeBron James` | Get player card with photo |
| `/random` | Get a random famous player |
| `/top` | Top 5 scorers this season |
| `/compare LeBron James vs Stephen Curry` | Compare two players |

## Tech Stack

- **Python 3.11+**
- [`python-telegram-bot`](https://github.com/python-telegram-bot/python-telegram-bot) — Telegram Bot API wrapper
- [`nba_api`](https://github.com/swar/nba_api) — unofficial NBA stats API (free, no key needed)
- Player photos from `cdn.nba.com`

## Setup

1. Clone the repo
   ```bash
   git clone https://github.com/yourusername/nba-bot.git
   cd nba-bot
   ```

2. Install dependencies
   ```bash
   pip install python-telegram-bot nba_api
   ```

3. Add your Telegram bot token in `bot.py`
   ```python
   TELEGRAM_TOKEN = "your_token_here"
   ```

4. Run the bot
   ```bash
   python bot.py
   ```

## Notes

- Stats are fetched from `stats.nba.com` — first request per player takes a few seconds
- Results are cached in memory — repeated requests are instant
- If a player has no 2024-25 stats, the bot automatically falls back to 2023-24 or 2022-23