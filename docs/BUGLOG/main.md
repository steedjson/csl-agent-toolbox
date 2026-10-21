# BUGLOG — main 已知坑与修法(append-only,最新在上)

条目由 /csl-buglog 或人工维护,供 coder/reviewer 动手前核对

## [2026-10-22][docs] 插件登记说明与统一组件目录矛盾
- 现象: README 仍声明插件不登记到 skills.json,与当前 plugins 数组冲突
- 根因: 组件管理扩展后,旧 Codex 插件章节未同步更新
- 修法: 区分统一组件目录与宿主 marketplace;旧目录方案归档并标记历史状态
- 关联: README.md、docs/archive/repository-layout-refactor.md
- 教训: 调整组件契约时,同时核对旧说明与历史方案入口

## [2026-10-22][toolbox-adapters] 参数等号写法扩大更新范围,运行器预检漏读组件 PATH
- 现象: `--kind=plugin` 未被转发层识别,误走全类型更新;组件在 env.PATH 指定可执行文件目录时,安装前预检错误拒绝
- 根因: 用原始参数 token 做成员判断代替 argparse 解析;运行器检查只读取父进程 PATH
- 修法: parse_known_args 解析类型/目录/组件选择后再按范围分发;使用组件展开后的 PATH 检查运行器;OMP 本地插件适配收窄到有效原生 package.json
- 关联: scripts/toolbox.py、scripts/test_toolbox.py(等号参数、跨类型范围、组件 PATH 回归)
- 教训: 命令行转发也是输入边界,不能用字符串存在性推断用户选定范围

## [2026-10-22][component-sync] 第三方同步缺少类型与写入边界,失败后内容和 pin 不一致
- 现象: npm 包根默认路径无法导入;归档成员可越出组件目录;前一个组件已更新而后一个源失败时,版本记录未保存
- 根因: 根路径直接拼前缀;文件键未验证;所有 pin 延迟到批次末尾写入
- 修法: 统一 skill/plugin/mcp 的组件路径与 manifest;拒绝越界路径和符号链接;临时目录准备完整组件,按组件提交并原子保存目录,普通写入失败恢复旧内容
- 关联: scripts/sync_upstream.py、scripts/test_sync_upstream.py(54 例)
- 教训: 固定版本是合并基线,必须和已落盘内容一起提交;新增组件类型不应复制一套更新器

## [2026-10-22][host-install] 默认全宿主和卸载预览不安全,依赖安装遗漏
- 现象: 未传宿主会覆盖所有宿主范围;unlink 的 dry-run 仍删链接;未知名字可删外来链接;只装入口 Skill 漏装声明的依赖
- 根因: 查询与写操作共享默认宿主展开;卸载未传预览参数;归属校验受名称存在条件限制;安装器不读取 depends_on
- 修法: 写操作强制显式宿主;卸载实现预览并拒绝未知来源;安装前解析依赖并拒绝循环;统一入口先检查宿主适配再执行
- 关联: scripts/install_skills.py、scripts/toolbox.py、scripts/test_install_skills.py、scripts/test_toolbox.py
- 教训: 用户选择的组件、范围、宿主和预览语义都必须落实在可执行边界上

## [2026-10-22][install-location] 擅自把用户级 ~/.agents/skills 挂到仓库,违背"默认装 agent 各自目录"原则
- 现象: 为解决 omp 可见性风险,把 `~/.agents/skills` 整体 symlink 到仓库并写成"omp 直连"架构;用户纠正:默认安装必须落各 agent 自己的技能目录,用户级目录只有明确指定时才用
- 根因: 解决"宿主清空断供"时,选了对工具最省事的位置(omp 原生扫 `~/.agents/skills`),而不是对架构正确的位置(装进 `~/.omp/agent/skills`);用户级目录是跨 agent 共享资源,擅自挂载等于替用户做了全局决策,且让 Vercel skills CLI 的写入直通仓库
- 修法: 撤销 symlink,`~/.agents/skills` 恢复普通目录(.gitignore 还原);AGENTS.md/CLAUDE.md/README 写入安装位置政策:默认装 agent 目录(`--host <agent>`),用户级仅在明确说"装到用户级"时使用;omp 需要技能时 `--host omp` 装进 `~/.omp/agent/skills`
- 关联: AGENTS.md:11、CLAUDE.md:11、README.md:181、~/.agents/skills
- 复发: 2 次 · 最近 2026-10-22(前次为 no-auto-install)
- 教训: 安装位置和安装动作一样属于用户决策——"装到哪一层"(agent 级 vs 用户级)必须点名,省事的路径不等于正确的路径

