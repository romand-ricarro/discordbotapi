# discordbotapi

A Python service that runs a Discord bot and a REST API side-by-side, allowing external systems to interact with Discord programmatically via HTTP.

## What it does

- Runs a Discord bot (discord.py) and a FastAPI/aiohttp server concurrently in the same process
- Exposes authenticated API endpoints secured with an `API_KEY`
- Includes API key management (`api_key_manager.py`) and rate limiting (`rate_limiter.py`)
- Designed for deployment on AWS, Railway, or Heroku (reads `PORT` from environment)
- Structured logging to daily rotating log files

## Project structure

```
main.py              # Entry point — starts bot and API server together
discord_bot.py       # Discord bot class and event handlers
api_server.py        # REST API server
api_key_manager.py   # API key creation and validation
rate_limiter.py      # Per-key rate limiting
config.py            # Config loaded from environment variables
debug_env.py         # Dev utility to verify environment is set up correctly
deploy.sh            # Deployment helper script
requirements.txt
```

## Setup

```bash
pip install -r requirements.txt
```

Create a `.env` file:

```
DISCORD_BOT_TOKEN=your_discord_bot_token
API_KEY=your_api_key
API_PORT=8000
ENVIRONMENT=production
AWS_REGION=us-east-1
```

## Usage

```bash
python main.py
```

To verify your environment before running:

```bash
python debug_env.py
```
