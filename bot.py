import json
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from boris_runtime import BOISRuntime
from core_manager.core_context import build_core_context
from core_manager.core_loader import get_active_core

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

runtime = BOISRuntime()


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message is None or update.message.text is None:
        return

    user_text = update.message.text
    session = _user_session(context)

    result = runtime.run(user_text, session_context=session)

    await update.message.reply_text(_render_bot_response(result))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message is None:
        return

    session = _user_session(context)
    core_brief = build_start_core_brief()
    session["core_brief"] = core_brief

    await update.message.reply_text(core_brief)


async def status_core(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message is None:
        return

    await update.message.reply_text(runtime.status_core())


def main():

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status_core", status_core))

    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle)
    )

    app.run_polling()


def build_start_core_brief(active_core=None) -> str:
    active_core = active_core or get_active_core()
    core_context = build_core_context(active_core)
    lines = [
        "BOIS/SIMA/BORIS base knowledge pack",
        f"Core available: {'yes' if core_context.get('available') else 'no'}",
        f"Core version: {core_context.get('version') or 'not detected'}",
        f"Validation status: {core_context.get('validation_status')}",
    ]
    identity = core_context.get("identity") or {}
    if identity.get("loaded_surface_sha256"):
        lines.append(f"Loaded surface: {identity['loaded_surface_sha256']}")

    donation_links = _donation_links_from_core_templates(active_core)
    if donation_links:
        lines.append("")
        lines.append("Donation links:")
        lines.extend(str(link) for link in donation_links)

    return "\n".join(lines)


def _render_bot_response(result: dict) -> str:
    answer = result["output"]["answer"]
    if os.getenv("DEV_MODE", "").lower() != "true":
        return answer
    return "Answer:\n{}\n\nTrace:\n{}".format(
        answer,
        json.dumps(result.get("trace", {}), ensure_ascii=False, indent=2),
    )


def _user_session(context) -> dict:
    if hasattr(context, "user_session"):
        if context.user_session is None:
            context.user_session = {}
        return context.user_session
    if hasattr(context, "user_data"):
        return context.user_data
    return {}


def _donation_links_from_core_templates(active_core) -> list[str]:
    surface_contract = getattr(active_core, "surface_contract", None) or {}
    templates = surface_contract.get("templates") if isinstance(surface_contract, dict) else None
    if not isinstance(templates, dict):
        return []

    links = []
    for key in ("donation_links", "donations", "support_links"):
        value = templates.get(key)
        if isinstance(value, str):
            links.append(value)
        elif isinstance(value, list):
            links.extend(str(item) for item in value if item)
        elif isinstance(value, dict):
            links.extend(str(item) for item in value.values() if item)
    return links


if __name__ == "__main__":
    main()
