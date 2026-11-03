---
name: dev-effort-estimator
description: 把开发任务、文字需求、原型页或 UI 设计稿拆解成可核查的工时评估：任务分解、复杂度定档、调整因子、P50/P80 区间、假设与风险清单。方法与编程语言无关，支持任意技术栈。Use when the user asks to estimate development effort/hours from a text requirement, prototype URL, UI design, or code change, size a requirement, justify a quote or sprint capacity, or review whether an existing estimate is credible.
---

# Dev Effort Estimator

Produce a defensible development-effort estimate: decompose work, size each item with an explicit basis, adjust with stated factors, and report ranges with assumptions — never a bare single number.

Core stance: effort is a function of **change type × complexity × adjustment factors**, not of programming language. The method is language-agnostic; the tech stack only enters as a familiarity factor. Do not maintain per-language hour tables.

This skill produces an estimate, not a commitment. State the evidence level of every estimate (code inspected vs. description only).

## Workflow

### 1. Collect input and classify scope

Determine which estimation object you have:

- **New requirement / feature**: estimate from requirement text or design doc.
- **Prototype URL / UI design**: if the host offers a browser/UI-reading skill (e.g. `browser-ui-reader`), convert the prototype or design into a structured requirement list first, then estimate from it; without such tooling, treat it as `description only` evidence and say so. Estimate the UI work from page/component count and interaction complexity, not from visual polish.
- **Change to existing code**: inspect the actual modules, call paths, and blast radius before sizing.
- **Whole project / lifecycle**: switch to project-lifecycle mode (below): phase-level estimate, wide range, calendar conversion. Do not decompose an entire project into 0.5-day tasks — that is false precision.

If any of these materially change the outcome and are missing, ask before estimating: acceptance criteria, target platforms/environments to support, data migration needs, integration scope, quality bar (tests/perf/security), and who reviews. If the user wants an immediate number, list the missing items as assumptions instead of blocking.

State the evidence level up front: `inspected code`, `partial inspection`, or `description only`.

### 2. Decompose into tasks (WBS)

Split work into tasks of **0.5–2 person-days** granularity. One row per task, each tagged with a change type. Include the work people forget:

- environment setup / build / CI wiring
- test data preparation, fixture and test writing
- integration and joint-debugging with other systems
- data migration and compatibility with old data
- release, rollback plan, gray/canary steps
- code review rework rounds (plan for at least one)
- documentation and handover when required

A task that would exceed 2 person-days after sizing is not decomposed enough — split it.

**Separated frontend/backend work**: keep frontend and backend as separate task rows, each sized with its own stack and familiarity factor. Add explicit rows for the API contract definition and for joint debugging. If the contract is fixed first, the two tracks can run in parallel; without an agreed contract, serialize the estimate (BE then FE integration) and state that in the assumptions — do not quote the parallel schedule by default.

**Testing effort**: developer self-testing and automated test writing stay inside the development rows (hidden-work checklist, quality-bar factor). Independent QA work — test-case design, functional testing, regression across affected features, compatibility passes — becomes its own test rows whenever the user asks for effort including QA or asks about test effort. If the user did not say whether QA is included, ask once; if blocked from asking, report the development total and add the QA estimate as a separate clearly-labeled line. Typical dev-to-test ratios are in `references/estimation-basis.md`.

### 3. Size each task with a complexity band

Assign each task a band **S / M / L / XL** from its complexity features (breadth of touch, unknowns, coupling), not from gut feeling. Band baselines and change-type typical values are in `references/estimation-basis.md`. Record the basis for each band in one phrase ("touches 3 modules, new auth flow").

### 4. Apply adjustment factors

Multiply the band baseline by explicit factors, each with its value and reason. Factor families (full table in the reference):

- **Familiarity**: team's command of the stack / codebase / domain (0.7–2.0). This is where "new language or framework" belongs.
- **Coupling & blast radius**: cross-module, cross-team, legacy code, poor tests.
- **Quality bar**: strict tests, performance/security work, compliance.
- **Clarity**: vague requirements, likely rework.
- **Coordination**: waiting on external teams, environments, approvals.

