import json
from typing import Any, Optional

from django.http import HttpResponse
from django.core.serializers.json import DjangoJSONEncoder


class JsonResponse(HttpResponse):
    """
    An HTTP response class that consumes data to be serialized to JSON.

    :param data: Data to be dumped into json. Unlike Django's ``JsonResponse``,
      non-``dict`` objects are allowed by default (``safe=False``).
    :param encoder: Should be an json encoder class. Defaults to
      ``django.core.serializers.json.DjangoJSONEncoder``.
    :param safe: Controls if only ``dict`` objects may be serialized. Defaults
      to ``False``.
    :param json_dumps_params: A dictionary of kwargs passed to json.dumps().
    """

    def __init__(
        self,
        data: Any,
        encoder: Any = DjangoJSONEncoder,
        safe: bool = False,
        json_dumps_params: Optional[dict] = None,
        **kwargs: Any
    ) -> None:
        if safe and not isinstance(data, dict):
            raise TypeError(
                "In order to allow non-dict objects to be serialized set the " "safe parameter to False."
            )
        if json_dumps_params is None:
            json_dumps_params = {}
        kwargs.setdefault("content_type", "application/json")
        data = json.dumps(data, cls=encoder, **json_dumps_params)
        super(JsonResponse, self).__init__(content=data, **kwargs)

    @staticmethod
    def success(data=None, message="", op_msg=""):
        if data is None:
            data = {}
        if not message:
            message = "操作成功"
        if op_msg:
            return JsonResponse({"code": 200, "msg": message, "data": data, "op_msg": op_msg})
        return JsonResponse({"code": 200, "msg": message, "data": data})

    @staticmethod
    def error(message="", code=500, data=None):
        if data is None:
            data = {}
        if not message:
            message = "操作失败"
        return JsonResponse({"code": code, "msg": message, "data": data})
