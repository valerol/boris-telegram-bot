import unittest

from boris_gate import ALLOW, ALLOW_WITH_SCOPE_LIMIT, DENY_OUT_OF_SCOPE, decide_capability
from boris_runtime import BOISRuntime
from sima_analyzer import parse


class BORISSupportRuntimeTest(unittest.TestCase):
    def test_generic_business_plan_is_denied_without_llm(self):
        calls = []
        runtime = BOISRuntime(llm_call=lambda prompt: calls.append(prompt) or "should not run")

        result = runtime.run("Сделай бизнес-план для интернет-магазина тайских штанов на завязках")

        self.assertEqual(result["input"]["gate"]["decision"], DENY_OUT_OF_SCOPE)
        self.assertEqual(calls, [])
        self.assertNotIn("выручка", result["output"]["answer"].lower())

    def test_bois_business_plan_methodology_is_scope_limited(self):
        runtime = BOISRuntime(llm_call=lambda prompt: "Метод: SIMA анализирует риски, BORIS оформляет runtime.")

        result = runtime.run("Как применить BOIS/SIMA/BORIS для бизнес-плана интернет-магазина?")

        self.assertIn(result["input"]["gate"]["decision"], {ALLOW, ALLOW_WITH_SCOPE_LIMIT})
        self.assertIn("BOIS/SIMA/BORIS", result["output"]["answer"])
        self.assertIn("SIMA", result["output"]["answer"])

    def test_telegram_runtime_implementation_is_allowed(self):
        analysis = parse("Как реализовать BOIS runtime в Telegram-боте?")
        decision = decide_capability(analysis, analysis["domain"])

        self.assertEqual(decision.decision, ALLOW)

    def test_recipe_is_denied(self):
        runtime = BOISRuntime(llm_call=lambda prompt: "should not run")

        result = runtime.run("Напиши рецепт борща")

        self.assertEqual(result["input"]["gate"]["decision"], DENY_OUT_OF_SCOPE)
        self.assertIn("выходит за пределы", result["output"]["answer"])

    def test_sima_analysis_request_is_allowed(self):
        analysis = parse("Проанализируй этот ответ с точки зрения SIMA")
        decision = decide_capability(analysis, analysis["domain"])

        self.assertEqual(decision.decision, ALLOW)

    def test_saas_boris_protocol_architecture_is_allowed(self):
        analysis = parse("Сделай архитектуру SaaS с BORIS-протоколом")
        decision = decide_capability(analysis, analysis["domain"])

        self.assertEqual(decision.decision, ALLOW)


if __name__ == "__main__":
    unittest.main()
