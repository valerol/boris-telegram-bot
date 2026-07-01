from __future__ import annotations

from core_manager.extracted_contract import ExtractedContract, FieldProvenance
from core_manager.core_loader import ActiveCore


SOURCE_FILES = (
    "runtime/surface_contract.json",
    "core/*.machine.json",
    "tables/active_rules.csv",
    "tables/procedures.csv",
    "tables/stop_signals.csv",
    "tables/criteria.csv",
    "core/conflict_policy.json",
    "load_order.txt",
    "integrity/validation_report.json",
)

OUTPUT_FIELD_SOURCES = {
    "scope_status": ("runtime/surface_contract.json", "surface_contract"),
    "request_type": ("core/*.machine.json", "machine_json"),
    "primary_domain": ("tables/active_rules.csv", "CORE-04"),
    "applied_domain": ("tables/active_rules.csv", "CORE-08"),
    "bois_section": ("tables/active_rules.csv", "CORE-01"),
    "sima_section": ("tables/active_rules.csv", "CORE-02"),
    "boris_section": ("tables/procedures.csv", "procedures"),
    "direct_answer": ("runtime/surface_contract.json", "surface_contract"),
    "boundary_note": ("core/conflict_policy.json", "conflict_policy"),
    "next_step": ("tables/active_rules.csv", "CORE-05"),
    "confidence": ("integrity/validation_report.json", "validation_report"),
    "missing_info": ("tables/stop_signals.csv", "STOP-UNKNOWN"),
}

INPUT_FIELD_SOURCES = {
    "user_text": ("runtime/surface_contract.json", "surface_contract"),
    "sima_analysis": ("core/*.machine.json", "machine_json"),
    "gate_decision": ("core/conflict_policy.json", "conflict_policy"),
    "core_application_protocol": ("tables/active_rules.csv", "active_rules"),
}


def extract_contract_from_active_core(active_core: ActiveCore) -> ExtractedContract:
    if not active_core.available:
        return ExtractedContract(
            contract_id="emergency-static-contract",
            core_version=active_core.detected_version,
            missing_sources=list(SOURCE_FILES),
            extraction_status="unavailable",
        )

    missing_sources = _missing_sources(active_core)
    source_files = [source for source in SOURCE_FILES if source not in missing_sources]
    required_output_fields = [
        _field(name, "output", OUTPUT_FIELD_SOURCES[name], active_core)
        for name in OUTPUT_FIELD_SOURCES
    ]
    required_input_fields = [
        _field(name, "input", INPUT_FIELD_SOURCES[name], active_core)
        for name in INPUT_FIELD_SOURCES
    ]

    return ExtractedContract(
        contract_id=f"boris-response-contract:{active_core.detected_version or 'unknown'}",
        core_version=active_core.detected_version,
        source_files=source_files,
        required_input_fields=required_input_fields,
        required_output_fields=required_output_fields,
        organs=_organs(active_core),
        rules=_select_rules(active_core),
        procedures=active_core.procedures,
        stop_signals=active_core.stop_signals,
        criteria=active_core.criteria,
        surface_rules=active_core.surface_contract,
        conflict_policy=active_core.conflict_policy,
        validation_boundary=active_core.validation_report,
        missing_sources=missing_sources,
        extraction_status="partial" if missing_sources else "complete",
    )


def _field(name: str, direction: str, source: tuple[str, str], active_core: ActiveCore) -> dict:
    source_file, preferred_source_id = source
    source_id, reason = _field_provenance_source(source_file, preferred_source_id, active_core)
    return {
        "name": name,
        "direction": direction,
        "type": _field_type(name),
        "provenance": FieldProvenance(
            field_path=f"{direction}.{name}",
            source_file=source_file,
            source_id=source_id,
            reason=reason,
        ).to_dict(),
        "source_available": source_file not in _missing_sources(active_core),
    }


def _field_type(name: str) -> str:
    if name == "confidence":
        return "number"
    if name == "missing_info":
        return "array"
    return "string"


