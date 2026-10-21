# csl-agent-toolbox

个人常用 Agent Skills、MCP 和插件源码库。自研内容直接维护；第三方内容记录来源和固定版本，通过三方合并追踪上游更新。按需选择组件和目标宿主安装。

仓库布局：

- `skills.json`：统一组件目录，含 `skills`、`plugins`、`mcps`；保留文件名以兼容已有工具。`category` 仅用于分类展示，不决定路径。
- `<skill-name>/`：根目录下每个含 `SKILL.md` 的目录是一个独立可分发 Skill。
- `plugins/<plugin-name>/`：宿主原生插件包，按 manifest 判断支持的宿主。
- `mcp/<name>/mcp.json`：独立 MCP 配置包；当前尚未收录独立 MCP。
- `.agents/plugins/marketplace.json`：仓库插件 marketplace 目录。

```bash
python3 scripts/toolbox.py list
python3 scripts/toolbox.py hosts
python3 scripts/toolbox.py install --skill grill-me --skill coding-discipline --host codex --dry-run
python3 scripts/toolbox.py install --skill grill-me --skill coding-discipline --host codex
python3 scripts/toolbox.py install --skill grilling --host zcode --dry-run
python3 scripts/toolbox.py install --skill grilling --host agents  # 明确安装到用户级共享目录
python3 scripts/toolbox.py check                               # 所有已登记第三方组件
python3 scripts/toolbox.py update                              # 预览
python3 scripts/toolbox.py update --apply                       # 应用到仓库
```

`--host` 可重复，`--skill` / `--mcp` / `--plugin` 可重复组合。仓库更新不会新增宿主安装；MCP 和插件通过原生 CLI 或原生配置安装。详细适配矩阵、MCP 格式和更新后的生效方式见 [安装与适配](docs/installation.md)。

ZCode 支持 Skill 软链接、MCP 原生配置和本地插件目录；MCP 写入 `~/.zcode/cli/config.json` 的 `mcp.servers`，插件登记到 `plugins.dirs`。不要求另装 `zcode` CLI。

## Skills 列表

其他已登记入口：[frontend-ui-ux-design](./frontend-ui-ux-design/)、[agent-reach](./agent-reach/)、[grill-with-docs](./grill-with-docs/)、[domain-modeling](./domain-modeling/)、[reverse-engineer-anything](./reverse-engineer-anything/)。完整来源和固定版本以 `python3 scripts/toolbox.py list` 为准。

### 模型与路由（models-and-routing）

#### [codexradar-model-advisor](./codexradar-model-advisor/)

读取 CodexRadar 当前实测数据与 15 天社区评分历史，为 OpenAI Codex 模型和 reasoning effort 提供质量、速度、成本建议。仅推荐当前有实测数据的组合，支持 Codex、Claude Code 和其他 Agent Skills 兼容宿主。

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

#### [django-test-sandbox](./django-test-sandbox/)

给 Django 项目落地实测验证过的内存测试沙盒（SQLite `:memory:` + 禁迁移 + PG 字段建表垫片 + 探针门禁）：纯逻辑测试不连库，ORM 查询语义测试在内存 SQLite 真实执行；含可选的 `manage.py test` 入口接管模板。已在 Django 4.2.16 + pytest-django 4.9 + pytest 8.3 实测（2026-10，phekda 首跑）。

#### [csl-django42-project-init](./csl-django42-project-init/)

按个人 Django 项目基线（提炼自 wework/backend + stdkit v1.2.6 源码快照）一次性初始化新后端项目：确定性渲染熟悉的 `apps/ + common/ + 配置包` 目录结构、View/Service/JWT 认证中间件通用基建、uuid 主键 + 软删除模型基座、内嵌 `stdkit/` 私有基础库（传递依赖固化在 requirements，不入库）、`make check/verify` 质量门禁、docs 与 AGENTS.md 骨架，并按需生成业务 app 骨架。只管新项目初始化；存量项目扫描走 `/csl-init-project`。

### 代码质量（code-quality）

