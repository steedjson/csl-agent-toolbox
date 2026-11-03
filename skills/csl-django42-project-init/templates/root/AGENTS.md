# AGENTS.md

本文件为 AI 编码智能体（ZCode 等）在此 Django 仓库中工作时提供指导。

## 工作原则

1. **证据优先**：没有命令输出、测试结果或可核对的源码证据，不得声称完成。
2. **歧义先调研**：选择实现方案前，先核对当前代码、调用方、下游消费者、测试和项目约束。
3. **最小完整变更**：避免无关重构，不引入没有明确收益的抽象；认为存在更简单方案或既有约定有害时，明确提出而不默默偏离。
4. **危险操作先确认**：生产部署、破坏性或无范围数据库写入、强制推送、硬重置和批量删除必须获得明确授权。
5. **实现与审查分离**：编辑完成后，从 Git 差异、调用方、消费者、边界条件和测试缺口角度独立复核。

## 工具路由

1. 存在 `.codegraph/` 索引时，优先使用 CodeGraph 获取源码、调用链和受影响测试。
2. 使用 `rg` 搜索字符串字面量、错误信息、配置、文档、模板。
3. 只读取已定位的源码区段。图谱结论仍需通过变更后的源码和真实测试验证。

## Python 质量门禁

修改 Python 文件后运行统一的变更文件门禁，并明确指定目标测试：

```bash
make verify TEST=<focused target>
```

该命令只对变更的 Python 文件执行 isort、Black 和错误级 Pylint，再运行目标 pytest、`git diff --check` 和 `git diff --stat`。`make check` 是不修改文件、不运行测试的快速检查。高风险共享逻辑先运行目标测试，再运行 `make verify-full` 完整测试。

修改模型、路由、中间件、Django 设置或 App 配置时额外运行 `.venv/bin/python manage.py check`；修改模型时再运行 `.venv/bin/python manage.py makemigrations --check --dry-run`。这些 Django 检查不进入每次 commit。

## 项目约定

- 技术栈：Django 4.2、Python 3.12、PostgreSQL、Redis、Django-Q、DRF 风格视图，以及私有基础库 `stdkit`（源码基架内嵌于根目录 `stdkit/`，随仓库分发、克隆即得，不依赖私服安装；传递依赖已列在 requirements.txt 末段）。`stdkit/` 不参与格式化与 lint（pre-commit 已排除），修改需回 csl-django42-project-init 技能模板同步。
- 业务应用位于 `apps/`，共享工具位于 `common/`，Django 配置位于 `__CONF_PACKAGE__/`。
- apps/ 应用地图：`db`（模型基座与共享模型）、`base`（登录态相关基础能力：上传/配置/任务结果）、`tasks`（Django-Q 异步任务，由 qcluster 执行）。
- `__CONF_PACKAGE__/settings_local.py` 保存数据库/Redis 等敏感配置且不入库，首次开发需自行创建；连不上数据库或 Redis 时先检查它。
- API 使用 `/api/v1/`；业务路由经各 app 的 `urls.py` 注册，再挂到 `__CONF_PACKAGE__/urls.py`。
- 视图继承 `common.views.View`，使用 `define_params` 校验参数，从 `request.cleaned_data` 读取数据，将业务逻辑委托给 Service，并返回 `JsonResponse`。
- Service 继承 `common.services.BaseService`；多表写操作使用 `transaction.atomic`，API 异常使用 `stdkit.error.exceptions`。
- 模型继承 `DirtyFieldsMixin` + `stdkit.db.models.Model`；表名前缀 `__TABLE_PREFIX__`（经 `db_table` 指定），字段注释用 `db_comment`。
- 模型主键为 `uuid`，不是 `id`。
- 有效记录使用 `deleted_at=0`；`objects` 自动过滤有效记录，`objects_all` 包含已删除记录。
- 时间字段为 `add_datetime` 和 `update_datetime`。
- 认证中间件根据 `verification_auth` 注入 `user_id`、`tenant_id` 和 `is_super`；JWT（PyJWT/HS256）在 `common/middlewares/request.py` 验证并缓存 Redis，免认证路径配置在 `settings.MISS_TOKEN_PATHS`。
- `ExportBaseView` 按 `params` 顺序位置传递 GET 参数；必须保持 `params` 顺序与 `_get_obj_list` 签名一致。大数据量经 Django-Q 异步导出（`LOCAL=True` 时同步执行），task_id 缓存防重复提交。

## 常用命令

```bash
.venv/bin/pytest -q
.venv/bin/python manage.py check
.venv/bin/python manage.py showmigrations
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python manage.py runserver
.venv/bin/python manage.py qcluster
```

不得仅为验证而执行迁移、初始化命令、Docker 发布/推送目标或生产集成。

## 交付报告

每次实现交付必须包含：变更文件；行为变化；实际执行的验证命令及结果；跳过项和阻塞原因；剩余风险；回滚注意事项。

详细架构与领域资料统一从 `docs/README.md` 进入。

## BUGLOG — 已知坑与修法(跨 agent 共享)

- 位置:`docs/BUGLOG/<当前分支>.md`(按分支一文件;分支名 `/`→`-`;无 git 用 `default.md`)
- **读的时机**:修改函数签名/对外行为前;审查 diff 前;fix 类提交前。通读最近 30 条及命中模块条目
- **写的时机**:修复缺陷并确认根因后,立即追加一条(最新在上):

  ```md
  ## [YYYY-MM-DD][模块] 简述
  - 现象: / - 根因: / - 修法: / - 关联: commit 或 文件:行号
  - 复发: N 次 · 最近 日期(可选) / - 教训: 一句话
  ```

- **脱敏红线**:禁止客户名/真实姓名/内网地址/凭证,用 `<占位符>` 替代
- 文件不存在则先创建标准头;条目只追加不删改