## [2026-10-21][no-auto-install] 仓库操作不得自动安装到 agent:安装必须等用户点名宿主
- 现象: import ego-browser 后顺手跑了 `install_skills.py link`,5 个宿主(含从未用过的 dsh)全被挂上链接;用户明确"本项目不自动将 skill 安装到 agent""当我说安装到哪个 agent 的时候再安装"
- 根因: `sync_upstream.py` 的 `--install`/`--prune` 把"更新后镜像到安装目录"做成了一等公民,`import` 也带 `--install`,鼓励了"顺手装"的路径;`ln-install-skill` 的 DST 解析含"探测第一个存在的宿主",等于替用户选 agent
- 修法: 删除 `mirror_installs`/`resolve_install_target`/`--install`/`--prune` 及 `import --install`,`update`/`import` 只写仓库文件并在结尾提示安装命令;`ln-install-skill` DST 改为"用户必须点名,未点名就问,不再探测";AGENTS.md/CLAUDE.md/README 写入"点名才装"政策;撤销已自动安装的 ego-browser 5 条链接
- 关联: scripts/sync_upstream.py、scripts/test_sync_upstream.py(28 例)、ln-install-skill/SKILL.md:18、AGENTS.md:11、CLAUDE.md:11、README.md「从本仓库安装到宿主(手动)」
- 复发: 1 次 · 最近 2026-10-21
- 教训: 安装是改变用户环境的操作,必须由用户点名目标;工具链里任何"顺手也帮你装了"的开关,最终都会被顺手用上

## [2026-10-21][repo-as-source] 源与副本方向反转:仓库成为唯一源,宿主改 symlink,关掉 CC Switch 自动回写
- 现象: 此前 `~/.cc-switch/skills` 被当作 SRC、本仓库当副本;4 个宿主里 114 个条目全部指向 `~/.cc-switch/skills`,另有 6 个真实目录副本(agent-reach/reverse-engineer-anything/xerj/grill-me/grilling)与仓库脱钩。CC Switch 自身 `skillSyncMethod: auto` + `resync_skills_to_apps`,下次启动会把 symlink 覆盖回副本,源再次分裂
- 根因: 仓库缺少"安装"能力,只能手工 `cp`;`ln-install-skill` 默认 SRC 也指向 cc-switch,把历史副本位置当成了源。同时 `agent-model-policy-sync/` 在会话中途从工作区消失但 skills.json 仍引用
- 修法: 新增 `scripts/install_skills.py`(status/link/unlink/list,只建删 symlink,`--prune` 重定向旧链接,真实目录不动);`link --prune` 把 114 条重定向到仓库,6 个副本先备份到 `~/.skill-copies-backup-<ts>` 再替换;`ln-install-skill` 默认 SRC 改为仓库根;CC Switch `skillSyncMethod` 改 `manual`(settings.json 与 db 均已备份);丢失技能从 HEAD `git checkout` 恢复并重新链接
- 关联: scripts/install_skills.py、scripts/test_install_skills.py(14 例)、ln-install-skill/SKILL.md:14、~/.cc-switch/settings.json、AGENTS.md/CLAUDE.md Source Of Truth 段
- 复发: 1 次 · 最近 2026-10-21
- 教训: 只要有第二个目录能写回宿主,源就永远是两个;切换源必须同时关掉旧源的回写开关,并把"是否 symlink"做成可检查的状态(real-directory 必须报出来而不是静默覆盖)

