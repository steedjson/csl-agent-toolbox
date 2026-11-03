# encoding=utf-8
"""
文件完整性校验工具
提供 MD5、SHA256 校验功能，用于检测文件损坏
"""
import hashlib
import os
from typing import Optional


class FileValidator:
    """文件完整性校验工具类"""
    
    # 默认分块大小 8KB，适合大文件处理
    DEFAULT_CHUNK_SIZE = 8192
    
    @staticmethod
    def calculate_md5(file_path: str, chunk_size: int = None) -> Optional[str]:
        """
        计算文件的 MD5 值
        
        Args:
            file_path: 文件路径
            chunk_size: 分块大小，默认 8KB
            
        Returns:
            MD5 十六进制字符串，文件不存在返回 None
        """
        if not os.path.exists(file_path):
            return None
            
        chunk_size = chunk_size or FileValidator.DEFAULT_CHUNK_SIZE
        md5_hash = hashlib.md5()
        
        try:
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    md5_hash.update(chunk)
            return md5_hash.hexdigest()
        except Exception:
            return None
    
    @staticmethod
    def calculate_sha256(file_path: str, chunk_size: int = None) -> Optional[str]:
        """
        计算文件的 SHA256 值
        
        Args:
            file_path: 文件路径
            chunk_size: 分块大小，默认 8KB
            
        Returns:
            SHA256 十六进制字符串，文件不存在返回 None
        """
        if not os.path.exists(file_path):
            return None
            
        chunk_size = chunk_size or FileValidator.DEFAULT_CHUNK_SIZE
        sha256_hash = hashlib.sha256()
        
        try:
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception:
            return None
    
    @staticmethod
    def verify_integrity(file_path: str, expected_hash: str, algorithm: str = 'md5') -> bool:
        """
        验证文件完整性
        
        Args:
            file_path: 文件路径
            expected_hash: 期望的哈希值
            algorithm: 算法类型，'md5' 或 'sha256'
            
        Returns:
            True 表示文件完整，False 表示文件损坏或不匹配
        """
        if not os.path.exists(file_path):
            return False
            
        algorithm = algorithm.lower()
        
        if algorithm == 'md5':
            actual_hash = FileValidator.calculate_md5(file_path)
        elif algorithm == 'sha256':
            actual_hash = FileValidator.calculate_sha256(file_path)
        else:
            raise ValueError(f"不支持的算法: {algorithm}，请使用 'md5' 或 'sha256'")
            
        return actual_hash == expected_hash.lower() if actual_hash else False
    
    @staticmethod
    def calculate_file_chunks_md5(file_path: str, chunk_count: int, chunk_size: int = None) -> list:
        """
        计算文件各分片的 MD5 值列表
        
        Args:
            file_path: 文件路径
            chunk_count: 分片数量
            chunk_size: 每个分片的大小（字节），None 表示自动计算
            
        Returns:
            各分片 MD5 值的列表
        """
        if not os.path.exists(file_path):
            return []
        
        if chunk_count <= 0:
            return []
            
        file_size = os.path.getsize(file_path)
        if chunk_size is None:
            chunk_size = (file_size + chunk_count - 1) // chunk_count
            
        md5_list = []
        
        try:
            with open(file_path, 'rb') as f:
                for i in range(chunk_count):
                    md5_hash = hashlib.md5()
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    md5_hash.update(chunk)
                    md5_list.append(md5_hash.hexdigest())
                    
            return md5_list
        except Exception:
            return []
    
    @staticmethod
    def get_file_info(file_path: str) -> dict:
        """
        获取文件完整信息，包括大小、MD5、SHA256
        
        Args:
            file_path: 文件路径
            
        Returns:
            包含文件信息的字典
        """
        if not os.path.exists(file_path):
            return {
                'exists': False,
                'path': file_path
            }
            
        file_stat = os.stat(file_path)
        
        return {
            'exists': True,
            'path': file_path,
            'size': file_stat.st_size,
            'md5': FileValidator.calculate_md5(file_path),
            'sha256': FileValidator.calculate_sha256(file_path),
            'modified_time': file_stat.st_mtime
        }