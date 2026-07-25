"""MCP server exposing the policy engine as agent tools.

Lets a Claude agent audit a cluster dump and run what-if impact analysis for a
proposed constraint — while the policy checks stay deterministic and tested.

    python -m gatekeeper_guard.mcp_server examples/resources.json

``mcp`` is an optional dependency (pip install "agentic-gatekeeper[mcp]").
"""
from __future__ import annotations

import sys

from . import engine, loader, policies, report

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:  # pragma: no cover
    FastMCP = None


def build_server(resources_path: str) -> FastMCP:
    if FastMCP is None:  # pragma: no cover
        raise SystemExit('The "mcp" package is required. Install: pip install "agentic-gatekeeper[mcp]"')

    mcp = FastMCP("agentic-gatekeeper")

    def _load():
        return loader.load(resources_path)

    @mcp.tool()
    def audit() -> list[dict]:
        """Live violations of the policies enforced (deny) today."""
        return [v.as_dict() for v in engine.audit(_load())]

    @mcp.tool()
    def what_if(policy: str) -> dict:
        """If `policy` were enforced, which resources would fail and why?"""
        return engine.whatif_by_name(_load(), policy).as_dict()

    @mcp.tool()
    def what_if_all_candidates() -> list[dict]:
        """Impact of every not-yet-enforced (dry-run) policy."""
        res = _load()
        return [engine.whatif(res, c).as_dict() for c in engine.candidate_policies()]

    @mcp.tool()
    def list_policies() -> list[dict]:
        """The policy catalog with enforcement status."""
        return [{"name": c.name, "enforcement": c.enforcement.value,
                 "kinds": sorted(c.kinds), "description": c.description} for c in policies.CATALOG]

    @mcp.tool()
    def audit_report(fmt: str = "markdown") -> str:
        """Rendered audit report (markdown|text)."""
        v = engine.audit(_load())
        return report.audit_markdown(v) if fmt == "markdown" else report.audit_text(v)

    return mcp


def main() -> None:  # pragma: no cover
    if len(sys.argv) < 2:
        print("usage: python -m gatekeeper_guard.mcp_server <resources.json>", file=sys.stderr)
        raise SystemExit(2)
    build_server(sys.argv[1]).run()


if __name__ == "__main__":  # pragma: no cover
    main()
