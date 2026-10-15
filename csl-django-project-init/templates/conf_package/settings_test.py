"""pytest 专用设置:从基线设置起步,切成 sqlite 内存库。

仅覆盖最小可跑面。项目引入 PG 专属字段(ArrayField/JSONField)后,
安装 django-test-sandbox 技能获得完整 PG 建表垫片(settings_test + conftest)。
"""

from .settings import *  # noqa

DEBUG = False
LOCAL = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# 测试环境不初始化 Sentry、不投递异步任务
RAVEN_CONFIG = {"dsn": "", "environment": "test"}
Q_CLUSTER_TASK = False
