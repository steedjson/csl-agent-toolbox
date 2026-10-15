# BUGLOG — main 已知坑与修法(append-only,最新在上)

条目由 /csl-buglog 或人工维护,供 coder/reviewer 动手前核对

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
