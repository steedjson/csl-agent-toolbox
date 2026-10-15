"""Django 测试沙盒的 PG 建表垫片(配合 settings_test.py 使用)。

分工:
- settings_test.py 负责"从 django.setup() 起就是 sqlite"(劫持数据库/缓存/邮件/Celery);
- 本文件只做两件事:
  1. 响亮门禁:沙盒模式下引擎不是 sqlite 就直接报错,绝不悄悄连真库;
  2. 最小建表垫片:PG 字段 JSON 存取往返 + 剥离 SQLite 建不了的索引/约束。

边界(与项目 AGENTS.md「测试沙盒能力与失真边界声明」一致):
- 不做任何 SQL 算子转译,PG 专属算子查询一律抽 Selector 后在测试层 Mock;
- 排他约束与 PG 特种索引被剥离后,沙盒内不存在,禁止在测试中断言其行为。

存量连库测试对真库执行的唯一出口:
    DJANGO_TEST_SANDBOX=0 pytest --ds=<真实设置模块> --migrations <路径>
"""
import json
import os

from django.apps import apps
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder

SANDBOX_ON = os.environ.get("DJANGO_TEST_SANDBOX", "1") == "1"

try:
    from django.contrib.postgres.constraints import ExclusionConstraint
    from django.contrib.postgres.fields import (
        ArrayField,
        DateRangeField,
        DateTimeRangeField,
        DecimalRangeField,
        HStoreField,
        IntegerRangeField,
    )
    from django.contrib.postgres.fields.array import ArrayExact
    from django.contrib.postgres.indexes import PostgresIndex

    HAS_POSTGRES_CONTRIB = True
except ImportError:
    HAS_POSTGRES_CONTRIB = False


def _array_exact_as_sqlite(self, compiler, connection):
    # ArrayExact 的 PG 实现把右值包成 Func(function='ARRAY') 表达式,
    # SQLite 解析不了。这里拆回原始值列表,走 JSON 文本等值。
    # 这是本垫片唯一一条查询级补丁;其余 PG 算子(__contains/__overlap/
    # __len/下标/Range 操作符)一律不补,走 Selector Mock。
    from django.db.models import Func

    lhs, lhs_params = self.process_lhs(compiler, connection)
    rhs = self.rhs
    if isinstance(rhs, Func) and getattr(rhs, "source_expressions", None):
        values = [e.value for e in rhs.source_expressions]
    else:
        values = rhs
    param = self.lhs.output_field.get_db_prep_value(values, connection, prepared=True)
    return f"{lhs} = %s", (*lhs_params, param)


def _json_prep_value(self, value, connection, prepared=False):
    # sort_keys=True 是 HStore 等值查询的前提:PG hstore 无序,JSON 文本有序
    if value is None:
        return None
    if isinstance(value, (list, dict)):
        return json.dumps(value, cls=DjangoJSONEncoder, sort_keys=True)
    return value


def _json_from_db_value(self, value, expression, connection):
    if value is None or not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return value


class _SQLiteRange:
    # 默认 bounds 与 psycopg 一致取 "[)"
    def __init__(self, lower=None, upper=None, bounds="[)", empty=False):
        self.lower = lower
        self.upper = upper
        self.bounds = bounds
        self.isempty = empty

    def __eq__(self, other):
        if hasattr(other, "lower") and hasattr(other, "upper"):
            return (
                self.lower == other.lower
                and self.upper == other.upper
                and getattr(other, "bounds", "[)") == self.bounds
            )
        if isinstance(other, (tuple, list)) and len(other) == 2:
            return self.lower == other[0] and self.upper == other[1]
        return False

    def __repr__(self):
        return f"_SQLiteRange(lower={self.lower!r}, upper={self.upper!r}, bounds={self.bounds!r})"


def _range_prep_value(self, value, connection, prepared=False):
    if value is None:
        return None
    if isinstance(value, (tuple, list)) and len(value) == 2:
        value = _SQLiteRange(value[0], value[1])
    if hasattr(value, "lower") and hasattr(value, "upper"):
        payload = {
            "__range__": True,
            "lower": value.lower,
            "upper": value.upper,
            "bounds": getattr(value, "bounds", "[)"),
            "empty": getattr(value, "isempty", False),
        }
        return json.dumps(payload, cls=DjangoJSONEncoder, sort_keys=True)
    return json.dumps(value, cls=DjangoJSONEncoder, sort_keys=True)


def _range_from_db_value(self, value, expression, connection):
    if value is None or not isinstance(value, str):
        return value
    try:
        data = json.loads(value)
    except (ValueError, TypeError):
        return value
    if isinstance(data, dict) and data.get("__range__"):
        return _SQLiteRange(
            data.get("lower"),
            data.get("upper"),
            bounds=data.get("bounds", "[)"),
            empty=data.get("empty", False),
        )
    return data


def patch_postgres_storage_for_sqlite():
    if not HAS_POSTGRES_CONTRIB:
        return

    # filter(tags=[...]) 的普通等值:唯一保留的查询级补丁
    ArrayExact.as_sqlite = _array_exact_as_sqlite

    for field_cls in (ArrayField, HStoreField):
        field_cls.db_type = lambda self, connection: "TEXT"
        field_cls.get_db_prep_value = _json_prep_value
        field_cls.from_db_value = _json_from_db_value
        # get_placeholder 默认产出 "%s::<类型>" 的 PG 强转,SQLite 解析不了
        field_cls.get_placeholder = lambda self, value, compiler, connection: "%s"

    for range_cls in (
        IntegerRangeField,
        DecimalRangeField,
        DateTimeRangeField,
        DateRangeField,
    ):
        range_cls.db_type = lambda self, connection: "TEXT"
        range_cls.get_db_prep_value = _range_prep_value
        range_cls.from_db_value = _range_from_db_value
        range_cls.get_placeholder = lambda self, value, compiler, connection: "%s"

    for model in apps.get_models():
        # 剥离后这些索引/约束在沙盒里不存在,相关行为禁止在测试断言
        model._meta.indexes = [
            idx
            for idx in model._meta.indexes
            if not isinstance(idx, PostgresIndex)
            and not getattr(idx, "opclasses", None)
        ]
        model._meta.constraints = [
            c
            for c in model._meta.constraints
            if not isinstance(c, ExclusionConstraint)
        ]

    # ArrayField.__init__ 在 base_field 带 from_db_value 时(如 JSONField)
    # 会把 _from_db_value 绑到实例属性,遮蔽类级补丁;删掉实例绑定,
    # 让读取路径回落到上面打补丁的 _json_from_db_value。
    patched_field_classes = (
        ArrayField,
        HStoreField,
        IntegerRangeField,
        DecimalRangeField,
        DateTimeRangeField,
        DateRangeField,
    )
    for model in apps.get_models():
        for field in model._meta.get_fields():
            if isinstance(field, patched_field_classes):
                field.__dict__.pop("from_db_value", None)


def pytest_configure(config):
    if not SANDBOX_ON:
        return
    engine = settings.DATABASES["default"]["ENGINE"]
    if not engine.endswith("sqlite3"):
        raise RuntimeError(
            "沙盒模式下测试必须跑在 sqlite 测试设置模块上(当前引擎:"
            f"{engine})。检查 pytest.ini 的 DJANGO_SETTINGS_MODULE 是否指向"
            "测试设置模块;确需对真库跑存量集成测试,用:"
            "DJANGO_TEST_SANDBOX=0 pytest --ds=<真实设置模块> --migrations"
        )
    patch_postgres_storage_for_sqlite()
