import time
import logging
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger("django")


class RequestStartEndTimeMiddleware(MiddlewareMixin):
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.logger = logging.getLogger("performance")

    def process_request(self, request):
        # 记录请求开始时间
        request.start_time = time.time()

    def process_response(self, request, response):
        start_time = getattr(request, "start_time", None)
        if start_time is None:
            return response
        duration = time.time() - start_time
        response.headers["X-page-Duration-ms"] = int(duration * 1000)
        self.logger.info("duration: %.4f seconds path: %s", duration, request.path)
        return response
