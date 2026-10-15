from rest_framework.views import APIView as DjangoView
from django_q.tasks import async_task, result
from django.core.cache import cache

from stdkit.rest.response import JsonResponse
from stdkit.utils.utils import Util
from openpyxl.workbook import Workbook
import datetime
from django.conf import settings


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

        # 本地调试，settings.LOCAL=True
        if getattr(settings, "LOCAL", False):
            rs = self._run_export(self.__class__, parsed_args, self.sheet_titles, self.params)
            return JsonResponse.success(rs)

        cache_key = f"{request.user_id}_{task_name}"
        task_id = cache.get(cache_key)
        if task_id:
            rs = result(task_id)
            if rs:
                return JsonResponse.success(rs)
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
        cache.set(task_id, task_id, 300)
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
        absolute_path, rel_path = Util().generate_media_path(filename, "export")
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
