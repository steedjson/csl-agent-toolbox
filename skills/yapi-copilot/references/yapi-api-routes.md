# YApi 核心 REST API 路由速查

以 yapi-new.sugonup.com 为准（2026-11 实测）。其自带开放接口文档在 `/openapi-doc.html`。

## 1. 认证（token 优先）

- **项目 token（首选）**：绝大多数 `/api/*` 端点直接接受 `token` 参数 —— GET 拼 query（`?token=<t>&project_id=<id>`），POST 并入 JSON body。控制台端点与开放端点均适用（`/api/project/get`、`/api/interface/list_menu`、`/api/interface/save` 等已实测）。token 从项目「设置 → token 配置」获取。
- **Cookie 会话（备用）**：请求头 `Cookie: _yapi_token=<JWT_TOKEN>; _yapi_uid=<UID>`，凭证来自本地 Chrome 解密（`scripts/yapi_client.py` 自动处理）或环境变量 `YAPI_COOKIE`。
- 客户端解析顺序：`--token` / `YAPI_TOKEN` > `--cookie` / `YAPI_COOKIE` > Chrome 解密。

## 2. 核心读接口

| 动作 | 方法 | 路径 | 关键入参 | 说明 |
| :-- | :-- | :-- | :-- | :-- |
| 获取项目详情 | `GET` | `/api/project/get` | `id=<project_id>` | 返回项目基本信息及配置 |
| 获取分类及接口菜单 | `GET` | `/api/interface/list_menu` | `project_id=<project_id>` | 返回完整分类树及各分类下的接口简要列表 |
| 获取接口分类树 | `GET` | `/api/interface/get_cat_tree` | `project_id` | 分类树结构 |
| 获取菜单列表 | `GET` | `/api/interface/getCatMenu` | `project_id` | 菜单列表 |
| 获取单个接口详情 | `GET` | `/api/interface/get` | `id=<interface_id>` | 返回接口完整定义（包括 Query/Body/Headers/JSON-Schema） |
| 获取分类下接口列表 | `GET` | `/api/interface/list_cat` | `catid=<cat_id>&page=1&limit=20` | 分页拉取分类下的接口 |
| 获取接口列表数据 | `GET` | `/api/interface/list` | `project_id` + 分页 | 接口简要列表 |

## 3. 核心写接口

| 动作 | 方法 | 路径 | 请求体格式 | 说明 |
| :-- | :-- | :-- | :-- | :-- |
| 创建分类 | `POST` | `/api/interface/add_cat` | JSON: `{project_id, name, desc}` | 在指定项目中新建左侧菜单分类 |
| 创建接口 | `POST` | `/api/interface/add` | JSON: `{project_id, catid, title, path, method}` | 新建接口基本骨架（创建成功后返回 `_id`） |
| 新增或更新接口 | `POST` | `/api/interface/save` | JSON: 完整接口对象（带 `id` 更新，不带则新增） | **同步首选**：天然幂等 upsert，token 直连 |
| 更新接口定义 | `POST` | `/api/interface/up` | JSON: 接口完整对象 (含 `id`) | 保存请求参数、返回 JSON-Schema、状态及备注 |
| 服务端数据导入 | `POST` | `/api/open/import_data` | 见下 | 批量导入 swagger 等数据 |

### import_data 注意（本实例实测与官方老文档不一致）

官方老文档写 `x-www-form-urlencoded` 平铺参数，但本实例按 JSON 校验嵌套结构 `{"data": {"token", "type", ...}}`（缺字段时报「请求参数 data 应当有必需属性 type/token」）。`type` 取 `swagger` 等，`merge` 取 `normal`(普通) / `good`(智能合并) / `merge`(完全覆盖)。导入前先用小 payload 实测当前版本接受的形态。

## 4. 导出与测试

| 动作 | 方法 | 路径 | 关键入参 | 说明 |
| :-- | :-- | :-- | :-- | :-- |
| 导出数据 | `GET` | `/api/plugin/export` | `pid`(token 鉴权自动取归属项目), `type=markdown/json` | **更新前备份现状用**，默认 html |
| 导出 Swagger | `GET` | `/api/plugin/exportSwagger` | `type=OpenAPIV2` | 仅支持 OpenAPI 2.0 |
| 运行自动化测试 | `GET` | `/api/open/run_auto_test` | `id=<测试集合id>`, `mode=json/html` | 测试集合须属于 token 归属项目 |

## 5. JSON-Schema 最佳实践

在 YApi 中配置返回体或请求体为 JSON-Schema 时：
1. `res_body_type` 设为 `"json"`；
2. `res_body_is_json_schema` 设为 `true`；
3. `res_body` 必须为合法的 JSON-Schema 字符串，根对象遵循 draft-04 规范：
   ```json
   {
     "$schema": "http://json-schema.org/draft-04/schema#",
     "type": "object",
     "properties": {
       "code": {"type": "integer", "description": "状态码"},
       "msg": {"type": "string", "description": "消息"},
       "data": {"type": "object", "properties": {...}}
     },
     "required": ["code", "msg", "data"]
   }
   ```
