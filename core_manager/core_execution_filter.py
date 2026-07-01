def build_core_execution_filter(active_core, sima_analysis, gate_decision) -> dict:
    return {
        "mode": "unknown",
        "forbidden_outputs": [],
        "required_reasoning_style": [],
        "must_use_layers": ["BOIS", "SIMA", "BORIS"],
        "response_boundary": "unset",
    }
