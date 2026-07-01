from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core_manager.core_flow_trace import trace_core_information_flow
from core_manager.core_loader import ActiveCore


class CoreFlowTraceTest(unittest.TestCase):
    def test_trace_reports_first_identity_loss_at_runtime_summary(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "core").mkdir()
            (root / "core" / "main.machine.json").write_text('{"rule":"native"}', encoding="utf-8")
            active_core = ActiveCore(
                active_path=root,
                core_version="trace-test",
                validation_status="passed",
                validation_errors=[],
                manifest={"version": "trace-test"},
                machine_json=[{"rule": "native"}],
                load_order=["core/main.machine.json"],
            )

            with patch("core_manager.core_flow_trace.get_active_core", return_value=active_core):
                trace = trace_core_information_flow("Расскажи о BOIS")

        self.assertEqual(trace["core_identity"]["detected_version"], "trace-test")
        self.assertEqual(trace["first_identity_loss_stage"], 'boris_runtime.analysis["active_core"]')
        self.assertEqual(trace["first_reduction_stage"], 'boris_runtime.analysis["active_core"]')
        self.assertTrue(trace["stages"][0]["same_information_identity_assertable"])
        self.assertFalse(trace["stages"][1]["same_information_identity_assertable"])

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
