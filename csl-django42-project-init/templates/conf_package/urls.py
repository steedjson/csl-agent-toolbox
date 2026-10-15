"""__PROJECT_NAME__ URL Configuration

API 统一挂 /api/v1/<app>/ 前缀,静态与媒体由 Django 直接服务(本地开发)。
"""

from django.conf import settings
from django.urls import include, re_path
from django.views.static import serve

urlpatterns = [
    re_path(r"^api/v1/base/", include("apps.base.urls")),
    re_path(r"^api/v1/task/", include("apps.tasks.urls")),
    # 业务 app 路由(scaffold 按需追加在这行下面)
]

urlpatterns += [
    re_path(
        r"^media/(?P<path>.*)$",
        serve,
        {
            "document_root": settings.MEDIA_ROOT,
        },
    ),
    re_path(
        r"^statics/(?P<path>.*)$",
        serve,
        {
            "document_root": settings.STATIC_ROOT,
        },
    ),
]
