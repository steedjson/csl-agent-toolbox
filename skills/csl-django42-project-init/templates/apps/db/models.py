"""模型基座。

约定(全项目统一,新增模型照此执行):
- 继承 DirtyFieldsMixin + stdkit.db.models.Model;
- 主键为 uuid(不是 id),由 stdkit 基类提供;
- 时间字段 add_datetime / update_datetime 由 stdkit 基类提供;
- 有效记录 deleted_at=0:`objects` 自动过滤有效记录,`objects_all` 包含已删除记录;
- 表名统一前缀 model_prefix(经 Meta.db_table 指定);
- 每个字段写 db_comment(数据库列注释)。
"""

from dirtyfields import DirtyFieldsMixin
from django.contrib.postgres.fields import ArrayField
from django.db.models import JSONField
from stdkit.db import models

from apps.db.const import ModelOperatioChoices

model_prefix = "__TABLE_PREFIX__"


class Tenant(DirtyFieldsMixin, models.Model):
    """
    租户
    """

    name = models.CharField(db_comment="名称", max_length=100, default="")
    enabled = models.BooleanField(db_comment="是否启用", default=True)

    def __str__(self):
        return f"{self.name}"

    class Meta:
        db_table = f"{model_prefix}tenant"
        verbose_name = verbose_name_plural = "租户"


class ConfigType(DirtyFieldsMixin, models.Model):
    """
    自定义配置类型
    仅限超级管理员操作
    """

    tenant = models.ForeignKey(
        "Tenant",
        db_comment="租户",
        on_delete=models.CASCADE,
        related_name="tenant_config_types",
        null=True,
        default=None,
    )
    name = models.CharField(db_comment="名称", max_length=100, default="")
    tag = models.CharField(db_comment="唯一标识", max_length=30, default="")
    enabled = models.BooleanField(db_comment="是否禁用", default=True)

    def __str__(self):
        return f"{self.name}"

    class Meta:
        db_table = f"{model_prefix}config_type"
        verbose_name = verbose_name_plural = "自定义配置分类"


class Configs(DirtyFieldsMixin, models.Model):
    """
    自定义配置
    仅限超级管理员操作
    """

    tenant = models.ForeignKey(
        "Tenant",
        db_comment="租户",
        on_delete=models.CASCADE,
        related_name="tenant_configs",
        null=True,
        default=None,
    )
    config_type = models.ForeignKey(
        "ConfigType", db_comment="类型", on_delete=models.CASCADE, related_name="config_type_configs"
    )
    name = models.CharField(db_comment="名称", max_length=30, default="")
    tag = models.CharField(db_comment="唯一标识", max_length=30, default="")
    value = ArrayField(JSONField(db_comment="选项信息"), db_comment="选项", default=None, null=True, blank=True)  # [{"": ""}]
    enabled = models.BooleanField(db_comment="是否启用", default=True)

    def __str__(self):
        return f"{self.name}"

    class Meta:
        db_table = f"{model_prefix}configs"
        verbose_name = verbose_name_plural = "自定义配置"


class Role(DirtyFieldsMixin, models.Model):
    """
    角色
    """

    tenant = models.ForeignKey(
        "Tenant", db_comment="租户", on_delete=models.CASCADE, related_name="tenant_roles"
    )
    name = models.CharField(db_comment="名称", max_length=100, default="", db_index=True)
    is_super = models.BooleanField(db_comment="超级管理角色", default=False)
    enabled = models.BooleanField(db_comment="是否启用", default=True)
    remarks = models.CharField(db_comment="备注", null=True, max_length=200, default="")

    def __str__(self):
        return f"{self.name}"

    class Meta:
        db_table = f"{model_prefix}role"
        verbose_name = verbose_name_plural = "角色表"


class Admin(DirtyFieldsMixin, models.Model):
    """
    后台管理用户
    """

    tenant = models.ForeignKey(
        "Tenant", db_comment="租户", on_delete=models.CASCADE, related_name="tenant_admins"
    )
    role = models.ForeignKey("Role", db_comment="角色", on_delete=models.CASCADE, related_name="role_admins")
    username = models.CharField(db_comment="用户名", max_length=100, default="", db_index=True)
    password = models.CharField(db_comment="密码", max_length=80, default="")
    nickname = models.CharField(db_comment="昵称", max_length=100, default="")
    avatar = models.CharField(db_comment="头像", max_length=100, default="")
    mobile = models.CharField(db_comment="手机号", max_length=20, default="")
    email = models.CharField(db_comment="邮箱", max_length=60, default="")
    enabled = models.BooleanField(db_comment="是否启用", default=True)
    last_time = models.DateTimeField(db_comment="最后登录时间", null=True)
    remarks = models.CharField(db_comment="备注", null=True, max_length=200, default="")

    def __str__(self):
        return f"{self.username}({self.nickname})"

    class Meta:
        db_table = f"{model_prefix}admin"
        verbose_name = verbose_name_plural = "管理员表"


class AOperationLog(DirtyFieldsMixin, models.Model):
    admin = models.ForeignKey("Admin", db_comment="操作用户", on_delete=models.SET_NULL, null=True)
    action_type = models.CharField(db_comment="操作类型", max_length=10, choices=ModelOperatioChoices.choices)
    ip_address = models.GenericIPAddressField(null=True, blank=True, db_comment="IP地址")
    db_table = models.CharField(max_length=255, db_comment="数据库表名", null=True, default=None)
    db_table_name = models.CharField(max_length=255, db_comment="数据库表名(中文)", null=True, default=None)
    model_class = models.CharField(max_length=255, db_comment="模型类名称", null=True, default=None)
    app_name = models.CharField(max_length=255, db_comment="app名称", null=True, default=None)
    model_name = models.CharField(max_length=255, db_comment="模型名称")
    object_id = models.CharField(max_length=255, db_comment="对象ID")
    object_repr = models.CharField(max_length=255, db_comment="对象表示")
    before_data = models.JSONField(null=True, blank=True, db_comment="修改前数据")
    after_data = models.JSONField(null=True, blank=True, db_comment="修改后数据")
    request_data = models.JSONField(null=True, blank=True, db_comment="请求参数")
    user_agent = models.TextField(db_comment="对象表示", default=None, null=True)

    class Meta:
        db_table = f"{model_prefix}aoperation_log"
        verbose_name = verbose_name_plural = "操作日志"
        ordering = ["-add_datetime"]

    def __str__(self):
        return f"{self.admin.nickname} {self.get_action_type_display()} {self.model_name} #{self.object_id}"


class Demo(DirtyFieldsMixin, models.Model):
    """
    示例模型:新业务模型照此结构编写(字段注释、db_table 前缀、verbose_name)
    """

    demo_choices = ((1, "示例"),)
    demo = models.CharField(verbose_name="示例", db_comment="示例", max_length=100, default="")
    choice_field = models.SmallIntegerField(
        verbose_name="系统性质", db_comment="系统性质", default=1, choices=demo_choices, null=True
    )

    class Meta:
        db_table = f"{model_prefix}demo"
        verbose_name = verbose_name_plural = "示例"
