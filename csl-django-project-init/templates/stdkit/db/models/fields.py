# coding=utf-8

from django.db import models as raw_models
from decimal import Decimal as D

try:
    from django.contrib.postgres.fields import ArrayField as OArrayField
except Exception:  # psycopg 未安装时不应阻断整个 db.models
    OArrayField = None
# 以下删除相关常量/异常为有意再导出：下游通过 stdkit.db.models 命名空间引用，
# 本文件内未使用也不得删除
from django.db.models.deletion import (
    CASCADE,
    DO_NOTHING,
    PROTECT,
    SET,
    SET_DEFAULT,
    SET_NULL,
    ProtectedError,
)


class AutoField(raw_models.AutoField):
    pass


class BigIntegerField(raw_models.BigIntegerField):
    pass


class BinaryField(raw_models.BinaryField):
    pass


class BooleanField(raw_models.BooleanField):
    pass


class CharField(raw_models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 1024)
        super(CharField, self).__init__(*args, **kwargs)


class CommaSeparatedIntegerField(raw_models.CommaSeparatedIntegerField):
    pass


class DateField(raw_models.DateField):
    pass


class DateTimeField(raw_models.DateTimeField):
    pass


class DecimalField(raw_models.DecimalField):
    def __init__(self, *args, **kwargs):
        default_max_digits = kwargs.get("max_digits", 10)
        default_decimal_places = kwargs.get("decimal_places", 2)
        default_default = D(
            "0" * (default_max_digits - default_decimal_places) + "." + "0" * default_decimal_places
        )
        kwargs.setdefault("max_digits", default_max_digits)
        kwargs.setdefault("decimal_places", default_decimal_places)
        kwargs.setdefault("default", default_default)
        super(DecimalField, self).__init__(*args, **kwargs)


class EmailField(raw_models.EmailField):
    pass


class FileField(raw_models.FileField):
    pass


class FilePathField(raw_models.FilePathField):
    pass


class FloatField(raw_models.FloatField):
    pass


class ImageField(raw_models.ImageField):
    pass


class IntegerField(raw_models.IntegerField):
    pass


class IPAddressField(raw_models.IPAddressField):
    pass


class GenericIPAddressField(raw_models.GenericIPAddressField):
    pass


class NullBooleanField(raw_models.NullBooleanField):
    pass


class PositiveIntegerField(raw_models.PositiveIntegerField):
    pass


class PositiveSmallIntegerField(raw_models.PositiveSmallIntegerField):
    pass


class SlugField(raw_models.SlugField):
    pass


class SmallIntegerField(raw_models.SmallIntegerField):
    pass


class TextField(raw_models.TextField):
    def __init__(self, null=True, blank=True, *args, **kwargs):
        kwargs["null"] = null
        kwargs["blank"] = blank
        super(TextField, self).__init__(*args, **kwargs)


class TimeField(raw_models.TimeField):
    pass


class URLField(raw_models.URLField):
    def __init__(self, max_length=1024, *args, **kwargs):
        kwargs["max_length"] = max_length
        super(URLField, self).__init__(*args, **kwargs)


class JSONField(raw_models.JSONField):
    pass


class ArrayField(OArrayField if OArrayField is not None else raw_models.Field):
    def __init__(self, *args, **kwargs):
        if OArrayField is None:
            raise ImportError("ArrayField requires django.contrib.postgres and a PostgreSQL backend")
        super(ArrayField, self).__init__(*args, **kwargs)


class ForeignKey(raw_models.ForeignKey):
    def __init__(self, to=None, on_delete=CASCADE, **kwargs):
        super(ForeignKey, self).__init__(to, on_delete, **kwargs)


class ManyToManyField(raw_models.ManyToManyField):
    def __init__(self, to, **kwargs):
        super(ManyToManyField, self).__init__(to, **kwargs)


class OneToOneField(raw_models.OneToOneField):
    def __init__(self, to, on_delete=CASCADE, to_field=None, **kwargs):
        super(OneToOneField, self).__init__(to, on_delete, to_field=to_field, **kwargs)
