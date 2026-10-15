from django.urls import re_path

from apps.base.views import base

urlpatterns = [
    re_path(r"^upload$", base.UploadView.as_view()),  # 上传文件
    re_path(r"^richtext/upload$", base.RichTextUploadView.as_view()),  # 富文本上传文件
    re_path(r"^bigupload/chunk$", base.BigUploadViews.as_view()),  # 大文件分片上传
    re_path(r"^bigupload/merge$", base.BigUploadViews.as_view()),  # 大文件分片合并
    re_path(r"^config$", base.ConfigView.as_view()),  # 配置信息
    re_path(r"^task/result$", base.QtaskResultView.as_view()),  # django-q异步任务结果查询
]
