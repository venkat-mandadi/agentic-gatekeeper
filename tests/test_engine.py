"""Engine tests: audit + what-if against the sample cluster dump."""
from pathlib import Path

import pytest

from gatekeeper_guard import engine, loader

SAMPLE = Path(__file__).parent.parent / "examples" / "resources.json"


@pytest.fixture
def resources():
    return loader.load(SAMPLE)


def test_sample_loads(resources):
    assert len(resources) == 8
    kinds = {r.kind for r in resources}
    assert {"Deployment", "Service", "BackendConfig"} <= kinds


def test_audit_finds_the_expected_violations(resources):
    v = engine.audit(resources)
    assert len(v) == 5
    policies_hit = {(x.name, x.policy) for x in v}
    refs = {(x.name, x.policy) for x in v}
    assert ("catalog-web", "image-valid-semver") in refs      # :latest
    assert ("catalog-web", "require-probes") in refs          # missing readiness
    assert ("legacy-worker", "image-valid-semver") in refs    # 1.4 not semver
    assert ("payments-svc", "service-has-backendconfig-annotation") in refs
    assert ("payments-bec", "backendconfig-has-securitypolicy") in refs
    assert policies_hit  # sanity


def test_compliant_resources_are_not_flagged(resources):
    flagged = {x.name for x in engine.audit(resources)}
    assert "payments-api" not in flagged
    assert "analytics" not in flagged
    assert "catalog-svc" not in flagged
    assert "catalog-bec" not in flagged


def test_whatif_owner_label_impact(resources):
    rep = engine.whatif_by_name(resources, "require-owner-label")
    # payments-api has team; catalog-web, legacy-worker, analytics don't
    assert rep.affected_resources == 3
    assert rep.evaluated_resources == 4          # four Deployments
    names = {v.name for v in rep.violations}
    assert names == {"catalog-web", "legacy-worker", "analytics"}


def test_whatif_resource_limits_impact(resources):
    rep = engine.whatif_by_name(resources, "require-resource-limits")
    assert rep.affected_resources == 3           # only payments-api sets limits
    assert "payments-api" not in {v.name for v in rep.violations}


def test_whatif_unknown_policy_raises(resources):
    with pytest.raises(KeyError):
        engine.whatif_by_name(resources, "does-not-exist")


def test_candidate_policies_are_the_dryrun_ones(resources):
    names = {c.name for c in engine.candidate_policies()}
    assert names == {"require-owner-label", "require-resource-limits"}


def test_violation_serialization(resources):
    v = engine.audit(resources)[0]
    d = v.as_dict()
    assert {"policy", "resource", "message", "fix", "enforcement"} <= set(d)
