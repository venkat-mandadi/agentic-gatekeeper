"""Evaluate resources against constraints — audit today, preview tomorrow."""
from __future__ import annotations

from collections import defaultdict

from . import policies
from .models import Constraint, Enforcement, ImpactReport, Resource, Violation


def evaluate_one(r: Resource, c: Constraint) -> list[Violation]:
    if not c.applies_to(r):
        return []
    return [
        Violation(c.name, r.ref, r.kind, r.namespace, r.name, msg, c.fix, c.enforcement.value)
        for msg in c.check(r, c.params)
    ]


def audit(resources: list[Resource], constraints: list[Constraint] | None = None) -> list[Violation]:
    """Live violations of the constraints that are *enforced* (deny) today."""
    active = [c for c in (constraints or policies.CATALOG) if c.enforcement is Enforcement.DENY]
    out: list[Violation] = []
    for r in resources:
        for c in active:
            out.extend(evaluate_one(r, c))
    # group by resource so a reviewer reads all of a workload's problems together
    out.sort(key=lambda v: (v.namespace, v.name, v.policy))
    return out


def whatif(resources: list[Resource], candidate: Constraint) -> ImpactReport:
    """If ``candidate`` were enforced, which resources would fail and why?

    This is the pre-flight check before flipping a Gatekeeper constraint from
    dryrun to deny — the answer to 'what breaks if I ship this policy?'
    """
    applicable = [r for r in resources if candidate.applies_to(r)]
    violations: list[Violation] = []
    for r in applicable:
        violations.extend(evaluate_one(r, candidate))

    affected = {v.ref for v in violations}
    by_ns: dict[str, int] = defaultdict(int)
    for ref in affected:
        by_ns[ref.split("/")[1]] += 1

    violations.sort(key=lambda v: (v.namespace, v.name))
    return ImpactReport(
        policy=candidate.name,
        description=candidate.description,
        affected_resources=len(affected),
        evaluated_resources=len(applicable),
        by_namespace=dict(sorted(by_ns.items())),
        violations=violations,
    )


def whatif_by_name(resources: list[Resource], name: str) -> ImpactReport:
    if name not in policies.BY_NAME:
        raise KeyError(f"unknown policy '{name}'. Known: {', '.join(sorted(policies.BY_NAME))}")
    return whatif(resources, policies.BY_NAME[name])


def candidate_policies() -> list[Constraint]:
    """Policies not yet enforced — the natural what-if candidates."""
    return [c for c in policies.CATALOG if c.enforcement is not Enforcement.DENY]
