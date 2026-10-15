---
name: csl-django-project-init
description: 按个人 Django 项目基线(提炼自 wework/backend)初始化新后端项目:一次性渲染熟悉的目录结构、common 通用基建(视图/Service/认证中间件/utils)、质量门禁(Makefile + pre-commit)、docs 与 AGENTS.md 骨架,并按需生成业务 app。Use when 用户要新建 Django 项目、初始化 Django 后端、按 wework 结构/个人标准搭项目骨架、生成 csl 流水线可接入的新 Django 仓库。存量项目改造不适用(走 /csl-init-project 或 django-personal-development)。
---

# csl-django-project-init — Django 项目基线初始化

## 概述

把 wework/backend 沉淀的个人 Django 项目基线(目录结构、common 通用工具、模型与认证约定、质量门禁)固化成脱敏模板,新项目一条命令渲染成型,结构不漂移、基建不重拷。初始化完成后,日常开发规范交棒给项目级 AGENTS.md 与 `django-personal-development` 技能。

## 资源指南

| 资源 | 何时加载 |
| --- | --- |
| `scripts/scaffold.py` | 执行渲染。确定性脚本:目标必须不存在或为空,`--force` 也绝不覆盖已有文件 |
| `references/project-blueprint.md` | 用户要加基线之外的能力(地区树、RBAC 菜单、企微/钉钉集成等),或对照 wework 演进模板时 |
| `references/coding-conventions.md` | 初始化后写首批业务代码、或修订项目 AGENTS.md「项目约定」时 |

## 工作流程

### 1. 一次问齐参数(不挤牙膏)

用 AskUserQuestion 一次确认:

- **目标路径**(必须为不存在或空目录);
- **项目名**(默认取目录名;影响 README/镜像名);
- **配置包名**(默认 `backend`;表名前缀默认取 `<配置包名>_`);
- **业务 app 清单**(如 `crm`、`fund_register`;可留空后补);
- 是否需要 PG 测试沙盒(django-test-sandbox 技能安装)。

### 2. 渲染骨架

```bash
python3 <技能目录>/scripts/scaffold.py <目标路径> --conf <配置包> --project <项目名> --app <app1> --app <app2>
```

脚本输出渲染 manifest 与后续步骤。渲染后自查:退出码 0、无占位符残留(脚本内置检查)。

stdkit 基架随模板自带(v1.2.6 快照):逐字拷入项目根 `stdkit/` 并随项目仓库分发(克隆即得,不依赖私服安装);传递依赖固化在 requirements.txt 末段;pre-commit 对其只查不改,保持与模板字节一致。用户明确不要时传 `--no-stdkit`。

### 3. 初始化 git(不提交)

目标无 `.git` 时 `git init`;**不执行任何 commit/push**(提交需用户明确指示)。

### 4. 生成项目 AGENTS.md 并呈报

模板已含按脚手架事实写好的 `AGENTS.md`(工作原则/质量门禁/项目约定/常用命令/BUGLOG)。按本项目实际(业务 app 清单、集成项)修订后呈报用户确认;用户也可改走 `/csl-init-project` 扫描式生成。两者不并用。

### 5. 运行时验证(用户授权后执行冒烟)

```bash
python3.12 -m venv .venv && make install-dev
cp <配置包>/settings_local.example.py <配置包>/settings_local.py
.venv/bin/python manage.py check
make migrate && make dev   # 起服务验证 /api/v1/base/config 返回
```

未获授权时,停在静态验证(py_compile 全部 .py 含 `stdkit/` + `bash -n scripts/local_quality_gate.sh`),并在交付报告中明确列为阻塞项。

### 6. 交付报告

包含:渲染文件数与关键路径;git/AGENTS.md 处置;已执行的验证命令及结果;阻塞项(token、沙盒未装);下一步建议(`make check`、装 django-test-sandbox、按 coding-conventions 写首批业务代码)。

## 边界

- 只初始化新项目;存量项目扫描用 `/csl-init-project`,日常开发规范用 `django-personal-development`。
- 模板是**脱敏基线**:不含真实密钥与令牌;`SECRET_KEY`/`JWT_SECRET` 均为占位值,生产在 settings_local.py 覆盖。
- 不自动安装依赖、不跑 migrate、不提交推送——除非用户明确授权。
- 基线不含业务集成(企微/钉钉/CRM/up_center/薪酬等);需要时按 `references/project-blueprint.md` 的可选扩展清单对照 wework 源搬移,不凭记忆重写。
- wework/backend 参考源不可见时本技能仍可完整工作(模板自包含);不要在运行时读取参考源路径。

## 质量标准

- scaffold.py 退出码 0,内置占位符残留检查通过,渲染产物全部 `py_compile` 通过(含 `stdkit/` 全部源码)。
- `stdkit/` 存在、与模板逐字一致、且未被 .gitignore 排除(随仓库分发);requirements.txt 末段含 stdkit 传递依赖。
- 目标目录策略验证:非空目标被拒绝,已有文件不被覆盖。
- 若执行了运行时验证:`manage.py check` 通过、`/api/v1/base/config` 可访问。
- 交付报告六要素齐全(文件数/路径、git 与 AGENTS.md 处置、验证证据、阻塞项、下一步)。
