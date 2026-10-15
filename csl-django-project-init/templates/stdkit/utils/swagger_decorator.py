"""
Swagger 文档自定义命名装饰器

用于在 Django View 类的方法上标注自定义的接口名和目录名，
Swagger 生成器（AST 静态分析）会自动读取这些信息。

用法示例：

    from swagger_decorator import swagger

    class UserView(View):

        @swagger(summary="查询用户列表", tag="用户管理")
        def get(self, request):
            ...

        @swagger(summary="新增用户", tag="用户管理")
        def post(self, request):
            ...

        @swagger(summary="删除用户")
        def delete(self, request):
            ...

说明：
    summary (str): 自定义接口名（显示在 Apifox 接口列表中的名称）
    tag     (str): 自定义目录名（显示在 Apifox 中的分组名）

注意：
    - 这是一个纯标记装饰器，运行时不做任何操作，仅用于静态分析
    - 参数都是可选的，不传则使用自动生成的默认值
"""

import functools
import inspect


def swagger(summary: str = "", tag: str = "") -> callable:
    """
    标记接口的自定义名称和目录名。

    Args:
        summary: 接口名（可选）
        tag:     目录名（可选）

    Returns:
        原函数（这是一个纯标记装饰器，不做任何操作）
    """
    def decorator(func):
        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await func(*args, **kwargs)
            return async_wrapper

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator
