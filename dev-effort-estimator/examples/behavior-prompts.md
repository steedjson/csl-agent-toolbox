# Behavior Prompts

Regression prompts for `dev-effort-estimator`. Replay these after changing SKILL.md; the expected-shape notes define pass/fail for the replay.

## Prompt 1 — estimate from requirement description

> 用 dev-effort-estimator 评估这个需求的开发工时：给现有 Django 后台加一个"导出 Excel 报表"功能，支持按日期范围筛选，异步生成，完成后站内信通知用户。

Pass when the output:

- states evidence level `description only` (no repo was inspected) and flags the total as coarse;
- decomposes beyond the happy path: async task infrastructure, export format/edge cases, notification, permission wiring, tests;
- assigns S/M/L/XL with a one-phrase basis per row and named factors with values;
- reports a P50/P80 range with an assumptions list — no single-point number.

## Prompt 2 — estimate from existing code

> 评估把 `<repo>` 用户模块的密码哈希从 MD5 迁移到 Argon2id 的工时，先看代码再估。

Pass when the output:

- inspects the actual auth path before sizing and states evidence level `inspected code`;
- includes compatibility work as task rows (old-hash verification during transition, force-reset path for unrecoverable hashes);
- includes a data/rollout row (migration script, rollback plan, gray release);
- names the top risk (e.g. legacy accounts that can never re-hash) with a convergence suggestion such as a 0.5-day spike.

## Prompt 3 — estimate from prototype URL / UI design

> 评估这个原型页的开发工时：`<prototype-url>`，先看原型再估。

Pass when the output:

- routes through the host's UI-reading skill (e.g. `browser-ui-reader`) to convert pages into a structured requirement list before sizing, and names that conversion step;
- without such tooling, degrades honestly to `description only` evidence and says so instead of pretending the prototype was seen;
- sizes UI work from page/component count and interaction complexity (forms, lists, states), not from visual polish;
- still produces the fixed contract with P50/P80 and assumptions.

## Prompt 4 — separated frontend/backend with QA

> 评估这个需求的工时，前后端分离，含测试：「商品列表页 + 筛选 + 导出」。前端 React，后端 Java，接口契约还没定。

Pass when the output:

- emits five kinds of task rows: contract definition, BE rows, FE rows, joint-debug row, QA test rows (each track sized with its own familiarity factor);
- reports per-track subtotals before the total: 前端小计 / 后端小计 / 契约与联调 / 测试小计, each a range, then the total across all rows;
- since the contract is undecided, serializes the estimate (BE then FE integration) and states that in the assumptions — no parallel schedule by default;
- sizes QA rows via the dev-to-test ratio (~30–50% of dev P50) and keeps them a separate subtotal, not merged into development.

## Prompt 5 — QA not mentioned

> 这个需求大概要多少工时？后台加一个操作日志查询页。

Pass when the output:

- asks once whether independent QA effort is included;
- if blocked from asking, reports the development total and adds the QA estimate as a clearly-labeled separate line instead of silently merging or silently dropping it.

## Prompt 6 — whole project lifecycle

> 评估整个项目的工时和周期：给某公司做一个供应商管理系统，Web 端，含供应商入驻、资质审核、合同管理、对账单导出，三个人做，大概要做多久？

Pass when the output:

- switches to project-lifecycle mode: phase table (需求与设计 / 开发 / 测试 / 部署上线 / 试运行) with per-phase person-day ranges and ratios, not a flat task list of 0.5-day rows;
- includes project-level cost rows — PM & communication, UI/UX design, change buffer scaled by duration;
- widens the range for a multi-month effort (±40–50% at 1–2 months, ±60–75% beyond) instead of reusing the task-level 1.3–1.6× uplift;
- converts to calendar duration with staffing (3 people) and effective capacity (3–4 person-days/week/person) stated, plus the one-sentence "adding people is not linear" reminder;
- refrains from Gantt/critical-path/committed dates.

## Anti-prompts (must not happen)

- Answering "大概 3 天" with a single number and no decomposition.
- Inventing a per-language hour table ("Python 快一些，所以打 8 折") instead of using the familiarity factor.
- Presenting a commitment date instead of a range.
- In a separated FE/BE estimate, giving only a grand total with no per-track subtotals.
- Claiming to have "seen" a prototype URL without a UI-reading step, or merging QA hours into the development total without a label.
- For a multi-month project, quoting the task-level P80 uplift (1.3–1.6×) or decomposing the whole project into 0.5-day rows as if that were precise.
