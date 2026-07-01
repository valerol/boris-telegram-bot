from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core_manager.core_flow_trace import trace_core_information_flow
from core_manager.core_loader import ActiveCore


class CoreFlowTraceTest(unittest.TestCase):
    def test_trace_preserves_identity_through_runtime_analysis_and_prompt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "core").mkdir()
            (root / "core" / "main.machine.json").write_text('{"rule":"native"}', encoding="utf-8")
            (root / "surface.json").write_text('{"mode":"trace-surface"}', encoding="utf-8")
            active_core = ActiveCore(
                active_path=root,
                core_version="trace-test",
                validation_status="passed",
                validation_errors=[],
                manifest={"version": "trace-test"},
                machine_json=[{"rule": "native"}],
                active_rules=[{"rule": "trace-active-rule"}],
                surface_contract={"mode": "trace-surface"},
                conflict_policy={"policy": "trace-conflict"},
                language_policy={"language": "trace-language"},
                load_order=["core/main.machine.json"],
            )

            with patch("core_manager.core_flow_trace.get_active_core", return_value=active_core):
                trace = trace_core_information_flow("Расскажи о BOIS")

        self.assertEqual(trace["core_identity"]["detected_version"], "trace-test")
        self.assertEqual(trace["first_identity_loss_stage"], "runtime LLM boundary")
        self.assertIsNone(trace["first_reduction_stage"])
        self.assertTrue(trace["stages"][0]["same_information_identity_assertable"])
        self.assertTrue(trace["stages"][1]["same_information_identity_assertable"])
        prompt_stage = next(stage for stage in trace["stages"] if stage["stage"] == "boris_llm.build_llm_prompt")
        self.assertTrue(prompt_stage["same_information_identity_assertable"])
        self.assertTrue(prompt_stage["evidence"]["contains_loaded_surface_sha256"])
        self.assertTrue(prompt_stage["evidence"]["contains_surface_contract_value"])
        self.assertTrue(prompt_stage["evidence"]["contains_active_rule_value"])

    def test_trace_reports_missing_core_as_lost(self):
        active_core = ActiveCore(
            active_path=None,
            core_version=None,
            validation_status="missing",
            validation_errors=["Active core path is missing"],
        )

        with patch("core_manager.core_flow_trace.get_active_core", return_value=active_core):
            trace = trace_core_information_flow("Расскажи о BOIS")

        self.assertFalse(trace["core_identity"]["available"])
        self.assertEqual(trace["stages"][0]["information_state"], "lost")
        self.assertEqual(trace["first_identity_loss_stage"], "core_loader.get_active_core")


if __name__ == "__main__":
    unittest.main()
