import json
import unittest
from pathlib import Path

import boris_runtime
from boris_gate import ALLOW, ALLOW_WITH_SCOPE_LIMIT, DENY_OUT_OF_SCOPE, decide_capability
from boris_runtime import BOISRuntime
from boris_templates import CORE_UNAVAILABLE_RU
from core_manager.core_loader import ActiveCore
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
        runtime = BOISRuntime(
            llm_call=lambda prompt: _contract_json(
                direct_answer="Методологический разбор через BOIS/SIMA/BORIS.",
                bois_section="BOIS задает смысл и границы.",
                sima_section="SIMA анализирует риски.",
                boris_section="BORIS оформляет runtime.",
            ),
            core_loader=_active_core,
        )

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

    def test_bois_related_request_without_core_returns_fallback_without_llm(self):
        calls = []
        runtime = BOISRuntime(
            llm_call=lambda prompt: calls.append(prompt) or "should not run",
            core_loader=_missing_core,
        )

        result = runtime.run("Расскажи о BOIS")

        self.assertEqual(calls, [])
        self.assertIn("Локальное BOIS Core", result["output"]["answer"])
        self.assertIn("https://github.com/temnik-bois/BOIS/", result["output"]["answer"])

    def test_fallback_contains_official_repository_and_loading_prompt(self):
        runtime = BOISRuntime(llm_call=lambda prompt: "should not run", core_loader=_missing_core)

        result = runtime.run("Что такое SIMA?")

        self.assertIn("https://github.com/temnik-bois/BOIS/", result["output"]["answer"])
        self.assertIn("Fully analyze the entire archive without omissions", result["output"]["answer"])

    def test_bois_related_request_attempts_core_load_first(self):
        events = []

        def load_core():
            events.append("core")
            return _missing_core()

        def llm_call(prompt):
            events.append("llm")
            return "should not run"

        runtime = BOISRuntime(llm_call=llm_call, core_loader=load_core)

        runtime.run("Расскажи о BORIS")

        self.assertEqual(events, ["core"])

    def test_status_core_reports_loader_state(self):
        runtime = BOISRuntime(llm_call=lambda prompt: "unused", core_loader=_active_core)

        status = runtime.status_core()

        self.assertIn("Active core found: yes", status)
        self.assertIn("Detected version: test-core", status)
        self.assertIn("Validation status: passed", status)

    def test_available_core_context_is_preserved_in_analysis(self):
        runtime = BOISRuntime(llm_call=lambda prompt: _contract_json(), core_loader=_active_core)

        result = runtime.run("Расскажи о BOIS")
        active_core = result["input"]["active_core"]

        self.assertTrue(active_core["available"])
        self.assertEqual(active_core["surface_contract"]["mode"], "canonical-test-surface")
        self.assertIn("canonical-test-rule", active_core["active_rules"][0]["formulation"])
        self.assertEqual(active_core["stop_signals"][0]["signal"], "canonical-test-stop")
        self.assertEqual(active_core["procedures"][0]["procedure"], "canonical-test-procedure")
        self.assertEqual(active_core["criteria"][0]["criterion"], "canonical-test-criterion")
        self.assertIn("canonical-test-machine", str(active_core["machine_json"][0]["scalar_snippets"]))
        self.assertIsNotNone(active_core["identity"]["loaded_surface_sha256"])

    def test_prompt_receives_identifiable_core_content_and_no_fallback(self):
        prompts = []
        runtime = BOISRuntime(
            llm_call=lambda prompt: prompts.append(prompt) or _contract_json(),
            core_loader=_active_core,
        )

        result = runtime.run("Расскажи о BOIS")

        self.assertNotEqual(result["output"]["answer"], CORE_UNAVAILABLE_RU)
        self.assertEqual(len(prompts), 1)
        self.assertIn("canonical-test-surface", prompts[0])
        self.assertIn("canonical-test-rule", prompts[0])
        self.assertIn(result["input"]["active_core"]["identity"]["loaded_surface_sha256"], prompts[0])

    def test_core_execution_filter_is_present_in_analysis_and_prompt(self):
        prompts = []
        runtime = BOISRuntime(
            llm_call=lambda prompt: prompts.append(prompt) or _contract_json(),
            core_loader=_active_core,
        )

        result = runtime.run("Расскажи о BOIS")

        self.assertEqual(result["contract"]["scope_status"], "in_scope")
        self.assertNotEqual(result["output"]["answer"], CORE_UNAVAILABLE_RU)
        self.assertIn("core_execution_filter", result["input"])
        execution_filter = result["input"]["core_execution_filter"]
        self.assertEqual(set(execution_filter), {"SIMA", "BOIS", "BORIS", "SOCRATES", "EXECUTION_CONTROL"})
        self.assertEqual(execution_filter["SIMA"]["intent_class"], "BOIS_query")
        self.assertEqual(execution_filter["BORIS"]["mode"], "explain")
        self.assertEqual(execution_filter["EXECUTION_CONTROL"]["response_boundary"], "no_generic_assistant_behavior")

        prompt = prompts[0]
        self.assertIn("CORE EXECUTION FILTER:", prompt)
        self.assertIn('"response_boundary": "no_generic_assistant_behavior"', prompt)
        self.assertIn("Apply CORE EXECUTION FILTER as the first active runtime control layer.", prompt)
        self.assertLess(prompt.index("BORIS Support identity:"), prompt.index("CORE EXECUTION FILTER:"))
        self.assertLess(prompt.index("CORE EXECUTION FILTER:"), prompt.index("Core Application Protocol:"))
        self.assertLess(prompt.index("Core Application Protocol:"), prompt.index("SIMA analysis:"))
        self.assertLess(prompt.index("SIMA analysis:"), prompt.index("Capability gate decision:"))
        self.assertLess(prompt.index("Capability gate decision:"), prompt.index("Relevant Native BOIS Core context:"))
        self.assertLess(prompt.index("Relevant Native BOIS Core context:"), prompt.index("User request:"))

    def test_core_execution_filter_is_created_after_sima_and_gate(self):
        calls = []
        original = boris_runtime.build_core_execution_filter

        def spy(active_core, sima_analysis, gate_decision):
            calls.append(
                {
                    "has_sima_operation": "requested_operation" in sima_analysis,
                    "has_gate_decision": bool(getattr(gate_decision, "decision", None)),
                }
            )
            return original(active_core, sima_analysis, gate_decision)

        boris_runtime.build_core_execution_filter = spy
        try:
            runtime = BOISRuntime(llm_call=lambda prompt: _contract_json(), core_loader=_active_core)
            runtime.run("Расскажи о BOIS")
        finally:
            boris_runtime.build_core_execution_filter = original

        self.assertEqual(calls, [{"has_sima_operation": True, "has_gate_decision": True}])

    def test_core_execution_filter_mode_changes_prompt_control(self):
        prompts = []
        runtime = BOISRuntime(
            llm_call=lambda prompt: prompts.append(prompt) or _contract_json(),
            core_loader=_active_core,
        )

        result = runtime.run("Как реализовать BOIS runtime в Telegram-боте?")

        self.assertEqual(result["contract"]["scope_status"], "in_scope")
        self.assertEqual(result["input"]["core_execution_filter"]["BORIS"]["mode"], "implement")
        self.assertIn('"mode": "implement"', prompts[0])
        self.assertIn('"reasoning_depth": "physiological"', prompts[0])

    def test_external_domain_with_boris_prompt_contains_application_protocol(self):
        prompts = []
        runtime = BOISRuntime(
            llm_call=lambda prompt: prompts.append(prompt) or _contract_json(direct_answer="Методологический ответ"),
            core_loader=_active_core,
        )

        result = runtime.run(
            "Как сделать бизнес-план для интернет-магазина тайских штанов на завязках с помощью BORIS?"
        )

        self.assertNotEqual(result["output"]["answer"], CORE_UNAVAILABLE_RU)
        self.assertEqual(len(prompts), 1)
        prompt = prompts[0]
        self.assertIn("Core Application Protocol", prompt)
        self.assertIn("do not create a generic business plan", prompt)
        self.assertIn("separate BOIS, SIMA, and BORIS", prompt)
        self.assertIn("external domain as applied object", prompt)
        self.assertTrue("CORE-01" in prompt or "Смысл до формы" in prompt)
        self.assertTrue("CORE-08" in prompt or "Нет ложной универсальности" in prompt)

        protocol = result["input"]["core_application_protocol"]
        self.assertEqual(protocol["request_kind"], "external_domain_with_boris_methodology")
        self.assertTrue(protocol["applicable_rules"])

    def test_arbitrary_unclear_input_returns_structured_clarification(self):
        runtime = BOISRuntime(llm_call=lambda prompt: "should not run", core_loader=_active_core)

        result = runtime.run("???")

        self.assertEqual(result["contract"]["scope_status"], "unclear")
        self.assertIn("Уточните", result["output"]["answer"])

    def test_malformed_llm_json_is_not_sent_to_user(self):
        runtime = BOISRuntime(llm_call=lambda prompt: "not json at all", core_loader=_active_core)

        result = runtime.run("Расскажи о BOIS")

        self.assertEqual(result["contract"]["scope_status"], "in_scope")
        self.assertNotIn("not json at all", result["output"]["answer"])
        self.assertNotIn("valid_response_contract", result["output"]["answer"])
        self.assertNotIn("неструктурированный", result["output"]["answer"])
        self.assertIn("структурированном формате BOIS/SIMA/BORIS", result["output"]["answer"])

    def test_formatter_creates_final_text_not_llm(self):
        runtime = BOISRuntime(
            llm_call=lambda prompt: _contract_json(
                direct_answer="LLM data field only",
                bois_section="BOIS field",
                sima_section="SIMA field",
                boris_section="BORIS field",
            ),
            core_loader=_active_core,
        )

        result = runtime.run("Расскажи о BOIS")

        self.assertNotEqual(result["output"]["answer"], result["reasoning"]["raw"])
        self.assertIn("BOIS: BOIS field", result["output"]["answer"])
        self.assertIn("SIMA: SIMA field", result["output"]["answer"])
        self.assertIn("BORIS: BORIS field", result["output"]["answer"])

    def test_answer_field_is_normalized_into_contract(self):
        runtime = BOISRuntime(
            llm_call=lambda prompt: json.dumps({"answer": "Что такое BOIS: структурный ответ"}, ensure_ascii=False),
            core_loader=_active_core,
        )

        result = runtime.run("Что такое BOIS?")

        self.assertEqual(result["contract"]["scope_status"], "in_scope")
        self.assertIn("Что такое BOIS", result["output"]["answer"])
        self.assertNotIn("valid_response_contract", result["output"]["answer"])

    def test_partial_direct_answer_is_completed(self):
        runtime = BOISRuntime(
            llm_call=lambda prompt: json.dumps({"direct_answer": "Частичный ответ"}, ensure_ascii=False),
            core_loader=_active_core,
        )

        result = runtime.run("Расскажи о BOIS")

        for field in (
            "scope_status",
            "request_type",
            "primary_domain",
            "applied_domain",
            "bois_section",
            "sima_section",
            "boris_section",
            "direct_answer",
            "boundary_note",
            "next_step",
            "confidence",
            "missing_info",
        ):
            self.assertIn(field, result["contract"])
        self.assertIn("Частичный ответ", result["output"]["answer"])

    def test_final_answer_never_contains_contract_validation_words(self):
        runtime = BOISRuntime(llm_call=lambda prompt: "not json at all", core_loader=_active_core)

        result = runtime.run("Что такое BOIS?")

        forbidden = (
            "valid_response_contract",
            "raw or unstructured model response",
            "validation error",
            "неструктурированный ответ модели",
        )
        for item in forbidden:
            self.assertNotIn(item, result["output"]["answer"])


