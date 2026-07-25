"""agentic-gatekeeper — audit GKE resources against OPA/Gatekeeper policies and
preview the impact of new ones.

Answers two questions: which live resources violate the policies enforced today
(audit), and — before you flip a constraint from dry-run to deny — which
workloads would start failing and why (what-if).

Public API:
    from gatekeeper_guard import loader, engine, policies, report
"""
from . import engine, loader, policies, report
from .models import Constraint, Enforcement, ImpactReport, Resource, Violation

__version__ = "0.1.0"

__all__ = [
    "Constraint",
    "Enforcement",
    "ImpactReport",
    "Resource",
    "Violation",
    "engine",
    "loader",
    "policies",
    "report",
]
