"""pytest 专用设置:从基线设置起步,切成 sqlite 内存库。

轨道边界(开箱状态):
- 轨道 A(纯逻辑,tests/nodb/,无 django_db)开箱即用;
- 轨道 B(@pytest.mark.django_db)受限:基线 Configs.value 为 ArrayField(PG 专属),
  sqlite 建表/写入会失败。装 django-test-sandbox 技能获得完整 PG 建表垫片
  (会以沙盒版 settings_test.py + conftest.py 覆盖/补充本文件)后再写轨道 B 用例。
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
