import copy
import json
import threading
from django.conf import settings
from django.core.files.uploadhandler import FileUploadHandler, SkipFile
from django.http import HttpRequest, QueryDict
import logging

logger = logging.getLogger("django")

# 线程本地存储
_request_local = threading.local()


def get_current_request():
    """获取当前线程的请求对象"""
    return getattr(_request_local, "request", None)


class RequestMiddleware(object):
    """存储当前请求对象到线程局部变量"""

    def __init__(self, get_response):
        # 必须接受 get_response 参数
        self.get_response = get_response

    def __call__(self, request):
        """处理请求的核心方法"""
        # 1. 请求处理前：存储请求对象
        _request_local.request = request

        try:
            # 2. 调用后续中间件和视图
            response = self.get_response(request)
        finally:
            # 3. 无论视图是否抛异常都清理请求对象，避免跨请求串数据
            if hasattr(_request_local, "request"):
                del _request_local.request

        return response


class RequestBodyCacheMiddleware:
    """缓存请求体以便多次访问"""

    def __init__(self, get_response):
        self.get_response = get_response
        config = getattr(settings, "REQUEST_BODY_CACHE_CONFIG", {})
        self.MAX_BODY_SIZE = config.get("MAX_SIZE", 10 * 1024 * 1024)  # 10MB 最大缓存大小
        self.EXCLUDE_PATHS = config.get("EXCLUDE_PATHS", ["/statics/", "/media/"])
        self.INCLUDE_PATHS = config.get("INCLUDE_PATHS", ["/api/v1/admin/"])
        self.INCLUDE_CONTENT_TYPES = config.get(
            "INCLUDE_CONTENT_TYPES", ["application/json", "application/x-www-form-urlencoded"]
        )

    def __call__(self, request: HttpRequest):
        # 将 process_request 的所有逻辑移到这里
        # 注意：代码是在 get_response 调用之前执行
        self.process_and_cache_body(request)

        response = self.get_response(request)

        # 这里是请求处理完成后，响应返回前的逻辑，可以留空
        return response

    def process_and_cache_body(self, request: HttpRequest):
        # 只处理特定路径
        if not any(request.path.startswith(path) for path in self.INCLUDE_PATHS):
            return
        # 排除特定路径
        if any(request.path.startswith(path) for path in self.EXCLUDE_PATHS):
            return

        # 只处理特定内容类型
        content_type = request.content_type
        if not any(content_type.startswith(ct) for ct in self.INCLUDE_CONTENT_TYPES):
            return
        # 只处理可能包含请求体的方法
        if request.method not in ("POST", "PUT"):
            return

        # 检查内容长度
        content_length = request.META.get("CONTENT_LENGTH", 0)
        try:
            content_length = int(content_length)
        except (ValueError, TypeError):
            content_length = 0

        # 跳过超大请求体
        if content_length > self.MAX_BODY_SIZE:
            return

        # 读取并缓存请求体
        try:
            # 缓存原始请求体
            request._cached_body = request.body

            # 缓存解析后的数据
            content_type = request.content_type
            if content_type == "application/json":
                request._cached_json = json.loads(request._cached_body.decode("utf-8"))
            elif content_type == "application/x-www-form-urlencoded":
                request._cached_form = QueryDict(request._cached_body)
            elif content_type.startswith("multipart/form-data"):
                # 对于 multipart 请求，我们只缓存元数据而不解析文件
                request._cached_form = self._safe_parse_multipart(request)
        except Exception as e:
            # 记录错误但继续处理
            logger.warning(
                "Failed to cache request body for path %s: %s",
                request.path,
                e,
                exc_info=True,  # 同时记录堆栈信息
            )
            request._cached_body = b""
            request._cached_error = str(e)

    def _safe_parse_multipart(self, request: HttpRequest):
        """安全解析 multipart 请求，不处理文件内容

        在请求副本上解析，避免污染真实请求的 upload_handlers（真实请求后续仍需
        自行解析 POST/FILES）。
        """
        probe = copy.copy(request)
        # SkipFileUploadHandler 需要 request 参数（FileUploadHandler.__init__ 签名）
        probe.upload_handlers = [SkipFileUploadHandler(probe)]

        # 解析表单数据（跳过文件）
        form_data = QueryDict("", mutable=True)
        for key, value in probe.POST.items():
            form_data[key] = value
        return form_data


class SkipFileUploadHandler(FileUploadHandler):
    """自定义上传处理器，跳过所有文件上传"""

    def new_file(
        self, field_name, file_name, content_type, content_length, charset=None, content_type_extra=None
    ):
        super(SkipFileUploadHandler, self).new_file(
            field_name, file_name, content_type, content_length, charset, content_type_extra
        )
        raise SkipFile()

    def receive_data_chunk(self, raw_data, start):
        return None

    def file_complete(self, file_size):
        return None
