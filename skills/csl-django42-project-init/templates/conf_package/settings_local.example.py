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
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', '')

# 缓存(django-redis):中间件 JWT 会话、导出防重、异步任务进度都走这里。
# 多 worker 部署必须共享 Redis——漏配会落到进程内 LocMemCache,状态互不可见且重启即丢。
# KEY_PREFIX 按 环境_项目_ 拼,多项目共库时避免互踩。
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f'redis://{REDIS_HOST}:{REDIS_PORT}',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {'max_connections': 100},
            # 'PASSWORD': REDIS_PASSWORD,
        },
        'KEY_PREFIX': 'dev___PROJECT_NAME___api_',
    }
}

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

# stdkit 请求体缓存(RequestBodyCacheMiddleware)。默认只对 /api/v1/admin/ 前缀生效,
# 新项目按自己的路由前缀调整,否则该中间件等于常闭:
REQUEST_BODY_CACHE_CONFIG = {
    'INCLUDE_PATHS': ['/api/v1/'],
    'EXCLUDE_PATHS': ['/statics/', '/media/'],
}
