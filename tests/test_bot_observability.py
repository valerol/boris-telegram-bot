import asyncio
import json
import os
import unittest
from pathlib import Path

import bot
from core_manager.core_loader import ActiveCore


class BotObservabilityTest(unittest.TestCase):
    def test_start_core_brief_returns_base_pack_and_core_template_donations(self):
        brief = bot.build_start_core_brief(_active_core_with_templates())

        self.assertIn("BOIS/SIMA/BORIS base knowledge pack", brief)
        self.assertIn("Core available: yes", brief)
        self.assertIn("Core version: bot-test-core", brief)
        self.assertIn("https://core.example/donate", brief)

    def test_start_handler_stores_core_brief_in_user_session(self):
        original = bot.build_start_core_brief
        bot.build_start_core_brief = lambda: "BOIS/SIMA/BORIS base knowledge pack"
        update = _FakeUpdate("/start")
        context = _FakeContext()
        try:
            asyncio.run(bot.start(update, context))
        finally:
            bot.build_start_core_brief = original

        self.assertEqual(context.user_session["core_brief"], "BOIS/SIMA/BORIS base knowledge pack")
        self.assertEqual(update.message.replies, ["BOIS/SIMA/BORIS base knowledge pack"])

    def test_handle_passes_session_context_to_runtime(self):
        calls = []

        class Runtime:
            def run(self, text, session_context=None):
                calls.append({"text": text, "session_context": dict(session_context)})
                return _runtime_result()

        original = bot.runtime
        bot.runtime = Runtime()
        update = _FakeUpdate("Расскажи о BOIS")
        context = _FakeContext({"core_brief": "cached base pack"})
        try:
            asyncio.run(bot.handle(update, context))
        finally:
            bot.runtime = original

        self.assertEqual(calls, [{"text": "Расскажи о BOIS", "session_context": {"core_brief": "cached base pack"}}])

    def test_start_core_brief_persists_into_next_message(self):
        calls = []

        class Runtime:
            def run(self, text, session_context=None):
                calls.append(dict(session_context))
                return _runtime_result()

        original_brief = bot.build_start_core_brief
        original_runtime = bot.runtime
        bot.build_start_core_brief = lambda: "BOIS/SIMA/BORIS base knowledge pack"
        bot.runtime = Runtime()
        context = _FakeContext()
        try:
            asyncio.run(bot.start(_FakeUpdate("/start"), context))
            asyncio.run(bot.handle(_FakeUpdate("Расскажи о BOIS"), context))
        finally:
            bot.build_start_core_brief = original_brief
            bot.runtime = original_runtime

        self.assertEqual(calls, [{"core_brief": "BOIS/SIMA/BORIS base knowledge pack"}])

    def test_dev_mode_exposes_trace_json(self):
        original = os.environ.get("DEV_MODE")
        os.environ["DEV_MODE"] = "true"
        try:
            rendered = bot._render_bot_response(_runtime_result())
        finally:
            if original is None:
                os.environ.pop("DEV_MODE", None)
            else:
                os.environ["DEV_MODE"] = original

        self.assertIn("Answer:\nRuntime answer", rendered)
        self.assertIn("Trace:", rendered)
        self.assertIn(json.dumps("LLM"), rendered)

    def test_production_mode_hides_trace(self):
        original = os.environ.get("DEV_MODE")
        os.environ["DEV_MODE"] = "false"
        try:
            rendered = bot._render_bot_response(_runtime_result())
        finally:
            if original is None:
                os.environ.pop("DEV_MODE", None)
            else:
                os.environ["DEV_MODE"] = original

        self.assertEqual(rendered, "Runtime answer")


class _FakeMessage:
    def __init__(self, text):
        self.text = text
        self.replies = []

    async def reply_text(self, text):
        self.replies.append(text)


class _FakeUpdate:
    def __init__(self, text):
        self.message = _FakeMessage(text)


class _FakeContext:
    def __init__(self, user_session=None):
        self.user_session = user_session or {}


def _runtime_result() -> dict:
    return {
        "output": {"answer": "Runtime answer"},
        "trace": {
            "route": "LLM",
            "llm_called": True,
            "core_used": True,
            "filter_applied": True,
        },
    }


def _active_core_with_templates() -> ActiveCore:
    return ActiveCore(
        active_path=Path("core/active"),
        core_version="bot-test-core",
        validation_status="passed",
        validation_errors=[],
        manifest={"version": "bot-test-core"},
        validation_report={"status": "passed"},
        machine_json=[{"machine": "bot-test"}],
        active_rules=[],
        stop_signals=[],
        procedures=[],
        criteria=[],
        surface_contract={
            "templates": {
                "donation_links": ["https://core.example/donate"],
            }
        },
        conflict_policy={},
        language_policy={},
        load_order=["runtime/surface_contract.json"],
    )


if __name__ == "__main__":
    unittest.main()
