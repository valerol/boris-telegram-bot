# Reasoning Telegram Bot

Production-ready Telegram AI bot with a deterministic, gated reasoning flow and a natural-language trace for users.

Every normal user response follows this visible format:

```text
🧭 What I understood
🧠 How I analyzed it
⚙️ How I decided to proceed
💬 Answer
```

Internal control, analysis, domain framing, validation, and state are never shown to the user. The first internal step is a hard gate; if it denies a request, intent analysis, domain structuring, and the LLM call do not run.

## Structure

```text
/bot
  telegram_adapter.py
/core
  orchestrator.py
  rendering.py
/bois
  guard.py
/sima
  engine.py
/boris
  engine.py
/runtime
  llm.py
/memory
  store.py
  postgres.py
/qa
  validator.py
/config
  settings.py
main.py
```

The visible response is rendered locally after model execution. The renderer does not call the LLM.

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

or:

```bash
python main.py
```

The application creates its PostgreSQL table at startup.

## Test

```bash
python -m pytest
```