def _field_provenance_source(source_file: str, preferred_source_id: str, active_core: ActiveCore) -> tuple[str, str]:
    if source_file == "tables/active_rules.csv":
        row = _find_row(active_core.active_rules, preferred_source_id) or _first_row(active_core.active_rules)
        return _row_source(row, preferred_source_id, source_file)
    if source_file == "tables/stop_signals.csv":
        row = _find_row(active_core.stop_signals, preferred_source_id) or _first_row(active_core.stop_signals)
        return _row_source(row, preferred_source_id, source_file)
    if source_file == "tables/procedures.csv":
        row = _first_row(active_core.procedures)
        return _row_source(row, preferred_source_id, source_file)
    if source_file == "tables/criteria.csv":
        row = _first_row(active_core.criteria)
        return _row_source(row, preferred_source_id, source_file)
    if source_file == "runtime/surface_contract.json":
        keys = ", ".join(str(key) for key in list((active_core.surface_contract or {}).keys())[:6])
        return preferred_source_id, f"derived from loaded surface contract keys: {keys}" if keys else "surface contract source missing"
    if source_file == "core/conflict_policy.json":
        keys = ", ".join(str(key) for key in list((active_core.conflict_policy or {}).keys())[:6])
        return preferred_source_id, f"derived from loaded conflict policy keys: {keys}" if keys else "conflict policy source missing"
    if source_file == "core/*.machine.json":
        snippets = _machine_snippets(active_core)
        return preferred_source_id, f"derived from loaded machine JSON keys: {', '.join(snippets[:6])}" if snippets else "machine JSON source missing"
    if source_file == "integrity/validation_report.json":
        status = (active_core.validation_report or {}).get("status", active_core.validation_status)
        return preferred_source_id, f"derived from validation report status: {status}" if status else "validation report source missing"
    return preferred_source_id, f"derived from {source_file}"


def _find_row(rows: list[dict], row_id: str) -> dict | None:
    for row in rows:
        if str(row.get("id") or row.get("rule_id") or row.get("source_id") or "") == row_id:
            return row
    return None


def _first_row(rows: list[dict]) -> dict | None:
    return rows[0] if rows else None


def _row_source(row: dict | None, fallback_id: str, source_file: str) -> tuple[str, str]:
    if not row:
        return fallback_id, f"{source_file} source missing"
    source_id = str(row.get("id") or row.get("rule_id") or row.get("source_id") or fallback_id)
    label = row.get("title") or row.get("name") or row.get("signal") or row.get("procedure") or row.get("criterion")
    if label:
        return source_id, f"derived from loaded {source_file} row: {label}"
    return source_id, f"derived from loaded {source_file} row"


def _missing_sources(active_core: ActiveCore) -> list[str]:
    missing = []
    for source in SOURCE_FILES:
        if not _source_available(source, active_core):
            missing.append(source)
    return missing


def _source_available(source: str, active_core: ActiveCore) -> bool:
    if source == "runtime/surface_contract.json":
        return bool(active_core.surface_contract)
    if source == "core/*.machine.json":
        return bool(active_core.machine_json)
    if source == "tables/active_rules.csv":
        return bool(active_core.active_rules)
    if source == "tables/procedures.csv":
        return bool(active_core.procedures)
    if source == "tables/stop_signals.csv":
        return bool(active_core.stop_signals)
    if source == "tables/criteria.csv":
        return bool(active_core.criteria)
    if source == "core/conflict_policy.json":
        return bool(active_core.conflict_policy)
    if source == "load_order.txt":
        return bool(active_core.load_order)
    if source == "integrity/validation_report.json":
        return active_core.validation_report is not None
    return False


def _organs(active_core: ActiveCore) -> list[dict]:
    organ_names = ("BOIS", "SIMA", "BORIS")
    snippets = _machine_snippets(active_core)
    return [
        {
            "name": name,
            "source_file": "core/*.machine.json",
            "source_id": "machine_json",
            "evidence": snippets,
        }
        for name in organ_names
    ]


def _machine_snippets(active_core: ActiveCore) -> list[str]:
    snippets = []
    for item in active_core.machine_json:
        if isinstance(item, dict):
            snippets.extend(str(key) for key in list(item.keys())[:8])
    return snippets[:16]


def _select_rules(active_core: ActiveCore) -> list[dict]:
    preferred = {"CORE-01", "CORE-02", "CORE-04", "CORE-05", "CORE-08"}
    selected = [rule for rule in active_core.active_rules if rule.get("id") in preferred]
    return selected or active_core.active_rules[:8]
