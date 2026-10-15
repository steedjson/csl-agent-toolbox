# coding=utf-8
import re
import time
import uuid
import json
import enum
import datetime
from django.apps import apps
from django.db import connections
from django.db.models.query import QuerySet  # noqa: F401  有意再导出，供下游 from stdkit.db.models import QuerySet
from .fields import *
# 显式导入，避免依赖 fields.py 无 __all__ 时把 raw_models 名字泄漏进来的隐式行为
from django.db import models as raw_models
from itertools import chain
from typing import List, Dict, Any, TypeVar, Type
from collections import OrderedDict
from django.db.models import TextChoices as DTextChoices, IntegerChoices as DIntegerChoices
import typing

SOFT_DELETE_FIELD_NAME = "deleted_at"

# 序列化/字段白名单中排除的公共字段，get_field_list 与 get_serializable_field_list 共用
SERIALIZE_EXCLUDE_FIELDS = frozenset({"add_datetime", "update_datetime", SOFT_DELETE_FIELD_NAME})


def format_field(field):
    if isinstance(field, datetime.datetime):
        return str(field)
    elif isinstance(field, datetime.date):
        return str(field)
    return field


def get_uuid_str():
    """
    获取UUID的字符串
    :return:
    """
    return uuid.uuid4().hex


def get_time_stamp():
    """
    获取整型时间戳
    :return:
    """
    return int(time.time())


def get_date_time():
    """
    获取整型时间戳
    :return:
    """
    return datetime.datetime.now()


def string_to_dynamic_instance(model_str, app_name="db"):
    """
    model_str: "CostType object (15b7028d5c23480cb397fd45185ac4dc)"
    :param model_str:
    :return:
    """
    # 提取模型名和主键
    match = re.match(r"(\w+) object \((.*?)\)$", model_str)
    if not match:
        return None

    model_name = match.group(1)  # 示例: "CostType"
    pk = match.group(2)  # 示例: "15b7028d5c23480cb397fd45185ac4dc"

    try:
        model_class = apps.get_model(app_name, model_name)
    except LookupError:
        return None
    try:
        return model_class.objects.get(pk=pk)
    except model_class.DoesNotExist:
        return None


class ModelManager(raw_models.Manager):
    def __init__(self, list_all=False, *args, **kwargs):
        super(ModelManager, self).__init__(*args, **kwargs)
        self.list_all = list_all

    def get_queryset(self):
        """
        自定义过滤QuerySet
        :return:
        """
        # 按 Django Manager 契约传递 hints（related manager 的 instance 提示依赖它），
        # 并使用 self._queryset_class 以支持 from_queryset() 自定义 QuerySet
        query_obj = self._queryset_class(model=self.model, using=self._db, hints=self._hints)
        if SOFT_DELETE_FIELD_NAME in [e.name for e in self.model._meta.fields] and not self.list_all:
            query_obj = query_obj.filter(**{SOFT_DELETE_FIELD_NAME: 0})

        return query_obj


