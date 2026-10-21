# 安装、更新与宿主适配

`csl-agent-toolbox` 保存源码；宿主安装是显式动作。`skills.json` 的 `skills`、`plugins`、`mcps` 是唯一组件目录。自研组件直接修改；第三方组件保留 `upstream` 和三方合并基线；改编材料用 `source_note` 记录来源。

## 选择组件和目标

```bash
python3 scripts/toolbox.py list
python3 scripts/toolbox.py hosts

# 多项、多宿主；grill-me 的 grilling 依赖也会安装
python3 scripts/toolbox.py install --skill grill-me --skill coding-discipline --host codex --host claude --dry-run
python3 scripts/toolbox.py install --skill grill-me --skill coding-discipline --host codex --host claude

# 用户级共享 Skill 目录，不顺带安装到其他宿主
python3 scripts/toolbox.py install --skill grilling --host agents

# 当前存在的原生插件
python3 scripts/toolbox.py install --plugin openwolf-codegraph-bridge --host codex --dry-run
python3 scripts/toolbox.py install --plugin openwolf-codegraph-bridge --host codex

python3 scripts/toolbox.py status --host codex
python3 scripts/toolbox.py uninstall --skill grill-me --host codex --dry-run
```

`--skill`、`--mcp`、`--plugin`、`--host` 可重复。省略组件或宿主报错。缺少 Skill 目标目录时创建；真实目录不覆盖；外来链接只有显式 `--prune` 才替换。卸载只移除选中链接，不级联删除依赖。

`--host codex/claude/omp/pi/...` 是 Agent 自己的用户安装位置；`--host agents` 是 `~/.agents/skills` 跨工具共享位置。MCP 和插件没有所有 Agent 通用的共享配置目录，必须指定具体宿主。共享目录不保证所有 Agent 默认启用相同的发现路径。

## 当前适配矩阵

核实日期：2026-10-22。原生加载后仍需在新会话验证功能。

| 目标 | Skill 默认路径 | MCP | 插件 |
| --- | --- | --- | --- |
| `codex` | `~/.codex/skills`，本机发现已确认 | 原生 `mcp add/get/remove` | Codex marketplace |
| `claude` | `~/.claude/skills` | 原生 `mcp add-json --scope user`、get/remove | Claude marketplace |
| `pi` | `~/.pi/agent/skills` | 原生 `mcp add/remove`；配置读取判重 | `package.json` 含 `pi` 对象；`pi install/remove` |
| `omp` | `~/.omp/agent/skills` | 原生 `mcp.json` 合并写入，保留其他配置 | `package.json` 含名称及 `omp`/`pi` 对象；`omp plugin link/uninstall` |
| `agents` | `~/.agents/skills` | 无共享适配 | 无共享适配 |
| `dsh` | `~/.dsh/skills` | 未适配 | 未适配 |
| `zcode` | `~/.zcode/skills`，隔离 CLI 发现已确认 | `~/.zcode/cli/config.json` 的 `mcp.servers` 合并写入 | 原生或兼容 manifest；本地目录登记到 `plugins.dirs` |
| `cow` | `~/cow/skills` | 未适配 | 未适配 |

DSH、Cow 保留用户已有目录约定；本机没有对应 CLI，未确认运行时发现。未知插件格式直接报错，不自动转换 hooks 或扩展代码。现有 `openwolf-codegraph-bridge` 使用 Codex manifest，Codex 支持原生安装；ZCode 原生校验通过，但其 Hook 行为未做会话验收。

Skill 路径尊重 `CODEX_HOME`、`CLAUDE_CONFIG_DIR`、`PI_CODING_AGENT_DIR`；OMP 也尊重 `PI_CONFIG_DIR`。OMP 命名 profile 需显式设置 `PI_CODING_AGENT_DIR` 指向该 profile 的 agent 目录，入口不猜测 profile。

保留 Codex marketplace 标识 `vlong-skills-local` 以兼容已有安装。项目和远程仓库使用 `csl-agent-toolbox`；旧 `my-skills` 路径作为兼容链接保留，已有宿主链接和 marketplace 来源继续可达。

