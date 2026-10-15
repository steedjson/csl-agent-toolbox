#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "__CONF_PACKAGE__.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError:
        try:
            import django
        except ImportError:
            raise ImportError(
                "Couldn't import Django. Are you sure it's installed and "
                "available on your PYTHONPATH environment variable? Did you "
                "forget to activate a virtual environment?"
            )
        raise
    try:
        execute_from_command_line(sys.argv)
    except Exception as e:
        # 启动期错误(设置导入、app ready)上报 Sentry;未配置时静默。
        try:
            from stdkit.rest.sentry_init import capture_exception, init_sentry

            from __CONF_PACKAGE__ import settings_local

            init_sentry(settings_local.RAVEN_CONFIG)
            capture_exception(e)
        except ImportError:
            pass
        raise e
