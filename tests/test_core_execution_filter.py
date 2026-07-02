import unittest
from pathlib import Path

from boris_gate import ALLOW, DENY_OUT_OF_SCOPE, GateDecision
from boris_execution.core_execution_filter import build_core_execution_filter


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


if __name__ == "__main__":
    unittest.main()
