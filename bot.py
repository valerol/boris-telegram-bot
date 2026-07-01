import os
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = "http://127.0.0.1:8000/process"  # если API локально

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_text = update.message.text

    response = requests.post(API_URL, json={
        "input": user_text
    })

    await update.message.reply_text(str(response.json()))

def main():

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    app.run_polling()

if __name__ == "__main__":
    main()
