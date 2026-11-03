"""沙盒探针:CI 第一道门禁。任何一条红 = 沙盒不成立,先修复再跑业务测试。
Layer-1 通用照抄;Layer-2 按盘点结论换成项目真实模型(managed=True)。
"""
import pytest
from django.db import connection

pytestmark = pytest.mark.django_db


# ── Layer-1 通用(勿改) ──────────────────────────────────────────

def test_00_gate_sandbox_is_active():
    """硬门禁:劫持没生效就红灯,绝不悄悄连真库。"""
    assert connection.vendor == "sqlite"
    # Django 会把 :memory: 测试库转为共享内存 URI(file:memorydb_...)
    assert "memory" in connection.settings_dict["NAME"]


def test_05_cache_is_local():
    from django.core.cache import cache, caches

    cache.set("probe", "v")
    assert cache.get("probe") == "v"
    assert type(caches["default"]).__name__ == "LocMemCache"


# ── Layer-2 项目化(按 Step 1 盘点替换模型与字段) ─────────────────

def test_10_<模型A>_table_created():
    from <app>.models import <模型A>

    <模型A>.objects.create(<必填字段>)
    assert <模型A>.objects.count() == 1


def test_11_<PG字段>_roundtrip_and_exact():
    from <app>.models import <模型A>

    m = <模型A>.objects.create(<PG字段>=<样例值>)
    fresh = <模型A>.objects.get(pk=m.pk)
    assert fresh.<PG字段> == <样例值>
    assert <模型A>.objects.filter(<PG字段>=<样例值>).exists()


def test_12_<嵌套JSON数组>_roundtrip_and_exact():
    """数组字段内嵌 dict 的往返(标量数组之外最强的一条)。"""
    from <app>.models import <模型B>

    val = [{"k": "v", "n": 1}]
    m = <模型B>.objects.create(<PG字段>=val)
    fresh = <模型B>.objects.get(pk=m.pk)
    assert fresh.<PG字段> == val
    assert <模型B>.objects.filter(<PG字段>=val).exists()
