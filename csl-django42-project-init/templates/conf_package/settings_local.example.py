# 本地开发环境配置示例
# 复制此文件为 settings_local.py 并根据实际环境修改

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

RAVEN_CONFIG = {
    'dsn': '',
    'environment': 'local',
}

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB', '__PROJECT_NAME__'),
        'USER': os.getenv('POSTGRES_USER', 'postgres'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'postgres'),
        'HOST': os.getenv('POSTGRES_HOST', 'localhost'),
        'PORT': os.getenv('POSTGRES_PORT', '5432'),
    }
}

# Redis 配置
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))

# Django-Q 配置
Q_CLUSTER_TASK = False
Q_CLUSTER = {
    'name': '__PROJECT_NAME__',
    'workers': 4,
    'timeout': 300,
    # 必须大于单任务 timeout。长任务(如批量导出)调大单任务 timeout 时,这里同步调大,
    # 过小会在完成前被重新投递。
    'retry': 3900,
    'queue_limit': 50,
    'bulk': 10,
    'orm': 'default',
    'redis': {
        'host': REDIS_HOST,
        'port': REDIS_PORT,
        'db': 0,
    },
}

# 开发/测试环境标识
DEBUG = True
LOCAL = True

ALLOWED_HOSTS = ['*']

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}

STATIC_URL = '/statics/'
MEDIA_URL = '/media/'
STATIC_ROOT = os.path.join(BASE_DIR, 'statics')
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# 安全相关(本地环境可以宽松;生产在各自环境的 settings_local.py 中覆盖)
SECRET_KEY = 'local-secret-key-change-in-production'  # pragma: allowlist secret
JWT_SECRET = 'local-jwt-secret-change-in-production'  # pragma: allowlist secret

# 第三方服务配置按需追加(本地用空值或 mock):
# QYWX_CONFIG / DINGTALK_APPKEY / 短信网关 等
