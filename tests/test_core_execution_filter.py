import unittest

from core_manager.core_execution_filter import build_core_execution_filter


class CoreExecutionFilterTest(unittest.TestCase):
    def test_build_core_execution_filter_returns_placeholder_structure(self):
        execution_filter = build_core_execution_filter(
            active_core=object(),
            sima_analysis={"intent": "explain"},
            gate_decision=object(),
        )

        self.assertEqual(execution_filter["mode"], "unknown")
        self.assertEqual(execution_filter["forbidden_outputs"], [])
        self.assertEqual(execution_filter["required_reasoning_style"], [])
        self.assertEqual(execution_filter["must_use_layers"], ["BOIS", "SIMA", "BORIS"])
        self.assertEqual(execution_filter["response_boundary"], "unset")


if __name__ == "__main__":
    unittest.main()
