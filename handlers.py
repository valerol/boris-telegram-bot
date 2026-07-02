from telegram import Update
from telegram.ext import ContextTypes

from llm_client import call_llm
from state import State, get_state, set_state
from ui import ASK_QUESTION, BOIS_INFO, BOIS_START, MAOS_INFO, MAOS_START, get_main_keyboard


GREETING = "Добро пожаловать в BORIS. Выберите действие:"
MENU_HINT = "Выберите действие в меню."
BOIS_INFO_TEXT = "BOIS: статическая информация будет добавлена из core."
BOIS_START_TEXT = "BOIS: стартовый сценарий будет добавлен позже."
MAOS_INFO_TEXT = "MaOS: статическая информация будет добавлена из core."
MAOS_START_TEXT = "MaOS: стартовый сценарий будет добавлен позже."


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user is None or update.message is None:
        return
    set_state(update.effective_user.id, State.MENU)
    await update.message.reply_text(GREETING, reply_markup=get_main_keyboard())


async def handle_button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query is None:
        return
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == ASK_QUESTION:
        set_state(user_id, State.WAITING_QUESTION)
        await query.message.reply_text("Введите вопрос")
        return

    set_state(user_id, State.MENU)
    text = {
        BOIS_INFO: BOIS_INFO_TEXT,
        BOIS_START: BOIS_START_TEXT,
        MAOS_INFO: MAOS_INFO_TEXT,
        MAOS_START: MAOS_START_TEXT,
    }.get(data, MENU_HINT)
    await query.message.reply_text(text, reply_markup=get_main_keyboard())


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user is None or update.message is None or update.message.text is None:
        return

    user_id = update.effective_user.id
    if get_state(user_id) != State.WAITING_QUESTION:
        await update.message.reply_text(MENU_HINT, reply_markup=get_main_keyboard())
        return

    answer = call_llm(update.message.text)
    set_state(user_id, State.MENU)
    await update.message.reply_text(answer, reply_markup=get_main_keyboard())