class Model(raw_models.Model):
    class Meta:
        abstract = True

    export_fields = []

    # 使用自扩展Manager
    objects = ModelManager()
    objects_all = ModelManager(list_all=True)

    # 序列化输出的字段
    output_fields = []

    # 时间日期格式
    datetime_format = "%Y-%m-%d %H:%M:%S"

    # 　可计算字段
    can_calc_fields = []

    # 公共字段
    uuid = CharField(
        verbose_name="UUID",
        max_length=32,
        default=get_uuid_str,
        editable=False,
        primary_key=True,
        db_comment="唯一主键",
    )
    add_datetime = DateTimeField(auto_now_add=True, db_comment="入库时间")
    update_datetime = DateTimeField(auto_now=True, db_comment="更新时间")
    deleted_at = BigIntegerField(default=0, db_comment="删除时间（是否已删除）")

    def as_dict(self, keys=None, exclude_keys=None, extra_fields=None, handle_field=False):
        """
        将ORM对象序列化为字典
        :param keys:
        :return:
        """
        if not keys:
            keys = self.output_fields
        if not extra_fields:
            extra_fields = []
        object_dict = dict()
        # 注意：many_to_many 字段取到的是 ManyRelatedManager 而非可序列化值，
        # 下游可能依赖该形态，故不在此转换；需要 JSON 输出时请自行处理 m2m 字段
        for f in chain(
            self._meta.concrete_fields,
            self._meta.private_fields,
            self._meta.many_to_many,
        ):
            # 过滤维度与输出维度对齐：字段既可用 ORM 名（f.name）引用，也可用输出键（f.column）引用，
            # 命中任一即视为匹配——下游既有传 ORM 名（如 author）的调用保持生效，
            # 同时支持传 as_dict() 的输出键（如默认外键的 author_id、自定义列名的 author_ref）。
            # 用 in 成员判断而非 set 交集：对 list/tuple/set 输入结果等价，
            # 且退化输入（裸字符串、不可哈希元素）保持改动前的行为，不引入新的异常或静默差异
            column = getattr(f, "column", None)
            field_names = (f.name, column)

            if exclude_keys and any(name in exclude_keys for name in field_names if name):
                continue
            if keys and not any(name in keys for name in field_names if name):
                continue

            # GenericForeignKey/GenericRelation 等私有字段没有对应数据库列（column 为 None），
            # 无输出键可取，跳过；普通字段与 m2m 的 column 恒为字符串，不受影响
            if not column:
                continue

            # 性能考虑，不做深度查询转换，自行按需处理
            # 值按实例属性名取（attname）：FK 的实例属性是 author_id，而 column 只是数据库列名，
            # 自定义 db_column 时二者不同，按 column 取会拿到 None（静默丢值）；
            # 输出键仍用 column，保持既有键形态（含自定义列名）
            o = getattr(self, f.attname, None)
            if handle_field:
                object_dict[f.column] = format_field(o)
            else:
                object_dict[f.column] = o

        for field in extra_fields:
            o = getattr(self, field, None)
            if handle_field:
                object_dict[field] = format_field(o)
            else:
                object_dict[field] = o
        return object_dict

    def as_json(self, keys=None):
        """
        JSON序列化

        注意：模型含 many_to_many 字段时，as_dict() 返回的是 ManyRelatedManager，
        json.dumps 会抛 TypeError，需先自行处理 m2m 字段。
        :param keys:
        :return:
        """
        return json.dumps(self.as_dict(keys))

    def get_add_time(self):
        """
        从ORM对象datetime转换为字符串时间格式
        :return:
        """
        if not self.add_datetime:
            return ""
        return self.add_datetime.strftime(self.datetime_format)

    get_add_time.allow_tags = True
    get_add_time.short_description = "添加时间"

    def get_update_time(self):
        """
        从ORM对象datetime转换为字符串时间格式
        :return:
        """
        if not self.update_datetime:
            return ""
        return self.update_datetime.strftime(self.datetime_format)

    get_update_time.allow_tags = True
    get_update_time.short_description = "更新时间"

    @property
    def get_add_datetime(self):
        """
        从ORM对象datetime对象换为字符串时间格式
        :return:
        """
        return self.add_datetime.strftime(self.datetime_format)

    @property
    def get_update_datetime(self):
        """
        从ORM对象datetime对象换为字符串时间格式
        :return:
        """
        return self.update_datetime.strftime(self.datetime_format)

    def soft_delete(self):
        """
        对象软删除，只更新删除标记 is_deleted 为 True
        :return: ObjectId
        """
        self.deleted_at = int(time.time())
        self.save()
        return self.pk

    @staticmethod
    def batch_soft_delete(objects):
        """
        批量对象软删除，只更新删除标记 deleted_at
        :return: objects
        """
        objects.update(deleted_at=int(time.time()))
        return objects

    @staticmethod
    def batch_update(objects, data=None):
        """
        批量对象修改
        :return: objects
        """
        payload = dict(data or {})
        payload["update_datetime"] = get_date_time()

        objects.update(**payload)
        return objects

    def update(self, data=None):
        """
        修改
        """
        payload = dict(data or {})
        field_keys = [f.attname for f in self.__class__._meta.fields]
        field_keys2 = [f.name for f in self.__class__._meta.fields]
        field_keys.extend(field_keys2)
        field_keys = list(set(field_keys))
        for k, v in payload.items():
            if k in field_keys:
                setattr(self, k, v)
        self.update_datetime = get_date_time()
        self.save()
        return self

    @classmethod
    def get_fields_verbose_names(cls, fields=None):
        all_fields_map = {f.name: f for f in cls._meta.fields}
        if fields is None:
            return {k: v.verbose_name for k, v in all_fields_map.items()}
        labels = []
        for field in fields:
            labels.append(all_fields_map[field].verbose_name)
        return labels

    @classmethod
    def get_fields_names(cls, fields=None):
        all_fields_map = {f.name: f for f in cls._meta.fields}
        if fields is None:
            return [v.name for k, v in all_fields_map.items()]
        names = []
        for field in fields:
            names.append(all_fields_map[field].name)
        return names

    @classmethod
    def get_db_table_attribute(cls, connection=None):
        if not connection:
            connection = connections["default"]
        rs_data = {
            "table": {
                "table": cls._meta.db_table,
                "table_name": cls._meta.verbose_name,
            },
            "fields": [],
        }
        all_fields_map = {f.name: f for f in cls._meta.fields}
        for _, field in all_fields_map.items():
            db_type = field.db_type(connection) if connection else ""
            if db_type == "timestamp with time zone":
                db_type = "timestamptz(6)"
            elif db_type == "bigint":
                db_type = "int8"
            elif db_type == "integer":
                db_type = "int4"
            elif db_type == "smallint":
                db_type = "int2"
            rs_data["fields"].append(
                {
                    "field": field.attname,
                    "name": field.verbose_name,
                    "type": db_type,
                    "choices": field.choices,
                }
            )

        return rs_data

    @classmethod
    def get_field_list(cls):
        """
        获取字段名列表（字符串），排除指定公共字段
        """
        return [
            f.name
            for f in cls._meta.get_fields()
            if f.concrete and not f.many_to_many and f.name not in SERIALIZE_EXCLUDE_FIELDS
        ]

    @classmethod
    def get_serializable_field_list(cls):
        """
        获取与 as_dict() 输出键对齐的字段名列表

        用 column（而非 attname）：as_dict() 以 f.column 作为输出键，
        两者同源才能对齐。默认外键下 column == attname（author_id），
        自定义 db_column 时为实际列名（如 author_ref）。
        """
        return [
            f.column
            for f in cls._meta.get_fields()
            if f.concrete and not f.many_to_many and f.name not in SERIALIZE_EXCLUDE_FIELDS
        ]

    @classmethod
    def get_choices_map(cls) -> typing.Dict[str, typing.Dict[typing.Any, str]]:
        """
        返回当前模型所有 choices 字段的字典映射
        格式: {'field_name': {value: 'label'}}
        """
        choices_map = {}
        for field in cls._meta.fields:
            if field.choices:
                # flatchoices 对普通 choices 与 choices 等价，对分组 choices 会展开为扁平
                # [(value, label), ...]，保证返回 {value: label} 形态
                choices_map[field.name] = dict(field.flatchoices)
        return choices_map


