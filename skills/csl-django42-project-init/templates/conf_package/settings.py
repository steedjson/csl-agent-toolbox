"""
Django settings for __PROJECT_NAME__ project.

基线提炼自 wework/backend。敏感与环境相关配置(数据库/Redis/Q 集群等)
统一放 settings_local.py(不入库),首次开发先复制 settings_local.example.py。
"""

import datetime
import os
from pathlib import Path

from stdkit.rest.sentry_init import init_sentry

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "change-me-in-settings-local"  # pragma: allowlist secret

DEBUG = False

# 基线宽松默认;各环境在 settings_local.py 里按实际收紧
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "django_q",
    "rest_framework",
    "apps.db",
    "apps.base",
    "apps.tasks",
    # 业务 app 注册(scaffold 按需追加在这行下面)
]

# JWT-only 栈:认证统一由 common.middlewares.request 处理,不用 session,DRF 侧
# 显式关闭默认 SessionAuth,防止将来视图访问 request.user 时触发不存在的 sessions 表。
MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "common.middlewares.request.RequestMiddleware",
    "stdkit.middleware.request_cache.RequestBodyCacheMiddleware",
    "stdkit.middleware.request_cache.RequestMiddleware",
    "stdkit.middleware.request_time.RequestStartEndTimeMiddleware",
]

ROOT_URLCONF = "__CONF_PACKAGE__.urls"

WSGI_APPLICATION = "__CONF_PACKAGE__.wsgi.application"

APPEND_SLASH = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(BASE_DIR, "db.sqlite3"),
    }
}

LANGUAGE_CODE = "zh-Hans"

TIME_ZONE = "Asia/Chongqing"

USE_I18N = True

# 沿用 wework 惯性:naive 本地时间直接存库;切 USE_TZ=True 属全局改造,勿顺手改
USE_TZ = False

STATIC_URL = "/statics/"
STATIC_ROOT = os.path.join(BASE_DIR, "statics")

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

MISS_TOKEN_PATHS = ["/statics", "/media"]

REST_FRAMEWORK = {
    "COERCE_DECIMAL_TO_STRING": False,
    "EXCEPTION_HANDLER": "stdkit.rest.handlers.custom_exception_handler",
    "DATE_FORMAT": "%Y-%m-%d",
    "DATETIME_FORMAT": "%Y-%m-%d %H:%M:%S",
    "PAGINATE_BY_PARAM": "page_size",
    "DEFAULT_AUTHENTICATION_CLASSES": [],
}
JWT_SECRET = "change-me-in-settings-local"  # pragma: allowlist secret

JWT_AUTH = {
    "JWT_EXPIRATION_DELTA": datetime.timedelta(days=365),
    "JWT_SECRET_KEY": JWT_SECRET,
}
TOKEN_EXPIRE_DAY = 30
JWT_TOKENS = {"admin": ["token_type", "tenant_id", "user_id", "is_super"]}

RAVEN_CONFIG = {
    "dsn": "",
    "environment": "local",
}

(Path(BASE_DIR) / "logs").mkdir(parents=True, exist_ok=True)
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "filters": {"require_debug_false": {"()": "django.utils.log.RequireDebugFalse"}},
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(threadName)s:%(thread)d] [%(name)s:%(lineno)d] [%(module)s:%(funcName)s]"
            " [%(levelname)s]- %(message)s"
        },
        "simple": {"format": "[%(asctime)s][%(levelname)s][%(filename)s:%(lineno)d]%(message)s"},
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
        "error": {
            "level": "ERROR",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(BASE_DIR, "logs", "error.log"),
            "maxBytes": 1024 * 1024 * 50,
            "backupCount": 5,
            "formatter": "standard",
            "encoding": "utf-8",
        },
        "info": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(BASE_DIR, "logs", "info.log"),
            "maxBytes": 1024 * 1024 * 50,
            "backupCount": 5,
            "formatter": "simple",
            "encoding": "utf-8",
        },
        "aps": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(BASE_DIR, "logs", "aps.log"),
            "maxBytes": 1024 * 1024 * 50,
            "backupCount": 5,
            "formatter": "simple",
            "encoding": "utf-8",
        },
    },
    "root": {"level": "INFO", "handlers": ["console"]},
    "loggers": {
        "django": {
            "handlers": ["error", "info", "console"],
            "level": "INFO",
            "propagate": False,
        },
        "aps": {
            "handlers": ["console", "aps"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

from .settings_local import *  # noqa

# Load local overrides only after the base settings (including BASE_DIR) exist.
init_sentry(RAVEN_CONFIG)
