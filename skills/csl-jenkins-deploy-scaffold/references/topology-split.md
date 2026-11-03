# 分镜像方案：按发布单元适配

可选示例，不是必须复制的模板，也不依赖外部项目。核心流程见 SKILL.md；只有已根据项目约束选择分镜像时才需要本文。下述路径和服务名均为假设，未做真实项目运行验证。

## 选择依据

分镜像适用于独立发布、独立伸缩、不同运行时、安全隔离，或独立静态服务器有明确收益的项目。前端 history 路由本身不是理由；现有后端若能正确托管静态文件和深链回退，同样可以单镜像。

先列真实单元：

| 假设单元 | 镜像与入口 | 发布关系 |
| --- | --- | --- |
| 静态 console | 构建产物交给静态服务器；生产镜像不运行 Vite dev server | 可独立更新 |
| API | 项目已确认的生产入口 | 与前端用 API 契约兼容 |
| worker | 可复用 API 镜像，切换已确认的工作进程命令 | 按队列、资源和迁移约束协调 |
| SSR web | 服务端运行镜像，不用静态站点镜像代替 | 可独立伸缩，核对会话与代理 |

不要把每个目录都变成镜像，也不要为了减少镜像数把多个服务用 shell 后台进程拼在一起。

## 源码位置与构建上下文

假设项目使用 `services/console`、`services/api` 和 `packages/shared`：

- 前端引用 shared 时，构建上下文通常需要仓库根；Dockerfile 可留在 `services/console/Dockerfile`。
- 对应命令形态为 `docker build -f services/console/Dockerfile -t "$WEB_IMAGE" .`；此命令只是例子，路径来自项目后才可使用。
- `.dockerignore` 的排除规则相对于上下文；别把根锁文件或 shared 包一起排掉。
- 若实际为独立仓库，每个仓库可独立构建；跨仓组合须固定版本输入，不靠隐式访问相邻本机目录。
- Jenkins 固定根 `make env all` 时加委托入口，传递上下文与镜像参数；没有该契约时不强制根 Dockerfile 或 Makefile。

每个实际单元都记录源码、上下文、Dockerfile、构建命令、产物和生产入口；缺哪个就核实哪个。

## Jenkins 兼容与缓存

所有实际被 `make env all` 调用的 Makefile 必须有 `env`。新 `env` 只做不含秘密的预检或摘要；不能以“缓存准备”为名隐式安装并推送依赖镜像。

构建、推送、部署按真实 CI 契约拆阶段。已有 `all` 包含 push 时保留并写明副作用；验证时先审阅 Makefile，再干跑，不能直接执行该入口。

锁文件、多阶段依赖层及构建器缓存通常已够用。独立依赖基础镜像仅在复用收益明确时引入，同时定义锁文件/工具链变化后的失效规则、版本关联和发布授权，不能把它当作分镜像的必需结构。

新依赖图中推送依赖构建完成；不要用 `all: image push` 作为顺序保证，`make -j` 可能并行。缺关键参数时失败，不默默回退到私人镜像库或 `latest`。

## 生产入口与配置

每个镜像应有独立可运行的生产命令；同镜像不同角色可由部署层显式覆盖。不要生成没有 CMD、又要求用户自行猜启动命令的镜像。

- Node：从生产脚本与产物确认运行方式；依赖装法由锁文件/workspace 决定。
- Python：确认实际 WSGI/ASGI 模块、服务器和依赖；不强制特定框架或模块名。
- 其他语言：沿用项目已有可复现打包与运行契约，不从本示例类推命令。
- 公共配置与秘密分开；真实秘密不放 ConfigMap、镜像或变量示例。配置文件挂载只有应用实际读取时才有作用。
- 静态前端的 API 地址通常是构建期公开输入；若要运行时切换，必须有应用实际读取的配置机制。

## 静态前端路由示例

只有确认使用 nginx、产物位于示例 root、API 服务名为 `api` 且监听 8080、API 保留 `/api` 前缀时，以下片段才适用。监听与非 root 镜像的目录权限需另行验证。

```nginx
server {
    listen 8080;
    server_name _;
    root /usr/share/nginx/html;

    location = /api {
        proxy_pass http://api:8080;
    }

    location ^~ /api/ {
        proxy_pass http://api:8080;
    }

    # 仅当项目资源前缀确实为 /assets/；缺失资源返回 404。
    location ^~ /assets/ {
        try_files $uri =404;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

`proxy_pass` 是否带尾部 `/` 会影响路径替换，按真实 API 契约测试。其他资源目录、上传限制、WebSocket、转发头和超时按需补充，不从旧项目复制。

SSR 应请求 SSR 服务端，而不是把动态路由全部改写为 index.html。HTTPS 与 HTTP 环境分别核对安全头，不默认关闭 HSTS/CSP。

## Compose 与 Kubernetes 映射

| 需求 | Compose | Kubernetes |
| --- | --- | --- |
| 内部 API 通信 | 服务名与容器端口 | Service 与 targetPort |
| 对外入口 | 仅必要的 host ports 或已有代理 | 已有 Ingress/Gateway；无域名时评估其他入口 |
| 非敏感配置文件 | 生成并明确引用的只读文件/config | ConfigMap；subPath 更新行为需说明 |
| 秘密 | 已确认 secret/环境注入方案 | 已确认 Secret/外部秘密管理方案 |
| 持久数据 | 必要的 named volume/已有挂载 | PVC 等由存储约束决定，不预设共享 claim |
| 数据库迁移 | 显式单次命令或协调步骤 | CI 阶段/Job/GitOps 原有机制，确保串行 |
| 就绪与重试 | 真 healthcheck、健康依赖或客户端重试 | readiness；慢启动时 startupProbe |

Compose 不必把 API、数据库、缓存全部暴露到宿主。`depends_on` 不会替代运行期断线重试，容器 unhealthy 也不等于自动重启。

Kubernetes 使用目标支持的 API；新 Ingress 通常为 `networking.k8s.io/v1`，必须有正确 pathType 与后端 service 字段。不假设某个控制器的 rewrite 注解可跨环境复用，不擅改共享网关或另一个运维仓库。

## 验收

1. 每个镜像构建成功；独立发布单元引用正确的不可变版本。
2. 使用真实生产命令启动；API 健康信号、前端页面、真实资源和深链按预期工作。
3. `/api`、`/api/...`、缺失 API、缺失静态资源不被 SPA index.html 掩盖。
4. 独立更新前端不要求无必要的 API/数据库重启；worker 不产生重复迁移。
5. HTTP/TLS、跨域、WebSocket 等只验证项目实际需要的路径。
6. 未执行的构建、浏览器、集群或回滚验证列为未执行；片段可读不等于方案已运行。
