---
name: django-test-sandbox
description: 把实测验证过的 Django 内存测试沙盒(SQLite :memory: + 禁迁移 + PG 字段建表垫片 + 探针门禁)安装到目标 Django 项目并完成验证。Use when 用户说"给这个 Django 项目上测试沙盒 / 装 django-test-sandbox / 装内存测试沙盒 / Django 沙盒安装"。
---

# Django 测试沙盒安装(实测版)

给 Django 项目落地无外部依赖的测试沙盒:纯逻辑测试(轨道 A)不连库,ORM/查询语义测试(轨道 B)跑内存 SQLite 真实执行。本流程的每个文件都在 Django 4.2.16 + pytest-django 4.9 + pytest 8.3 上实测跑通过(2026-10,phekda 首跑)。

## 铁律(不可协商)

1. **唯一正确架构是独立测试设置模块**。严禁任何"导入后改 settings"的劫持——Django 模型类定义阶段就会访问 `connection.ops`(`django/db/models/options.py` 的 db_table 处理),`django.setup()` 导入 models 时连接包装已按生产配置创建缓存,事后改 `settings.DATABASES` 无效(Django 建测试库只改包装对象、不重读 settings)。这是实测结论,不要再试。
2. **探针先行,红则分诊**。探针任何一条红 = 沙盒不成立:修复垫片,或止损退出。严禁删探针、改弱断言换绿灯。探针在验证过程中真实抓到过两次垫片失效,它不是仪式。
3. **只新增文件 + 追加配置**。不碰业务代码、不动存量测试、不自动连真库。真库相关的验证命令只打印,执行需用户明确指示。
4. **Django 版本先对表**。垫片在 4.2.16 实测;其他版本(尤其 5.x)先跑探针再采信,大版本升级后必须重跑探针。

## 工作流

### Step 0 前置检查

- `git status --porcelain` 记录脏文件清单(只记录,不处理,汇报时带上);
- 根目录已有 conftest.py → 停下向用户说明合并方案再动;已有 pytest.ini → 按合并方案处理:保留原有 `python_files`/`markers`/`testpaths` 等项,`DJANGO_SETTINGS_MODULE` 改指测试设置模块,`addopts` 加 `--no-migrations`,`testpaths` 追加根 `tests`;
- 盘点目录级 conftest 两类危险形态(模板已内置对应防御,此处为确认与告知):
  - **autouse db 夹具**(如 `enable_db_access(db)`)→ 其下所有用例默认跳过(过滤器接管);
  - **实例短路 create_test_db**("直连开发库")→ 建表会被跳过,防御夹具在首个测试前弹掉实例补丁;
- 确认 Django 版本、venv 路径、settings 布局(base 模块、local 覆盖链如何挂载)。

### Step 1 盘点

```bash
rg -l "ArrayField|HStoreField|RangeField|GinIndex|BrinIndex|ExclusionConstraint" apps/ common/ -g '!migrations'
rg -n "__contains|__overlap|SearchVector|ArrayAgg|StringAgg|RawSQL|\.extra\(|select_for_update|distinct\(['\"]" apps/ common/ -g '!migrations' -g '!*tests*'
```

盘点结论决定三件事:
- **自定义 PG 字段子类**:读其源码,若只覆写 `__init__`/默认值 → 继承垫片补丁,无需处理;若覆写了 `db_type`/`get_db_prep_value`/`from_db_value`/`get_placeholder` → 需在 conftest 对该子类追加补丁;
- **Selector Mock 清单**:第二条 rg 命中的文件逐个列出,交给用户(这是业务改造工作清单,skill 不代改业务代码);
- **探针 Layer-2 模型**:从盘点结果里选 managed=True、字段简单、带 PG 字段的真实模型(注意 `managed = False` 的模型 syncdb 不建表,不能当探针目标)。

### Step 2 落四个文件

模板在 `templates/`,按 `<PLACEHOLDER>` 适配:
- `settings_test.py.tpl` → 放到 Django settings 包内,`from <BASE>.settings import *` 后覆盖 DATABASES/CACHES/EMAIL/PASSWORD_HASHERS。项目用 celery 才保留 EAGER 两行;用 django-q 的项目删掉 celery 行(q 任务在沙盒里只入队不执行,测试断言入队不断言执行);
- `conftest.py` → pytest 根落地,替换跳过原因里唯一的 `<真实设置模块>` 占位符,其余勿改(含五项机制:响亮门禁、字段垫片、实例绑定清理、存量连库跳过过滤器、create_test_db 实例补丁防御;后两项在干净项目空转,无副作用);
- `pytest.ini.tpl` → pytest 根,填 DJANGO_SETTINGS_MODULE 为测试设置模块;已有 pytest.ini 时按 Step 0 合并方案改写;`testpaths` 指向沙盒测试区(新建根 `tests/` + 原有收集范围);
- `test_sandbox_probes.py.tpl` → 根 `tests/`,Layer-1 通用照抄,Layer-2 换成 Step 1 选出的真实模型。
- 建议项:若 Step 0 发现祖先级 autouse db 夹具,提示用户给各 nodb 目录加 `django_db_blocker.block()` 的 autouse 上锁 conftest(wework 范式),防 nodb 用例意外触碰 ORM。

