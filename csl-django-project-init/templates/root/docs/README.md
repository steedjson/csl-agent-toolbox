# __PROJECT_NAME__ 文档中心

统一文档入口。只维护索引,内容放各子目录。

## 目录

| 目录 | 职责 |
| --- | --- |
| `development/` | 开发规范:项目规则、安全指南、hooks 指南 |
| `architecture/` | 架构:overview、模块说明、图示 |
| `planning/` | 需求规划:按最细业务功能模块一文件夹,见 planning/README.md |
| `BUGLOG/` | 跨 agent 共享坑与修法,按分支一文件,见根 AGENTS.md |

## 维护规则

1. 新增或移动文档后同步更新本索引。
2. 功能规划文档(需求定稿/开发规划)放 `planning/<功能文件夹>/`,组织约定见 `planning/README.md`。
3. 跨功能 TODO 放 `planning/TODOS.md`,不散落。