class Choices(enum.Enum):
    """
    Choices生成器
    """

    @classmethod
    def get_choices(cls):
        """
        从枚举类生成django-field-choices
        :return:
        """
        return tuple([(e.value, k) for k, e in cls.__members__.items()])

    @classmethod
    def get_choice_key_list(cls):
        """
        从枚举类生成django-field-choices
        :return:
        """
        return tuple([item.name for item in cls])

    @classmethod
    def get_choice_value_list(cls):
        """
        从枚举类生成django-field-choices
        :return:
        """
        return tuple([item.value for item in cls])


# 类型变量，用于类型注解
_ChoiceT = TypeVar("_ChoiceT", bound="ChoiceMixin")


class ChoiceMixin:
    """为 Choices 类提供 list,dict 方法的 Mixin"""

    @classmethod
    def list(cls: Type[_ChoiceT]) -> List[Dict[str, Any]]:
        """
        返回格式为 [{"label": "", "value": ""}] 的列表
        """
        return [{"label": str(member.label), "value": member.value} for member in cls]

    @classmethod
    def as_choices(cls: Type[_ChoiceT]) -> List[Dict[str, Any]]:
        """别名方法，与 list() 相同"""
        return cls.list()

    @classmethod
    def as_dict(cls: Type[_ChoiceT]) -> Dict[str, str]:
        """
        返回格式为 {value: label} 的字典
        例如: {'FR': 'Freshman', 'SO': 'Sophomore'}
        """
        return {member.value: str(member.label) for member in cls}

    @classmethod
    def as_label_dict(cls: Type[_ChoiceT]) -> Dict[str, str]:
        """
        返回格式为 {label: value} 的字典
        例如: {'Freshman': 'FR', 'Sophomore': 'SO'}
        """
        return {str(member.label): member.value for member in cls}

    @classmethod
    def as_nested_dict(cls: Type[_ChoiceT]) -> Dict[str, Dict[str, str]]:
        """
        返回格式为 {value: {"label": label}} 的嵌套字典
        例如: {'FR': {'label': 'Freshman'}, 'SO': {'label': 'Sophomore'}}
        """
        return {member.value: {"label": str(member.label)} for member in cls}

    @classmethod
    def as_ordered_dict(cls: Type[_ChoiceT]) -> "OrderedDict[str, str]":
        """
        返回有序字典，保持定义顺序 {value: label}
        """
        return OrderedDict((member.value, str(member.label)) for member in cls)

    @classmethod
    def as_grouped_dict(cls: Type[_ChoiceT], group_key: str = "options") -> Dict[str, List[Dict[str, Any]]]:
        """
        返回分组字典，便于前端组件使用
        例如: {"options": [{"label": "Freshman", "value": "FR"}, ...]}
        """
        return {group_key: cls.list()}

    @classmethod
    def get_label_by_value(cls: Type[_ChoiceT], value: str) -> str:
        """
        根据值获取对应的标签
        """
        for member in cls:
            if member.value == value:
                return str(member.label)
        raise ValueError(f"Invalid value: {value}")

    @classmethod
    def get_value_by_label(cls: Type[_ChoiceT], label: str) -> str:
        """
        根据标签获取对应的值
        """
        for member in cls:
            if str(member.label) == label:
                return member.value
        raise ValueError(f"Invalid label: {label}")

    @classmethod
    def is_valid_value(cls: Type[_ChoiceT], value: str) -> bool:
        """
        检查值是否有效
        """
        return any(member.value == value for member in cls)

    @classmethod
    def is_valid_label(cls: Type[_ChoiceT], label: str) -> bool:
        """
        检查标签是否有效
        """
        return any(str(member.label) == label for member in cls)

    @classmethod
    def get_member_by_value(cls: Type[_ChoiceT], value: str) -> Any:
        """
        根据值获取对应的枚举成员
        """
        for member in cls:
            if member.value == value:
                return member
        return None


class TextChoices(ChoiceMixin, DTextChoices):
    """
    TextChoices生成器
    """

    pass


class IntegerChoices(ChoiceMixin, DIntegerChoices):
    """
    IntegerChoices生成器
    """

    pass
