from django.urls import re_path

from apps.__APP_NAME__.views import demo

urlpatterns = [
    re_path(r"^demo$", demo.DemoView.as_view()),  # 示例路由:替换为真实业务视图
]
