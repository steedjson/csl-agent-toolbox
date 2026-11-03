import functools
from stdkit.rest.response import JsonResponse
from marshmallow import ValidationError, Schema
from inspect import iscoroutinefunction
import json


def _to_dict(data):
    if data is None:
        return {}
    if hasattr(data, "dict"):
        return data.dict()
    return dict(data)


def _get_request(args):
    for arg in args:
        if hasattr(arg, "method") and (hasattr(arg, "GET") or hasattr(arg, "query_params")):
            return arg
    return None


def _get_body_params(request):
    data = getattr(request, "data", None)
    if data is not None:
        return _to_dict(data)

    if getattr(request, "method", "").upper() == "GET":
        return {}

    if getattr(request, "content_type", "") == "application/json":
        body = getattr(request, "body", b"")
        if not body:
            return {}
        loaded = json.loads(body)
        return loaded if isinstance(loaded, dict) else {}

    return _to_dict(getattr(request, "POST", None))


def _get_query_params(request):
    data = getattr(request, "query_params", None)
    if data is None:
        data = getattr(request, "GET", None)
    return _to_dict(data)


def _get_url_kwargs(request, kwargs):
    data = {}
    parser_context = getattr(request, "parser_context", None) or {}
    if isinstance(parser_context, dict):
        data.update(parser_context.get("kwargs") or {})
    data.update(kwargs)
    return data


def _get_request_params(request, kwargs):
    data = _get_body_params(request)
    data.update(_get_query_params(request))
    data.update(_get_url_kwargs(request, kwargs))
    return data


def define_params(schema_cls: Schema):
    def decorator(view_func):
        # 注入 schema 信息，方便脚本直接读取，不用翻闭包
        view_func._marshmallow_schema = schema_cls
        is_async = iscoroutinefunction(view_func)

        def _error_response(err):
            if isinstance(err, json.JSONDecodeError):
                return JsonResponse.error(message="请求体不是合法 JSON", code=400)
            return JsonResponse.error(message=format_msg(err.messages), code=400)

        @functools.wraps(view_func)
        async def async_wrapped_view(*args, **kwargs):
            request = _get_request(args)
            # 找不到请求对象时无从校验参数，直接调用被装饰函数（不注入 cleaned_data）
            if request is not None:
                try:
                    setattr(request, "cleaned_data", schema_cls().load(_get_request_params(request, kwargs)))
                except (ValidationError, json.JSONDecodeError) as err:
                    return _error_response(err)
            return await view_func(*args, **kwargs)

        @functools.wraps(view_func)
        def sync_wrapped_view(*args, **kwargs):
            request = _get_request(args)
            # 找不到请求对象时无从校验参数，直接调用被装饰函数（不注入 cleaned_data）
            if request is not None:
                try:
                    setattr(request, "cleaned_data", schema_cls().load(_get_request_params(request, kwargs)))
                except (ValidationError, json.JSONDecodeError) as err:
                    return _error_response(err)
            return view_func(*args, **kwargs)

        return async_wrapped_view if is_async else sync_wrapped_view
    return decorator

def format_msg(messages):
    if messages is None:
        return ""
    if isinstance(messages, dict):
        parts = []
        for key, value in messages.items():
            formatted = format_msg(value)
            parts.append("%s: %s" % (key, formatted) if formatted else str(key))
        return " | ".join(parts)
    if isinstance(messages, (list, tuple)):
        parts = []
        for item in messages:
            if isinstance(item, (dict, list, tuple)):
                parts.append(format_msg(item))
            else:
                parts.append(str(item))
        return "; ".join(part for part in parts if part)
    return str(messages)

def add_schedule_task(task_list, name, cron, schedule_type):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        # 将任务信息附加到函数对象上
        wrapper.task_metadata = {
            "name": name,
            "cron": cron,
            "type": schedule_type,
        }

        # 添加到已注册任务列表
        task_list.append(wrapper)

        return wrapper

    return decorator
