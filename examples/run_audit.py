"""Runnable demo — no cluster needed.

    python examples/run_audit.py

Audits the sample resources against the enforced policies, then previews the
impact of each candidate (dry-run) policy.
"""
from pathlib import Path

from gatekeeper_guard import engine, loader, report

HERE = Path(__file__).parent


def main() -> None:
    resources = loader.load(HERE / "resources.json")

    print("### EXISTING VIOLATIONS (enforced policies) ###\n")
    print(report.audit_text(engine.audit(resources)))

    print("\n\n### WHAT-IF (candidate policies not yet enforced) ###\n")
    for candidate in engine.candidate_policies():
        print(report.impact_text(engine.whatif(resources, candidate)))
        print()


if __name__ == "__main__":
    main()
