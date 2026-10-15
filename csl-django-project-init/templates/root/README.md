# __PROJECT_NAME__ backend

Django 后端服务。结构基线来自 wework/backend 个人标准。

## 快速开始

```bash
python3.12 -m venv .venv
make install-dev
cp __CONF_PACKAGE__/settings_local.example.py __CONF_PACKAGE__/settings_local.py
make migrate
make dev                  # 启动开发服务器
make worker               # 另开终端:启动异步任务 worker
```

> `stdkit/` 为内嵌私有基础库,已随仓库分发,克隆即得,不依赖私服安装;
> 传递依赖列在 requirements.txt 末段,升级 stdkit 基架时同步。
> pre-commit 对 `stdkit/` 只做检查不做改写,保持与模板字节一致。

## 常用命令

见 `make help`。质量门禁:`make check` / `make verify TEST=<目标测试>` / `make verify-full`。

架构与规范从 `docs/README.md` 进入;AI 协作规范见根 `AGENTS.md`。
