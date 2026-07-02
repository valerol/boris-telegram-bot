import asyncio
import unittest

import handlers
from state import State, get_state, set_state
from ui import ASK_QUESTION, BOIS_INFO


class BotFSMTest(unittest.TestCase):
    def setUp(self):
        handlers.call_llm = lambda text: f"LLM: {text}"

    def test_start_moves_user_to_menu_and_sends_keyboard(self):
        update = _MessageUpdate(1, "/start")

        asyncio.run(handlers.handle_start(update, _Context()))

        self.assertEqual(get_state(1), State.MENU)
        self.assertEqual(update.message.replies[0]["text"], handlers.GREETING)
        self.assertIsNotNone(update.message.replies[0]["reply_markup"])

    def test_info_button_does_not_call_llm_and_keeps_menu(self):
        calls = []
        handlers.call_llm = lambda text: calls.append(text) or "unused"
        set_state(2, State.MENU)
        update = _ButtonUpdate(2, BOIS_INFO)

        asyncio.run(handlers.handle_button_click(update, _Context()))

        self.assertEqual(calls, [])
        self.assertEqual(get_state(2), State.MENU)
        self.assertEqual(update.callback_query.message.replies[0]["text"], handlers.BOIS_INFO_TEXT)

    def test_ask_button_moves_to_waiting_question(self):
        update = _ButtonUpdate(3, ASK_QUESTION)

        asyncio.run(handlers.handle_button_click(update, _Context()))

        self.assertEqual(get_state(3), State.WAITING_QUESTION)
        self.assertEqual(update.callback_query.message.replies[0]["text"], "Введите вопрос")

    def test_waiting_question_calls_llm_and_returns_to_menu(self):
        calls = []
        handlers.call_llm = lambda text: calls.append(text) or "Ответ core"
        set_state(4, State.WAITING_QUESTION)
        update = _MessageUpdate(4, "Что такое BOIS?")

        asyncio.run(handlers.handle_message(update, _Context()))

        self.assertEqual(calls, ["Что такое BOIS?"])
        self.assertEqual(get_state(4), State.MENU)
        self.assertEqual(update.message.replies[0]["text"], "Ответ core")

    def test_menu_message_shows_hint_without_llm(self):
        calls = []
        handlers.call_llm = lambda text: calls.append(text) or "unused"
        set_state(5, State.MENU)
        update = _MessageUpdate(5, "Привет")

        asyncio.run(handlers.handle_message(update, _Context()))

        self.assertEqual(calls, [])
        self.assertEqual(get_state(5), State.MENU)
        self.assertEqual(update.message.replies[0]["text"], handlers.MENU_HINT)


class _User:
    def __init__(self, user_id):
        self.id = user_id


class _Message:
    def __init__(self, text):
        self.text = text
        self.replies = []

    async def reply_text(self, text, reply_markup=None):
        self.replies.append({"text": text, "reply_markup": reply_markup})


class _CallbackQuery:
    def __init__(self, user_id, data):
        self.from_user = _User(user_id)
        self.data = data
        self.message = _Message("")
        self.answered = False

    async def answer(self):
        self.answered = True


class _MessageUpdate:
    def __init__(self, user_id, text):
        self.effective_user = _User(user_id)
        self.message = _Message(text)
        self.callback_query = None


class _ButtonUpdate:
    def __init__(self, user_id, data):
        self.effective_user = _User(user_id)
        self.message = None
        self.callback_query = _CallbackQuery(user_id, data)


class _Context:
    pass


if __name__ == "__main__":
    unittest.main()
