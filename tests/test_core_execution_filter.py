import unittest
from pathlib import Path

from boris_gate import ALLOW, DENY_OUT_OF_SCOPE, GateDecision
from boris_execution.core_execution_filter import (
    apply_core_execution_filter,
    build_core_execution_filter,
    validate_against_execution_contract,
)


class CoreExecutionFilterTest(unittest.TestCase):
    def test_module_exists_in_boris_execution_layer(self):
        path = Path(__file__).resolve().parents[1] / "boris_execution" / "core_execution_filter.py"

        self.assertTrue(path.exists())

    def test_build_core_execution_filter_returns_org_structure(self):
        execution_filter = build_core_execution_filter(
            active_core=object(),
            sima_analysis={"intent": "question", "requested_operation": "explain_bois", "is_bois_related": True},
            gate_decision=GateDecision(ALLOW, "inside_boris_support_scope"),
        )

        self.assertEqual(set(execution_filter), {"SIMA", "BOIS", "BORIS", "SOCRATES", "EXECUTION_CONTROL"})
        self.assertEqual(execution_filter["SIMA"]["intent_class"], "BOIS_query")
        self.assertEqual(execution_filter["BOIS"]["must_separate"], ["fact", "inference", "hypothesis"])
        self.assertEqual(execution_filter["BORIS"]["mode"], "explain")
        self.assertEqual(execution_filter["SOCRATES"]["input_state"], "S_in")
        self.assertTrue(execution_filter["EXECUTION_CONTROL"]["must_apply_to_prompt"])
        self.assertEqual(
            execution_filter["EXECUTION_CONTROL"]["response_boundary"],
            "no_generic_assistant_behavior",
        )

    def test_execution_mode_changes_from_sima_and_gate(self):
        implement_filter = build_core_execution_filter(
            active_core=object(),
            sima_analysis={"requested_operation": "integrate_with_application"},
            gate_decision=GateDecision(ALLOW, "inside_boris_support_scope"),
        )
        refuse_filter = build_core_execution_filter(
            active_core=object(),
            sima_analysis={"requested_operation": "write_recipe"},
            gate_decision=GateDecision(DENY_OUT_OF_SCOPE, "outside_boris_support_scope"),
        )

        self.assertEqual(implement_filter["BORIS"]["mode"], "implement")
        self.assertEqual(implement_filter["BORIS"]["reasoning_depth"], "physiological")
        self.assertEqual(refuse_filter["BORIS"]["mode"], "refuse")
        self.assertIn("outside_boris_support_scope", refuse_filter["BOIS"]["stop_conditions"])

    def test_apply_core_execution_filter_builds_hard_contract(self):
        execution_filter = build_core_execution_filter(
            active_core=object(),
            sima_analysis={"requested_operation": "integrate_with_application"},
            gate_decision=GateDecision(ALLOW, "inside_boris_support_scope"),
        )

        contract = apply_core_execution_filter(
            execution_filter,
            {"requested_operation": "integrate_with_application"},
            GateDecision(ALLOW, "inside_boris_support_scope"),
        )

        self.assertEqual(contract["enforcement"], "hard")
        self.assertEqual(contract["route"], "CONSTRAINED_LLM")
        self.assertEqual(contract["allowed_reasoning_modes"], ["implement"])
        self.assertIn("generic_consulting", contract["forbidden_response_forms"])
        self.assertTrue(contract["mandatory_structure_compliance"]["must_use_bois_sima_boris_sections"])

    def test_validate_against_execution_contract_rejects_missing_structure_and_generic_output(self):
        execution_filter = build_core_execution_filter(
            active_core=object(),
            sima_analysis={"requested_operation": "explain_bois", "is_bois_related": True},
            gate_decision=GateDecision(ALLOW, "inside_boris_support_scope"),
        )
        enforced = apply_core_execution_filter(
            execution_filter,
            {"requested_operation": "explain_bois"},
            GateDecision(ALLOW, "inside_boris_support_scope"),
        )

        valid, errors = validate_against_execution_contract(
            {
                "scope_status": "in_scope",
                "request_type": "explain_bois",
                "primary_domain": "boris_support",
                "applied_domain": "bois_core",
                "bois_section": "",
                "sima_section": "",
                "boris_section": "",
                "direct_answer": "As a consultant, here is advice.",
                "boundary_note": "",
                "next_step": "",
                "confidence": 0.8,
                "missing_info": [],
            },
            enforced,
        )

        self.assertFalse(valid)
        self.assertIn("Empty constrained LLM field: bois_section", errors)
        self.assertIn("Forbidden response form detected: generic_consulting", errors)


if __name__ == "__main__":
    unittest.main()
