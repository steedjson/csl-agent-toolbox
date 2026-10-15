---
name: csl-django42-project-init
description: 按个人 Django 4.2 基线(钉 Django 4.2.16 + stdkit v1.2.6,提炼自 wework/backend)初始化新后端项目:一次性渲染熟悉的目录结构、common 通用基建(视图/Service/认证中间件/utils)、内嵌 stdkit/ 基架、质量门禁(Makefile + pre-commit)、docs 与 AGENTS.md 骨架,并按需生成业务 app。Use when 用户要新建 Django 项目、初始化 Django 后端、按 wework 结构/个人标准搭项目骨架、初始化 Django 4.2 后端、生成 csl 流水线可接入的新 Django 仓库。存量项目改造不适用(走 /csl-init-project 或 django-personal-development);Django 5.x 基线是另一套模板,不归本技能。
---

# csl-django42-project-init — Django 项目基线初始化

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

脚本输出渲染 manifest 与后续步骤。内置保障:保留名守卫(配置包不得撞 `apps/common/stdkit` 等根目录,业务 app 不得撞 `db/base/tasks` 且查重);`settings_local.py` 自动生成(同 example 占位值,已 gitignore);业务 app 路由自动挂进配置包 urls.py 锚点**并自动注册进 INSTALLED_APPS**(漏注册则 makemigrations 无视其模型)。渲染后自查:退出码 0、无占位符残留(脚本内置全文件扫描)。

stdkit 基架随模板自带(v1.2.6 快照):逐字拷入项目根 `stdkit/` 并随项目仓库分发(克隆即得,不依赖私服安装);传递依赖固化在 requirements.txt 末段;pre-commit 对其只查不改,保持与模板字节一致。用户明确不要时传 `--no-stdkit`。

### 3. 初始化 git(不提交)

目标无 `.git` 时 `git init`;**不执行任何 commit/push**(提交需用户明确指示)。

### 4. 生成项目 AGENTS.md 并呈报

模板已含按脚手架事实写好的 `AGENTS.md`(工作原则/质量门禁/项目约定/常用命令/BUGLOG)。按本项目实际(业务 app 清单、集成项)修订后呈报用户确认;用户也可改走 `/csl-init-project` 扫描式生成。两者不并用。

### 5. 运行时验证(用户授权后执行冒烟)

```bash
python3.12 -m venv .venv && make install-dev
.venv/bin/python manage.py check
make migrate && make dev
# 冒烟:免认证 GET /api/v1/base/config 返回 200 JSON 信封;
#      无 token GET /api/v1/<业务app>/demo 返回 401(验证 JWT 中间件正向拦截)
```

未获授权时,停在静态验证(py_compile 全部 .py 含 `stdkit/` + `bash -n scripts/local_quality_gate.sh` + `bash -n scripts/git-hooks/pre-push`),并在交付报告中明确列为阻塞项。

### 5b. 默认安装测试沙盒(交接 django-test-sandbox)

轨道 A(nodb)开箱即用;轨道 B(`@pytest.mark.django_db`)因基线 `Configs.value` 为 ArrayField 在 sqlite 失败——**默认按 django-test-sandbox 技能流程安装沙盒**(盘点 PG 字段 → 落四文件 → 跑探针 → AGENTS.md 三区声明)。该技能不可用时,明确报告轨道 B 受限及原因,不悄悄降级。

### 6. 交付报告

包含:渲染文件数与关键路径;git/AGENTS.md 处置;已执行的验证命令及结果;阻塞项(token、沙盒未装);下一步建议(`make check`、装 django-test-sandbox、按 coding-conventions 写首批业务代码)。

## 边界

- 只初始化新项目;存量项目扫描用 `/csl-init-project`,日常开发规范用 `django-personal-development`。
- 模板是**脱敏基线**:不含真实密钥与令牌;`SECRET_KEY`/`JWT_SECRET` 均为占位值,生产在 settings_local.py 覆盖。
- 不自动安装依赖、不跑 migrate、不提交推送——除非用户明确授权。
- 基线不含业务集成(企微/钉钉/CRM/up_center/薪酬等);需要时按 `references/project-blueprint.md` 的可选扩展清单对照 wework 源搬移,不凭记忆重写。
- wework/backend 参考源不可见时本技能仍可完整工作(模板自包含);不要在运行时读取参考源路径。

## 质量标准

- scaffold.py 退出码 0,内置占位符残留检查(全文件含 Makefile 等无后缀文件)通过,渲染产物全部 `py_compile` 通过(含 `stdkit/`)。
- 保留名守卫生效:`--conf common`、`--app db`、重复 app 均被拒绝且退出码 2。
- `stdkit/` 存在、与模板逐字一致、且未被 .gitignore 排除(随仓库分发);requirements.txt 末段含 stdkit 传递依赖。
- `make install-hooks` 可执行:scripts/git-hooks/pre-push 存在且 `bash -n` 通过。
- settings_local.py 自动生成,pytest 无需手工前置步骤即可跑轨道 A。
- 若执行了运行时验证:`manage.py check` 通过、`/api/v1/base/config` 200、受保护路由无 token 401、`makemigrations` 能看到业务 app 的模型(INSTALLED_APPS 注册生效)。
- 交付报告六要素齐全(文件数/路径、git 与 AGENTS.md 处置、验证证据、阻塞项、下一步)。
