"""Render audit results and what-if impact for terminal, Slack, or a PR."""
from __future__ import annotations

from collections import defaultdict

from .models import ImpactReport, Violation


def audit_text(violations: list[Violation]) -> str:
    if not violations:
        return "✅ No violations of enforced policies."
    by_res: dict[str, list[Violation]] = defaultdict(list)
    for v in violations:
        by_res[v.ref].append(v)
    lines = [f"❌ {len(violations)} violation(s) across {len(by_res)} resource(s):", "=" * 72]
    for ref, vs in by_res.items():
        lines.append(ref)
        for v in vs:
            lines.append(f"    [{v.policy}] {v.message}")
            lines.append(f"        fix: {v.fix}")
    return "\n".join(lines)


def impact_text(report: ImpactReport) -> str:
    mark = "⚠️ " if report.affected_resources else "✅ "
    lines = [
        f"WHAT-IF: enforce '{report.policy}'",
        f"  {report.description}",
        "-" * 72,
        f"  {mark} {report.affected_resources} of {report.evaluated_resources} "
        f"applicable resource(s) would start failing admission.",
    ]
    if report.by_namespace:
        ns = ", ".join(f"{k}: {v}" for k, v in report.by_namespace.items())
        lines.append(f"  by namespace — {ns}")
    if report.violations:
        lines.append("  affected:")
        for v in report.violations:
            lines.append(f"    - {v.ref}: {v.message}")
        lines.append(f"  fix: {report.violations[0].fix}")
    return "\n".join(lines)


def audit_markdown(violations: list[Violation]) -> str:
    if not violations:
        return "## ✅ Policy audit\n\nNo violations of enforced policies."
    lines = [
        f"## ❌ Policy audit — {len(violations)} violation(s)",
        "",
        "| Resource | Policy | Why | Fix |",
        "| --- | --- | --- | --- |",
    ]
    for v in violations:
        lines.append(f"| `{v.ref}` | {v.policy} | {v.message} | {v.fix} |")
    return "\n".join(lines)


def impact_markdown(report: ImpactReport) -> str:
    lines = [
        f"## 🔮 What-if: enforcing `{report.policy}`",
        "",
        f"_{report.description}_",
        "",
        f"**{report.affected_resources} of {report.evaluated_resources}** applicable "
        f"resources would start failing admission.",
        "",
    ]
    if report.violations:
        lines += ["| Resource | Why |", "| --- | --- |"]
        lines += [f"| `{v.ref}` | {v.message} |" for v in report.violations]
    return "\n".join(lines)
