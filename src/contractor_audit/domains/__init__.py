"""Registry of contract domains. Adding a domain = a new subpackage plus one entry here."""

from contractor_audit.domains.civil_works import DOMAIN as CIVIL_WORKS
from contractor_audit.domains.drilling import DOMAIN as DRILLING
from contractor_audit.shared.domain import AuditDomain

REGISTRY: dict[str, AuditDomain] = {domain.name: domain for domain in (CIVIL_WORKS, DRILLING)}


def get_domain(name: str) -> AuditDomain:
    try:
        return REGISTRY[name]
    except KeyError:
        raise KeyError(f"unknown domain {name!r}; known: {', '.join(sorted(REGISTRY))}") from None
