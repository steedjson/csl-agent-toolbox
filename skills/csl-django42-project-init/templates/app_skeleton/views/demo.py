from stdkit.rest.response import JsonResponse

from common.views import View


class DemoView(View):
    """示例视图:替换为真实业务视图。参数校验用 define_params,业务逻辑委托 Service。"""

    def get(self, request, *args, **kwargs):
        return JsonResponse.success({"app": "apps.__APP_NAME__"})
