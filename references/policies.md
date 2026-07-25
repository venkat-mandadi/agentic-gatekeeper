# Policy catalog — reference & how to extend

Load this only to add/modify a policy or map real Gatekeeper ConstraintTemplates.
A normal audit or what-if doesn't need it.

## Contents
- [How a constraint is defined](#how-a-constraint-is-defined)
- [The built-in checks](#the-built-in-checks)
- [Adding a policy](#adding-a-policy)
- [Mapping to real Gatekeeper](#mapping-to-real-gatekeeper)

## How a constraint is defined

A `Constraint` (`src/gatekeeper_guard/models.py`) bundles a check with the
metadata that makes a violation explainable:

- `name` — stable id, matches your ConstraintTemplate
- `kinds` — which resource kinds it targets
- `enforcement` — `deny` (audited as live), `warn`, or `dryrun` (what-if only)
- `description` / `fix` — shown to humans
- `check(resource, params) -> list[str]` — pure; returns one message per
  distinct violation (e.g. per offending container), empty if compliant
- `params` — knobs (e.g. the required label key)

## The built-in checks

`src/gatekeeper_guard/policies.py`:

| Policy | Kinds | Rule |
| --- | --- | --- |
| `image-valid-semver` | workloads | tag must match `^v?\d+\.\d+\.\d+(-…)?(\+…)?$`; `:latest`/no-tag rejected; digest OK |
| `require-probes` | Deployment, StatefulSet, DaemonSet | each container needs `livenessProbe` and `readinessProbe` |
| `backendconfig-has-securitypolicy` | BackendConfig | `spec.securityPolicy.name` must be set |
| `service-has-backendconfig-annotation` | Service | `cloud.google.com/backend-config` annotation required |
| `require-owner-label` (dryrun) | workloads | `metadata.labels.<params.label>` (default `team`) required |
| `require-resource-limits` (dryrun) | workloads | each container needs cpu+memory requests and limits |

Image parsing (`_split_image`) strips `registry[:port]/path` before reading the
tag and treats an `@sha256:` digest as an immutable, acceptable pin — so neither
produces a false positive.

## Adding a policy

1. Write a check — pure, returns messages:

   ```python
   def check_no_privileged(r: Resource, params: dict) -> list[str]:
       out = []
       for c in r.containers:
           if (c.get("securityContext") or {}).get("privileged"):
               out.append(f"container '{c.get('name','?')}' runs privileged")
       return out
   ```

2. Add it to `CATALOG` with target kinds, enforcement, description, and fix.
   Start new policies at `Enforcement.DRYRUN` so they show up in what-if before
   you ever block anything.

3. Add a unit test with a compliant and a violating resource.

## Mapping to real Gatekeeper

Each `Constraint` here mirrors a ConstraintTemplate + Constraint pair. To keep
this catalog honest against a live cluster:

- Export constraints — `kubectl get constraints -o json` — and mirror their
  `spec.enforcementAction` into the `enforcement` field (Gatekeeper's `dryrun`
  maps to a what-if candidate; `deny` to an audited policy).
- Export resources — `kubectl get <kinds> -A -o json` — and run `audit`.
- The result is the same list `gator test` would give you, minus the webhook —
  usable in CI to block a PR that would add a violating manifest, or to preview a
  constraint change before it merges.