## ZCode

安装器直接合并用户配置，不依赖 `zcode` 可执行文件。Skill 仍通过软链接安装到 `~/.zcode/skills`；不触碰用户级共享目录。

```bash
python3 scripts/toolbox.py install --skill grilling --host zcode --dry-run
python3 scripts/toolbox.py install --skill grilling --host zcode
python3 scripts/toolbox.py status --host zcode
python3 scripts/toolbox.py install --plugin openwolf-codegraph-bridge --host zcode --dry-run
python3 scripts/toolbox.py uninstall --skill grilling --host zcode --dry-run
```

MCP 使用 `~/.zcode/cli/config.json` → `mcp.servers.<name>`。支持本仓库的 stdio、HTTP 配置，`streamable-http` 转为原生 `http`；Bearer 环境变量展开为 `headers.Authorization`。保留其他 server、provider、hooks、插件和其他配置；同名 server 拒绝覆盖；配置原子替换，文件权限为 `0600`。如果当前使用 `~/.agents/mcp.json` 回退，添加首个原生 server 会遮蔽该回退，因此安装器拒绝操作，要求先自行迁移到 `mcp.servers`。

插件接受 `.zcode-plugin/plugin.json`、`.claude-plugin/plugin.json`、`.codex-plugin/plugin.json`，按此顺序选择，manifest 名称必须与登记组件一致。安装把源码绝对路径加入 `plugins.dirs`，重复安装不重复登记；卸载只移除匹配目录，不删除插件源码或其他插件配置。`plugins.enabled: false` 时安装报错，不自行开启全局插件开关。此方式属于本地源码加载，不写 marketplace 缓存；插件 Hook、MCP 模板和宿主 API 是否兼容仍需逐个验收。

2026-10-22 使用本机 ZCode Desktop `3.16.2`（附带 CLI `0.17.0`）在临时 HOME、临时仓库验证：Skill 链接可被 `skills list --json` 发现；原生插件通过 `plugins validate`，出现在 `plugins list`，贡献的 Skill 可被发现；卸载保留源码。已有 bridge 的原生 validate 返回 `ok: true`、无诊断。MCP 配置读写、stdio/HTTP/Bearer、判重、预览、无关配置保留和错误配置拒绝由离线回归测试覆盖。

未验证真实 MCP 连接和插件 Hook 执行。直接调用桌面附带 CLI 的 `/mcp list` 探针在 provider 初始化阶段因缺少相邻内置 provider 配置而退出，未到 MCP 握手；这不影响已完成的插件和 Skill 清单验证。实际安装后在 ZCode 新会话的 Settings → MCP / Plugin Management / Skills 验收；宿主开关和桌面托管配置可能影响生效。

## 独立 MCP 包

保存到 `mcp/<name>/mcp.json`，在 `mcps` 列表登记 `name`、`description`、`files`，第三方再登记 `upstream`。目前未收录独立 MCP，以下只是格式示例：

```json
{
  "mcpServers": {
    "example": {
      "type": "stdio",
      "command": "python3",
      "args": ["${COMPONENT_ROOT}/server.py"],
      "env": {"API_KEY": "${EXAMPLE_API_KEY}"}
    }
  }
}
```

包必须正好包含与包名相同的一个 server。HTTP 示例：

```json
{
  "mcpServers": {
    "example": {
      "type": "streamable-http",
      "url": "https://example.com/mcp",
      "bearer_token_env_var": "EXAMPLE_API_KEY"
    }
  }
}
```

支持 `stdio`、`http`、`streamable-http`，以及 `command`、`args`、`env`、`url`、`headers`、`bearer_token_env_var`；未知字段报错。Codex 原生 add CLI 无自定义 HTTP headers 参数，含此字段时拒绝该组合；Pi、Claude、OMP、ZCode 支持 headers。入口不转换 OAuth、SSE 和其他扩展字段，此类配置使用宿主原生工具维护。

