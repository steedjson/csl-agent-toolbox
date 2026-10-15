# encoding=utf-8
"""
文件上传工具类
修复文件句柄泄漏、内存溢出、完整性校验等问题
优化：边写边计算MD5、增大分块大小、可选MD5计算
"""
import uuid
import os
import datetime
import random
import mimetypes
import fcntl
import logging
import hashlib
from django.conf import settings
from stdkit.utils.utils import Util
from stdkit.utils.file_validator import FileValidator

logger = logging.getLogger(__name__)


class FileLock:
    """文件锁工具类，用于并发控制"""
    
    def __init__(self, lock_file):
        self.lock_file = lock_file
        self.lock_fd = None
    
    def __enter__(self):
        self.lock_fd = open(self.lock_file, 'w')
        fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_EX)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.lock_fd:
            fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_UN)
            self.lock_fd.close()
        return False


class UploadFile:
    """文件上传工具类"""
    
    # 流式读写的分块大小（64KB，提升I/O性能）
    STREAM_CHUNK_SIZE = 65536
    
    # 图片压缩配置
    IMAGE_COMPRESS_QUALITY = 85
    IMAGE_MAX_WIDTH = 1920
    IMAGE_MAX_HEIGHT = 1920

    def get_file_category(self, file_type):
        """
        获取文件分类
        :param file_type: 文件 MIME 类型
        :return: 文件分类字符串
        """
        if file_type in ["image/jpeg", "image/jpg", "image/png", "image/gif", "image/heic"]:
            return "image"
        elif file_type in ["video/mp4", "video/x-msvideo", "video/x-flv", "video/quicktime"]:
            return "video"
        elif file_type in ["application/pdf"]:
            return "pdf"
        elif file_type in [
            "application/msword",
            "application/wps-writer",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ]:
            return "doc"
        elif file_type in [
            "application/octet-stream",
            "application/vnd.ms-powerpoint",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ]:
            return "ppt"
        elif file_type in [
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel",
        ]:
            return "xls"
        elif file_type in ["text/csv"]:
            return "csv"
        elif file_type in ["application/vnd.android.package-archive"]:
            return "apk"
        # application/octet-stream 为通用二进制类型，语义含混；沿用既有归属（ppt 分支，见上）
        elif file_type in ["audio/amr", "audio/mpeg", "audio/wav"]:
            return "audio"
        return ""

    def upload(self, file, u_folder="", small=True, target_size=3 * 1024, quality=85, step=5, calculate_md5=True):
        """
        上传文件（支持图片压缩）
        
        Args:
            file: Django 上传文件对象
            u_folder: 上传文件夹名称
            small: 是否压缩图片
            target_size: 目标大小（保留以兼容既有调用，当前实现忽略）
            quality: 压缩质量
            step: 压缩步长（保留以兼容既有调用，当前实现忽略）
            calculate_md5: 是否计算MD5（默认True，设为False可提升性能）
            
        Returns:
            包含文件信息的字典，包括路径、名称、类型、大小、MD5等
        """
        file_type = file.content_type.lower()
        is_png = file_type in ["image/png"]
        file_category = self.get_file_category(file_type=file_type)
        
        # 生成唯一文件名
        str2 = uuid.uuid4().hex
        folder = str2[:2]
        directory_name = datetime.datetime.now().strftime("%Y/%m/" + folder)
        filename = str2[2:10] + "_" + str(random.randint(1000, 9999))
        file_ext = os.path.splitext(file.name)[-1]
        
        if is_png and "png" not in file_ext.lower():
            file_ext = ".png"
        
        # 原始文件名和压缩文件名
        original_filename = filename + file_ext
        small_filename = filename + "_small" + file_ext
        
        saved_path = os.path.join("media", u_folder, directory_name)
        original_file_path = os.path.join(saved_path, original_filename)
        small_file_path = os.path.join(saved_path, small_filename)
        abs_original_file_path = os.path.join(settings.BASE_DIR, original_file_path)

        os.makedirs(os.path.dirname(abs_original_file_path), exist_ok=True)
        
        # 写入原始文件（边写边计算MD5，避免二次读取）
        md5_hash = hashlib.md5() if calculate_md5 else None
        with open(abs_original_file_path, "wb+") as destination:
            for chunk in file.chunks():
                destination.write(chunk)
                if md5_hash:
                    md5_hash.update(chunk)
        
        # 获取MD5值
        original_md5 = md5_hash.hexdigest() if md5_hash else ""
        
        # 最终返回的文件路径（默认为原始文件）
        final_file_path = original_file_path
        
        # 图片压缩处理
        if file_category == "image" and os.path.isfile(abs_original_file_path) and small:
            try:
                from PIL import Image, ImageFile

                current_img = Image.open(abs_original_file_path)
                
                # 处理 RGBA 模式
                if current_img.mode in ("RGBA",) and not is_png:
                    current_img = current_img.convert("RGB")
                
                # 保存全局标志原值，处理结束后恢复，避免污染进程内其他图片处理
                load_truncated_images_before = ImageFile.LOAD_TRUNCATED_IMAGES
                ImageFile.LOAD_TRUNCATED_IMAGES = True
                
                try:
                    small_absolute_file_path = os.path.join(settings.BASE_DIR, small_file_path)
                    
                    w, h = current_img.size
                    if w > self.IMAGE_MAX_WIDTH or h > self.IMAGE_MAX_HEIGHT:
                        # 计算缩放比例
                        if (1.0 * w / self.IMAGE_MAX_WIDTH) > (1.0 * h / self.IMAGE_MAX_HEIGHT):
                            scale = 1.0 * w / self.IMAGE_MAX_WIDTH
                        else:
                            scale = 1.0 * h / self.IMAGE_MAX_HEIGHT
                        
                        # 缩放并保存（使用更快的BILINEAR算法）
                        img = current_img.resize(
                            (round(w / scale), round(h / scale)), 
                            Image.Resampling.BILINEAR
                        )
                        img.save(small_absolute_file_path, optimize=True, quality=self.IMAGE_COMPRESS_QUALITY)
                        img.close()
                    else:
                        # 直接保存压缩版本
                        current_img.save(
                            small_absolute_file_path, 
                            optimize=True, 
                            quality=self.IMAGE_COMPRESS_QUALITY
                        )
                    
                    current_img.close()
                    
                    # 压缩成功后，返回压缩文件路径
                    final_file_path = small_file_path
                    logger.info(f"图片压缩成功: {original_file_path} -> {small_file_path}")
                finally:
                    ImageFile.LOAD_TRUNCATED_IMAGES = load_truncated_images_before
                
            except Exception as e:
                # 压缩失败，返回原始文件
                logger.error(f"图片压缩失败，使用原始文件: {str(e)}")
                final_file_path = original_file_path

        ra_data = {
            "name": file.name,
            "path": "/" + final_file_path,
            "original_path": "/" + original_file_path,  # 保留原始文件路径
            "type": file_type,
            "size": Util().pybyte(file.size, "MB"),
            "md5": original_md5,  # 添加 MD5 校验值
        }
        return ra_data

    def chunk_upload(self, file, chunk_path, chunk_index=None, calculate_md5=True):
        """
        上传文件分片
        
        Args:
            file: Django 上传文件对象
            chunk_path: 分片存储路径
            chunk_index: 分片序号（可选）
            calculate_md5: 是否计算MD5（默认True，设为False可提升性能）
            
        Returns:
            包含分片信息的字典，包括 MD5 校验值
        """
        if ".." in chunk_path or chunk_path.lstrip().startswith(("/", "\\")):
            return {
                "success": False,
                "chunk_path": chunk_path,
                "md5": "",
                "size": 0,
                "error": "Invalid chunk path: potential security risk",
            }

        relative_file_path = os.path.join("media", chunk_path)
        abs_file_path = os.path.join(settings.BASE_DIR, relative_file_path)
        os.makedirs(os.path.dirname(abs_file_path), exist_ok=True)
        
        # 写入分片文件（边写边计算MD5）
        md5_hash = hashlib.md5() if calculate_md5 else None
        file_size = 0
        with open(abs_file_path, "wb+") as destination:
            for chunk in file.chunks():
                destination.write(chunk)
                if md5_hash:
                    md5_hash.update(chunk)
                file_size += len(chunk)
        
        return {
            'success': True,
            'chunk_path': chunk_path,
            'md5': md5_hash.hexdigest() if md5_hash else "",
            'size': file_size
        }

    def chunk_merge(self, file_name, chunk_path, chunk_count, expected_md5=None):
        """
        合并文件分片（修复文件句柄泄漏、内存溢出、添加完整性校验）
        
        Args:
            file_name: 最终文件名
            chunk_path: 分片路径前缀
            chunk_count: 分片总数
            expected_md5: 期望的文件 MD5 值（可选）
            
        Returns:
            (success, data) 元组，success 为布尔值，data 为文件信息或错误消息
        """
        # 安全校验：防止路径穿越和绝对路径
        if ".." in chunk_path or chunk_path.lstrip().startswith(("/", "\\")):
            return False, "Invalid chunk path: potential security risk"

        # 验证分片序号连续性
        missing_chunks = []
        for i in range(chunk_count):
            tmp_chunk_path = f"{chunk_path}{i}"
            chunk_filename = os.path.join(settings.BASE_DIR, "media", f"{tmp_chunk_path}")
            if not os.path.exists(chunk_filename):
                missing_chunks.append(i)
        
        if missing_chunks:
            return False, f"Missing chunks: {missing_chunks}"

        # 生成最终文件路径
        str2 = uuid.uuid4().hex
        folder = str2[:2]
        directory_name = datetime.datetime.now().strftime("%Y/%m/" + folder)
        saved_path = os.path.join("media", "bigfile", directory_name)
        filename = str2[2:10] + "_" + str(random.randint(1000, 9999))
        ext = os.path.splitext(file_name)[1]
        filename = filename + ext
        relative_file_path = os.path.join(saved_path, filename)
        abs_file_path = os.path.join(settings.BASE_DIR, relative_file_path)
        os.makedirs(os.path.dirname(abs_file_path), exist_ok=True)
        
        # 使用临时文件进行原子写入
        temp_file_path = abs_file_path + '.tmp'
        lock_file_path = abs_file_path + '.lock'
        
        try:
            # 使用文件锁防止并发合并
            with FileLock(lock_file_path):
                # 流式合并分片（避免内存溢出）
                with open(temp_file_path, "wb") as target_file:
                    for chunk_index in range(chunk_count):
                        tmp_chunk_path = f"{chunk_path}{chunk_index}"
                        chunk_filename = os.path.join(settings.BASE_DIR, "media", f"{tmp_chunk_path}")
                        
                        try:
                            # 使用 with 语句管理文件句柄
                            with open(chunk_filename, "rb") as source_file:
                                # 流式读写（8KB chunks）
                                while True:
                                    data = source_file.read(self.STREAM_CHUNK_SIZE)
                                    if not data:
                                        break
                                    target_file.write(data)
                        except Exception as e:
                            logger.error(f"读取分片 {chunk_index} 失败: {str(e)}")
                            # 清理临时文件
                            if os.path.exists(temp_file_path):
                                os.remove(temp_file_path)
                            return False, f"Failed to read chunk {chunk_index}: {str(e)}"
                
                # 完整性校验
                if expected_md5:
                    actual_md5 = FileValidator.calculate_md5(temp_file_path)
                    if actual_md5 != expected_md5.lower():
                        logger.error(f"文件完整性校验失败: expected={expected_md5}, actual={actual_md5}")
                        # 清理临时文件
                        if os.path.exists(temp_file_path):
                            os.remove(temp_file_path)
                        return False, "File integrity check failed: MD5 mismatch"
                
                # 原子重命名（从临时文件到最终文件）
                os.rename(temp_file_path, abs_file_path)
                
                # 清理分片文件
                cleaned_chunks = []
                for chunk_index in range(chunk_count):
                    tmp_chunk_path = f"{chunk_path}{chunk_index}"
                    chunk_filename = os.path.join(settings.BASE_DIR, "media", f"{tmp_chunk_path}")
                    try:
                        if os.path.exists(chunk_filename):
                            os.remove(chunk_filename)
                            cleaned_chunks.append(chunk_index)
                    except Exception as e:
                        logger.warning(f"清理分片 {chunk_index} 失败: {str(e)}")
                
                logger.info(f"成功合并 {chunk_count} 个分片，清理了 {len(cleaned_chunks)} 个分片文件")
                
        except Exception as e:
            logger.error(f"文件合并失败: {str(e)}")
            # 清理临时文件
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            return False, f"Merge failed: {str(e)}"
        finally:
            # 清理锁文件
            if os.path.exists(lock_file_path):
                try:
                    os.remove(lock_file_path)
                except Exception:
                    pass
        
        # 计算最终文件的 MD5
        final_md5 = FileValidator.calculate_md5(abs_file_path)
        
        # 获取文件信息
        mimetype, _ = mimetypes.guess_type(abs_file_path)
        file_type = mimetype.lower() if mimetype else "application/octet-stream"
        size = os.path.getsize(abs_file_path)
        
        ra_data = {
            "name": file_name,
            "path": "/" + relative_file_path,
            "type": file_type,
            "size": Util().pybyte(size, "MB"),
            "md5": final_md5,  # 添加 MD5 校验值
        }
        return True, ra_data

    def verify_chunk_integrity(self, chunk_path, chunk_count, chunk_md5_list):
        """
        验证分片完整性
        
        Args:
            chunk_path: 分片路径前缀
            chunk_count: 分片总数
            chunk_md5_list: 各分片的 MD5 值列表
            
        Returns:
            (success, message) 元组
        """
        # 安全校验：防止路径穿越和绝对路径（与 chunk_upload/chunk_merge 一致）
        if ".." in chunk_path or chunk_path.lstrip().startswith(("/", "\\")):
            return False, "Invalid chunk path: potential security risk"

        if len(chunk_md5_list) != chunk_count:
            return False, f"MD5 list length mismatch: expected {chunk_count}, got {len(chunk_md5_list)}"
        
        for i, expected_md5 in enumerate(chunk_md5_list):
            tmp_chunk_path = f"{chunk_path}{i}"
            chunk_filename = os.path.join(settings.BASE_DIR, "media", f"{tmp_chunk_path}")
            
            if not os.path.exists(chunk_filename):
                return False, f"Chunk {i} not found"
            
            if not expected_md5:
                return False, f"Chunk {i} MD5 missing"
            
            actual_md5 = FileValidator.calculate_md5(chunk_filename)
            if actual_md5 != expected_md5.lower():
                return False, f"Chunk {i} MD5 mismatch: expected={expected_md5}, actual={actual_md5}"
        
        return True, "All chunks verified successfully"