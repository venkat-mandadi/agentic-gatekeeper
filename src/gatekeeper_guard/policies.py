"""The constraint catalog.

Each policy is a small, pure check that returns a list of human-readable
violation messages (empty = compliant). They mirror real Gatekeeper
ConstraintTemplates but run offline — the same idea as ``gator test``: evaluate
policy against manifests without a live admission webhook, so you can find
today's violations *and* preview tomorrow's.

Adding a policy is one function plus one ``Constraint`` entry in ``CATALOG``.
"""
from __future__ import annotations

import re

from .models import WORKLOAD_KINDS, Constraint, Enforcement, Resource

# X.Y.Z with optional leading v and optional pre-release / build metadata.
_SEMVER = re.compile(r"^v?\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")


def _split_image(image: str) -> tuple[str, str, bool]:
    """Return (repo, tag, has_digest). Handles registry ports and digests."""
    has_digest = "@" in image
    if has_digest:
        image = image.split("@", 1)[0]
    name_part = image.rsplit("/", 1)[-1]      # strip registry[:port]/path
    if ":" in name_part:
        repo, tag = image.rsplit(":", 1)
        return repo, tag, has_digest
    return image, "", has_digest


# ---- checks ---------------------------------------------------------------

def check_image_semver(r: Resource, params: dict) -> list[str]:
    """Images must carry a valid semantic-version tag and never ':latest'."""
    out = []
    for cont in r.containers:
        image = cont.get("image", "")
        name = cont.get("name", "?")
        repo, tag, has_digest = _split_image(image)
        if has_digest and not tag:
            continue  # immutable digest pin is acceptable
        if not tag:
            out.append(f"container '{name}' image '{image}' has no tag (implies :latest)")
        elif tag == "latest":
            out.append(f"container '{name}' image '{image}' uses the ':latest' tag")
        elif not _SEMVER.match(tag):
            out.append(f"container '{name}' image tag '{tag}' is not a valid semantic version (expect X.Y.Z)")
    return out


def check_probes(r: Resource, params: dict) -> list[str]:
    """Deployments etc. must define both liveness and readiness probes."""
    out = []
    for cont in r.containers:
        name = cont.get("name", "?")
        missing = [p for p in ("livenessProbe", "readinessProbe") if p not in cont]
        if missing:
            out.append(f"container '{name}' is missing {' and '.join(missing)}")
    return out


def check_backendconfig_securitypolicy(r: Resource, params: dict) -> list[str]:
    """BackendConfig must reference a Cloud Armor security policy."""
    sp = (r.spec.get("securityPolicy") or {}).get("name")
    if not sp:
        return ["BackendConfig has no spec.securityPolicy.name (Cloud Armor policy)"]
    return []


def check_service_backendconfig_annotation(r: Resource, params: dict) -> list[str]:
    """Services must be annotated to attach a BackendConfig."""
    key = "cloud.google.com/backend-config"
    if key not in r.annotations:
        return [f"Service is missing the '{key}' annotation"]
    return []


def check_required_label(r: Resource, params: dict) -> list[str]:
    """Workloads must carry an ownership label (default: 'team')."""
    key = params.get("label", "team")
    if key not in r.labels:
        return [f"workload is missing the required '{key}' label"]
    return []


def check_resource_limits(r: Resource, params: dict) -> list[str]:
    """Containers must set CPU and memory requests and limits."""
    out = []
    for cont in r.containers:
        name = cont.get("name", "?")
        res = cont.get("resources", {}) or {}
        for section in ("requests", "limits"):
            block = res.get(section, {}) or {}
            missing = [k for k in ("cpu", "memory") if k not in block]
            if missing:
                out.append(f"container '{name}' has no {section} for {', '.join(missing)}")
    return out


# ---- catalog --------------------------------------------------------------

CATALOG: list[Constraint] = [
    Constraint(
        "image-valid-semver", WORKLOAD_KINDS,
        "Container images must use a valid semantic-version tag and never ':latest'.",
        "Pin the image to an immutable X.Y.Z tag (or a digest) instead of ':latest'.",
        check_image_semver, Enforcement.DENY,
    ),
    Constraint(
        "require-probes", frozenset({"Deployment", "StatefulSet", "DaemonSet"}),
        "Workloads must define both liveness and readiness probes.",
        "Add livenessProbe and readinessProbe to each container.",
        check_probes, Enforcement.DENY,
    ),
    Constraint(
        "backendconfig-has-securitypolicy", frozenset({"BackendConfig"}),
        "Every BackendConfig must reference a Cloud Armor security policy.",
        "Set spec.securityPolicy.name to your Cloud Armor policy.",
        check_backendconfig_securitypolicy, Enforcement.DENY,
    ),
    Constraint(
        "service-has-backendconfig-annotation", frozenset({"Service"}),
        "Services must be annotated to bind a BackendConfig.",
        "Add the 'cloud.google.com/backend-config' annotation referencing the BackendConfig.",
        check_service_backendconfig_annotation, Enforcement.DENY,
    ),
    # ---- candidate policies (not enforced yet — the "what-if") ----
    Constraint(
        "require-owner-label", frozenset({"Deployment", "StatefulSet", "DaemonSet"}),
        "Workloads must carry a 'team' ownership label.",
        "Add a metadata.labels.team identifying the owning team.",
        check_required_label, Enforcement.DRYRUN, {"label": "team"},
    ),
    Constraint(
        "require-resource-limits", frozenset({"Deployment", "StatefulSet", "DaemonSet"}),
        "Containers must set CPU and memory requests and limits.",
        "Add resources.requests and resources.limits for cpu and memory.",
        check_resource_limits, Enforcement.DRYRUN,
    ),
]

BY_NAME = {c.name: c for c in CATALOG}