#### [thermo-nuclear-code-quality-review](./thermo-nuclear-code-quality-review/)

对代码变更执行极严格的可维护性审查：抽象边界、超大文件、分支复杂度、重复逻辑和结构性简化机会。适合明确要求深度或严苛代码质量审查的场景；不替代功能正确性、安全性或测试审查。

#### [coding-discipline](./coding-discipline/)

把 Gist 中的工程准则转成 Codex 可调用 Skill：面向非琐碎或高风险实现，先理解真实流程，再做最小精准修改；对重要取舍显式说明；修复根因并按风险验证。含三条行为反测 prompt，不替代框架工作流或专门代码审查。

### 项目检索（project-search）

#### [xerj](./xerj/)

用本机已安装的 XERJ 服务检索当前项目的索引源码与文档：从目标项目工作目录调用 `xerj-project` wrapper（Git 根绝对路径哈希为独立索引前缀，自动携带端点与鉴权，不打印密钥），支持 `search` / `def` / `query` / `map` / `watch` 等。每个项目独立索引与日志；安装与升级仅限本机 macOS Apple Silicon，官方发布包经 SHA-256 与 GitHub digest 双重校验后原子替换（上游 [xerj-org/xerj](https://github.com/xerj-org/xerj) 为 Apache-2.0 开源；wrapper 三件套为本机自产，不在上游仓库）。默认词法检索而非语义理解，未命中不等于不存在；与 LSP / codegraph 互补，不替代符号引用检查。

### 工程规划（engineering-planning）

#### [dev-effort-estimator](./dev-effort-estimator/)

把开发任务、文字需求、原型页或 UI 设计稿拆解成可核查的工时评估：WBS 任务分解（0.5–2 人日粒度）、S/M/L/XL 复杂度定档、显式调整因子（熟悉度/耦合/质量/清晰度/协作）、P50/P80 区间输出，附假设清单、Top 风险与收敛建议。原型/设计稿输入时先经 `browser-ui-reader` 转结构化需求清单再估算。方法与编程语言无关，技术栈只作为熟悉度因子进入估算；支持历史 actual 校准。不替代项目管理工具，估算非承诺。

### 浏览器与 UI（browser-and-ui）

#### [csl-xiaopiu-design-draft-capture](./csl-xiaopiu-design-draft-capture/)

把 xiaopiu（小PIU）原型项目导出为本地完整设计稿截图：每页一张 PNG、整画布无接缝（画布平铺一次成像，禁滚动拼接），并产出映射页面树身份的 `manifest.json`（页面 ID 即原型树节点 key，供交互式审查员跳回原型的导航键）。内置虚拟滚动 SPA 的硬约束剧本（点树切页、内联样式压制、兄弟页副本隐藏、视口上限适配）。产物是设计稿走查与 UI 审查子智能体的标准输入；通用网页截图不在范围内。

#### [browser-ui-reader](./browser-ui-reader/)

看本地浏览器页面内容、操作浏览器页面、把 UI 设计图/原型转成结构化需求清单。主体用 `agent-browser`（CDP、可访问性树 `@eN` refs、会话隔离、附着已登录 Chrome），AppleScript+JS 注入作为零配置后备（不重启、直接附着已打开的 Chrome，只读为主）。覆盖公开页读取、已登录页附着（`--auto-connect`/`--cdp` + `--pin-tab`）、SPA 原型逐页爬取（xiaopiu 52 页已验证）、图片批量下载与宽表分段读取。写操作默认逐项确认，只读默认。

#### [design-taste-frontend](./design-taste-frontend/)

落地页、作品集与改版的反模板化前端设计方向：先读 brief 推断设计意图，再选设计系统与三个设计旋钮，校准排版/配色/布局，最后过一遍反 AI 套路预检清单。上游为 `tasteskill`（npm `natureco-cli` 内的 `skills/taste-skill`），按 `skills.json` 的 `upstream` 固定版本同步。

#### [ego-browser](./ego-browser/)

面向 AI Agent 的 Chromium 浏览器自动化：打开/操作网站、填表、点按钮、截图、提取页面数据、用已登录站点完成 Web 测试与 QA。用法以 `ego-browser skill` 输出的指南为准（随安装版本变化）；`references/install.md` 覆盖安装与升级，`learnings/` 内置 GitHub/Google/X 站点的沉淀工具脚本。上游为 [citrolabs/ego-lite](https://github.com/citrolabs/ego-lite)（MIT），即 `npx skills add citrolabs/ego-lite` 背后的同一目录，按 `skills.json` 的 `upstream` 固定 commit 同步。

### 视觉感知（visual-perception）

#### [perceived-form](./perceived-form/)

按人眼实际怎么「看见」来诊断和校正图形：负空间、视觉重量、邻近语法、默认态 vs 兼容态、黄金家族尺子、马赫带与光学校正。适用于 UI / 图标 / Logo / 字标 / 生图提示词「几何对齐了仍别扭」。不替代落地页口味（`design-taste-frontend`）或读页面（`browser-ui-reader`）。

### Skill 管理（skill-management）

#### [ln-install-skill](./ln-install-skill/)

用符号链接把本仓库（`csl-agent-toolbox`）中的 Skill 安装、列出、校验或卸载到任意宿主 skills 目录：Claude Code（`~/.claude/skills`）、Codex（`~/.codex/skills`）、跨工具（`~/.agents/skills`）、DSH（`~/.dsh/skills`）、pi（`~/.pi/agent/skills`）、omp（`~/.omp/agent/skills`）、zcode（`~/.zcode/skills`）、cow（`~/cow/skills`），或项目内 `<repo>/.claude/skills` / `<repo>/.agents/skills`。目标宿主必须由用户点名，未点名先询问，不自行探测。只操作 symlink，永远不碰源目录和源 `SKILL.md`，安装与卸载均可逆。本仓库是唯一源；`~/.cc-switch/skills` 只是历史副本位置，不再作为源。

#### [dao-skill](./dao-skill/)

Skill 元设计器：先把模糊需求归根，再设计、生成、审计、优化或按证据进化可运行的 Skill；也用于评估既有 Skill 仓库、把方法论/文章/代码库转成可执行 Skill 体系。上游 [gnipbao/dao-skill](https://github.com/gnipbao/dao-skill)（MIT），按 `skills.json` 的 `upstream` 固定 commit 同步。

### 生产力（productivity）

#### [grill-me](./grill-me/) / [grilling](./grilling/)

`grill-me` 是 `/grill-me` 的显式入口（`disable-model-invocation: true`），正文只转调 `grilling`；`grilling` 才是实际工作流：把计划或决策展开成设计树，按轮次追问整个 frontier，每问附带推荐答案，直到双方理解一致。两者上游均为 [mattpocock/skills](https://github.com/mattpocock/skills)（MIT）；`grill-me` 在 `skills.json` 里以 `depends_on: ["grilling"]` 声明依赖，只装前者不会工作。

## Codex 插件

`plugins/` 存放宿主原生插件包，兼容性由插件 manifest 决定。插件登记在 `skills.json` 的 `plugins` 数组；`.agents/plugins/marketplace.json` 是供 Codex 发现和安装插件的 marketplace 目录。当前插件包含 hook，安装后需显式信任并验证激活。

### [openwolf-codegraph-bridge](./plugins/openwolf-codegraph-bridge/)

在用户级统一接入 Codex 生命周期事件。仅当仓库存在 `.wolf/` 或 `.codegraph/` 时启用：转发 OpenWolf 本地 hook，并注入 CodeGraph 优先导航规则。

完整安装 / 使用 / 验证 / 卸载说明见 [`plugins/openwolf-codegraph-bridge/README.md`](./plugins/openwolf-codegraph-bridge/README.md)。

---

## 安装

### 名称迁移

- `openwolf-codegraph@my-skills-local` 已更名为 `openwolf-codegraph-bridge@vlong-skills-local`。
- 仓库改名不会自动删除已安装的旧 Skill、旧插件或旧 marketplace 注册。先安装并验证新名称，再按实际安装状态清理旧条目。

Skill 安装见下方「从本仓库安装到宿主」——用 symlink，不要手工 `cp`，否则宿主里会出现与仓库脱钩的旧副本。

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

## 从本仓库安装到宿主（手动）

**本仓库是唯一源，但不自动安装。** `import` / `update` / `sync` 等仓库操作只写仓库文件，从不触碰宿主目录；把 skill 装进哪个 agent 由你显式决定。宿主目录（`~/.claude/skills`、`~/.codex/skills`、`~/.agents/skills`、`~/.dsh/skills`、`~/.pi/agent/skills`、`~/.omp/agent/skills`、`~/.zcode/skills`、`~/cow/skills`）只是 symlink 挂载点；`~/.cc-switch/skills` 是历史副本位置，不再是源。

**安装位置政策。** 默认装到目标 agent 自己的技能目录（`~/.claude/skills`、`~/.codex/skills`、`~/.omp/agent/skills`、`~/.pi/agent/skills`、`~/.zcode/skills`、`~/cow/skills`、`~/.dsh/skills`）；用户级跨工具目录 `~/.agents/skills` **只在明确说"装到用户级"时使用**，默认不挂载、更不允许自行指向本仓库。omp 需要技能时用 `--host omp` 装进 `~/.omp/agent/skills`（agent 级），不走用户级。`~/.agents/.skill-lock.json` 是 Vercel skills CLI 的锁文件——该 CLI 同样默认写用户级，别再用 `npx skills add`，入仓一律走 `python3 scripts/sync_upstream.py import`。

```bash
# 看每个宿主装了什么、哪些还指向旧位置
python3 scripts/install_skills.py status

# 装某一个 skill 到点名的 agent（推荐形式：skill + host 都写明）
python3 scripts/install_skills.py link --skill grilling --host codex

# 将所有 Skill 安装到明确指定的宿主
python3 scripts/install_skills.py link --host codex

# 把仍指向仓库外的旧链接改指到仓库
python3 scripts/install_skills.py link --host codex --prune

# 卸载（只删链接）
python3 scripts/install_skills.py unlink --skill grilling --host codex

# 列出仓库里的 skill 及其上游来源
python3 scripts/install_skills.py list
```

`status` 会把每个条目分成 `linked`（已指向仓库）、`elsewhere`（指向旧目录，需 `--prune`）、`missing`（未安装）、`real-directory`（是真实目录而非链接，脚本不会动它，需人工确认后删除）。

Skill 安装自动补齐 `depends_on`；目标目录不存在时创建，真实目录不覆盖。symlink 保持安装与源码同步；宿主可能缓存 Skill，当前对话未刷新时新开对话验证。目录存在或命令退出成功不等于运行能力已验证。

---

## 第三方组件更新

第三方组件在 `skills.json` 对应的 `skills`、`plugins`、`mcps` 列表中声明 `upstream`，记录来源、上游路径、固定版本和许可证。自研组件不带 `upstream`，更新器会跳过。不可固定版本的改编材料用 `source_note` 记录来源，不伪装成可同步上游。

### 搬进来（一次性）

`import` 直接把上游内容落盘，同时把 pin 写进 `skills.json`——pin 就是以后三方合并的基线，所以必须搬入时记录。

```bash
# 仓库根就是 Skill（SKILL.md 在顶层）
python3 scripts/sync_upstream.py import \
  --source gnipbao/dao-skill \
  --exclude '.github/' --exclude '.gitignore' --exclude 'assets/' \
  --category skill-management

# monorepo 里的单个 Skill：直接贴浏览器地址即可，路径和 ref 自动解析
python3 scripts/sync_upstream.py import \
  --source 'https://github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md' \
  --category productivity --license MIT

# npm 包里的目录
python3 scripts/sync_upstream.py import --source npm:natureco-cli --path skills/taste-skill

# 第三方插件、MCP 配置包也复用相同的来源与更新逻辑
# 将 owner/repository 和路径替换为真实来源
python3 scripts/toolbox.py import --kind plugin --source owner/repository --path plugins/example --name example
python3 scripts/toolbox.py import --kind mcp --source owner/repository --path mcp/example --name example
```

`--source` 接受 `owner/repo`、GitHub URL、`/tree/<ref>/<path>`、`/blob/<ref>/.../SKILL.md`、`npm:<package>`。`--path` 显式覆盖解析出的子目录；`--name` 覆盖目录名（默认取子目录或仓库 basename）；`--exclude` 可重复，用 glob 剔除 CI 配置、`.gitignore`、大图等不该入库的东西；`--license` 用于上游没有 LICENSE 文件的情况，否则记为 `UNVERIFIED`。

Skill 之间互相依赖时（例如 `grill-me` 正文只有一句 `Call the Skill tool with "grilling"`），给被依赖项也建一条 `upstream`，并在 `skills.json` 里加 `"depends_on": ["grilling"]`；`validate_repo.py` 会校验引用存在。

### 更新

```bash
# 只检查：对比固定版本与上游最新版，列出会发生的变更（不写文件）
python3 scripts/sync_upstream.py check

# 只检查单个 skill
python3 scripts/sync_upstream.py check --skill grok-build-cli

# 预览更新（dry run）
python3 scripts/sync_upstream.py update

# 应用更新：写文件、推进 skills.json 里的 ref/version、刷新 files 列表
python3 scripts/sync_upstream.py update --apply

# 统一入口：所有组件；指定 --kind 与 --component 可缩小范围
python3 scripts/toolbox.py check
python3 scripts/toolbox.py update --kind skill --component grok-build-cli --apply
python3 scripts/toolbox.py update --apply
```

旧 `sync_upstream.py` 命令默认只处理 Skill；统一入口 `toolbox.py check/update` 默认遍历有上游记录的三类组件。`--kind skill|plugin|mcp` 选择一类，`--component` 可重复；旧 `--skill` 过滤参数仍兼容。

更新只写仓库。Skill 和本地链接包读取仓库源码；原生插件管理器缓存的包、已经启动的 MCP 进程需要按宿主方式更新或重启，不能把源码更新等同于运行时已更新。每个成功组件立即保存版本记录，后续来源失败不丢前面的完成状态。

`check` 输出三种状态：`current`（与上游一致，括号里会标出本地改动数）、`pin behind`（内容没变但上游有更新的 commit）、`drift`（上游内容变了，逐文件列出 update/merge/delete/add/conflict）。

同步规则：上游 `ref`/`version` 同时是三方合并的基线。

- 本地未改 → 直接取上游。
- 上游未改 → 保留本地改。
- 两边都改 → `git merge-file` 合并；有冲突则该 skill 整个跳过、不动文件、不推进版本号，解决后重跑。
- 二进制文件（图片等）两边都改 → 直接记冲突，不做文本合并。
- 上游删文件 → 本地也未改则删除；本地改过则记为冲突。
- 上游新增文件 → 直接加入。

支持的 `upstream.type`：`github`（`repo` + `path` + `ref`，取单个 commit）与 `npm`（`package` + `path` + `version`，校验 sha512 后解包）。`path` 为 `.` 表示仓库/包根目录；`exclude` 在两种类型下都生效。

不要手改 pin。跑 `update --apply` 会同时刷新 `files` 和 `synced_at`。

---

## 目录结构

```
csl-agent-toolbox/
├── .agents/
│   └── plugins/
│       └── marketplace.json
├── codexradar-model-advisor/
│   └── SKILL.md
├── custom-image-gen/
│   ├── SKILL.md
│   └── agents/openai.yaml
├── django-development/
│   ├── SKILL.md
│   └── agents/openai.yaml
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
├── scripts/toolbox.py
├── mcp/<name>/mcp.json   # 收录独立 MCP 后创建
├── AGENTS.md
└── README.md
```

---

## License

MIT

---

## 联系

- GitHub: [@steedjson](https://github.com/steedjson)
- Repository: [steedjson/csl-agent-toolbox](https://github.com/steedjson/csl-agent-toolbox)
