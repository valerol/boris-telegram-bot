from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FieldProvenance:
    field_path: str
    source_file: str
    source_id: str
    reason: str

    def to_dict(self) -> dict:
        return {
            "field_path": self.field_path,
            "source_file": self.source_file,
            "source_id": self.source_id,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class ExtractedContract:
    contract_id: str
    core_version: str | None
    source_files: list[str] = field(default_factory=list)
    required_input_fields: list[dict] = field(default_factory=list)
    required_output_fields: list[dict] = field(default_factory=list)
    organs: list[dict] = field(default_factory=list)
    rules: list[dict] = field(default_factory=list)
    procedures: list[dict] = field(default_factory=list)
    stop_signals: list[dict] = field(default_factory=list)
    criteria: list[dict] = field(default_factory=list)
    surface_rules: dict | None = None
    conflict_policy: dict | None = None
    validation_boundary: dict | None = None
    missing_sources: list[str] = field(default_factory=list)
    extraction_status: str = "unavailable"

    @property
    def available(self) -> bool:
        return self.extraction_status in {"complete", "partial"}

    @property
    def output_field_names(self) -> list[str]:
        return [field["name"] for field in self.required_output_fields if "name" in field]

    def to_dict(self) -> dict:
        return {
            "contract_id": self.contract_id,
            "core_version": self.core_version,
            "source_files": self.source_files,
            "required_input_fields": self.required_input_fields,
            "required_output_fields": self.required_output_fields,
            "organs": self.organs,
            "rules": self.rules,
            "procedures": self.procedures,
            "stop_signals": self.stop_signals,
            "criteria": self.criteria,
            "surface_rules": self.surface_rules,
            "conflict_policy": self.conflict_policy,
            "validation_boundary": self.validation_boundary,
            "missing_sources": self.missing_sources,
            "extraction_status": self.extraction_status,
        }
