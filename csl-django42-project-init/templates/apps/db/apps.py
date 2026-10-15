from django.apps import AppConfig


class DbConfig(AppConfig):
    name = "apps.db"

    def ready(self):
        # 需要信号(操作日志等)时,在这里导入并注册信号模块
        pass
