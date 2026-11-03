import logging
import os

from django.conf import settings
from django.core.cache import cache
from django_q.models import Task
from stdkit.error.exceptions import BadRequestException, NotFoundException
from stdkit.rest.response import JsonResponse
from stdkit.utils.upload_file import UploadFile

from apps.db.models import ConfigType, Configs
from common.utils import pybyte
from common.views import View

logger = logging.getLogger(__name__)


def _validate_upload_file(file, max_size_mb):
    """校验上传文件：类型、大小，返回文件类别和大小（MB）"""
    file_size = pybyte(file.size, "MB")
    if not file_size:
        raise BadRequestException("文件大小无效")

    file_type = file.content_type.lower()
    upload_obj = UploadFile()
    file_category = upload_obj.get_file_category(file_type=file_type)
    if not file_category:
        raise BadRequestException("不支持的文件格式")

    if float(file_size) > float(max_size_mb):
        raise BadRequestException(f"上传文件大小限制{max_size_mb}M以内")

    return file_category, file_size


class UploadView(View):
    """
    上传文件（增强版：支持完整性校验）
    """

    verification_auth = False

    def post(self, request, *args, **kwargs):
        try:
            file = request.FILES.get("file")
            if not file:
                raise BadRequestException("请上传文件")

            u_folder = request.data.get("folder", "default")
            small = request.data.get("small", True)

            _validate_upload_file(file, max_size_mb="50.00")

            upload_obj = UploadFile()
            ra_data = upload_obj.upload(file, u_folder, small)

            logger.info(f"文件上传成功: {ra_data.get('path')}, MD5: {ra_data.get('md5')}")
            return JsonResponse.success(ra_data)

        except BadRequestException:
            raise
        except Exception as e:
            logger.error(f"文件上传失败: {str(e)}", exc_info=True)
            raise BadRequestException(f"文件上传失败: {str(e)}")


class RichTextUploadView(View):
    """
    富文本编辑器文件上传（增强版：支持完整性校验）
    """

    verification_auth = False

    def post(self, request, *args, **kwargs):
        try:
            file = request.FILES.get("file")
            if not file:
                return JsonResponse({"errno": 1, "message": "请上传文件"})

            u_folder = request.data.get("folder", "default")

            _validate_upload_file(file, max_size_mb="20.00")

            upload_obj = UploadFile()
            rs = upload_obj.upload(file, u_folder, small=False)

            logger.info(f"富文本文件上传成功: {rs.get('path')}, MD5: {rs.get('md5')}")

            rs_data = {
                "errno": 0,
                "data": {
                    "url": rs["path"],
                    "alt": rs["name"],
                    "href": rs["path"],
                    "md5": rs.get("md5", ""),
                },
            }
            return JsonResponse(rs_data)

        except BadRequestException as e:
            return JsonResponse({"errno": 1, "message": str(e)})
        except Exception as e:
            logger.error(f"富文本文件上传失败: {str(e)}", exc_info=True)
            return JsonResponse({"errno": 1, "message": f"上传失败: {str(e)}"})


