"""Domain models for the Gatekeeper policy engine.

The engine works on plain Kubernetes resources (the JSON you get from
``kubectl get ... -o json``) and a catalog of constraints. Two questions it
answers:

- **Audit** — which live resources violate the constraints that are *enforced*
  today?
- **What-if** — if we introduce or tighten a constraint (flip it from dry-run
  to deny), which workloads would start failing, and why?

Everything is a small dataclass so the policy checks stay readable and an agent
can reason over compact violation objects instead of raw manifests.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum


class Enforcement(str, Enum):
    DENY = "deny"        # blocks admission today — audit surfaces live violations
    WARN = "warn"        # admits but warns
    DRYRUN = "dryrun"    # not enforced yet — the "what-if" candidate


# Workload kinds that carry a pod template (where containers/probes live).
WORKLOAD_KINDS = frozenset({"Deployment", "StatefulSet", "DaemonSet", "Pod", "Job", "CronJob"})


@dataclass(frozen=True)
class Resource:
    """A thin wrapper over a parsed Kubernetes manifest."""
    raw: dict

    @property
    def api_version(self) -> str:
        return self.raw.get("apiVersion", "")

    @property
    def kind(self) -> str:
        return self.raw.get("kind", "")

    @property
    def name(self) -> str:
        return self.raw.get("metadata", {}).get("name", "<unnamed>")

    @property
    def namespace(self) -> str:
        return self.raw.get("metadata", {}).get("namespace", "default")

    @property
    def labels(self) -> dict:
        return self.raw.get("metadata", {}).get("labels", {}) or {}

    @property
    def annotations(self) -> dict:
        return self.raw.get("metadata", {}).get("annotations", {}) or {}

    @property
    def spec(self) -> dict:
        return self.raw.get("spec", {}) or {}

    @property
    def ref(self) -> str:
        return f"{self.kind}/{self.namespace}/{self.name}"

    @property
    def containers(self) -> list[dict]:
        """Return the container specs regardless of workload kind."""
        k = self.kind
        if k == "Pod":
            return self.spec.get("containers", []) or []
        if k == "CronJob":
            return (self.spec.get("jobTemplate", {}).get("spec", {})
                    .get("template", {}).get("spec", {}).get("containers", []) or [])
        if k in WORKLOAD_KINDS:
            return self.spec.get("template", {}).get("spec", {}).get("containers", []) or []
        return []


@dataclass(frozen=True)
class Constraint:
    """A Gatekeeper-style constraint: a check plus the metadata that makes a
    violation explainable and fixable."""
    name: str
    kinds: frozenset[str]
    description: str
    fix: str
    check: Callable[["Resource", dict], list[str]]
    enforcement: Enforcement = Enforcement.DENY
    params: dict = field(default_factory=dict)

    def applies_to(self, r: Resource) -> bool:
        return r.kind in self.kinds


@dataclass(frozen=True)
class Violation:
    policy: str
    ref: str
    kind: str
    namespace: str
    name: str
    message: str
    fix: str
    enforcement: str

    def as_dict(self) -> dict:
        return {
            "policy": self.policy, "resource": self.ref, "kind": self.kind,
            "namespace": self.namespace, "name": self.name,
            "message": self.message, "fix": self.fix, "enforcement": self.enforcement,
        }


@dataclass(frozen=True)
class ImpactReport:
    """The answer to 'if we enforce this constraint, what breaks?'"""
    policy: str
    description: str
    affected_resources: int
    evaluated_resources: int
    by_namespace: dict
    violations: list[Violation]

    def as_dict(self) -> dict:
        return {
            "policy": self.policy,
            "description": self.description,
            "affected_resources": self.affected_resources,
            "evaluated_resources": self.evaluated_resources,
            "by_namespace": self.by_namespace,
            "violations": [v.as_dict() for v in self.violations],
        }
