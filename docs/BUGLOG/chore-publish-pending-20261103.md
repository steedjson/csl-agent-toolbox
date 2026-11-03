# BUGLOG — chore/publish-pending-20261103 已知坑与修法

条目只追加，最新在上。记录已确认根因与复发规则；不含凭据或私人业务数据。

## [2026-11-03][component-packaging] 子目录导入遗漏上级许可，发现清单被误当作完整宿主兼容证据
- 现象: 新增的设计技能与知识图谱插件只有许可名称，缺少上级 LICENSE/NOTICE 或内嵌依赖许可；本地 Codex 清单沿用完整功能描述，但实际 hook 使用 Claude 事件与变量；插件本地 dist 未忽略
- 根因: 按子目录同步时只保留子树文件；静态 manifest 能被目录发现并不证明目标宿主的命令、代理与 hook 运行兼容；未隔离首次构建产生的目录
- 修法: 补固定版本根 LICENSE/NOTICE 并验证 Git blob，补第三方 screenshot 与 Dart grammar 许可，登记完整 files 和来源记录；收窄 Codex 适配说明；忽略 dist、node_modules 与 .dao 运行状态，保留登记的 WASM 运行依赖
- 关联: skills/impeccable/LICENSE、skills/impeccable/NOTICE.md、plugins/understand-anything/LICENSE、plugins/understand-anything/.codex-plugin/plugin.json、skills.json、README.md、.gitignore
- 教训: 发布子树前检查上级与内嵌依赖的许可材料；将“目录可发现”和“宿主运行已验证”分别记录，不能相互代替
