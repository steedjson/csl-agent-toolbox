---
name: csl-frontend-kickoff
description: 前端页面开工编排：先用 AskUserQuestion 采访用户（任务 + 视觉偏好），同一真实页面、同一批数据做两个可运行的设计方案并说明取舍，用户选定后才落实 Ant Design 组件与主题，最后以双端截图 + 交互实测验收。Use when starting a new frontend page/module from zero or redesigning an existing page（新做页面 / 重做界面 / 出两版设计对比 / 先问我再动手）, BEFORE writing any UI code. Not for locked-style small tweaks（既有页面小改直接走常规流程）.
---

# Frontend Kickoff（前端开工五拍）

把"从零做页面/重做界面"组织成五拍：**采访 → 双方案 → 选择 → 落地 → 验收**。本技能是编排器：设计方向找 `frontend-design`，组件与主题找 `antd-component-lookup` / `antd-theme-customization`，浏览器验证找 `browser-use:control-browser`，截图核验找 `csl-vision`。它不替代其中任何一个，只规定顺序与门禁。

适用：新页面、新模块、整体重做。不适用：风格已定的小改动（直接做，别硬走双方案）、纯后端任务。

## 铁律（每条都是实战换来的）

1. **先采访后动手**。采访用 AskUserQuestion，3–5 问一次问完，不挤牙膏式追问。
2. **双方案必须同页面、同数据、同交互**，差异只在设计语言。共享同一份数据模块；原型必须可运行（真数据、真筛选、真空态），纸面描述和静态稿不给选。
3. **原型阶段不落 antd、不落生产主题**。被淘汰的方案不值得工程化；选定后才做组件与 Token 实现。
4. **选择必须带逃生口**：选项含 A / B / 两案融合 / 都不满意重出。豁免条款：小改动或项目风格已定 → 只出一案并说明理由。
5. **验收门禁不过不交付**，交付报告写清"实现了什么 / 实际验证了什么 / 未验证什么"，无法执行的验证明说，不得当作已通过。

## Workflow

### 0. 判定豁免

任务只是既有页面小改（改文案、调间距、换图标）或项目已有定稿设计系统 → 跳过双方案，直接进入第 4 拍落地，并在回复中说明豁免理由。

### 1. 采访（AskUserQuestion）

必问四维，按任务补问：

- **改造对象**：哪个页面/模块做底（信息密度高的页面最能比出设计差异）。
- **差异策略**：两极拉开（理性 vs 个性）还是同气质比布局。
- **底色与字体**：浅/深底、衬线/无衬线/等宽气质，或明确"交给你搭"。
- **验收侧重**（multiSelect）：不像模板 / 信息效率 / 移动端体验 / 细节打磨。

补充维度视任务：目标用户与场景、品牌约束、参考站点、数据形态。用户已答过的偏好不再重复问。

### 2. 双方案

- 先过 `frontend-design` 定两套方向，刻意拉开，不要两案趋同。
- 数据层单源（共享 data 模块）；每案样式用独立前缀，互不污染。
- 每案交付：可运行路由 + 双宽截图 + 取舍说明（取什么、舍什么、最适合什么场景）。
- 原型最低验证：构建 0 错、搜索/筛选/空态可跑、控制台 0 报错。

### 3. 选择（AskUserQuestion）

四选项：A / B / 两案融合（说明取舍要点）/ 都不满意（要求指出哪里不行）。呈现时附现场链接与截图路径，取舍说明放在提问前的正文里。

### 4. Ant Design 落地（选定后）

- 拿不准的组件 API 用 `antd-component-lookup` 查当前文档（大版本差异真实存在：弃用组件、废弃 prop、context 用法，以查到的为准，不凭记忆）。
- 主题用 `antd-theme-customization`：ConfigProvider Token 全局一份；不同页面主色不同时用 per-route ConfigProvider 隔离，不改别页。
- 原型样式文件与正式版单源共用（改名/挪位置，不复制第二份）；同值色出现两处即提为 token。
- 组件优先复用项目已有的；表单提交的 `validateFields` rejection 必须 catch。

### 5. 验收门禁

全部通过才算交付：

1. 预览启动（预览命令在计划里写死）。
2. 1440 与 390 双宽截图；移动端无横向溢出。
3. 主要流程交互实测：筛选、表单校验、成功反馈、错误与重试。
4. `npx impeccable detect <url>`：primary = 0（advisory 记录不阻断）。
5. `csl-vision` 对照截图逐条核验（主模型无视觉，不得自行目检宣布通过）。
6. 控制台 0 报错（unhandledrejection 也算错）。
7. 问题修复后重新截图；最终回复附截图路径与检测结果。

## 实战坑清单

- **样式文件忘 import** → 整页"裸排"。判据是 DOM/computed-style 审计，不要只信截图——截图工具的全页拼接偶发伪影（内容重复、行截半），DOM 实测干净就是工具问题。
- **无空格的 inline 序列**（chip 串）不会自动换行 → 容器改 `display:flex; flex-wrap:wrap`。
- **antd Form 空提交**的 `validateFields` 会 reject，不 catch 就泄漏 unhandledrejection。
- 测试中途用户可能在同一浏览器里操作，关键断言前先 fresh goto，标签绑定失效按 browser-use 协议恢复。
- 低对比度是 impeccable 高频命中：占位符、灰 chip、装饰性大数字（大字也要 3:1）逐类过一遍再送检。

## Tooling

- 采访/选择：AskUserQuestion（ZCode 内置）。
- 浏览器/截图：`browser-use:control-browser`（每次 JS 调用重新 bootstrap）。
- 视觉核验：`csl-vision` 子 Agent（只读图出结论）。
- 设计方向：`frontend-design`；组件/主题：`antd-component-lookup` + `antd-theme-customization`。
- 静态检测：`npx impeccable detect <url>`。
