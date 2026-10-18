# BUGLOG — main 已知坑与修法(append-only,最新在上)

条目由 /csl-buglog 或人工维护,供 coder/reviewer 动手前核对

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
