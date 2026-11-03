"""纯逻辑测试(轨道 A):不连数据库,不依赖 django_db。

ORM/查询语义测试(轨道 B)加 @pytest.mark.django_db 放根 tests/,
跑内存 SQLite(pytest 默认设置模块 __CONF_PACKAGE__.settings_test)。
"""


def test_demo_skeleton_loaded():
    from apps.__APP_NAME__ import apps

    assert apps.__APP_CLASS__.name == "apps.__APP_NAME__"
