from boris_identity import ALLOWED_DOMAINS, ALLOWED_OPERATIONS, FORBIDDEN_DOMAINS, FORBIDDEN_OPERATIONS


def is_allowed_domain(domain: str) -> bool:
    return domain in ALLOWED_DOMAINS


def is_forbidden_domain(domain: str) -> bool:
    return domain in FORBIDDEN_DOMAINS


def is_allowed_operation(operation: str) -> bool:
    return operation in ALLOWED_OPERATIONS


def is_forbidden_operation(operation: str) -> bool:
    return operation in FORBIDDEN_OPERATIONS
