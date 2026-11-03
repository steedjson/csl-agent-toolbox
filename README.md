# csl-agent-toolbox

个人常用 Agent Skills、MCP 和插件源码库。自研内容直接维护；第三方内容记录来源和固定版本，通过三方合并追踪上游更新。按需选择组件和目标宿主安装。

仓库布局：

- `skills.json`：统一组件目录，含 `skills`、`plugins`、`mcps`；保留文件名以兼容已有工具。`category` 仅用于分类展示，不决定路径。
- `skills/<skill-name>/`：所有独立可分发 Skill 集中在 `skills/`，各自包含 `SKILL.md`。
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

其他已登记入口：[frontend-ui-ux-design](./skills/frontend-ui-ux-design/)、[agent-reach](./skills/agent-reach/)、[grill-with-docs](./skills/grill-with-docs/)、[domain-modeling](./skills/domain-modeling/)、[reverse-engineer-anything](./skills/reverse-engineer-anything/)。完整来源和固定版本以 `python3 scripts/toolbox.py list` 为准。

### 模型与路由（models-and-routing）

#### [codexradar-model-advisor](./skills/codexradar-model-advisor/)

读取 CodexRadar 当前实测数据与 15 天社区评分历史，为 OpenAI Codex 模型和 reasoning effort 提供质量、速度、成本建议。仅推荐当前有实测数据的组合，支持 Codex、Claude Code 和其他 Agent Skills 兼容宿主。

#### [grok-build-cli](./skills/grok-build-cli/)