Full factor table with value ranges: `references/estimation-basis.md`.

Do not stack factors that describe the same cause twice. Cap the combined multiplier per task at 3.0; if it wants to go higher, the task is mis-decomposed or is a spike candidate.

### 5. Summarize and report

Output this fixed contract (adapt column names to the user's language):

```md
## 工时评估：<对象>
证据级别：inspected code | partial inspection | description only
| # | 任务 | 变更类型 | 档位 | 基准(人日) | 因子(值×理由) | 调整后区间 | 依据/假设 |
汇总：P50 = X 人日，P80 = Y 人日（Y ≈ 1.3–1.6 × X，按不确定性取值）
关键假设：…
Top 风险：…（每条附收敛建议，如"先花 0.5 天 spike 验证 X"）
```

Rules:

- Always give a **range** (P50/P80), never a single number.
- Sum ranges, then round up to 0.5 day granularity.
- When frontend/backend or dev/test task rows exist, report **per-track subtotals before the total**: 前端小计 / 后端小计 / 契约与联调, plus 测试小计 when test rows exist — each as a P50–P80 range, then the total across all rows. Single-track estimates report the total only.
- List every assumption; an estimate with unstated assumptions is not defensible.
- If the total comes from `description only` evidence, say the range is coarse and name what inspection would tighten it.

### 6. Calibrate (when history exists)

If the user provides actuals from past tasks ("estimated 3d, took 5d"), compute a personal correction factor per change type and apply it to future estimates. Suggest recording estimated-vs-actual pairs; do not invent history.

## Project-lifecycle mode

Used when the object is a whole project or a multi-month effort. Ratios and duration rules: `references/estimation-basis.md`.

1. **Size the development core first** with the task-level workflow (Sections 1–5), coarse bands allowed (M/L/XL, no S rows).
2. **Build the phase estimate** on top of the development core: requirements & solution design, development, testing (independent QA), release & deployment, stabilization/trial run, plus project-level costs that task-level estimation always forgets — PM & communication, UI/UX design effort, training & handover documentation, and a change-buffer sized by project duration.
3. **Widen uncertainty with duration**: 1–2 weeks ≈ ±20–30%; ~1–2 months ≈ ±40–50%; 3+ months ≈ ±60–75%, or re-slice into phases and estimate the near phase finely and the far phases coarsely (rolling wave).
4. **Convert to calendar duration on request**: 周 ≈ 总人日 ÷ (投入人数 × 每周有效人日 3–4). State the assumed staffing and the effective-capacity discount. One sentence reminder is mandatory: adding people does not shorten a project linearly (communication cost grows).

Output shape: phase table (阶段 | 内容 | 人日区间 | 占比), total person-days as a range, calendar-duration line with assumptions, top risks with convergence suggestions.

## Boundaries

- Not a project-management tool: no Gantt charts, no critical-path analysis, no staffing plans, no committed dates. A coarse calendar-duration conversion with stated assumptions is allowed and expected in lifecycle mode; converting it into a schedule is the user's decision.
- Not a commitment: communicate ranges; conversion to dates is the user's decision.
- Do not pad silently: all buffers appear as named factors or the P80 uplift.
- Do not fake precision: person-days with one decimal at most.
- No per-language hour tables; if asked "how long for X in language Y", answer via change type + familiarity factor, and say the method is stack-agnostic.

## Checklist for delivery gates and traps

Before delivering, verify every gate; a failed gate means the estimate is not done:

- The output contains a range (P50/P80), not a single number.
- Every task row names its band basis and every factor names its value and reason.
- All assumptions are written down; buffers appear as named factors or the P80 uplift, never silent padding.
- The evidence level is stated, and `description only` totals are flagged as coarse.
- The hidden-work checklist from `references/estimation-basis.md` has been scanned; each unchecked item is a missing task row.
- Decomposition holds: no task exceeds 2 person-days after sizing; combined multiplier per task ≤ 3.0.

Common traps that cause gate failures:

- Anchoring on a number the user mentioned.
- Optimism bias on integration, testing, and rework — the three most underestimated items.
- Extrapolating a familiar submodule to the whole project.
- Single-point numbers presenting false precision.