def _active_core() -> ActiveCore:
    return ActiveCore(
        active_path=Path("core/active"),
        core_version="test-core",
        validation_status="passed",
        validation_errors=[],
        manifest={"version": "test-core"},
        machine_json=[{"machine": "canonical-test-machine"}],
        active_rules=[
            {
                "id": "CORE-01",
                "title": "Смысл до формы",
                "formulation": "canonical-test-rule: meaning before form",
            },
            {
                "id": "CORE-02",
                "title": "Разделение утверждений",
                "formulation": "separate fact, inference, hypothesis, risk, unknown, and boundary",
            },
            {
                "id": "CORE-04",
                "title": "Протокол и инструкция различаются",
                "formulation": "protocol and instruction are distinct",
            },
            {
                "id": "CORE-05",
                "title": "Следующий шаг не является знанием",
                "formulation": "next step is a hypothesis, not knowledge",
            },
            {
                "id": "CORE-08",
                "title": "Нет ложной универсальности",
                "formulation": "avoid false universality",
            },
        ],
        stop_signals=[{"id": "stop-1", "signal": "canonical-test-stop"}],
        procedures=[{"id": "procedure-1", "procedure": "canonical-test-procedure"}],
        criteria=[{"id": "criterion-1", "criterion": "canonical-test-criterion"}],
        surface_contract={"mode": "canonical-test-surface"},
        conflict_policy={"policy": "canonical-test-conflict"},
        language_policy={"language": "canonical-test-language"},
        load_order=["core/main.machine.json"],
    )


def _missing_core() -> ActiveCore:
    return ActiveCore(
        active_path=None,
        core_version=None,
        validation_status="missing",
        validation_errors=["Active core path is missing"],
    )


def _contract_json(**overrides) -> str:
    contract = {
        "scope_status": "in_scope",
        "request_type": "explain_bois",
        "primary_domain": "boris_support",
        "applied_domain": "bois_core",
        "bois_section": "BOIS section",
        "sima_section": "SIMA section",
        "boris_section": "BORIS section",
        "direct_answer": "Core-aware answer",
        "boundary_note": "Inside BORIS Support scope.",
        "next_step": "Use this as a structured next step.",
        "confidence": 0.8,
        "missing_info": [],
    }
    contract.update(overrides)
    return json.dumps(contract, ensure_ascii=False)


if __name__ == "__main__":
    unittest.main()
