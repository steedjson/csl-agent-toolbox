# vlong's Agent Skills & Codex Plugins

个人 Agent Skills 与 Codex 插件源码集合。

仓库布局：

- `skills.json`：Skill 注册表，`category` 仅用于分类展示，不决定路径。
- `<skill-name>/`：根目录下每个含 `SKILL.md` 的目录是一个独立可分发 Skill。
- `plugins/<plugin-name>/`：可安装的 Codex 插件包。
- `.agents/plugins/marketplace.json`：仓库插件 marketplace 目录。

## Skills 列表

### 模型与路由（models-and-routing）

#### [codexradar-model-advisor](./codexradar-model-advisor/)

读取 CodexRadar 当前实测数据与 15 天社区评分历史，为 OpenAI Codex 模型和 reasoning effort 提供质量、速度、成本建议。仅推荐当前有实测数据的组合，支持 Codex、Claude Code 和其他 Agent Skills 兼容宿主。

#### [agent-model-policy-sync](./agent-model-policy-sync/)

把子智能体模型与 reasoning effort 策略幂等写入项目 `AGENTS.md` 或用户指定的 Agent 指令文件；支持 dry-run、标记区块更新和路径安全检查。

#### [model-delegate](./model-delegate/)

使用 Codex 原生子智能体和 App 顶层任务建立自动压缩感知的低上下文成本分工。`CONTEXT_GATE` 按 40%/55%/70%/85% 分层选择双轮、单轮、交接或压缩 checkpoint，并校验有效窗口、自动压缩阈值、样本新鲜度和安全余量。核心不依赖特定供应商或计费数据库。

固定静态门禁：`python3 model-delegate/scripts/validate_contract.py`。它不调用模型或创建任务；真实委派 E2E 只在用户明确确认后运行。运行环境没有 usage 数据时正常完成，并把费用节省标记为未验证。

#### [ccs-restore-efforts](./ccs-restore-efforts/)

当 CC Switch 同步模型目录或重写 `config.toml` 后，模型依赖的 `Effort` 和 `Speed` 元数据可能回归。运行 `scripts/restore_efforts.py restore-ui` 会按 Codex Auto Review、DeepSeek V4、Grok 4.5/4.6 与 GPT-5.6/5.5/5.4/5.4-mini/5.2 官方档位、上下文和输出上限收敛，并给其他模型补回通用推理档位、`Fast / priority` 速度档位及丢失的 `model` 行。

#### [grok-build-cli](./grok-build-cli/)

