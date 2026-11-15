---
name: yapi-copilot
description: Manage and sync YApi interface documents (categories, APIs, JSON-Schema request/response contracts) directly via YApi REST APIs with zero UI clicking and automated local Chrome cookie or token authentication. Use when the user asks to create, update, query, diff, or document API interfaces on YApi, sync backend code (Django, FastAPI, Spring, etc.) to YApi, or manage YApi projects and categories.
---

# YApi Copilot

通过 YApi 后台原生 REST API 自动化维护接口文档，替代脆弱易错的浏览器网页点选。鉴权优先用项目 token（`--token` / `YAPI_TOKEN`），无 token 时回退自动解密本地 Chrome 已登录凭证。

## 核心工作流

### 1. 鉴权与连通性验证

项目 token 首选（YApi 项目「设置 → token 配置」获取，控制台端点与开放端点均直连可用）；无 token 再走 Chrome 凭证（`YAPI_COOKIE`）：

```bash
python3 scripts/yapi_client.py auth-check [--url <YAPI_BASE_URL>] --token <PROJECT_TOKEN>
```

如未提供 `--url`，默认使用当前企业 YApi 域名（yapi-new.sugonup.com）。该实例自带开放接口文档：`/openapi-doc.html`。

### 2. 检索现有项目与分类

在创建或修改前，先拉取项目树避免重复建类或接口冲突；覆盖性变更前用 `/api/plugin/export?type=json` 备份现状：

```bash
# 查询项目分类及接口列表
python3 scripts/yapi_client.py list-menu --project-id <PROJECT_ID> --token <PROJECT_TOKEN>
```

### 3. 创建分类与接口（支持层级）

YApi 分类支持嵌套（`add_cat` 传 `parent_id`，`get_cat_tree` 读树，`del_category(catid)` 删空分类）。同步 OpenAPI 文档时的层级约定：

1. **默认规则**：文档 `info.title` 为根分类，每个 tag 一个子分类，接口按其 tag 归位；
2. **项目定制**：源文档/URL 模块有更准确的目录树时（如 tag 描述或前端菜单），用显式映射表 `{tag: (祖先链, 叶子名)}` 逐级建分类，未映射的 tag 落根分类兜底；
3. **幂等**：分类按 `(parent_id, name)` 匹配，接口按 `(path, method)` 匹配带 `id` 更新；
4. 重构分类树后，把腾空的旧分类自底向上 `del_category` 清掉。

同步已有接口定义优先用幂等的 `POST /api/interface/save`（带 `id` 更新，不带则新增）；注意 JSON 请求体 schema 必须放 `req_body_other` 字段（`req_body` 会被服务端静默丢弃），token 认证走 query 参数（body 内 token 部分端点不认）。

```bash
# 1. 创建分类（parent_id 建层级；catid 匹配已有分类则复用）
python3 scripts/yapi_client.py add-cat --project-id <PROJECT_ID> --name "分类名称" --token <PROJECT_TOKEN>

# 2. 调用 Python 客户端（save_interface upsert / cat_map 定层级）进行增量更新
```

批量导入 Swagger 等数据用 `POST /api/open/import_data`，注意本实例校验嵌套 `{"data": {token, type, ...}}` 结构（与官方老文档的平铺表单不一致），导入前先小 payload 实测。

### 4. 增量更新原则（严禁覆盖破坏历史契约）

在调用 `POST /api/interface/up` 更新接口时，必须遵循以下契约保护规则：
1. **先读后改**：通过 `GET /api/interface/get?id=<ID>` 获取线上现有完整数据对象；
2. **只增不删**：保留线上已有字段与备注，仅在 `properties`、`req_query` 或 `req_body_other` 中增量合入新字段；
3. **Draft-04 规范**：返回 JSON 体必须设为 `res_body_type="json"`、`res_body_is_json_schema=true`，根节点使用 `$schema: "http://json-schema.org/draft-04/schema#"`；
4. **准确标注**：明确标注字段类型（`string`, `integer`, `array`, `object`）、格式（如 `date`）、是否必填（`required` 数组）以及中文 `description`。

### 5. 校验与验证

更新完成后，必须再次请求 `GET /api/interface/get?id=<ID>` 回查确认 `errcode == 0` 且字段已成功生效。

## 资源索引

- `scripts/yapi_client.py`: 核心客户端 CLI 与 Python 类库。
- `references/yapi-api-routes.md`: YApi 官方原生 REST API 路由速查字典。
