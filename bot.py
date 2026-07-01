import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

from bois_runtime import BOISRuntime

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

runtime = BOISRuntime()


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message is None or update.message.text is None:
        return

    user_text = update.message.text

    result = runtime.run(user_text)

    await update.message.reply_text(
        result["output"]["answer"]
    )


def main():

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle)
    )

    app.run_polling()


if __name__ == "__main__":
    main()
