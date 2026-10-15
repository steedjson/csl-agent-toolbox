# 架构总览

(项目落地后补充:模块图、调用链、外部集成。)

## 基线架构

- 分层:View(common.views.View + define_params 参数校验)→ Service(common.services.BaseService)→ Model(stdkit 基座,uuid 主键 + 软删除)。
- 认证:JWT(HS256)经 `common/middlewares/request.py`,会话缓存 Redis,可按表重建。
- 异步:Django-Q,`apps/tasks` 容器 + `ExportBaseView` 通用异步导出。
