from dataclasses import dataclass

from boris_capabilities import (
    is_allowed_domain,
    is_allowed_operation,
    is_forbidden_domain,
    is_forbidden_operation,
)


ALLOW = "ALLOW"
DENY_OUT_OF_SCOPE = "DENY_OUT_OF_SCOPE"
CLARIFY = "CLARIFY"
ALLOW_WITH_SCOPE_LIMIT = "ALLOW_WITH_SCOPE_LIMIT"


@dataclass(frozen=True)
class GateDecision:
    decision: str
    reason: str

    def to_dict(self) -> dict:
        return {
            "decision": self.decision,
            "reason": self.reason,
        }


def decide_capability(analysis: dict, domain: str) -> GateDecision:
    operation = analysis.get("requested_operation", "general_request")

    if is_allowed_domain(domain) or is_allowed_operation(operation):
        if analysis.get("requires_domain_expertise") and _has_boris_relation(analysis):
            return GateDecision(ALLOW_WITH_SCOPE_LIMIT, "external_domain_limited_to_boris_methodology")
        return GateDecision(ALLOW, "inside_boris_support_scope")

    if _has_boris_relation(analysis):
        return GateDecision(ALLOW_WITH_SCOPE_LIMIT, "boris_related_external_domain")

    if is_forbidden_domain(domain) or is_forbidden_operation(operation):
        return GateDecision(DENY_OUT_OF_SCOPE, "outside_boris_support_scope")

    return GateDecision(CLARIFY, "unclear_boris_support_scope")


def _has_boris_relation(analysis: dict) -> bool:
    return bool(
        analysis.get("is_bois_related")
        or analysis.get("is_sima_related")
        or analysis.get("is_boris_related")
    )