让 Codex 调用本机 `grok` CLI：检查可用模型与凭据、选择单轮或 agentic 调用、轮询长任务并返回结果。只覆盖调用机制，不规定任务内容。凭据可以是 `~/.grok/config.toml` 模型 key、已缓存的 `auth.json`，或环境变量 `XAI_API_KEY`；不必先 `grok login`。源： [Pluviobyte/rnskill](https://github.com/Pluviobyte/rnskill/tree/main/skills/grok-build-cli)，可用性检查已按官方认证方式放宽。

### 媒体生成（media-generation）

#### [custom-image-gen](./custom-image-gen/)

通过 `image_auth.json` 和当前 Codex provider 配置解析自定义图片生成端点与凭据（Key 缺失时回退 `auth.json` 的 `OPENAI_API_KEY`），再复用系统 `imagegen` Skill 和 CLI。仅负责 provider 适配，不复制系统图片生成工作流。

#### [gemini-banana-image](./gemini-banana-image/)

使用 Google Gemini 图像模型（默认 `gemini-3.1-flash-image`，亦支持 `gemini-3-pro-image-preview` / Nano Banana Pro）文生图与图生图。支持多层级配置解析：优先读取自定义中转端点（`base_url` 与 `api_key`），无配置或指定 `--official` 时自动回退 Google 官方端点；支持 1K/2K/4K 分辨率、多种画幅比例以及 Thinking 链流式结果提取。默认存储于系统临时目录避免污染代码库。

#### [grok-image](./grok-image/)

使用 xAI Grok 图像模型（默认 `grok-imagine-image`，亦支持 `grok-2-image`）文生图。支持多层级配置解析：优先读取自定义中转端点（`base_url` 与 `api_key`），自动兼容本地既有 `~/.grok/config.toml` 配置与 `~/.config/grok-image/config.json`，无配置或指定 `--official` 时自动回退 xAI 官方端点；支持 Base64 / URL 双重响应解码。默认存储于系统临时目录避免污染代码库。

#### [candid-character-image-prompts](./candid-character-image-prompts/)

生成成年虚构角色的偷拍感 COS / 角色摄影图片提示词：公共日常场景、隐蔽机位、长焦或手机抓拍、不完美构图，支持 `n=10` 十种独立构图。

### 框架工作流（framework-workflows）

#### [yapi-copilot](./yapi-copilot/)

基于 YApi 官方原生 REST API 自动化维护接口文档（分类、接口契约、JSON-Schema 增量合入），替代脆弱易错的浏览器网页点选。内置 macOS Chrome 本地已登录 Cookie 自动解密，支持零配置免手动抓包鉴权。

#### [django-development](./django-development/)

在任意 Django 后端项目中发现并遵循现有约定，完成实现、调试、审查或审计。覆盖原生 Django、Django REST Framework、Django Ninja，以及 API、Service/用例、模型、迁移、Admin、Form、后台任务、信号、管理命令、设置和测试。

#### [django-personal-development](./django-personal-development/)

按个人工程规范处理 Django 新项目、旧项目修改和渐进式规范迁移；以 `sugon-webwork-backend` 作为个人习惯参考项目。

#### [django-test-sandbox](./django-test-sandbox/)

给 Django 项目落地实测验证过的内存测试沙盒（SQLite `:memory:` + 禁迁移 + PG 字段建表垫片 + 探针门禁）：纯逻辑测试不连库，ORM 查询语义测试在内存 SQLite 真实执行；含可选的 `manage.py test` 入口接管模板。已在 Django 4.2.16 + pytest-django 4.9 + pytest 8.3 实测（2026-10，phekda 首跑）。

#### [csl-django42-project-init](./csl-django42-project-init/)

按个人 Django 项目基线（提炼自 wework/backend + stdkit v1.2.6 源码快照）一次性初始化新后端项目：确定性渲染熟悉的 `apps/ + common/ + 配置包` 目录结构、View/Service/JWT 认证中间件通用基建、uuid 主键 + 软删除模型基座、内嵌 `stdkit/` 私有基础库（传递依赖固化在 requirements，不入库）、`make check/verify` 质量门禁、docs 与 AGENTS.md 骨架，并按需生成业务 app 骨架。只管新项目初始化；存量项目扫描走 `/csl-init-project`，日常开发规范走 `django-personal-development`。

### 代码质量（code-quality）

#### [thermo-nuclear-code-quality-review](./thermo-nuclear-code-quality-review/)

对代码变更执行极严格的可维护性审查：抽象边界、超大文件、分支复杂度、重复逻辑和结构性简化机会。适合明确要求深度或严苛代码质量审查的场景；不替代功能正确性、安全性或测试审查。

#### [coding-discipline](./coding-discipline/)

把 Gist 中的工程准则转成 Codex 可调用 Skill：面向非琐碎或高风险实现，先理解真实流程，再做最小精准修改；对重要取舍显式说明；修复根因并按风险验证。含三条行为反测 prompt，不替代框架工作流或专门代码审查。

### 工程规划（engineering-planning）

#### [dev-effort-estimator](./dev-effort-estimator/)

把开发任务、文字需求、原型页或 UI 设计稿拆解成可核查的工时评估：WBS 任务分解（0.5–2 人日粒度）、S/M/L/XL 复杂度定档、显式调整因子（熟悉度/耦合/质量/清晰度/协作）、P50/P80 区间输出，附假设清单、Top 风险与收敛建议。原型/设计稿输入时先经 `browser-ui-reader` 转结构化需求清单再估算。方法与编程语言无关，技术栈只作为熟悉度因子进入估算；支持历史 actual 校准。不替代项目管理工具，估算非承诺。

### 浏览器与 UI（browser-and-ui）

#### [csl-xiaopiu-design-draft-capture](./csl-xiaopiu-design-draft-capture/)

把 xiaopiu（小PIU）原型项目导出为本地完整设计稿截图：每页一张 PNG、整画布无接缝（画布平铺一次成像，禁滚动拼接），并产出映射页面树身份的 `manifest.json`（页面 ID 即原型树节点 key，供交互式审查员跳回原型的导航键）。内置虚拟滚动 SPA 的硬约束剧本（点树切页、内联样式压制、兄弟页副本隐藏、视口上限适配）。产物是设计稿走查与 UI 审查子智能体的标准输入；通用网页截图不在范围内。

#### [browser-ui-reader](./browser-ui-reader/)

看本地浏览器页面内容、操作浏览器页面、把 UI 设计图/原型转成结构化需求清单。主体用 `agent-browser`（CDP、可访问性树 `@eN` refs、会话隔离、附着已登录 Chrome），AppleScript+JS 注入作为零配置后备（不重启、直接附着已打开的 Chrome，只读为主）。覆盖公开页读取、已登录页附着（`--auto-connect`/`--cdp` + `--pin-tab`）、SPA 原型逐页爬取（xiaopiu 52 页已验证）、图片批量下载与宽表分段读取。写操作默认逐项确认，只读默认。

### 视觉感知（visual-perception）

#### [perceived-form](./perceived-form/)

按人眼实际怎么「看见」来诊断和校正图形：负空间、视觉重量、邻近语法、默认态 vs 兼容态、黄金家族尺子、马赫带与光学校正。适用于 UI / 图标 / Logo / 字标 / 生图提示词「几何对齐了仍别扭」。不替代落地页口味（`design-taste-frontend`）或读页面（`browser-ui-reader`）。

### Skill 管理（skill-management）

#### [ln-install-skill](./ln-install-skill/)

用符号链接把本地 skills 目录（默认 `~/.cc-switch/skills`）中的 Skill 安装、列出、校验或卸载到任意宿主 skills 目录：DSH（`~/.dsh/skills`）、Claude Code（`~/.claude/skills`）、pi（`~/.pi/agent/skills`）、跨工具（`~/.agents/skills`），或项目内 `<repo>/.claude/skills` / `<repo>/.agents/skills`。目标目录按「用户指定 → 项目级 → 探测首个存在」解析，支持一次装到所有宿主。只操作 symlink，永远不碰源目录和源 `SKILL.md`，安装与卸载均可逆。

## Codex 插件

`plugins/` 存放需要构建、测试、安装和显式信任 hook 的 Codex 插件运行时。插件不是独立 Agent Skill，不登记到 `skills.json`。仓库插件目录为 `.agents/plugins/marketplace.json`。

### [openwolf-codegraph-bridge](./plugins/openwolf-codegraph-bridge/)

在用户级统一接入 Codex 生命周期事件。仅当仓库存在 `.wolf/` 或 `.codegraph/` 时启用：转发 OpenWolf 本地 hook，并注入 CodeGraph 优先导航规则。

完整安装 / 使用 / 验证 / 卸载说明见 [`plugins/openwolf-codegraph-bridge/README.md`](./plugins/openwolf-codegraph-bridge/README.md)。

---

## 安装

### 名称迁移

- `openwolf-codegraph@my-skills-local` 已更名为 `openwolf-codegraph-bridge@vlong-skills-local`。
- 仓库改名不会自动删除已安装的旧 Skill、旧插件或旧 marketplace 注册。先安装并验证新名称，再按实际安装状态清理旧条目。

复制 skill 目录下的 `SKILL.md` 到 Claude Code skills 路径：

```bash
mkdir -p ~/.claude/skills/codexradar-model-advisor
cp codexradar-model-advisor/SKILL.md ~/.claude/skills/codexradar-model-advisor/SKILL.md

mkdir -p ~/.claude/skills/model-delegate
cp -R model-delegate/. ~/.claude/skills/model-delegate/

mkdir -p ~/.claude/skills/custom-image-gen
cp -R custom-image-gen/. ~/.claude/skills/custom-image-gen/

mkdir -p ~/.claude/skills/ln-install-skill
cp ln-install-skill/SKILL.md ~/.claude/skills/ln-install-skill/SKILL.md

mkdir -p ~/.claude/skills/grok-build-cli
cp -R grok-build-cli/. ~/.claude/skills/grok-build-cli/
```

`openwolf-codegraph-bridge` 无构建步骤：

```bash
cd plugins/openwolf-codegraph-bridge
node --check hooks/openwolf.mjs
python3 <plugin-creator-root>/scripts/validate_plugin.py .
```

首次本地安装：

```bash
# marketplace 源指向本仓库根目录（.agents/plugins/marketplace.json）
codex plugin marketplace add <repo-root>

codex plugin add openwolf-codegraph-bridge@vlong-skills-local
```

安装或更新后：

1. 重新信任 hook
2. 开新 Codex 任务验证（旧任务不热加载）
3. 目标仓库准备 `.codegraph/` 和/或 `.wolf/`

快速验收：

```bash
codex plugin list | rg openwolf-codegraph-bridge
codegraph status
```

详细安装、仓库准备、日常使用、卸载与故障排查见 [`plugins/openwolf-codegraph-bridge/README.md`](./plugins/openwolf-codegraph-bridge/README.md)。

---

## 目录结构

```
my-skills/
├── .agents/
│   └── plugins/
│       └── marketplace.json
├── codexradar-model-advisor/
│   └── SKILL.md
├── model-delegate/
│   ├── SKILL.md
│   ├── references/
│   │   ├── compact-coordinator.md
│   │   ├── context-gate.md
│   │   ├── delegation-capsule.md
│   │   ├── log-analysis.md
│   │   ├── passive-return.md
│   │   ├── passive-session.md
│   │   └── staged-review.md
│   └── scripts/validate_contract.py
├── custom-image-gen/
│   ├── SKILL.md
│   └── agents/openai.yaml
├── django-development/
│   ├── SKILL.md
│   └── agents/openai.yaml
├── ccs-restore-efforts/
│   ├── SKILL.md
│   ├── scripts/
│   └── tests/
├── browser-ui-reader/
│   ├── SKILL.md
│   ├── scripts/
│   └── references/
├── csl-xiaopiu-design-draft-capture/
│   └── SKILL.md
├── ln-install-skill/
│   └── SKILL.md
├── grok-build-cli/
│   ├── SKILL.md
│   └── agents/openai.yaml
├── plugins/
│   └── openwolf-codegraph-bridge/
│       ├── .codex-plugin/plugin.json
│       └── hooks/
├── skills.json
├── AGENTS.md
└── README.md
```

---

## License

MIT

---

## 联系

- GitHub: [@steedjson](https://github.com/steedjson)
- Repository: [steedjson/my-skills](https://github.com/steedjson/my-skills)
