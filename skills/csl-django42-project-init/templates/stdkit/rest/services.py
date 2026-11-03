from django.core.paginator import Paginator, EmptyPage
from enum import Enum
from stdkit.error.exceptions import BadRequestException
from stdkit.db import models
from stdkit.utils.utils import Util


class BaseService(Util):

    def _paginate(self, queryset, page_num, page_size):
        """分页公共逻辑，返回 count/previous/next/results（results 为 Page 对象）"""
        page_num = max(1, page_num)  # 页码至少为1
        page_size = max(1, page_size)  # 页大小至少为1
        previous = page_num - 1
        next_page = page_num + 1
        result = {
            "count": 0,
            "previous": None,
            "next": None,
            "results": [],
        }

        result["count"] = queryset.count()
        # 计算总页数
        total_pages = (result["count"] + page_size - 1) // page_size
        result["previous"] = previous if previous >= 1 and previous <= total_pages else None
        result["next"] = next_page if next_page <= total_pages else None
        pnr = Paginator(queryset, page_size)
        try:
            result["results"] = pnr.page(page_num)
        except EmptyPage:
            result["results"] = []
        return result

    def get_pg_page_data(self, queryset, page_num, page_size, extra_fields=None):
        result = self._paginate(queryset, page_num, page_size)
        # results 为 Page 对象或空列表（超出范围时），后者迭代结果为空列表
        result["results"] = [item.as_dict(extra_fields=extra_fields) for item in result["results"]]
        return result

    def convert_enum_to_value(self, data):
        """
        Recursively converts all Enum instances in a dict (or sub-dicts) to their values.

        Args:
            data (dict): The dictionary to be processed.

        Returns:
            dict: A new dictionary with all Enum values replaced by their corresponding numeric values.
        """
        if isinstance(data, dict):
            return {key: self.convert_enum_to_value(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self.convert_enum_to_value(item) for item in data]
        elif isinstance(data, Enum):
            return data.value
        else:
            return data

    def _base_wrap_items_get_origin_fields(self, items, field_maps: list):
        # field_map exp: {"origin_field": "", "to_field": "", "field_type": ""}
        origin_fields = []
        for item in items:
            for field_map in field_maps:
                if item.get(field_map["origin_field"]):
                    if field_map["field_type"] == "str":
                        origin_fields.append(item[field_map["origin_field"]])
                    elif field_map["field_type"] == "list":
                        origin_fields.extend(item[field_map["origin_field"]])

        origin_fields = list(set(origin_fields))
        return origin_fields

    def _base_wrap_items_by_map(self, items, field_maps: list, wrap_map: dict):
        # field_map exp: {"origin_field": "", "to_field": "", "field_type": ""}
        for item in items:
            for field_map in field_maps:
                if not item.get(field_map["origin_field"]):
                    continue
                if field_map["field_type"] == "str":
                    item[field_map["to_field"]] = wrap_map.get(item[field_map["origin_field"]])
                elif field_map["field_type"] == "list":
                    item[field_map["to_field"]] = [wrap_map.get(i) for i in item[field_map["origin_field"]]]

        return items

    def get_pg_page_obj(self, queryset, page_num, page_size):
        return self._paginate(queryset, page_num, page_size)

    def filter_fields(self, items, fields=None, exclude=False):
        """
        过滤数据中的字段。

        :param items: list of dicts, 需要过滤的原始数据。
        :param fields: list, 需要返回或移除的字段名。
        :param exclude: bool, True 表示移除字段，False 表示仅返回指定字段。
        :return: list of dicts, 过滤后的数据。
        """
        if not fields:
            return items

        filtered_data = []
        for item in items:
            if exclude:
                filtered_item = {key: value for key, value in item.items() if key not in fields}
            else:
                filtered_item = {key: value for key, value in item.items() if key in fields}

            filtered_data.append(filtered_item)

        return filtered_data

    def filter_nested_fields(self, items, fields=None, exclude=False, children_key="subs"):
        """
        递归过滤多级结构中的字段。

        :param items: list of dicts, 需要过滤的原始数据。
        :param fields: list, 需要返回或移除的字段名。
        :param exclude: bool, True 表示移除字段，False 表示仅返回指定字段。
        :param children_key: str, 子菜单的键名（默认为 "subs"）。
        :return: list of dicts, 过滤后的数据。
        """
        if not fields:
            return items

        filtered_data = []
        for item in items:
            if exclude:
                filtered_item = {k: v for k, v in item.items() if k not in fields}
            else:
                filtered_item = {k: v for k, v in item.items() if k in fields}

            # 递归处理 children
            if children_key in item and isinstance(item[children_key], list):
                filtered_item[children_key] = self.filter_nested_fields(
                    item[children_key], fields=fields, exclude=exclude, children_key=children_key
                )

            filtered_data.append(filtered_item)

        return filtered_data

    def wrap_items_with_name(
        self, items, model_cls, origin_field, to_field, field_type="str", model_field="name"
    ):
        field_maps = [
            {
                "origin_field": origin_field,
                "to_field": to_field,
                "field_type": field_type,
            },
        ]
        data_ids = self._base_wrap_items_get_origin_fields(items=items, field_maps=field_maps)
        if not data_ids:
            return items

        datas = list(model_cls.objects.filter(uuid__in=data_ids).values_list("uuid", model_field))
        data_map = {data[0]: data[1] for data in datas}
        items = self._base_wrap_items_by_map(items=items, field_maps=field_maps, wrap_map=data_map)
        return items

    @property
    def nil_result(self):
        result = {
            "count": 0,
            "previous": None,
            "next": None,
            "results": [],
        }
        return result

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0]
        return request.META.get("REMOTE_ADDR")