让 Codex 调用本机 `grok` CLI：检查可用模型与凭据、选择单轮或 agentic 调用、轮询长任务并返回结果。只覆盖调用机制，不规定任务内容。凭据可以是 `~/.grok/config.toml` 模型 key、已缓存的 `auth.json`，或环境变量 `XAI_API_KEY`；不必先 `grok login`。源： [Pluviobyte/rnskill](https://github.com/Pluviobyte/rnskill/tree/main/skills/grok-build-cli)，可用性检查已按官方认证方式放宽。

### 媒体生成（media-generation）

#### [custom-image-gen](./skills/custom-image-gen/)

通过 `image_auth.json` 和当前 Codex provider 配置解析自定义图片生成端点与凭据（Key 缺失时回退 `auth.json` 的 `OPENAI_API_KEY`），再复用系统 `imagegen` Skill 和 CLI。仅负责 provider 适配，不复制系统图片生成工作流。

#### [gemini-banana-image](./skills/gemini-banana-image/)

使用 Google Gemini 图像模型（默认 `gemini-3.1-flash-image`，亦支持 `gemini-3-pro-image-preview` / Nano Banana Pro）文生图与图生图。支持多层级配置解析：优先读取自定义中转端点（`base_url` 与 `api_key`），无配置或指定 `--official` 时自动回退 Google 官方端点；支持 1K/2K/4K 分辨率、多种画幅比例以及 Thinking 链流式结果提取。默认存储于系统临时目录避免污染代码库。

#### [grok-image](./skills/grok-image/)

使用 xAI Grok 图像模型（默认 `grok-imagine-image`，亦支持 `grok-2-image`）文生图。支持多层级配置解析：优先读取自定义中转端点（`base_url` 与 `api_key`），自动兼容本地既有 `~/.grok/config.toml` 配置与 `~/.config/grok-image/config.json`，无配置或指定 `--official` 时自动回退 xAI 官方端点；支持 Base64 / URL 双重响应解码。默认存储于系统临时目录避免污染代码库。

#### [candid-character-image-prompts](./skills/candid-character-image-prompts/)

生成成年虚构角色的偷拍感 COS / 角色摄影图片提示词：公共日常场景、隐蔽机位、长焦或手机抓拍、不完美构图，支持 `n=10` 十种独立构图。

### 框架工作流（framework-workflows）

#### [yapi-copilot](./skills/yapi-copilot/)

基于 YApi 官方原生 REST API 自动化维护接口文档（分类、接口契约、JSON-Schema 增量合入），替代脆弱易错的浏览器网页点选。内置 macOS Chrome 本地已登录 Cookie 自动解密，支持零配置免手动抓包鉴权。

#### [django-development](./skills/django-development/)

在任意 Django 后端项目中发现并遵循现有约定，完成实现、调试、审查或审计。覆盖原生 Django、Django REST Framework、Django Ninja，以及 API、Service/用例、模型、迁移、Admin、Form、后台任务、信号、管理命令、设置和测试。

#### [django-test-sandbox](./skills/django-test-sandbox/)

给 Django 项目落地实测验证过的内存测试沙盒（SQLite `:memory:` + 禁迁移 + PG 字段建表垫片 + 探针门禁）：纯逻辑测试不连库，ORM 查询语义测试在内存 SQLite 真实执行；含可选的 `manage.py test` 入口接管模板。已在 Django 4.2.16 + pytest-django 4.9 + pytest 8.3 实测（2026-10，phekda 首跑）。

#### [csl-django42-project-init](./skills/csl-django42-project-init/)

按个人 Django 项目基线（提炼自 wework/backend + stdkit v1.2.6 源码快照）一次性初始化新后端项目：确定性渲染熟悉的 `apps/ + common/ + 配置包` 目录结构、View/Service/JWT 认证中间件通用基建、uuid 主键 + 软删除模型基座、内嵌 `stdkit/` 私有基础库（传递依赖固化在 requirements，不入库）、`make check/verify` 质量门禁、docs 与 AGENTS.md 骨架，并按需生成业务 app 骨架。只管新项目初始化；存量项目扫描走 `/csl-init-project`。

#### [csl-jenkins-deploy-scaffold](./skills/csl-jenkins-deploy-scaffold/)

项目自适应部署：先发现构建、运行、发布与持久化约束，再选择单镜像、分镜像或多服务结构，按需生成 Jenkins、Docker、Compose、Kubernetes 文件。核心流程只需 `SKILL.md`，不依赖私人样板仓库、固定目录、域名或预设技术栈；缺少会影响方案的信息时给出推荐并提问，保留现有流水线入口，明确静态检查、构建、运行及集群验证的边界。附分镜像示例、故障诊断与 12 个合成验收案例。

首次使用：`分析当前项目，推荐改动最小的 Jenkins 和容器部署方案；能从代码确认的先查，关键缺项再问，确认事实后生成必要文件。`

### 代码质量（code-quality）

#### [thermo-nuclear-code-quality-review](./skills/thermo-nuclear-code-quality-review/)

对代码变更执行极严格的可维护性审查：抽象边界、超大文件、分支复杂度、重复逻辑和结构性简化机会。适合明确要求深度或严苛代码质量审查的场景；不替代功能正确性、安全性或测试审查。

#### [coding-discipline](./skills/coding-discipline/)

把 Gist 中的工程准则转成 Codex 可调用 Skill：面向非琐碎或高风险实现，先理解真实流程，再做最小精准修改；对重要取舍显式说明；修复根因并按风险验证。含三条行为反测 prompt，不替代框架工作流或专门代码审查。

### 项目检索（project-search）

#### [xerj](./skills/xerj/)

用本机已安装的 XERJ 服务检索当前项目的索引源码与文档：从目标项目工作目录调用 `xerj-project` wrapper（Git 根绝对路径哈希为独立索引前缀，自动携带端点与鉴权，不打印密钥），支持 `search` / `def` / `query` / `map` / `watch` 等。每个项目独立索引与日志；安装与升级仅限本机 macOS Apple Silicon，官方发布包经 SHA-256 与 GitHub digest 双重校验后原子替换（上游 [xerj-org/xerj](https://github.com/xerj-org/xerj) 为 Apache-2.0 开源；wrapper 三件套为本机自产，不在上游仓库）。默认词法检索而非语义理解，未命中不等于不存在；与 LSP / codegraph 互补，不替代符号引用检查。

### 工程规划（engineering-planning）

#### [dev-effort-estimator](./skills/dev-effort-estimator/)

把开发任务、文字需求、原型页或 UI 设计稿拆解成可核查的工时评估：WBS 任务分解（0.5–2 人日粒度）、S/M/L/XL 复杂度定档、显式调整因子（熟悉度/耦合/质量/清晰度/协作）、P50/P80 区间输出，附假设清单、Top 风险与收敛建议。原型/设计稿输入时先经 `browser-ui-reader` 转结构化需求清单再估算。方法与编程语言无关，技术栈只作为熟悉度因子进入估算；支持历史 actual 校准。不替代项目管理工具，估算非承诺。

### 浏览器与 UI（browser-and-ui）

#### [csl-frontend-kickoff](./skills/csl-frontend-kickoff/)

前端页面开工编排（采访 → 双方案 → 选择 → 落地 → 验收五拍）：先用 AskUserQuestion 采访任务与视觉偏好，同一真实页面、同一批数据做两个可运行设计方案并说明取舍，用户选定后才落实 Ant Design 组件与主题，最后按双端截图 + 交互实测 + impeccable + csl-vision 门禁验收。是 `frontend-design` / `antd-component-lookup` / `antd-theme-customization` / `browser-use` 的编排入口而非替代。适用于从零新做页面或整体重做；风格已定的小改动可豁免双方案。

#### [csl-xiaopiu-design-draft-capture](./skills/csl-xiaopiu-design-draft-capture/)

把 xiaopiu（小PIU）原型项目导出为本地完整设计稿截图：每页一张 PNG、整画布无接缝（画布平铺一次成像，禁滚动拼接），并产出映射页面树身份的 `manifest.json`（页面 ID 即原型树节点 key，供交互式审查员跳回原型的导航键）。内置虚拟滚动 SPA 的硬约束剧本（点树切页、内联样式压制、兄弟页副本隐藏、视口上限适配）。产物是设计稿走查与 UI 审查子智能体的标准输入；通用网页截图不在范围内。

#### [browser-ui-reader](./skills/browser-ui-reader/)

看本地浏览器页面内容、操作浏览器页面、把 UI 设计图/原型转成结构化需求清单。主体用 `agent-browser`（CDP、可访问性树 `@eN` refs、会话隔离、附着已登录 Chrome），AppleScript+JS 注入作为零配置后备（不重启、直接附着已打开的 Chrome，只读为主）。覆盖公开页读取、已登录页附着（`--auto-connect`/`--cdp` + `--pin-tab`）、SPA 原型逐页爬取（xiaopiu 52 页已验证）、图片批量下载与宽表分段读取。写操作默认逐项确认，只读默认。

#### [design-taste-frontend](./skills/design-taste-frontend/)

落地页、作品集与改版的反模板化前端设计方向：先读 brief 推断设计意图，再选设计系统与三个设计旋钮，校准排版/配色/布局，最后过一遍反 AI 套路预检清单。上游为 `tasteskill`（npm `natureco-cli` 内的 `skills/taste-skill`），按 `skills.json` 的 `upstream` 固定版本同步。

#### [html-design-draft](./skills/html-design-draft/)

自包含 HTML 设计稿：海报、界面 mockup、落地页视觉稿、信息图与示意图，每块画板一个双击即看的独立 HTML（零构建、零依赖、除 Google Fonts 外无外链），`index.html` 汇总导航，`assets/` 放图片字体；附确定性校验脚本（自包含性 / 本地资源存在性 / 结构必备项）。方法论改编自 [JimLiu/baocut](https://github.com/JimLiu/baocut) 内置 design 技能（commit 7aa049e8，BaoCut Community License——只参考思想、全文重写，未搬运任何文件），改编记录见 `skills.json` 的 `source_note`。整体方向未定先走 `frontend-design` / `design-taste-frontend`，长期设计系统走 `ui-design-system`，开发真实前端项目不用本技能。

#### [frontend-design](./skills/frontend-design/)

Anthropic 的前端视觉设计 Skill：从具体主题确定设计方向，规划颜色、字体与布局，再实现并自查，覆盖响应式、可访问性、动效和界面文案。原入口为 [claude-code 的 frontend-design 插件](https://github.com/anthropics/claude-code/tree/main/plugins/frontend-design)；导入时确认技能正文与官方 [anthropics/skills](https://github.com/anthropics/skills/tree/main/skills/frontend-design) 版本逐字节一致，使用后者完整携带的 `LICENSE.txt`（Apache-2.0），按 `skills.json` 的 `upstream` 固定 commit 同步。

#### [impeccable](./skills/impeccable/)

编码 agent 的设计词汇表与 AI slop 检测：24 个子命令分四组——Steer（`bolder`/`quieter`/`distill` 等调整方向）、Review（`critique` 打分 UX 评审 / `audit` P0-P3 技术审计）、Finish（`polish`/`harden`/`optimize` 等收尾）、Iterate（`live` 浏览器内选元素换变体回写源码）。自带 62 条确定性检测规则的引擎启动器（首次运行下载二进制到 `~/.impeccable/bin/`，无需 Node）。上游为 [pbakaus/impeccable](https://github.com/pbakaus/impeccable) 的 `.claude/skills/impeccable` 构建（Apache-2.0），按 `skills.json` 的 `upstream` 固定 commit 同步。随包保留固定版本根目录的 `LICENSE`、`NOTICE.md`，并附带 modern-screenshot 的 MIT 许可。本仓库只 vendor 技能本体；各工具的 design hook 与浏览器扩展不随行，需要时用 `npx impeccable install`。与 `frontend-design` 同源且为其超集演化版：定方向先走 `frontend-design`，迭代与评审走本技能。

#### [creative-direction](./skills/creative-direction/)

把模糊的创意意图整理成可供设计、文案与艺术指导复用的美学简报：确定语气、美学取向、受众关系和感官体验，记录参考、排除项与待决问题。上游为 [rampstackco/claude-skills](https://github.com/rampstackco/claude-skills/tree/main/dist/codex/.agents/skills/creative-direction)（MIT），使用其 Codex 兼容发行目录，保留三个参考文件与原始目录元数据，按 `skills.json` 的 `upstream` 固定 commit 同步；随技能保留仓库根目录的 `LICENSE`。

#### [ui-design-system](./skills/ui-design-system/)

设计系统工具包：生成颜色、字体、间距等 Design Tokens，规划组件体系、响应式布局和开发交付。选用 [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills/tree/main/product-team/skills/ui-design-system) 版本（MIT），按 `skills.json` 的 `upstream` 固定 commit 同步；随技能保留仓库根目录的 `LICENSE`。本地修正文档中的 CLI 参数写法，并补齐 SCSS 导出。

#### [css-animation-creator](./skills/css-animation-creator/)

网页动效工具包：CSS transitions、关键帧、微交互、加载状态、页面过渡与滚动动画，包含 Tailwind、Framer Motion、性能和减少动态效果偏好的参考。上游为 [OneWave-AI/claude-skills](https://github.com/OneWave-AI/claude-skills/tree/main/css-animation-creator)（MIT），按 `skills.json` 的 `upstream` 固定 commit 同步；随技能保留仓库根目录的 `LICENSE`。

#### [antd-component-lookup](./skills/antd-component-lookup/)

查询 Ant Design React 组件的 API、默认值、类型和用法示例，通过官网组件页面与 `llms.txt` / `llms-full.txt` 获取文档。上游为 [ant-design/ant-design](https://github.com/ant-design/ant-design) 的 `public/.well-known/agent-skills/antd-component-lookup`（MIT），按 `skills.json` 的 `upstream` 固定 commit 同步；随技能保留该版本仓库根目录的 `LICENSE`。

#### [antd-theme-customization](./skills/antd-theme-customization/)

使用 Design Tokens 和 `ConfigProvider` 定制 Ant Design 主题，覆盖全局与组件级样式、暗色模式、CSS 变量和 Token 提取。上游为 [ant-design/ant-design](https://github.com/ant-design/ant-design) 的 `public/.well-known/agent-skills/antd-theme-customization`（MIT），按 `skills.json` 的 `upstream` 固定 commit 同步；随技能保留该版本仓库根目录的 `LICENSE`。

#### [shadcn](./skills/shadcn/)

React shadcn/ui 官方 Skill：查询与安装组件、组合表单与聊天界面、定制主题、使用组件 registry 和 preset，并检查设计系统展示页的组件覆盖。上游为 [shadcn-ui/ui](https://github.com/shadcn-ui/ui/tree/main/skills/shadcn)（MIT），按 `skills.json` 的 `upstream` 固定 commit 同步；随技能保留仓库根目录的 `LICENSE.md`。

#### [shadcn-vue](./skills/shadcn-vue/)

Vue 3 shadcn-vue 官方 Skill：组件查询、安装与组合，表单、主题、registry 和 preset 用法；Vue 项目使用此技能。上游为 [unovue/shadcn-vue](https://github.com/unovue/shadcn-vue/tree/dev/skills/shadcn-vue)（MIT），按 `skills.json` 的 `upstream` 固定 commit 同步；随技能保留仓库根目录的 `LICENSE`。

两个 shadcn 技能均做最小可移植适配：描述明确 React / Vue 3 适用范围；将 Claude 专用的动态命令插值改成显式执行项目上下文查询；原 `user-invocable: false` 以 `metadata.upstream-user-invocable` 字符串保留来源记录，宿主是否提供手动入口由宿主决定。

#### [mantine-form](./skills/mantine-form/)

Mantine 官方 React 表单 Skill：`useForm`、非受控表单、校验、嵌套字段、数组字段和跨组件表单状态。面向 Mantine 9.x；上游为 [mantinedev/skills](https://github.com/mantinedev/skills/tree/master/skills/mantine-form)（MIT），按 `skills.json` 的 `upstream` 固定 commit 同步；随技能保留仓库根目录的 `LICENSE`。

#### [mantine-combobox](./skills/mantine-combobox/)

Mantine 官方 React 下拉选择 Skill：先选用现成组件，再按需组合 `Combobox`，覆盖搜索、多选、自定义选项与键盘交互。面向 Mantine 9.x；上游为 [mantinedev/skills](https://github.com/mantinedev/skills/tree/master/skills/mantine-combobox)（MIT），按 `skills.json` 的 `upstream` 固定 commit 同步；随技能保留仓库根目录的 `LICENSE`。

#### [mantine-custom-components](./skills/mantine-custom-components/)

Mantine 官方 React 自定义组件 Skill：使用 factory、Styles API、CSS 变量、复合组件和 `MantineProvider` 接入主题。面向 Mantine 9.x；上游为 [mantinedev/skills](https://github.com/mantinedev/skills/tree/master/skills/mantine-custom-components)（MIT），按 `skills.json` 的 `upstream` 固定 commit 同步；随技能保留仓库根目录的 `LICENSE`。

#### [ego-browser](./skills/ego-browser/)

面向 AI Agent 的 Chromium 浏览器自动化：打开/操作网站、填表、点按钮、截图、提取页面数据、用已登录站点完成 Web 测试与 QA。用法以 `ego-browser skill` 输出的指南为准（随安装版本变化）；`references/install.md` 覆盖安装与升级，`learnings/` 内置 GitHub/Google/X 站点的沉淀工具脚本。上游为 [citrolabs/ego-lite](https://github.com/citrolabs/ego-lite)（MIT），即 `npx skills add citrolabs/ego-lite` 背后的同一目录，按 `skills.json` 的 `upstream` 固定 commit 同步。

### 视觉感知（visual-perception）

#### [perceived-form](./skills/perceived-form/)

按人眼实际怎么「看见」来诊断和校正图形：负空间、视觉重量、邻近语法、默认态 vs 兼容态、黄金家族尺子、马赫带与光学校正。适用于 UI / 图标 / Logo / 字标 / 生图提示词「几何对齐了仍别扭」。不替代落地页口味（`design-taste-frontend`）或读页面（`browser-ui-reader`）。

### Skill 管理（skill-management）

#### [ln-install-skill](./skills/ln-install-skill/)

用符号链接把本仓库（`csl-agent-toolbox`）中的 Skill 安装、列出、校验或卸载到任意宿主 skills 目录：Claude Code（`~/.claude/skills`）、Codex（`~/.codex/skills`）、跨工具（`~/.agents/skills`）、DSH（`~/.dsh/skills`）、pi（`~/.pi/agent/skills`）、omp（`~/.omp/agent/skills`）、zcode（`~/.zcode/skills`）、cow（`~/cow/skills`），或项目内 `<repo>/.claude/skills` / `<repo>/.agents/skills`。目标宿主必须由用户点名，未点名先询问，不自行探测。只操作 symlink，永远不碰源目录和源 `SKILL.md`，安装与卸载均可逆。本仓库是唯一源；`~/.cc-switch/skills` 只是历史副本位置，不再作为源。

#### [dao-skill](./skills/dao-skill/)

Skill 元设计器：先把模糊需求归根，再设计、生成、审计、优化或按证据进化可运行的 Skill；也用于评估既有 Skill 仓库、把方法论/文章/代码库转成可执行 Skill 体系。上游 [gnipbao/dao-skill](https://github.com/gnipbao/dao-skill)（MIT），按 `skills.json` 的 `upstream` 固定 commit 同步。

### 生产力（productivity）

#### [grill-me](./skills/grill-me/) / [grilling](./skills/grilling/)

`grill-me` 是 `/grill-me` 的显式入口（`disable-model-invocation: true`），正文只转调 `grilling`；`grilling` 才是实际工作流：把计划或决策展开成设计树，按轮次追问整个 frontier，每问附带推荐答案，直到双方理解一致。两者上游均为 [mattpocock/skills](https://github.com/mattpocock/skills)（MIT）；`grill-me` 在 `skills.json` 里以 `depends_on: ["grilling"]` 声明依赖，只装前者不会工作。

#### [invoice-organizer](./skills/invoice-organizer/)

把混乱目录里的发票与收据（PDF、扫描件、截图）整理成报税就绪的归档：逐个文件提取供应商、日期、金额等信息，按 `YYYY-MM-DD Vendor - Invoice - 描述.ext` 规范重命名，再按供应商/费用类别/时间段/税务类别归类，动文件前先展示整理方案。上游为 [ranbot-ai/awesome-skills](https://github.com/ranbot-ai/awesome-skills/tree/main/skills/awesome-llm-invoice-organizer)（衍生自 Prat011/awesome-llm-skills）；上游无 license 声明，`skills.json` 记为 `UNVERIFIED`，vendored 时修复了上游截断的结尾与损坏的代码围栏。

#### [wechat-article-reader](./skills/wechat-article-reader/)

读取微信公众号公开单篇文章，提取正文、标题、作者、公众号名与发布时间，按需总结、翻译或保存 Markdown。网页工具失败时使用本地 HTTPS 备用流程，包含请求限时、链接与重定向校验、正文验收及防覆盖保存规则。来源为用户提供的技能包，经本地重写修订；来源记录见 `skills.json` 的 `source_note`。已通过单篇真实文章备用抓取实测，图片与异常分支未验证。

#### [wechat-channels-reader](./skills/wechat-channels-reader/)

读取微信视频号公开单篇分享链接，保存视频、元数据、带时间戳转写与抽帧。支持 ffmpegtool、paste2vid 及显式选用登录态的元宝路线；各服务需单独允许，包含解析预算、下载边界、模型校验及失败状态。来源为用户附件的本地修订版，记录见 `skills.json` 的 `source_note`。已通过 81 项离线回归；单条真实视频经 paste2vid 下载、tiny 转写与抽帧成功，tiny 有明显错字；元宝及 FunASR 线上兼容性未验证。

## Codex 插件

`plugins/` 存放宿主原生插件包，兼容性由插件 manifest 决定。插件登记在 `skills.json` 的 `plugins` 数组；`.agents/plugins/marketplace.json` 是供 Codex 发现和安装插件的 marketplace 目录。当前插件包含 hook，安装后需显式信任并验证激活。

### [openwolf-codegraph-bridge](./plugins/openwolf-codegraph-bridge/)

在用户级统一接入 Codex 生命周期事件。仅当仓库存在 `.wolf/` 或 `.codegraph/` 时启用：转发 OpenWolf 本地 hook，并注入 CodeGraph 优先导航规则。

完整安装 / 使用 / 验证 / 卸载说明见 [`plugins/openwolf-codegraph-bridge/README.md`](./plugins/openwolf-codegraph-bridge/README.md)。

### [understand-anything](./plugins/understand-anything/)

代码库知识图谱插件：多 agent 管线（10 个 agent）把任意项目转成可交互仪表盘——结构图（文件/函数/依赖节点）、业务域视图、依赖序 guided tours、diff 影响分析，另含 `/understand-knowledge` 可把 Karpathy 式 LLM wiki 解析成知识图谱。`/understand` 等主命令随插件分发，首次运行时自建 `packages/core`（需 Node ≥ 22 + pnpm ≥ 10）；整体目录原样同步，与上游 install.sh 的整目录 symlink 分发一致。上游为 [Egonex-AI/Understand-Anything](https://github.com/Egonex-AI/Understand-Anything) 的 `understand-anything-plugin` 子目录（MIT），按 `skills.json` 的 `upstream` 固定 commit 同步；已登记 `.agents/plugins/marketplace.json`（Codex）与 `.claude-plugin/marketplace.json`（Claude）。本地适配：补齐固定版本根目录 MIT 许可与 Dart grammar 许可；上游只带 `.claude-plugin/plugin.json`，新增 `.codex-plugin/plugin.json` 仅用于目录登记与发现适配。Codex 命令发现、多 agent 执行及 hook 激活均未实测，不能据此宣称完整兼容。内含使用 Claude 事件和环境变量的 post-tool-use auto-update hook，安装到 Claude 后需显式信任；该 hook 未适配或验证为 Codex 原生 hook。与 CodeGraph 互补而非替代：CodeGraph 管 agent 检索（符号引用/调用路径/影响面），本插件产出人读的可视化导览仪表盘。

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
├── .agents/plugins/marketplace.json
├── skills/
│   ├── codexradar-model-advisor/
│   │   └── SKILL.md
│   ├── custom-image-gen/
│   │   ├── SKILL.md
│   │   └── agents/openai.yaml
│   ├── browser-ui-reader/
│   │   ├── SKILL.md
│   │   ├── scripts/
│   │   └── references/
│   └── .../                 # 所有独立 Skill，不按 category 分目录
├── plugins/
│   └── openwolf-codegraph-bridge/
│       ├── .codex-plugin/plugin.json
│       └── hooks/
├── skills.json
├── scripts/toolbox.py
├── mcp/<name>/mcp.json       # 收录独立 MCP 后创建
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
