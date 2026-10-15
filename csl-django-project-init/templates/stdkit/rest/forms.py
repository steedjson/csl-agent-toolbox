# validates/pre_load 等名字是下游借道本模块使用的 marshmallow API
# （下游写法：from stdkit.rest.forms import Schema, fields, validates），
# 属于既有对外契约，不得删除
from marshmallow import Schema as M_Schema, fields, EXCLUDE, validates, pre_load  # noqa: F401


class Schema(M_Schema):
    class Meta:
        unknown = EXCLUDE  # 所有继承该类的 schema 都默认忽略未知字段


class GetSchema(Schema):
    uuid = fields.String(required=True)


class DelSchema(Schema):
    uuid = fields.String(required=True)


class GetListSchema(Schema):
    page = fields.Integer(load_default=1)
    size = fields.Integer(load_default=10)

    @pre_load
    def remove_empty_fields(self, data, **kwargs):
        if not isinstance(data, dict):
            return data

        # 定义需要过滤的"空值"类型：空字符串、None、null（JSON传入的null会被解析为None）
        empty_values = ("", None)

        # 在副本上过滤，避免修改调用方传入的 dict
        return {key: value for key, value in data.items() if value not in empty_values}