class DataService(BaseService):
    model_cls: models.Model = None
    show_fields = []

    def get_data_list(self, cleaned_data):
        """获取数据列表"""
        cleaned_data = self.convert_enum_to_value(cleaned_data)
        order_by = cleaned_data.get("order_by") or "-add_datetime"
        order_field = str(order_by).lstrip("-")
        allowed_fields = {f.name for f in self.model_cls._meta.fields}
        if order_field not in allowed_fields:
            order_by = "-add_datetime"
        query = self.model_cls.objects.order_by(order_by)
        query = self._query_func(query, cleaned_data)
        result = self.get_pg_page_data(query, cleaned_data["page"], cleaned_data["size"])
        result["results"] = self._wrap_func(result["results"])
        if not self.show_fields:
            # 用与 as_dict() 键对齐的字段名（外键为 attname），否则 FK 值会被白名单过滤丢弃
            self.show_fields = self.model_cls.get_serializable_field_list()
        result["results"] = self.filter_fields(result["results"], self.show_fields)
        result = self._bind_choice_map(result)
        return result

    def _query_func(self, query, cleaned_data):
        """查询数据列表时，自定义查询参数"""
        return query

    def _wrap_func(self, result):
        """查询数据列表时，自定义处理数据返回"""
        return result

    def _get_wrap_func(self, uuid, result):
        """查询数据详情时，自定义处理数据返回"""
        return result

    def _post_add_func(self, obj):
        """添加数据后的自定义操作"""
        pass

    def add_data(self, cleaned_data):
        """添加数据"""
        cleaned_data = self.params_clean(cleaned_data)
        cleaned_data = self.convert_enum_to_value(cleaned_data)

        data = self.model_cls()
        cleaned_data = self._pre_add_check(data.uuid, cleaned_data)
        for k, v in cleaned_data.items():
            setattr(data, k, v)

        data.save()

        self._post_add_func(data)
        return data.uuid

    def mod_data(self, cleaned_data):
        """修改数据"""
        cleaned_data = self.params_clean(cleaned_data)
        cleaned_data = self.convert_enum_to_value(cleaned_data)
        cleaned_data = self._pre_mod_check(cleaned_data)
        data = self.model_cls.objects.filter(uuid=cleaned_data["uuid"]).first()
        if not data:
            raise BadRequestException("数据不存在")

        del cleaned_data["uuid"]
        for k, v in cleaned_data.items():
            setattr(data, k, v)
        data.save()

        return data.uuid

    def del_data(self, uuid):
        """删除数据"""
        data = self.model_cls.objects.filter(uuid=uuid).first()
        if not data:
            raise BadRequestException("数据不存在")
        data.soft_delete()
        self._after_del(uuid)

    def get_data(self, uuid):
        """获取数据详情"""
        data = self.model_cls.objects.filter(uuid=uuid).first()
        if not data:
            raise BadRequestException("数据不存在")

        result = data.as_dict()
        result = self._wrap_func([result])[0]
        result = self._get_wrap_func(uuid, result)
        result = self._bind_choice_map(result)
        return result

    def _pre_add_check(self, uuid, cleaned_data):
        """添加前置操作"""
        return cleaned_data

    def _pre_mod_check(self, cleaned_data):
        """修改前置操作"""
        return cleaned_data

    def _after_del(self, uuid):
        """删除后置操作"""
        pass

    def _bind_choice_map(self, result):
        """返回枚举值map"""
        choice_map = self.model_cls.get_choices_map()
        if choice_map:
            result["choices_map"] = choice_map
        return result