`${COMPONENT_ROOT}` 指包目录，`${TOOLBOX_ROOT}` 指仓库，其他 `${NAME}` 从环境读取。安装时变量缺失或 stdio 运行器缺失会在写入前报错。密钥不放入仓库；宿主可能把展开的值保存到自己的用户配置，入口不打印这些值。

```bash
# example 登记后才能安装；没有登记时明确报错
python3 scripts/toolbox.py install --mcp example --host codex --host claude --dry-run
python3 scripts/toolbox.py install --mcp example --host omp
python3 scripts/toolbox.py uninstall --mcp example --host omp
```

已有同名 MCP 安装时报错，要求先处理冲突。配置成功不代表连接成功；使用原生 `mcp get/list`、会话 `/mcp` 和实际工具调用验收。`toolbox.py status` 当前只检查 Skill 链接。

## 第三方更新

```bash
python3 scripts/toolbox.py import --source owner/repository --path skills/example --name example --license MIT
python3 scripts/toolbox.py import --kind plugin --source owner/repository --path plugins/example --name example
python3 scripts/toolbox.py import --kind mcp --source owner/repository --path mcp/example --name example
python3 scripts/toolbox.py check
python3 scripts/toolbox.py update
python3 scripts/toolbox.py update --apply
python3 scripts/toolbox.py update --kind skill --component grilling --component grill-me --apply
```

导入和更新不安装宿主。支持 GitHub/npm 来源，默认追踪默认分支或 npm latest；显式导入分支则继续追踪该分支。更新后 pin 指向实际 commit/version。本地改动保留，冲突跳过整个组件；二进制双边改动报冲突。每个成功组件立即保存 pin；同组件普通写入失败恢复旧内容。

Codex/Claude 插件还需在 `.agents/plugins/marketplace.json` 或 `.claude-plugin/marketplace.json` 登记路径和原生名称，安装器校验匹配。OMP/Pi 本地包用原生路径安装。普通 npm 包不能冒充插件，必须有原生 manifest。

Skill 和本地链接扩展读取仓库；原生插件缓存、已启动的 MCP 需要原生更新、重新安装或重启。更新器不改变安装范围，也不声称运行时已经热更新。

同步边界：拒绝包内符号链接；新增文件未保留上游执行位，优先用 `node script.js`、`python3 script.py` 等显式运行器。没有多进程锁或断电级事务保证。

## 核对依据

- [OpenAI Skills](https://developers.openai.com/codex/skills)、[MCP](https://developers.openai.com/codex/mcp)、[配置目录](https://developers.openai.com/codex/config-advanced)、[插件打包](https://developers.openai.com/plugins/build/plugins)。Codex 自有 Skill 目录来自本次运行清单；最新官方目录表列出共享目录。
- [Claude Skills](https://code.claude.com/docs/en/skills)、[MCP](https://code.claude.com/docs/en/mcp)、[插件格式](https://code.claude.com/docs/en/plugins-reference)。
- [OMP Skills](https://github.com/can1357/oh-my-pi/blob/main/docs/skills.md)、[MCP](https://github.com/can1357/oh-my-pi/blob/main/docs/mcp-config.md)、[插件安装](https://github.com/can1357/oh-my-pi/blob/main/docs/plugin-manager-installer-plumbing.md)。
- ZCode 官方 [MCP](https://github.com/zai-org/ZCode/blob/main/apps/zcode-cli/docs/usage/07-mcp.md)、[Skills](https://github.com/zai-org/ZCode/blob/main/apps/zcode-cli/docs/usage/08-skills.md)、[本地插件](https://github.com/zai-org/ZCode/blob/main/apps/zcode-cli/docs/usage/10-plugins.md)；本机桌面安装包 `Resources/glm/packages/zcode-guide-plugin/skills/` 配置指南与诊断文档。
- 本机 CLI help：Codex `0.163.0-alpha.10.2`、Claude `2.1.306`、OMP `18.12.5`、Pi `@earendil-works/pi-coding-agent 1.3.0`；Pi 随安装包提供的 configuration、skills、mcp、packages 文档。