## [2026-10-20][sync-upstream] 两种第三方形态暴露 updater 三个缺陷:根路径不可用、懒加载 2 分半、二进制合并崩溃
- 现象: ① 仓库根即 Skill 的形态(`gnipbao/dao-skill`,SKILL.md 在顶层)配 `path: "."` 时,前缀切成 `./`,所有相对路径都匹配不上;② 单 skill monorepo 形态(`mattpocock/skills`)38 个文件逐个 `git show`,在 blobless 克隆下每次触发一次网络请求,单次 fetch 耗时 2 分半;③ 上游带 2.2MB PNG,两边都改时 `git merge-file` 直接以 255 退出,抛原始异常而非记冲突
- 根因: ① 前缀用 `path.rstrip("/") + "/"` 拼,`.` 不是空串;② 未做 blob 预取,`--filter=blob:none` 的按需拉取退化成 N 次串行请求;③ merge3 不判断内容类型,git 对二进制只返回错误码 255
- 修法: 根路径归一为 `scope=[]`/`prefix=""`;`prefetch_blobs` 用一次 `git fetch <oid...>` 批量取回(38 文件 10s→2.8s);`is_binary` 检测 NUL 字节,二进制两边都改直接记冲突;另加 `import` 子命令把"搬入即记 pin"变成一条命令,`exclude` 过滤 CI/大图,`depends_on` 声明转调依赖
- 关联: scripts/sync_upstream.py(github_files/prefetch_blobs/is_binary/merge3/cmd_import)、scripts/test_sync_upstream.py(30 例)
- 复发: 1 次 · 最近 2026-10-20
- 教训: 部分克隆(`--filter=blob:none`)的收益只在批量取 blob 时成立;逐文件读取会退化成 N 次网络往返,比直接全量 fetch 慢一个数量级

