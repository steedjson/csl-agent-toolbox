# 项目蓝图 — wework/backend 基线结构映射

模板从 wework/backend(`~/Obj/sugon/wework/backend`)提炼。本文记录:渲染产物每部分的职责、与参考源的对应关系、以及基线**有意未含**的可选扩展。参考源不可见时,以本文为准理解结构。

## 渲染产物与参考源映射

| 模板产物 | 参考源 | 裁剪说明 |
| --- | --- | --- |
| `<conf>/settings.py` | `backend/settings.py` | 去 raven_compat/sorl INSTALLED_APPS 与业务 app;密钥换占位值;保留 stdkit 中间件链/DRF/JWT/日志分层 |
| `<conf>/settings_local.example.py` | `backend/settings_local.example.py` | 去 QYWX/DINGTALK/PHEKDA/CRM 业务配置,留追加位 |
| `<conf>/settings_test.py` | (新增最小版) | sqlite :memory: + locmem 缓存;轨道 B 因基线 ArrayField 受限,默认交接 django-test-sandbox 安装完整垫片(其 settings_test 会覆盖本文件) |
| `<conf>/urls.py` | `backend/urls.py` | 只挂 base/tasks;业务路由随 app 增加 |
| `common/views.py` | `common/views.py` | 保留 View/ExportBaseView/admin_validator;去 CRMView/crm_admin_validator(CRM 集成) |
| `common/services.py` | `common/services.py` | 只留 BaseService 核心(tenant_id 解析/get_configs)+ DataService;去 CRM name-wrap 方法与菜单树 |
| `common/middlewares/request.py` | `common/middlewares/request.py` | 保留 JWT admin 认证 + 会话重建 + 统一异常响应;去 up_center 统一认证与 crm_validate |
| `common/utils.py` | `common/utils.py` | **逐字保留**(通用工具函数全集) |
| `apps/db/models.py` | `apps/db/models.py`(6154 行) | 只留基座:Tenant/ConfigType/Configs/Role/Admin/AOperationLog/Demo + 模型约定头注释 |
| `apps/db/const.py` | `apps/db/const.py` | 只留 ModelOperatioChoices/OperationType;业务枚举随业务加 |
| `apps/base/` | `apps/base/` | 保留上传(普通/富文本/分片)/配置/Q任务结果视图;去 Region/Kkfile/Mapqq/缩略图/JsapiTicket/部门用户/承接主体 |
| `apps/tasks/` | `apps/tasks/` | 骨架:apps.py + 空 urls + jobs.py 示例;业务任务随业务加 |
| `Makefile` + `scripts/local_quality_gate.sh` | 同名文件 | 镜像名参数化;质量门禁逐字保留(format/lint/check/verify/full) |
| `pyproject.toml` / `pytest.ini` / `.pre-commit-config.yaml` / `.editorconfig` | 同名文件 | known_first_party/DJANGO_SETTINGS_MODULE 参数化,其余一致 |
| `requirements*.txt` | 同名文件 | 三段式:核心链路(E3 实测子集)→ stdkit git 依赖已移除、其传递依赖(v1.2.6 pyproject 全集,去重后 13 项,钉版与 stdkit 对齐)→ 按需启用段(weasyprint/sorl/chinesecalendar 等,默认注释) |
| `scripts/git-hooks/pre-push` | wework 同名文件 | 逐字保留(只检查待推送提交的 whitespace,不含业务);`make install-hooks` 依赖它 |
| `stdkit/` | `~/Obj/stdlib/stdkit/src/stdkit`(v1.2.6 快照) | **进技能模板随基架分发**(`templates/stdkit/`),渲染时逐字拷入项目根、不做占位符替换;随项目仓库入库(克隆即得,不依赖私服安装),pre-commit 对其只查不改;`.zcodeignore` 排除以省 agent 上下文;升级方式见下方演进约定 |
| `Dockerfile` / `release.Dockerfile` / `compiler.py` | 同名文件 | 逐字保留(Cython 编译发布链) |
| `docs/` + 根 `AGENTS.md` + `README.md` | wework 对应文档 | 按脚手架事实重写的骨架 |

## 目录职责速查

```
<project>/
├── <conf>/            # Django 配置包:settings(基线)/settings_local(本机,不入库)/settings_test(pytest)
├── apps/
│   ├── db/            # 模型基座 + 共享模型(全项目模型约定的锚点)
│   ├── base/          # 基础能力:文件上传、系统配置、异步任务结果查询
│   └── tasks/         # Django-Q 异步任务容器(qcluster 执行)
├── common/            # 跨 app 共享:View/ExportBaseView、BaseService、JWT 认证中间件、utils
├── scripts/           # local_quality_gate.sh(make check/verify 的实现)
├── stdkit/            # 私有基础库源码基架(随仓库分发,克隆即得;.zcodeignore 排除以省 agent 上下文)
├── docs/              # development/ architecture/ planning/ BUGLOG/(组织约定见 docs/README.md)
├── data/              # 初始化数据与业务字典(按需)
├── statics/ media/ logs/   # 静态/媒体/日志(不入库)
└── Makefile           # 质量门禁与开发命令入口(make help)
```

## 可选扩展(基线未含,对照 wework 源搬移)

按需从参考源搬以下能力,**整块搬移并连带依赖**,不凭记忆重写:

| 能力 | 参考源位置 | 依赖 |
| --- | --- | --- |
| RBAC 菜单(Menu/RoleMenu + 菜单树 Service) | `apps/db/models.py` Menu/RoleMenu;`common/services.py` get_menu_tree/build_menu_tree | 前端配合 |
| 地区树(省市区) | `apps/db/models.py` Region/RegionZone;`apps/db/region_tree.py`;`apps/base/views/base.py` Region*;`data/region/` | 数据文件 |
| 统一认证平台(up_center) | `common/up_center.py`;中间件 up_center_validate;`UserBindUpCenter` 模型 | 外部平台 |
| 企业微信 | `common/qywx.py`;`apps/qywx/`;JsapiTicket 视图 | 企微配置 |
| 钉钉 | `common/dingtalk/`;`apps/ding/`;stdkit.dingtalk | 钉钉配置 |
| 管理后台业务 app | `apps/admin/`(views/ + admin_services/ + sp_handlers/ 按域拆分) | 按需裁剪 |
| sorl 缩略图 | SorlThumbnail 视图 + INSTALLED_APPS | sorl-thumbnail |
| kkfile 文件预览 | KkfileHtmlView + settings.KK_CONFIG | kkfile 服务 |
| 腾讯地图逆地理 | MapqqPosition + stdkit.map | mapqq key |
| Excel 导入解析 | `common/excel.py` | openpyxl/xlrd |
| 短信 | `common/mc_sms.py` | 阿里云 |
| 登录/租户管理完整流 | `apps/base/views/base.py` 相关节选 + admin 域 | — |

## 演进约定

基线升级(如 stdkit 版本、质量门禁调整)时:先改本技能 `templates/`,再跑一次 scaffold 到临时目录做 py_compile + 残留检查,通过后才算模板更新完成。模板与参考源的偏离必须记录在上表「裁剪说明」列。

stdkit 升级专则:从 stdkit 仓库 `src/stdkit` 重新整树拷贝覆盖 `templates/stdkit/`(清掉 `__pycache__`),并把新版 pyproject 的传递依赖差异同步进 `templates/root/requirements.txt` 末段、更新本文件版本号标注——两处必须一起改。
