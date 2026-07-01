# Reasoning Telegram Bot

Production-ready Telegram AI bot with a hidden structured reasoning flow and a natural-language trace for users.

Every normal user response follows this visible format:

```text
🧭 What I understood
🧠 How I analyzed it
⚙️ How I decided to proceed
💬 Answer
```

Internal control, analysis, domain framing, validation, and state are never shown to the user.

## Requirements

- Python 3.11+
- PostgreSQL
- Telegram bot token
- OpenAI API key

## Configuration

Set these environment variables:

```bash
TELEGRAM_BOT_TOKEN=...
OPENAI_API_KEY=...
DATABASE_URL=postgresql://user:password@localhost:5432/reasoning_bot
OPENAI_MODEL=gpt-4.1-mini
```

Optional:

```bash
LOG_LEVEL=INFO
MAX_HISTORY_MESSAGES=20
```

## Run

```bash
python -m bot.telegram_adapter
```

The application creates its PostgreSQL table at startup.

## Test

```bash
python -m pytest
```

