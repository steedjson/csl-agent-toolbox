"""测试沙盒设置模块:pytest.ini 的 DJANGO_SETTINGS_MODULE 指向这里。

必须在 django.setup() 之前就是 sqlite——模型类定义阶段就会触碰
connection.ops 并按当前 DATABASES 创建连接包装,事后改 settings 无效。
"""
from <BASE_SETTINGS_MODULE> import *  # noqa: F401,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
        "ATOMIC_REQUESTS": False,
        "AUTOCOMMIT": True,
        "CONN_MAX_AGE": 0,
        "OPTIONS": {},
        "TIME_ZONE": None,
        "USER": "",
        "PASSWORD": "",
        "HOST": "",
        "PORT": "",
        "TEST": {"NAME": ":memory:"},
    }
}

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# 仅项目使用 celery 时保留;django-q 项目删除这两行(q 任务只入队不执行)
# CELERY_TASK_ALWAYS_EAGER = True
# CELERY_TASK_EAGER_PROPAGATES = True