class BigUploadViews(View):
    """
    大文件分片上传（增强版：支持完整性校验、分片验证、并发控制）
    """

    verification_auth = False

    def post(self, request, *args, **kwargs):
        """
        上传文件分片
        支持参数：
        - file: 文件分片
        - task_id: 任务唯一标识
        - chunk: 分片序号（从0开始）
        - chunk_md5: 分片MD5值（可选，用于校验）
        """
        try:
            # 匿名可达端点:user_id 未注入时落 anonymous 桶,分片本身按 task_id 隔离
            user_id = getattr(self.request, "user_id", None) or "anonymous"
            upload_file = request.FILES.get("file")

            if not upload_file:
                raise NotFoundException("请上传文件")

            task = request.data.get("task_id")
            chunk = request.data.get("chunk", 0)
            chunk_md5 = request.data.get("chunk_md5")  # 可选的分片MD5

            if not task:
                raise BadRequestException("缺少 task_id 参数")

            # 构建分片文件名
            filename = f"{task}_{chunk}"
            upload_obj = UploadFile()
            chunk_path = os.path.join("tmp", f"{user_id}", f"{filename}")

            # 上传分片
            result = upload_obj.chunk_upload(upload_file, chunk_path, chunk)

            # 如果提供了 MD5，验证分片完整性
            if chunk_md5:
                actual_md5 = result.get('md5')
                if actual_md5 != chunk_md5.lower():
                    logger.error(f"分片 {chunk} MD5 校验失败: expected={chunk_md5}, actual={actual_md5}")
                    # 删除损坏的分片
                    chunk_full_path = os.path.join(settings.BASE_DIR, "media", chunk_path)
                    if os.path.exists(chunk_full_path):
                        os.remove(chunk_full_path)
                    return JsonResponse.error(f"分片 {chunk} 完整性校验失败")

            logger.info(f"分片上传成功: task={task}, chunk={chunk}, md5={result.get('md5')}")

            return JsonResponse.success(
                {'chunk': chunk, 'md5': result.get('md5'), 'size': result.get('size')}
            )

        except (BadRequestException, NotFoundException):
            raise
        except Exception as e:
            logger.error(f"分片上传失败: {str(e)}", exc_info=True)
            raise BadRequestException(f"分片上传失败: {str(e)}")

    def put(self, request, *args, **kwargs):
        """
        合并文件分片
        支持参数：
        - task_id: 任务唯一标识
        - filename: 文件名
        - chunk_count: 分片总数
        - file_md5: 文件MD5值（可选，用于完整性校验）
        - chunk_md5_list: 各分片MD5列表（可选，用于分片验证）
        """
        try:
            # 匿名可达端点:user_id 未注入时落 anonymous 桶,分片本身按 task_id 隔离
            user_id = getattr(self.request, "user_id", None) or "anonymous"
            task_id = request.data.get("task_id")
            file_name = request.data.get("filename", "")
            try:
                chunk_count = int(request.data.get("chunk_count", 1))
            except (ValueError, TypeError):
                raise BadRequestException("分片数量无效")
            file_md5 = request.data.get("file_md5")  # 可选的文件MD5
            chunk_md5_list = request.data.get("chunk_md5_list")  # 可选的分片MD5列表

            if not task_id:
                raise BadRequestException("缺少 task_id 参数")

            if chunk_count < 1:
                raise BadRequestException("分片数量无效")

            upload_obj = UploadFile()
            chunk_path = os.path.join("tmp", f"{user_id}", f"{task_id}")

            # 如果提供了分片MD5列表，验证分片完整性
            if chunk_md5_list:
                verified, message = upload_obj.verify_chunk_integrity(chunk_path, chunk_count, chunk_md5_list)
                if not verified:
                    logger.error(f"分片完整性验证失败: {message}")
                    return JsonResponse.error(f"分片验证失败: {message}")

            # 合并分片
            rs, rs_data = upload_obj.chunk_merge(file_name, chunk_path, chunk_count, file_md5)

            if not rs:
                logger.error(f"分片合并失败: {rs_data}")
                return JsonResponse.error(rs_data)

            logger.info(f"文件合并成功: {rs_data.get('path')}, MD5: {rs_data.get('md5')}")

            return JsonResponse.success(rs_data)

        except BadRequestException:
            raise
        except Exception as e:
            logger.error(f"文件合并失败: {str(e)}", exc_info=True)
            raise BadRequestException(f"文件合并失败: {str(e)}")


class ConfigView(View):
    """
    系统配置
    """

    verification_auth = False

    def get(self, request, *args, **kwargs):
        tag = self.request.GET.get("tag", "")
        tenant_id = self.request.GET.get("tenant_id", "")
        if not tag:
            return JsonResponse.success({})
        tags = tag.split(",")
        config_types = ConfigType.objects.filter(tag__in=tags, enabled=True)
        if tenant_id:
            config_types = config_types.filter(tenant_id=tenant_id)
        else:
            config_types = config_types.order_by("add_datetime").first()
            config_types = [config_types] if config_types else []
        if not config_types:
            return JsonResponse.success({})
        data_list = Configs.objects.filter(config_type__in=config_types, enabled=True)
        rs_data = {}
        for data in data_list:
            rs_data[data.tag] = {"name": data.name, "value": data.value}
        return JsonResponse.success(rs_data)


class QtaskResultView(View):
    """
    django-q 异步任务结果查询
    """

    verification_auth = False

    def get(self, request, *args, **kwargs):
        task_id = request.GET.get("task_id", "")
        if not task_id:
            return JsonResponse.error("缺少 task_id")

        # 1. 优先按业务 task_id 查询；再通过映射查询 Django-Q 实际任务 ID
        task = Task.get_task(task_id)  # 使用 Django-Q 提供的快捷方法
        q_task_id = cache.get(f"task:map:{task_id}")
        if not task and q_task_id:
            task = Task.get_task(str(q_task_id))

        # 2. 获取缓存中的进度数据
        task_id_cache_data = cache.get(task_id)

        if task:
            # 任务已完成（无论成功失败，只要数据库有记录）
            task_data = task.result

            # 清理缓存
            if task_id_cache_data:
                task_id_cache_key = task_id_cache_data.get("task_id_cache_key", "")
                if task_id_cache_key:
                    cache.delete(task_id_cache_key)
                cache.delete(task_id)
            cache.delete(f"task:map:{task_id}")

            if task.success:
                return JsonResponse.success({"status": "ok", "progress": 100, "result": task_data or {}})
            else:
                # 失败处理：返回具体的错误堆栈
                error_msg = task.result or "任务执行失败"
                return JsonResponse.error(f"操作失败: {error_msg}")

        else:
            # 3. 数据库没记录，检查是否在队列中或正在执行
            if task_id_cache_data:
                progress = task_id_cache_data.get("progress", 0)
                pending_result = {
                    key: value for key, value in task_id_cache_data.items() if key != "progress"
                }
                return JsonResponse.success(
                    {"status": "pending", "progress": progress, "result": pending_result}
                )

            # 既没入库也没缓存，可能是 task_id 错误或任务被丢弃
            return JsonResponse.error("任务不存在或已过期")
