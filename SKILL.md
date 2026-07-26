---
name: agentic-gatekeeper
description: >-
  Audit Kubernetes / GKE workloads against OPA Gatekeeper policies and preview
  the impact of a new or tightened policy before it is enforced. Finds existing
  violations (bad image tags, missing probes, BackendConfig without a security
  policy, Services missing the backend-config annotation, missing owner labels
  or resource limits) and answers the what-if question — if we flip a constraint
  from dry-run to deny, which apps would fail admission and why. Use this
  whenever the user mentions OPA, Gatekeeper, gator, admission policy,
  policy-as-code, constraint templates, image-tag or probe or label policies, or
  asks what would break if a policy were enforced, or which workloads are out of
  compliance. Prefer this over reading raw manifests and reasoning by hand.
---

# agentic-gatekeeper — policy audit + what-if for GKE

**Your role.** Act as a platform-security SRE who owns policy-as-code: you reason
about admission policy, blast radius, and how to roll a new constraint out
(dry-run → deny) without breaking teams. The engine does the matching; you
explain the violations and plan the rollout.

Checking policy compliance across a cluster is mechanical evaluation over a lot
of manifests, with a couple of parsing traps (registry ports, digests). The
mechanics belong in the engine; your job is judgment and clear communication.
**Do not pull raw manifests into context and evaluate them by hand** — it's slow,
token-heavy, and drifts. Run the engine and reason over its violations.

## What you need to run this

**The engine (required).** Python 3.10+ and the bundled `gatekeeper_guard`
package. This one is mostly an *offline evaluator* — it audits a `kubectl -o json`
dump, so it needs no cluster at all if you feed it a saved dump (see
`examples/resources.json`).

**MCP servers (for live use).** Only two, and both optional:

- **A Kubernetes MCP** — to pull the live resource dump instead of a saved file.
  Any kubectl-backed MCP works; the engine just wants the JSON.
- **A GitHub / GitLab MCP** — to open a PR that flips a constraint from dry-run
  to deny once the what-if comes back clean.

No metrics or chat servers are involved — this skill is about policy, not
telemetry. If you already run a different Kubernetes or SCM tool, swap it in; the
engine only consumes the JSON dump.

## When to use this

Anything policy/admission related: "are we compliant with our Gatekeeper
policies," "what's violating the image-tag policy," "we want to require owner
labels — what breaks," "audit the payments namespace," "if I enforce probes,
which deployments fail." Also drift checks after adding a constraint.

## Workflow

1. **Get the resources.** The engine reads a `kubectl -o json` dump. If the user
   hasn't provided one, tell them:
   `kubectl get deploy,statefulset,daemonset,svc,backendconfig -A -o json > cluster.json`
   or offer to run against the bundled sample (`examples/resources.json`).

2. **Pick the question and run the engine — don't evaluate manifests yourself.**

   - **Existing violations** (what's out of compliance today):
     ```bash
     python scripts/gatekeeper_check.py <resources.json> audit
     ```
   - **What-if** (impact of enforcing a candidate policy):
     ```bash
     python scripts/gatekeeper_check.py <resources.json> whatif <policy-name>
     python scripts/gatekeeper_check.py <resources.json> whatif --all
     ```
   - List the catalog with `... policies`. Add `--format markdown` for a PR/Slack.

3. **Communicate results usefully.**
   - For an **audit**, group by resource so a team sees all of a workload's
     problems at once, and always include the fix — a violation without a
     remediation is noise.
   - For a **what-if**, lead with the blast radius ("N of M workloads would fail")
     and the per-namespace breakdown, then list the affected workloads and why.
     This is a *decision aid* for whether to enforce — frame it that way.

## What the engine encodes (so you can explain it)

- **Audit and what-if share one evaluator** — the preview matches what
  enforcement would actually do.
- **Semver check is careful** — a registry port (`reg:5000/app:v1.0.0`) is not a
  tag, and an immutable digest pin is acceptable; it won't false-positive.
- **Every violation names the exact field and a fix**, because these land in a
  PR or an incident channel where "policy denied" alone is useless.

## Going deeper

- To add or change policies, or map real Gatekeeper ConstraintTemplates, read
  [`references/policies.md`](references/policies.md) — load it only when the user
  wants to modify the catalog.
- To run interactively as MCP tools: `pip install -e ".[mcp]"` then
  `python -m gatekeeper_guard.mcp_server <resources.json>`.

## Don't

- Don't dump raw manifests into your reply or evaluate them by hand — that's the
  token waste this skill exists to avoid.
- Don't report a what-if as if the policy is already enforced — it's a preview of
  a dry-run constraint; say so.
- Don't invent violations or counts — report the engine's output, with fixes.
