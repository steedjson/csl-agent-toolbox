# coding=utf-8
"""接管 manage.py test:默认委托给 pytest 内存沙盒。

背景:项目历史文档的验收命令大量写作 `manage.py test`(真库 + 全量
迁移,慢且违背"新测试不连外部数据库服务")。本命令把该入口改指
pytest 沙盒,旧命令自动走新路,历史文档一处都不用改。

- 无参数:转跑 pytest(沙盒设置由根 pytest.ini 接管),透传退出码;
- 带参数:点路径语义无法无损翻译为 pytest 文件路径,打印指引并以
  非零码退出——宁可响亮失败,不做误翻译后的假绿;
- 需要真库/真迁移状态的测试,用 pytest 侧出口(见下方指引)。

落点:放任一已注册 app 的 management/commands/ 目录(优先选已有
commands 目录的 app,覆盖内置同名命令是 Django 官方机制)。
"""
import os
import subprocess
import sys

from django.core.management.base import BaseCommand, CommandError

PYTEST_CMD = "<PYTEST_CMD>"                    # 例:".venv/bin/python -m pytest"
REAL_SETTINGS_MODULE = "<REAL_SETTINGS_MODULE>"  # 例:"yourproj.settings"


class Command(BaseCommand):
    help = "已接管:无参时转跑 pytest 内存沙盒"

    def add_arguments(self, parser):
        parser.add_argument("args", nargs="*", metavar="test_label", help="测试标签(不再支持,见命令说明)")

    def handle(self, *args, **options):
        if args:
            self.stderr.write(
                "manage.py test 已改由 pytest 沙盒接管,点路径参数不再支持:\n"
                f"  跑全部沙盒测试: python manage.py test\n"
                f"  跑指定文件:    {PYTEST_CMD} <路径>\n"
                f"  真库/真迁移:   DJANGO_TEST_SANDBOX=0 {PYTEST_CMD}"
                f" --ds={REAL_SETTINGS_MODULE} --migrations <路径>\n"
                "宁可响亮失败,不做参数误翻译后的假绿。"
            )
            raise CommandError("不支持的调用形态,见上方指引")
        # manage.py 已 setdefault DJANGO_SETTINGS_MODULE 指向真实设置,
        # 子进程继承它会压过 pytest.ini 的沙盒设置(会被 conftest 门禁拦下),
        # 清掉让 pytest.ini 作为唯一正典来源。
        env = dict(os.environ)
        env.pop("DJANGO_SETTINGS_MODULE", None)
        result = subprocess.run([sys.executable, "-m", "pytest"], env=env)
        sys.exit(result.returncode)