## [2026-10-20][sync-upstream] 第三方 skill 只能手工复制,无来源记录也无更新路径
- 现象: 仓库 21 个 skill 中 3 个来自第三方(`grok-build-cli`、`thermo-nuclear-code-quality-review`、`design-taste-frontend`),但没有 `upstream` 元数据、没有 pin、README 只写 `cp -R`,上游改动只能靠人工 diff;`design-taste-frontend` 甚至未登记进 `skills.json`
- 根因: 仓库定位是"源集合",只约定复制安装,从未定义 vendored skill 的来源与同步契约;`ln-install-skill` 只做 symlink,不理解上游
- 修法: `skills.json` 增加 `upstream` 块(github/npm、路径、pin、license、synced_at);新增 `scripts/sync_upstream.py`,以 pin 为三方合并基线,`check` 报告漂移、`update --apply` 写入并推进 pin、冲突则整 skill 跳过;`--install` 镜像到已安装副本;`validate_repo.py` 增加 upstream 结构校验;确定性测试 `scripts/test_sync_upstream.py`(15 例,含 file:// 上游端到端)
- 关联: scripts/sync_upstream.py、scripts/test_sync_upstream.py、scripts/validate_repo.py:37、skills.json、README.md「第三方 Skill 更新」
- 复发: 1 次 · 最近 2026-10-20
- 教训: 复制第三方内容进仓库的那一刻就要写下来源与 pin,否则"本地改动"和"上游版本"永久无法区分,后续任何自动化都无从判断基线

## [2026-10-18][xerj] xerj-project 输出被 xerj-service 用法文本污染,且意外暴露 service 命令面
- 现象: 每次调用 xerj-project(--help/info/search 等),stdout 前置 6 行 xerj-service 用法文本,search --json 的 jq 管道解析被破坏;更严重的是 xerj-project install/update --force 会经 import 副作用真实执行 service 命令,而非走 xerj-project 自己的未知命令拒绝
- 根因: ~/.bun/bin/xerj-service 顶层 CLI 分发块无 import.meta.main 模块守卫;xerj-project L7 import 该模块取 acquireOperation/scheduleUpdate 时,分发块以宿主 argv 立即执行
- 修法: 分发块整体包 `if (import.meta.main) {}`;直跑(spawn/shebang)行为不变。实测 --help/info 输出干净、service 直跑 usage/status 正常
- 关联: ~/.bun/bin/xerj-service:263、~/.bun/bin/xerj-project:7、本仓库 xerj/SKILL.md(镜像)
- 复发: 1 次 · 最近 2026-10-18
- 教训: wrapper 三件套(xerj-project/xerj-service/xerj-startup.ts)是 2026-10-18 OMP 会话直写 ~/.bun/bin 的本机自产代码,上游 xerj-org/xerj(Apache-2.0)仓库无这些文件——重新生成时必须带回 import.meta.main 守卫;修复前备份 ~/.bun/bin/xerj-service.bak-20261018

## [2026-10-15][csl-django42-project-init] 基线漏配 CACHES:redis 只喂了 Q_CLUSTER,缓存落回进程内 LocMem
- 现象: 基线 requirements 带 django-redis/redis/hiredis 但无任何 CACHES 配置;运行时 Django 隐式落 LocMemCache——多 worker 下 JWT 会话/导出防重/任务进度互不可见,重启即丢
- 根因: wework 的 CACHES 只活在未入库的 settings_local.py(_dev/_local 同),入库 example 只定义 REDIS_HOST/PORT 喂 Q_CLUSTER;提炼模板只读入库文件,洞被原样继承
- 修法: settings_local.example 补参数化 CACHES(LOCATION 接 REDIS_HOST/PORT,KEY_PREFIX 按 环境_项目_api_,PASSWORD 注释位);settings_test 维持 locmem 覆盖,测试不碰 redis
- 关联: csl-django42-project-init/templates/conf_package/settings_local.example.py
- 复发: 1 次 · 最近 2026-10-15
- 教训: 从存量项目提炼配置模板,未入库的本地覆盖文件也是"事实上的配置面"——入库 example 里定义而无人消费的变量(REDIS_HOST 只喂 Q_CLUSTER)是漏配的信号

## [2026-10-15][csl-django42-project-init] 基线模板三处继承缺陷:业务 app 漏注册/分片上传必炸/认证中间件线程不安全
- 现象: ① `--app demo` 渲染后 urls 已挂载但 INSTALLED_APPS 无 `apps.demo`,业务 app 写首个模型时 makemigrations 静默无视;② POST/PUT `/api/v1/base/bigupload/*` 每次必返回"分片上传失败: ...no attribute 'user_id'";③ 认证中间件 `self.verification_auth`/`self.err` 为跨请求共享实例状态,线程并发下受保护判定与 401 报文可串改;MISS_TOKEN_PATHS 用 startswith 前缀匹配,`/statics` 前缀的未来路由被静默免认证
- 根因: ① scaffold 只挂 urls 不写 settings;② 匿名端点(verification_auth=False)读 `self.request.user_id`,而该属性仅认证分支注入(wework 同构继承);③ wework 中间件以实例属性承载请求级状态 + startswith 前缀匹配(wework 同构继承)
- 修法: ① settings.py 模板加锚点,scaffold `register_apps_in_settings` 追加;② `getattr(request,"user_id",None) or "anonymous"` 兜底,分片按 task_id 隔离;③ 判定状态改请求内局部变量、错误体局部构造,路径匹配改段级精确(`^/statics(/|$)`)
- 关联: csl-django42-project-init/templates/{conf_package/settings.py,apps/base/views/base.py,common/middlewares/request.py} + scripts/scaffold.py
- 复发: 1 次 · 最近 2026-10-15
- 教训: 从存量项目提炼模板,保真裁剪之外必须过一遍"继承缺陷"清单(共享状态/前缀匹配/属性注入假设),wework 能跑不等于该路径真被用过

<!-- wolf:bug-004 -->
## [2026-08-21][external] Claude Code 回复被渲染成逐碎片换行（每几个字符一行，thinking 块交替插入），用户称'无脑换行'
- 现象: Claude Code 回复被渲染成逐碎片换行（每几个字符一行，thinking 块交替插入），用户称'无脑换行'
- 根因: 上游百炼 TokenPlan 网关的 OpenAI 流在每个 content chunk 携带 reasoning_content:""（存在但空串）；cc-switch 3.19.2 转换器把空串当 reasoning delta，逐 chunk 切换 thinking/text block，content 数组碎片化（transcript 可见 thinking+text 交替），CLI 每块渲染成独立段落。已知上游 bug：gh#4869/#6421/#5706/#5692/#4404，修复 PR 截至 v3.20.0 均未合并。
- 修法: 临时：cc-switch 切到原生 Anthropic 格式 provider（my-sub2api / Claude Official）绕过转换层；或等 PR 合并升级。升 v3.20.0 无效。内容本身完整，仅显示碎。
- 关联: external: ~/.cc-switch + CCSwitchMulti 3.19.2-9 (proxy OpenAI→Anthropic 转换层)
- 复发: 最近 2026-08-21
- 备注: tags=cc-switch,streaming,reasoning_content,fragmentation,bailian-tokenplan,proxy-conversion · occurrences=1 · related=bug-003
- 教训: -
<!-- wolf:bug-003 -->
## [2026-08-21][external] unexpected status 503 Service Unavailable: CC Switch local proxy failed while ha…
- 现象: unexpected status 503 Service Unavailable: CC Switch local proxy failed while handling Codex endpoint /responses. Provider: csap-codexbuy-订阅; model: gpt-5.6-sol; upstream_status: HTTP 503; cause: Service temporarily unavailable, url: http://127.0.0.1:15721/v1/responses
- 根因: Not a CC Switch local-proxy bug. Codex MultiRouter forwards native /v1/responses to https://sub2api.950420.xyz/v1/responses (provider csap-codexbuy-订阅). That Sub2API gateway returns HTTP 502/503 Service/Upstream temporarily unavailable, usually in 180-600ms with input_tokens=0. Failover is disabled. Large compaction/memory bodies retry-storm the same failing route. Local proxy on 127.0.0.1:15721 i…
- 修法: Do not rewrite CC Switch wire_api. Check Sub2API account/node health; wait/retry; switch Codex model off the GPT route (apopo-bailian/grok/qianwen); or add a second GPT Responses provider and enable failover. Optional: DIRECT rule for sub2api.950420.xyz if Clash fake-ip (198.18.0.54/utun6) is unstable.
- 关联: external: ~/.cc-switch + CCSwitchMulti 3.19.2-9
- 复发: 最近 2026-08-21
- 备注: tags=cc-switch,codex,503,sub2api,csap-codexbuy,gpt-5.6-sol · occurrences=1
- 教训: -
<!-- wolf:bug-002 -->
## [2026-08-20][ln-install-skill] ln-install-skill 撞名检查脚本用 normpath 比较路径，把 DST 里新建的 symlink 自身误判为 COLLISION（假阳性）
- 现象: ln-install-skill 撞名检查脚本用 normpath 比较路径，把 DST 里新建的 symlink 自身误判为 COLLISION（假阳性）
- 根因: DST 内条目是 symlink；os.path.normpath 只清理路径文本、不解析符号链接，normpath(DST/grill-me) != normpath(SRC/grill-me)，于是'其他条目'过滤失效，把新链接自己当成撞名者
- 修法: 改用 os.path.realpath 双向解析后再比较；SKILL.md verify 第 5 步补充说明：DST 条目是 symlink，必须 realpath 比较
- 关联: ln-install-skill/SKILL.md (verify step 5 执行脚本)
- 复发: 最近 2026-08-20
- 备注: tags=symlink,path-comparison,ln-install-skill,verify · occurrences=1
- 教训: -
<!-- wolf:bug-001 -->
## [2026-08-06][cc-switch-reasoning-tier-repair] repair.py 使用非贪婪正则解析包含嵌套数组的 TOML models 字段
- 现象: repair.py 使用非贪婪正则解析包含嵌套数组的 TOML models 字段
- 根因: 正则表达式在第一个内部方括号处提前结束，且后续代码从错误的前缀提取数组
- 修法: 改用字符串感知的括号深度扫描，并直接解析完整数组表达式
- 关联: cc-switch-reasoning-tier-repair/scripts/repair.py
- 复发: 最近 2026-08-06
- 备注: tags=parser,toml,reasoning-tier-repair · occurrences=1
- 教训: -
