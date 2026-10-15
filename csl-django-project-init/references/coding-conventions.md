# 编码约定 — 初始化后写业务代码的基线规则

提炼自 wework/backend 的 AGENTS.md 与 `docs/development/项目规则.md`。初始化完成后的日常开发以项目 AGENTS.md 为准,本文是其展开与母版(修订项目 AGENTS.md「项目约定」时从这里取材)。

## 分层架构

```
URL(re_path, /api/v1/<app>/…)
  → View(common.views.View 子类,只做参数校验与编排)
    → Service(common.services.BaseService 子类,业务逻辑与数据组装)
      → Model(apps/db 模型,stdkit 基座)
```

- View 不写业务逻辑;Service 不直接返回 HTTP 响应;模型方法只封装单行级逻辑。
- 跨 app 复用逻辑放 `common/`;单 app 逻辑放该 app 的 `services.py`(大 app 按域拆 `admin_services/` 子包)。

## View 层

- 继承 `common.views.View`(DRF APIView 封装);免认证视图设 `verification_auth = False`。
- 参数校验用 `@method_decorator(define_params(Schema))`,Schema 继承 `stdkit.rest.forms.Schema/GetListSchema` + `fields`;校验后从 `request.cleaned_data` 取值。
- 统一返回 `stdkit.rest.response.JsonResponse`(success/error);异常抛 `stdkit.error.exceptions`(BadRequestException 等),中间件统一兜底。
- 列表导出继承 `ExportBaseView`:`params`(GET 参数名,顺序=位置参数)、`sheet_titles`、`_get_obj_list`、`_get_values`;**params 顺序必须与 `_get_obj_list` 签名一致**;大数据量自动走 Django-Q 异步(`LOCAL=True` 同步)。

## Service 层

- 继承 `common.services.BaseService`;构造传 request 自动解析 `tenant_id`。
- 多表写操作必须 `transaction.atomic`。
- 列表 name 组装(wrap_items_with_xxx_name)模式:先收集 id 批量查询建 map,再回填,避免 N+1。

## Model 层(硬约定)

- 继承 `DirtyFieldsMixin, stdkit.db.models.Model`。
- 主键 `uuid`(基类提供);时间字段 `add_datetime`/`update_datetime`(基类提供);软删除 `deleted_at`,`objects` 自动过滤有效记录,`objects_all` 含已删除。
- `Meta.db_table` 用统一前缀 `model_prefix`(项目初始化时定死);字段一律写 `db_comment`。
- 模型集中放 `apps/db/models.py`(或按域拆包后注册);业务枚举放 `apps/db/const.py`(TextChoices/IntegerChoices)。
- 金额字段 `DecimalField`;查询前确认真实关联路径,**不假设所有模型都有 tenant_id**。

## 路由

- API 前缀 `/api/v1/<app>/`;app 内 `urls.py` 用 `re_path`,视图路径不带尾斜杠(APPEND_SLASH=False)。
- 新 app 的 urls 挂到 `<conf>/urls.py`;新 app 加入 INSTALLED_APPS。

## 异步任务

- 任务函数放 `apps/tasks/`(或业务 app),收 plain 参数,不传 request/model 实例。
- `make worker`(qcluster)执行;定时任务经 Django-Q Schedule;`settings.LOCAL=True` 时导出同步执行。

## 测试

- pytest 设置模块 `<conf>.settings_test`(sqlite 内存);纯逻辑测试放 app `tests/nodb/`,ORM 语义测试加 `@pytest.mark.django_db` 放根 `tests/`。
- 新测试一律不连外部数据库;项目用 PG 专属字段时装 django-test-sandbox 沙盒。
- 测试数据按真实表结构构造(字段名/类型/关联一致),优先共享工厂函数。

## 质量门禁(命令固定)

```bash
make check          # 只读快查:变更文件 isort/black 检查 + Pylint errors-only + git diff --check
make verify TEST=<目标测试>   # 格式化 + lint + 目标 pytest + diff 检查(改 Python 文件后的标准门禁)
make verify-full    # 全量测试(高风险共享逻辑)
```

- 改模型/路由/中间件/设置另跑 `manage.py check`;改模型再跑 `makemigrations --check --dry-run`。
- 行宽 110,Black skip-string-normalization,isort profile=black(pyproject.toml 已固化)。

## 命名与注释

- 类 PascalCase;函数/变量 snake_case;常量 UPPER_SNAKE;文件小写下划线。
- 注释写"为什么";导入分三组(标准库/第三方/本地 apps.common.conf),组内字母序(isort 自动)。
- 中文注释与 db_comment 是项目惯例,保持一致。
