"""Unit tests for individual policy checks."""
from gatekeeper_guard import policies
from gatekeeper_guard.models import Resource


def deploy(name, containers, labels=None):
    return Resource({
        "apiVersion": "apps/v1", "kind": "Deployment",
        "metadata": {"name": name, "namespace": "ns", "labels": labels or {}},
        "spec": {"template": {"spec": {"containers": containers}}},
    })


def test_semver_accepts_valid_tags():
    r = deploy("a", [{"name": "c", "image": "repo/app:v1.2.3"}])
    assert policies.check_image_semver(r, {}) == []


def test_semver_rejects_latest_and_missing_and_bad():
    assert policies.check_image_semver(deploy("a", [{"name": "c", "image": "nginx:latest"}]), {})
    assert policies.check_image_semver(deploy("a", [{"name": "c", "image": "nginx"}]), {})
    assert policies.check_image_semver(deploy("a", [{"name": "c", "image": "repo/app:1.4"}]), {})


def test_semver_allows_registry_port_and_digest():
    # registry:port must not be mistaken for a tag
    assert policies.check_image_semver(deploy("a", [{"name": "c", "image": "reg:5000/app:v1.0.0"}]), {}) == []
    # a digest pin is immutable and acceptable
    assert policies.check_image_semver(deploy("a", [{"name": "c", "image": "app@sha256:abcd"}]), {}) == []


def test_probes_require_both():
    only_live = [{"name": "c", "image": "x:v1.0.0", "livenessProbe": {}}]
    msgs = policies.check_probes(deploy("a", only_live), {})
    assert msgs and "readinessProbe" in msgs[0]
    both = [{"name": "c", "image": "x:v1.0.0", "livenessProbe": {}, "readinessProbe": {}}]
    assert policies.check_probes(deploy("a", both), {}) == []


def test_backendconfig_security_policy():
    missing = Resource({"kind": "BackendConfig", "metadata": {"name": "b"}, "spec": {}})
    assert policies.check_backendconfig_securitypolicy(missing, {})
    present = Resource({"kind": "BackendConfig", "metadata": {"name": "b"},
                        "spec": {"securityPolicy": {"name": "armor"}}})
    assert policies.check_backendconfig_securitypolicy(present, {}) == []


def test_service_backendconfig_annotation():
    missing = Resource({"kind": "Service", "metadata": {"name": "s"}})
    assert policies.check_service_backendconfig_annotation(missing, {})
    present = Resource({"kind": "Service", "metadata": {"name": "s",
                        "annotations": {"cloud.google.com/backend-config": "x"}}})
    assert policies.check_service_backendconfig_annotation(present, {}) == []


def test_required_label():
    assert policies.check_required_label(deploy("a", []), {"label": "team"})
    assert policies.check_required_label(deploy("a", [], labels={"team": "x"}), {"label": "team"}) == []
