from telegram import InlineKeyboardButton, InlineKeyboardMarkup


BOIS_INFO = "bois_info"
BOIS_START = "bois_start"
MAOS_INFO = "maos_info"
MAOS_START = "maos_start"
ASK_QUESTION = "ask_question"


def get_main_keyboard():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Что такое BOIS", callback_data=BOIS_INFO)],
            [InlineKeyboardButton("BOIS: старт", callback_data=BOIS_START)],
            [InlineKeyboardButton("Что такое MaOS", callback_data=MAOS_INFO)],
            [InlineKeyboardButton("MaOS: старт", callback_data=MAOS_START)],
            [InlineKeyboardButton("Задать вопрос", callback_data=ASK_QUESTION)],
        ]
    )
