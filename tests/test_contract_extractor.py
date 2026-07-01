from __future__ import annotations

import unittest
from pathlib import Path

from boris_llm import build_response_format
from boris_response_contract import validate_response_contract
from core_manager.contract_extractor import extract_contract_from_active_core
from core_manager.core_loader import ActiveCore


class ContractExtractorTest(unittest.TestCase):
    def test_contract_extractor_reads_active_core(self):
        contract = extract_contract_from_active_core(_active_core())

        self.assertEqual(contract.extraction_status, "complete")
        self.assertEqual(contract.core_version, "extract-test")
        self.assertTrue(contract.source_files)
        self.assertTrue(contract.required_output_fields)
        self.assertTrue(contract.rules)

    def test_every_required_output_field_has_provenance(self):
        contract = extract_contract_from_active_core(_active_core())

        for field in contract.required_output_fields:
            provenance = field.get("provenance")
            self.assertTrue(provenance)
            self.assertTrue(provenance["field_path"])
            self.assertTrue(provenance["source_file"])
            self.assertTrue(provenance["source_id"])
            self.assertTrue(provenance["reason"])

    def test_missing_source_file_makes_extraction_partial(self):
        active_core = _active_core()
        active_core = ActiveCore(
            active_path=active_core.active_path,
            core_version=active_core.core_version,
            validation_status=active_core.validation_status,
            validation_errors=active_core.validation_errors,
            manifest=active_core.manifest,
            validation_report=active_core.validation_report,
            machine_json=active_core.machine_json,
            active_rules=[],
            stop_signals=active_core.stop_signals,
            procedures=active_core.procedures,
            criteria=active_core.criteria,
            surface_contract=active_core.surface_contract,
            conflict_policy=active_core.conflict_policy,
            language_policy=active_core.language_policy,
            load_order=active_core.load_order,
        )

        contract = extract_contract_from_active_core(active_core)

        self.assertEqual(contract.extraction_status, "partial")
        self.assertIn("tables/active_rules.csv", contract.missing_sources)

    def test_llm_schema_is_built_from_extracted_contract(self):
        contract = extract_contract_from_active_core(_active_core())

        response_format = build_response_format(contract)
        schema = response_format["json_schema"]["schema"]

        self.assertEqual(response_format["type"], "json_schema")
        self.assertEqual(schema["required"], contract.output_field_names)
        self.assertIn("scope_status", schema["properties"])

    def test_validator_accepts_extracted_contract_dict(self):
        contract = extract_contract_from_active_core(_active_core())
        value = {
            "scope_status": "in_scope",
            "request_type": "definition",
            "primary_domain": "boris_support",
            "applied_domain": "bois",
            "bois_section": "BOIS field",
            "sima_section": "SIMA field",
            "boris_section": "BORIS field",
            "direct_answer": "Answer",
            "boundary_note": "",
            "next_step": "Next",
            "confidence": 0.8,
            "missing_info": [],
        }

        parsed, errors = validate_response_contract(value, contract.to_dict())

        self.assertEqual(errors, [])
        self.assertEqual(parsed["direct_answer"], "Answer")

    def test_validator_does_not_require_emergency_fields_when_extracted_contract_is_available(self):
        extracted_contract = _MinimalExtractedContract(["direct_answer"])

        parsed, errors = validate_response_contract({"direct_answer": "core-defined field"}, extracted_contract)

        self.assertEqual(errors, [])
        self.assertEqual(parsed["direct_answer"], "core-defined field")


def _active_core() -> ActiveCore:
    return ActiveCore(
        active_path=Path("core/active"),
        core_version="extract-test",
        validation_status="passed",
        validation_errors=[],
        manifest={"version": "extract-test"},
        validation_report={"status": "passed"},
        machine_json=[{"machine": "contract-machine"}],
        active_rules=[
            {"id": "CORE-01", "title": "Смысл до формы", "formulation": "meaning before form"},
            {"id": "CORE-02", "title": "Разделение утверждений", "formulation": "separate claims"},
            {"id": "CORE-04", "title": "Протокол и инструкция различаются", "formulation": "protocol boundary"},
            {"id": "CORE-05", "title": "Следующий шаг не является знанием", "formulation": "next step hypothesis"},
            {"id": "CORE-08", "title": "Нет ложной универсальности", "formulation": "no false universality"},
        ],
        stop_signals=[{"id": "STOP-UNKNOWN", "signal": "unknown"}],
        procedures=[{"id": "PROC-01", "content": "procedure"}],
        criteria=[{"id": "CRIT-01", "content": "criterion"}],
        surface_contract={"visible_header": {"required": True}},
        conflict_policy={"principle": "boundary"},
        language_policy={"language": "operator"},
        load_order=["runtime/surface_contract.json"],
    )


class _MinimalExtractedContract:
    available = True

    def __init__(self, fields: list[str]) -> None:
        self.output_field_names = fields


if __name__ == "__main__":
    unittest.main()
