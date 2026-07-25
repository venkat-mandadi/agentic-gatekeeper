"""Command-line entry point.

    gatekeeper-check <resources.json> audit
    gatekeeper-check <resources.json> whatif <policy-name>
    gatekeeper-check <resources.json> whatif --all
    gatekeeper-check <resources.json> policies      # list the catalog

Runs entirely offline against a kubectl JSON dump — no cluster connection.
"""
from __future__ import annotations

import argparse

from . import engine, loader, policies, report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="gatekeeper-check",
                                description="Audit and preview OPA/Gatekeeper policies against Kubernetes resources.")
    p.add_argument("resources", help="kubectl -o json dump or manifest file (see examples/)")
    p.add_argument("mode", choices=["audit", "whatif", "policies"])
    p.add_argument("policy", nargs="?", help="policy name for whatif mode")
    p.add_argument("--all", action="store_true", help="whatif: run every candidate (dry-run) policy")
    p.add_argument("--format", choices=["text", "markdown"], default="text")
    args = p.parse_args(argv)

    if args.mode == "policies":
        for c in policies.CATALOG:
            print(f"[{c.enforcement.value:6}] {c.name:38} {c.description}")
        return 0

    resources = loader.load(args.resources)

    if args.mode == "audit":
        violations = engine.audit(resources)
        print(report.audit_markdown(violations) if args.format == "markdown" else report.audit_text(violations))
        return 0

    # whatif
    candidates = engine.candidate_policies() if args.all else None
    if candidates is None:
        if not args.policy:
            p.error("whatif needs a <policy-name> or --all")
        candidates = [policies.BY_NAME.get(args.policy)]
        if candidates[0] is None:
            p.error(f"unknown policy '{args.policy}'. Try: {', '.join(sorted(policies.BY_NAME))}")
    for c in candidates:
        rep = engine.whatif(resources, c)
        print(report.impact_markdown(rep) if args.format == "markdown" else report.impact_text(rep))
        print()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
