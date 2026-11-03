# Estimation Basis

Reference tables for `dev-effort-estimator`. All values are person-days for one competent developer with normal familiarity, and are language-agnostic by design.

## Complexity bands

| Band | Baseline | Features |
|---|---|---|
| S | 0.5–1 | Single module, well-understood pattern, few unknowns, existing tests to follow |
| M | 1–3 | One feature slice, 1–2 modules, some design decisions, new tests needed |
| L | 3–5 | Multiple modules or services, real design choices, migration or contract changes, non-trivial failure modes |
| XL | 5–10 | Cross-system work, significant unknowns, architecture-level decisions, broad blast radius |

XL is a split signal: if a task lands here, either decompose it further or convert the first chunk into a 0.5–1 day spike to retire the unknowns.

## Typical band by change type

| Change type | Typical band | Notes |
|---|---|---|
| UI/text tweak, config change | S | Verify where the value is consumed |
| Simple bug fix (repro known, cause clear) | S–M | Include regression test |
| New field / endpoint following existing pattern | S–M | Copy-pattern work is fast; contract + tests are the cost |
| New business logic with rules/edge cases | M–L | Rules enumeration drives the size, not the code volume |
| Cross-module feature | L | Integration and review rework dominate |
| Separated frontend/backend feature | L | Task rows: contract definition + FE rows + BE rows + joint-debug row. Parallel tracks only when the contract is fixed first; otherwise serialized |
| QA test pass (independent) | M–L | Test-case design + functional testing + regression of affected features. Typical total ≈ 30–50% of development P50; wide compatibility matrix (browsers/devices/legacy data) or regulated domains take the high end. Smoke-only passes land S–M |
| Refactor without behavior change | M–L | Sizing by test coverage of the target area |
| Data migration / backfill | M–L | Dry-run and rollback plan are part of the task |
| Third-party / cross-team integration | L | Waiting time is coordination factor, not this band |
| Performance / security hardening | L–XL | Profiling or audit scope first; size follows findings |
| Greenfield scaffold (new service/app) | XL | Treat as project estimate: coarse range only |

## Adjustment factors

Apply per task with value + reason. Never stack two factors for the same cause. Combined multiplier cap: 3.0.

| Family | Value | When |
|---|---|---|
| Familiarity: stack/codebase/domain | 0.7 / 1.0 / 1.5 / 2.0 | Team has shipped this before / normal / new to team / new to the org |
| Coupling & blast radius | 1.0–1.5 | Cross-module, shared kernels, legacy with weak tests |
| Quality bar | 1.0–1.5 | Strict test requirements, perf/security budgets, compliance |
| Clarity | 1.0–1.5 | Vague requirements, expected requirement churn |
| Coordination | 1.0–1.5 | External teams, shared environments, approval gates |

Familiarity is where the tech stack enters. "Done it many times in React" does not transfer to "first time in Rust" — pick the factor from the team's actual track record with that stack, not from the stack's reputation.

## Hidden-work checklist

Scan before finalizing; each unchecked item is a missing task row:

- [ ] environment/build/CI wiring
- [ ] test data and fixtures; automated tests
- [ ] integration/joint debugging with other systems
- [ ] data migration and old-data compatibility
- [ ] release, rollback plan, canary/gray steps
- [ ] code review rework (≥ 1 round)
- [ ] documentation/handover if required
- [ ] feature flag / config / permission wiring

## P50 / P80

- **P50**: the sum of adjusted medians — "coin-flip date".
- **P80**: P50 × 1.3–1.6 — use 1.3 when requirements are stable and code was inspected, 1.6 under `description only` evidence or heavy unknowns. Quote both; commit against P80.

For multi-week totals, the range widens further: phase-level estimates from coarse input should be quoted as ±50%, not from a false-precision sum.

## Project-lifecycle ratios

Baseline: development core = 100. Phase costs scale from it; ratios are for typical business systems, not fixed law — state deviations.

| Phase | Ratio | Notes |
|---|---|---|
| Requirements & solution design | 15–25 | Interviews, clarification, technical design, prototype UI/UX design effort if applicable |
| Development core | 100 | Task-level estimate from Sections 1–5 |
| Independent QA testing | 25–40 | Test-case design + functional + regression; see QA row above |
| Release & deployment | 5–10 | Environments, data migration, rollout/rollback plan, gray release |
| Stabilization / trial run | 10–20 | Post-launch defect triage and fixes until steady state |
| PM & communication | 10–15 | Meetings, status, cross-team coordination |
| Change buffer | 10–20 | Scales with duration: short project low end, 3+ months high end |

## Duration uncertainty and calendar conversion

- 1–2 weeks of work: quote ±20–30% around P50.
- ~1–2 months: ±40–50%.
- 3+ months: ±60–75%, or use rolling wave — near phase ±20–30%, far phases ±75%, re-estimate at each phase boundary.
- Calendar weeks ≈ total person-days ÷ (staff count × effective person-days per week). Effective capacity is 3–4 days/week/person (meetings, context switching, leave) — never 5.
- Adding people does not shorten the calendar line linearly: communication paths grow roughly n(n−1)/2. Say this in one sentence whenever a conversion is quoted.

## Calibration

Keep a log of `task | band | estimate | actual | cause of drift`. After 5+ pairs per change type, derive a personal correction factor and apply it before factors in step 4. Drift causes worth naming: unknowns retired too cheaply, review rounds > 1, integration discovered late.
