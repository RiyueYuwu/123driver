import time
import asyncio
from functools import wraps
from typing import Any, Dict

import httpx
from tqdm import tqdm
from rich.console import Console
from rich.table import Table
from cachetools import cached, TTLCache


class Utils:
    
    def __init__(self):
        self.console = Console()
        self.files_cache = TTLCache(maxsize=1000, ttl=600)  # 10分钟
    
    def format_file_size(self, size_bytes: int, decimal_places: int = 1) -> str:
        """
        格式化文件大小显示
        
        Args:
            size_bytes: 文件大小（字节）
            decimal_places: 小数位数，默认1位，可选1或2位
            
        Returns:
            格式化后的文件大小字符串，如 "1.2 KB", "1.23 MB"
        """
        if size_bytes == 0:
            return "0 B"
        
        # 定义单位
        units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
        unit_index = 0
        
        # 计算合适的单位
        size = float(size_bytes)
        while size >= 1024.0 and unit_index < len(units) - 1:
            size /= 1024.0
            unit_index += 1
        
        # 格式化显示
        if unit_index == 0:  # B单位，不显示小数
            return f"{int(size)} {units[unit_index]}"
        else:
            # 确保小数位数不超过2位
            decimal_places = min(decimal_places, 2)
            format_str = f"{{:.{decimal_places}f}} {units[unit_index]}"
            return format_str.format(size)
    
    def print_file_list(self, files):
        """
        打印文件列表
        
        Args:
            files: 文件列表
        """
        table = Table(title="文件列表")
        table.add_column("类型", style="cyan", width=10)
        table.add_column("名称", style="magenta")
        table.add_column("大小", style="green", width=15)
        table.add_column("修改时间", style="yellow", width=20)
    
        for file in files:
            type = self.print_file_type(file)
            name = file['filename']
            size = self.format_file_size(file.get('size', 0))
            modified = file.get('updateAt', '')
            
            table.add_row(type, name, size, modified)

        self.console.print(table)
        
    def print_file_type(self, file: Dict[str, Any]) -> str:
        """
        格式化文件类型显示
        
        Args:
            file: 文件信息字典            
            
        Returns:
            格式化后的文件类型字符串，如 "文件夹", "音频", "视频", "图片", "未知"
        """
        if file['type'] == 1:
            return "文件夹"
        else:
            if file['category'] == 1:
                return "音频"
            elif file['category'] == 2:
                return "视频"
            elif file['category'] == 3:
                return "图片"
            else:
                return "未知"
            
    def computing_page(self, page: int, limit: int) -> list:
        """
        计算分页信息
        
        Args:
            page: 当前页码
            limit: 每页显示数量
            
        Returns:
            包含所有分页的列表，如 [1, 2, 3]
        """
        pages = []
        for i in range(page * limit - limit, page * limit, 100):
            page_i = i // 100 + 1
            pages.append(page_i)
        return pages
    
    def merge_files(self, files_list: list[Dict[str, Any]]) -> Dict[str, Any]:
        """
        合并文件列表
        
        Args:
            files_list: 文件列表响应json数据列表
            
        Returns:
            合并后的文件列表响应json数据
        """
        merged_files = {
            'code': 0,
            'message': 'ok',
            'data': {'lastFileId': 0,'fileList': []},
            'x-traceID': ''
        }
        for files in files_list:
            merged_files['code'] = files['code']
            merged_files['message'] = files['message']
            merged_files['data']['lastFileId'] = files['data']['lastFileId']
            merged_files['data']['fileList'] += files['data']['fileList']
            merged_files['x-traceID'] = files['x-traceID']
        return merged_files
        
            
    def cache_files(self, files: Dict[str, Any], parentFileId: int, page: int = 1):
        """
        缓存文件列表
        
        Args:
            files: 文件列表
            parentFileId: 父目录ID
            page: 页码
        """
        cache_key = f"files:{parentFileId}:{page}"
        self.files_cache[cache_key] = {
            'files': files,
            'timestamp': time.time()
        }
        
    def get_cached_files(self, parentFileId: int, page: int = 1) -> Dict[str, Any]:
        """获取缓存的文件列表"""
        cache_key = f"files:{parentFileId}:{page}"
        if self.files_cache.get(cache_key):
            return self.files_cache[cache_key]['files']
        else:
            return {}
    
    def cache_limit(self, maxsize=1000, ttl=300):
        """
        设置缓存文件大小限制
        
        Args:
            maxsize: 缓存文件大小限制
            ttl: 缓存过期时间
        """
        self.files_cache = TTLCache(maxsize=maxsize, ttl=ttl)
        
    def computing_time(self, start_time: float) -> str:
        """
        计算耗时
        
        Args:
            start_time: 开始时间
            
        Returns:
            格式化后的耗时字符串，如 "0.123 s"
        """
        end_time = time.time()
        elapsed_time = end_time - start_time
        return f"{elapsed_time:.3f} s"
    
    def download_file(self, url: str, file_path: str, progress_bar: bool = True) -> None:
        """
        下载文件
        
        Args:
            url: 文件URL
            file_path: 保存路径
            progress_bar: 是否显示进度条
        """
        with httpx.stream("GET", url) as response:
            response.raise_for_status()
            total_size = int(response.headers.get("Content-Length", 0))
            if progress_bar:
                progress = tqdm(total=total_size, unit="iB", unit_scale=True)
            with open(file_path, "wb") as file:
                for data in response.iter_bytes():
                    file.write(data)
                    if progress_bar:
                        progress.update(len(data))
            if progress_bar:
                progress.close()


def async_to_sync(func):
    """装饰器: 将异步方法转换为同步方法, 自动处理asyncio.run()"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))
    return wrapper