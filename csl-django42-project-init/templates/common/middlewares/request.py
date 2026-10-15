import json
import logging
import traceback
import urllib.parse

import jwt
from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse
from django.urls import resolve
from jwt.exceptions import ExpiredSignatureError
from stdkit.error.exceptions import MyException

from apps.db.models import Admin

logger = logging.getLogger("django")


def _is_miss_token_path(path: str) -> bool:
    """免认证路径按段精确匹配:/statics 放行 /statics 与 /statics/...,但不放行 /statics-evil。"""
    for miss_path in settings.MISS_TOKEN_PATHS:
        normalized = miss_path.rstrip("/")
        if path == normalized or path.startswith(normalized + "/"):
            return True
    return False


class RequestMiddleware(object):
    """JWT 认证与统一异常响应。

    并发约束:中间件实例跨请求共享,判定状态一律用请求内局部变量,
    禁止写 self(gunicorn 线程并发下会串改)。
    """

    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        func, args, kwargs = resolve(request.path)
        verification_auth = False
        if hasattr(func, "view_class") and hasattr(func.view_class, "verification_auth"):
            verification_auth = func.view_class.verification_auth
        if _is_miss_token_path(request.path):
            verification_auth = False
        if verification_auth:
            rs = self.admin_validate(request)
            if isinstance(rs, HttpResponse):
                return rs
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        pass

    def process_exception(self, request, exception):
        if settings.DEBUG:
            logger.error(f"中间件捕获到异常: {type(exception).__name__}: {exception}")
            traceback.print_exc()

        err_data = {"error": "", "code": 500, "msg": "", "data": None}
        code = 500

        if isinstance(exception, MyException):
            err_data["msg"] = exception.detail
            err_data["code"] = exception.code
            code = exception.code
        else:
            if settings.DEBUG:
                err_data["error"] = traceback.format_exc()
            else:
                err_data["error"] = ":{0}: {1}".format(exception.__class__.__name__, str(exception))

        return HttpResponse(json.dumps(err_data), content_type="application/json", status=code)

    def _extract_token(self, request):
        raw = (
            request.META.get("HTTP_AUTHORIZATION", "")
            or request.GET.get("token", "")
            or request.GET.get("authorization", "")
        )
        if not raw:
            return ""
        s = urllib.parse.unquote(str(raw)).strip()
        if s.startswith("JWT "):
            return s[4:].strip()
        if s.startswith("Bearer "):
            return s[7:].strip()
        return s

    def admin_validate(self, request):
        encoded_jwt = self._extract_token(request)
        if not encoded_jwt:
            return self.build_login_error("登录失效(未提供token)")
        try:
            payload = jwt.decode(encoded_jwt, settings.JWT_SECRET, algorithms=["HS256"])
        except ExpiredSignatureError:
            return self.build_login_error("登录失效2")
        except Exception:
            return self.build_login_error("登录失效3")
        user_id = payload.get("user_id", "")
        if not user_id:
            return self.build_login_error("登录失效4")
        payload = cache.get(user_id)
        if not payload:
            # Redis 会话丢失（重启/淘汰）时，用已通过签名与过期校验的 token 重建会话
            payload = self.rebuild_admin_session(user_id)
        if not payload:
            return self.build_login_error("登录失效5")
        if "token_type" not in payload.keys():
            return self.build_login_error("登录失效6")
        token_type = payload.get("token_type")
        if token_type not in settings.JWT_TOKENS.keys():
            return self.build_login_error("登录失效7")
        request.token = encoded_jwt
        for k in settings.JWT_TOKENS[token_type]:
            setattr(request, k, payload.get(k))

    def rebuild_admin_session(self, user_id):
        """
        按 Admin 表重建登录会话；账号不存在或已停用则返回 None（维持登录失效5）。
        仅在 cache.get(user_id) 未命中且 JWT 已通过签名+过期校验后调用。
        """
        admin = Admin.objects.filter(uuid=user_id).first()
        if not admin or not admin.enabled:
            return None
        payload = {
            "token_type": "admin",
            "tenant_id": admin.tenant_id,
            "user_id": admin.uuid,
            "is_super": admin.role.is_super,
        }
        cache.set(admin.uuid, payload, settings.TOKEN_EXPIRE_DAY * 3600 * 24)
        return payload

    def build_login_error(self, msg):
        err = {"error": "", "code": 401, "msg": msg, "data": None}
        return HttpResponse(
            json.dumps(err),
            content_type="application/json",
            status=401,
        )
