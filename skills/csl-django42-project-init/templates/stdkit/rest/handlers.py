import sys
import traceback

from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import exception_handler

from stdkit.error.exceptions import MyException
from stdkit.rest.sentry_init import capture_exception


def _exception_message(detail):
    if detail is None:
        return ""
    if isinstance(detail, dict):
        parts = ["%s: %s" % (key, _exception_message(value)) for key, value in detail.items()]
        return " | ".join(parts)
    if isinstance(detail, (list, tuple)):
        return "; ".join(_exception_message(item) for item in detail)
    return str(detail)


class JsonError(Response):
    """
    An HttpResponse that renders its content into JSON.
    """

    def __init__(self, error_string, code=400, http_status=None, **kwargs):
        data = {
            "error": kwargs.pop("error", error_string or ""),
            "code": code,
            "msg": error_string or "操作失败",
            "data": None,
        }
        data.update(kwargs)
        super(JsonError, self).__init__(
            data=data,
            status=http_status,
            content_type="application/json",
        )


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if isinstance(exc, MyException):
        code = getattr(exc, "code", 400)
        http_status = code if code in (401, 403) else None
        return JsonError(_exception_message(exc.detail), code=code, http_status=http_status)

    if response is None:
        if exc is not None:
            capture_exception(exc)
            if getattr(settings, "DEBUG", False):
                traceback.print_exc(file=sys.stderr)
                return JsonError("系统内部错误", code=500, error=str(exc))
            return JsonError("系统内部错误", code=500, error="")
        return None

    status_code = getattr(response, "status_code", 500)
    if status_code >= 500:
        capture_exception(exc)
        return JsonError("系统内部错误", code=status_code, http_status=status_code, error="")

    return JsonError(
        _exception_message(getattr(response, "data", exc)),
        code=status_code,
        http_status=status_code,
    )