venv 缺 pytest 时:`pip install pytest pytest-django`(pytest-django ≥ 4.3)。

### Step 3 跑探针

```bash
pytest tests/test_sandbox_probes.py -q
```

全绿 → Step 4。红 → 分诊:多半是垫片漏形态(新字段类型/索引形态/子类覆写),补垫片重跑;同一阻塞反复出现 → 止损退出并汇报。

### Step 4 项目 AGENTS.md 追加三区声明

用模板尾部给出的声明段(真实可执行区 / 失真静默区 / 语法不支持区 + 轨道约定 + 出口命令)。只追加,不改既有内容。

### Step 4.5(可选)接管 manage.py test 入口

适用判据:项目历史文档/CI/习惯中大量引用 `manage.py test`(用 `rg -l "manage\.py test"` 盘点),值得收敛旧入口时才装;引用寥寥可跳过。

- 模板 `templates/manage_test_override.py.tpl`,填 `<PYTEST_CMD>` 与 `<REAL_SETTINGS_MODULE>`,落到任一已注册 app 的 `management/commands/test.py`(优先选已有 commands 目录的 app);
- 无参调用委托 pytest 沙盒并透传退出码;带参调用响亮失败给指引,不做点路径误翻译;
- 已知坑:子进程会继承 manage.py setdefault 的 `DJANGO_SETTINGS_MODULE`,必须从子进程环境清掉,否则压过 pytest.ini、被 conftest 门禁拦下(模板已处理,含注释);
- 装完必须验证两种形态:无参 → 探针绿 + exit 0;带参 → 指引 + exit 1。AGENTS.md 声明同步改写(原"manage.py test 流程不动"的表述作废)。

### Step 5 验收(三条硬标准)

1. 探针在目标仓库全绿(逐条列出);
2. 存量测试出口就绪:项目原有运行方式不受影响,如需 pytest 侧出口,打印 `DJANGO_TEST_SANDBOX=0 pytest --ds=<真实设置模块> --migrations <路径>` 供用户显式执行;装了 Step 4.5 接管时,真库出口以接管命令指引里的为准;
3. 汇报:新增文件清单、探针结果原文、Selector Mock 清单、脏文件记录、回滚方式。

## 边界

- 不迁移、不修改任何存量测试;新轨道 A 测试放项目既有 nodb 约定处,新轨道 B 测试放根 `tests/`;
- 不处理 CI 接线以外的 DevOps(接 CI 由用户另行指示);
- 失真区清单(排他约束剥离、select_for_update 静默空操作、LIKE 大小写、中文 collation)写进 AGENTS.md 后即为项目契约,sandbox 内禁止断言这些行为。

## 质量标准

一次安装合格的判定,必须拿到全部三条证据:

1. 探针套件在目标仓库全绿(附结果原文,含耗时);
2. 存量测试运行方式零影响或明确跳过:存量连库用例默认显式 skip(带出口命令)属预期行为,须与"沙盒致败"区分;
3. 交付清单完整:新增文件、AGENTS.md 追加段、Selector Mock 工作清单、脏文件记录、回滚步骤。

失败分流铁律:全量跑出现存量用例失败时,先在真实设置下复跑该用例
(`DJANGO_TEST_SANDBOX=0 pytest --ds=<真实设置模块> <路径>`,不连库的用例
不会碰真库)——真实设置下同样失败的,是存量既有问题,如实上报不属于
本次安装;真实设置下能过、沙盒下挂的,才是沙盒致败,必须修垫片。

回归纪律:Django 大版本升级、新增 PG 字段类型/索引形态、conftest 改动,三者任一发生都必须重跑探针;探针红时严禁通过删探针/弱化断言来恢复绿灯——这条本身就是 checklist 第一项。

## 回滚

删除新增的 4-5 个文件(settings_test / conftest / pytest.ini / tests/;可选接管命令为其一)+ 还原 AGENTS.md 追加段。零业务代码改动,回滚即干净。
