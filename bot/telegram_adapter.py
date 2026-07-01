from __future__ import annotations

import logging

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from config.settings import get_settings
from core.orchestrator import Orchestrator
from memory.postgres import PostgresSessionStore
from runtime.llm import OpenAILLMClient


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message is None:
        return
    await update.effective_message.reply_text(
        "🧭 What I understood\nYou opened the assistant and want to start a conversation.\n\n"
        "🧠 How I analyzed it\nThis is a simple start request, so no extra context is needed.\n\n"
        "⚙️ How I decided to proceed\nI’ll keep the response brief and invite you to send a message.\n\n"
        "💬 Answer\nSend me anything you want help with."
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user is None or update.effective_chat is None or update.effective_message is None:
        return
    orchestrator: Orchestrator = context.application.bot_data["orchestrator"]
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    response = await orchestrator.handle_message(
        user_id=update.effective_user.id,
        chat_id=update.effective_chat.id,
        user_text=update.effective_message.text or "",
    )
    await update.effective_message.reply_text(response)


async def post_init(application: Application) -> None:
    store: PostgresSessionStore = application.bot_data["store"]
    await store.connect()


async def post_shutdown(application: Application) -> None:
    store: PostgresSessionStore = application.bot_data["store"]
    await store.close()


def build_application() -> Application:
    settings = get_settings()
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required.")
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required.")

    logging.basicConfig(level=settings.log_level)
    store = PostgresSessionStore(settings.database_url)
    llm = OpenAILLMClient(api_key=settings.openai_api_key, model=settings.openai_model)
    orchestrator = Orchestrator(settings=settings, store=store, llm=llm)

    application = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )
    application.bot_data["store"] = store
    application.bot_data["orchestrator"] = orchestrator
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    return application


def main() -> None:
    application = build_application()
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
