"""Django-Q 异步任务定义。

约定:
- 异步任务函数收 plain 参数(django_q 序列化限制,不传 request/model 实例);
- 大数据量导出直接继承 common.views.ExportBaseView,不在这里重复实现;
- 任务由 `make worker`(manage.py qcluster)执行;settings.LOCAL=True 时导出同步执行。
"""

import logging

logger = logging.getLogger("aps")


def demo_job(foo: str):
    """示例异步任务:make worker 启动后经 django_q.tasks.async_task(demo_job, ...) 调用"""
    logger.info(f"demo_job start: {foo}")
    return {"foo": foo}
