import resource
from django.utils.deprecation import MiddlewareMixin
import logging

logger = logging.getLogger("django")


class MemoryMonitorMiddleware(MiddlewareMixin):
    """内存使用监控中间件"""

    def process_request(self, request):
        request._memory_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

    def process_response(self, request, response):
        import sys

        mem_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        mem_before = getattr(request, "_memory_before", mem_after)
        if sys.platform == "darwin":
            # macOS 的 ru_maxrss 单位为字节，换算为 KB
            mem_used = (mem_after - mem_before) / 1024
        else:
            # Linux 等平台的 ru_maxrss 单位已是 KB
            mem_used = mem_after - mem_before

        if mem_used > (1024 * 10):  # 超过10MB
            logger.warning(f"Large memory usage: {mem_used:.2f}KB " f"for {request.method} {request.path}")

        return response
