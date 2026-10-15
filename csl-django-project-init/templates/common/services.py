from stdkit.rest.services import BaseService as StdKitBaseService
from stdkit.rest.services import DataService as StdKitDataService

from apps.db.models import ConfigType, Configs, Tenant


class BaseService(StdKitBaseService):

    tenant_id = None

    def __init__(self, request=None):
        if request:
            self.tenant_id = getattr(request, "tenant_id", None)
        if not self.tenant_id:
            self.tenant_id = self.get_tenant_id()
        super().__init__()

    def get_tenant_id(self):
        if self.tenant_id:
            return self.tenant_id
        return Tenant.objects.order_by('add_datetime').first().uuid if Tenant.objects.exists() else None

    def get_configs(self, tenant_id, config_type_tag, tag):
        config_type = ConfigType.objects.filter(tenant_id=tenant_id, tag=config_type_tag).first()
        if not config_type:
            return None
        configs = Configs.objects.filter(tenant_id=tenant_id, config_type_id=config_type.uuid, tag=tag).all()
        if not configs:
            return None
        result = [config.as_dict() for config in configs]
        return result


class DataService(BaseService, StdKitDataService):
    pass
