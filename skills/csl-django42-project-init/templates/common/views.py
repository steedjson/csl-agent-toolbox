import datetime

from django.conf import settings
from django.core.cache import cache
from django_q.tasks import async_task, result
from openpyxl.workbook import Workbook
from rest_framework.views import APIView as DjangoView
from stdkit.rest.response import JsonResponse

from common.utils import generate_media_path


class View(DjangoView):

    verification_auth = True

    def __init__(self):
        super(View, self).__init__()


class ExportBaseView(View):
    params: list = []  # 查询参数
    sheet_titles: list  # 表头

    def get(self, request, *args, **kwargs):
        parsed_args = self._parse_params(request)
        task_name = self._get_task_name()

        # 本地调试，settings.LOCAL=True:同步执行并直接带回导出文件 url
        if getattr(settings, "LOCAL", False):
            result_data = self._run_export(self.__class__, parsed_args, self.sheet_titles, self.params)
            return JsonResponse.success(result_data)

        cache_key = f"{request.user_id}_{task_name}"
        task_id = cache.get(cache_key)
        if task_id:
            rs = result(task_id)
            if rs:
                return JsonResponse.error("请勿重复操作")
            return JsonResponse.success({"task_id": task_id})

        task_id = async_task(
            self.__class__._run_export,
            self.__class__,
            parsed_args,
            self.sheet_titles,
            self.params,
            task_name=task_name,
        )
        cache.set(cache_key, task_id, 300)
        cache.set(
            task_id,
            {
                "task_id": task_id,
                "task_id_cache_key": cache_key,
            },
            300,
        )
        return JsonResponse.success({"task_id": task_id})

    def _parse_params(self, request):
        # 参数解析，有定制化参数处理，可以继承重写
        result = []
        for param in self.params:
            result.append(request.GET.get(param, ""))
        return result

    @classmethod
    def _run_export(cls, view_cls, args, sheet_titles, params):
        """通过传入类、参数和表头实现通用导出"""
        instance = view_cls()
        instance.sheet_titles = sheet_titles
        instance.params = params
        return instance.export(*args)

    def export(self, *args):
        self._init_load(*args)
        obj_list = self._get_obj_list(*args)
        if not obj_list:
            return {"url": ""}

        wb = Workbook()
        ws = wb.active
        ws.append(self.sheet_titles)
        v = []
        for obj in obj_list:
            values = self._get_values(obj)
            ws.append(values)
            v.append(values)
        now_datetime = datetime.datetime.now()
        filename = f"{now_datetime.strftime('%Y%m%d%H%M%S')}.xlsx"
        absolute_path, rel_path = generate_media_path(filename, "export")
        wb.save(absolute_path)
        wb.close()
        return {"url": rel_path}

    def _get_task_name(self):
        return self.__class__.__name__.lower()

    def _get_obj_list(self, *args):
        # 列表数据获取
        raise NotImplementedError

    def _get_values(self, obj):
        # 单行数据获取
        raise NotImplementedError

    def _init_load(self, *args):
        # 如果有公共数据需要在循环中访问，在该函数中赋值给self传递
        pass


def admin_validator(view_func):
    """函数视图的管理员门卫:request.is_super 由认证中间件注入"""

    def wrapped_view(request, *args, **kwargs):
        if not request.is_super:
            return JsonResponse.error("权限不足", code=403)
        return view_func(request, *args, **kwargs)

    return wrapped_view
