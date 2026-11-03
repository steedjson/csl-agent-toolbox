from stdkit.db import models


class ModelOperatioChoices(models.TextChoices):
    CREATE = "create", "创建"
    UPDATE = "update", "更新"
    DELETE = "delete", "删除"


class OperationType(models.IntegerChoices):
    Create = 1, "创建"
    Read = 2, "读取"
    Update = 3, "更新"
    Delete = 4, "删除"
    Import = 5, "导入"
    Export = 6, "导出"
    Discard = 7, "废弃"
