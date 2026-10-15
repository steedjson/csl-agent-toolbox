from marshmallow import fields, ValidationError


class EnumField(fields.Field):

    def __init__(self, enum, *args, **kwargs):
        self.enum = enum
        super().__init__(*args, **kwargs)

    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return None
        if isinstance(value, self.enum):
            return value.value
        raise ValidationError(f"Invalid enum value: {value}")

    def _deserialize(self, value, attr, data, **kwargs):
        try:
            return self.enum(int(value))
        except (ValueError, TypeError, OverflowError):
            raise ValidationError(f"Invalid enum value: {value}")
