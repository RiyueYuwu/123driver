import re
import os
from typing import Dict, List, Optional, Any

from _api import API
from _logger import logger
from _utils import async_to_sync, Utils


class Driver:
    
    def __init__(self, client_id: str, client_secret: str, base_url: str = "https://open-api.123pan.com"):
        self.utils = Utils()
        self.api = API(client_id=client_id, client_secret=client_secret, base_url=base_url)
        self.api.check_access_token()
        logger.info("Driver initialized.")
        
    async def user_info(self):
        """获取用户信息"""
        logger.info("Calling user_info()")
        user_info = await self.api.get_user_info()
        if user_info.get('code') == 0:
            logger.info("User info fetched successfully.")
        else:
            logger.error(f"Error: {user_info.get('message')}")
        logger.debug(f"user_info result: {user_info}")
        return user_info
    
    async def list_dir(
        self,
        dir: str = '/',
        page: int = 1,
        limit: int = 100,
        return_parentFileId: bool = False,
    ):
        """获取目录下的文件列表"""
        logger.info(f"Calling list_dir(dir={dir}, page={page}, limit={limit})")
        parentFileId = 0
        dir_list = dir.split('/')
        files = await self._list_dir_fetch_or_cache(parentFileId=parentFileId, page=page, limit=limit)
        for i in dir_list:
            logger.debug(f"Processing dir segment: '{i}' with parentFileId={parentFileId}")
            if i:
                parentFileId = await self._list_dir_fetch_parentFileId(parentFileId, files, i, limit)
                logger.debug(f"Updated parentFileId: {parentFileId}")
                files = await self._list_dir_fetch_or_cache(parentFileId=parentFileId, page=page, limit=limit)
        logger.info(f"Returning file list for dir={dir}")
        if return_parentFileId:
            return files['data']['fileList'], parentFileId
        else:
            return files['data']['fileList']
    
    async def _list_dir_fetch_or_cache(
        self,
        parentFileId: int,
        page: int = 1,
        limit: int = 100,
        lastFileId: Optional[int] = None,
    ) -> Dict[str, Any]:
        """从缓存中获取目录下的文件列表，如果缓存中没有，则从API获取"""
        files_list = []
        pages = self.utils.computing_page(page=page, limit=limit)
        for p in pages:
            logger.debug(f"_list_dir_fetch_or_cache(parentFileId={parentFileId}, page={p}.")
            files = self.utils.get_cached_files(parentFileId=parentFileId, page=p)
            if not files:
                logger.debug(f"No cached files found for parentFileId={parentFileId}, fetching from API.")
                files = await self.api.list_files_v2(parentFileId=parentFileId, limit=limit, lastFileId=lastFileId)
                self.utils.cache_files(files=files, parentFileId=parentFileId, page=p)
                return files
            else:
                logger.debug(f"Cached files found for parentFileId={parentFileId}, returning from cache.")
                files = self.utils.get_cached_files(parentFileId=parentFileId, page=p)
            files_list.append(files)
        return self.utils.merge_files(files_list)

    async def _list_dir_fetch_parentFileId(
        self,
        parentFileId: int,
        files: Dict[str, Any],
        filename: str,
        limit: int = 100,
        lastFileId: Optional[int] = None,
    ) -> int:
        logger.info(f"_list_dir_fetch_parentFileId(parentFileId={parentFileId}, filename={filename}, limit={limit}, lastFileId={lastFileId})")
        if await self._list_dir_in_files(files, filename) and lastFileId != -1: # 文件名在文件列表中，直接返回parentFileId
            logger.debug(f"Found {filename} in files, getting parentFileId.")
            return await self._list_dir_get_parentFileId(files, filename)
        elif lastFileId != -1: # 文件名不在文件列表中，但有lastFileId，继续搜索
            logger.debug(f"Fetching more files for parentFileId={parentFileId} with lastFileId={lastFileId}")
            files = await self.api.list_files_v2(parentFileId=parentFileId, limit=limit, lastFileId=lastFileId)
            return await self._list_dir_fetch_parentFileId(parentFileId, files, filename, limit, files['data']['lastFileId'])
        else: # 文件名不在文件列表中，且lastFileId等于-1，说明文件列表已经遍历完毕，没有找到返回0
            if await self._list_dir_in_files(files, filename):
                logger.debug(f"Found {filename} in files after lastFileId exhausted.")
                return await self._list_dir_get_parentFileId(files, filename)
            else:
                logger.error(f"Error: {filename} not found in {files['data']['fileList']}")
                return 0

    async def _list_dir_get_parentFileId(
       self,
       files: Dict[str, Any],
       filename: str,
    ) -> int:
        """获取指定目录的parentFileId"""
        logger.info(f"_list_dir_get_parentFileId(filename={filename})")
        for f in files['data']['fileList']:
            if f['type'] == 1 and f['filename'] == filename:
                logger.debug(f"Found parentFileId: {f['fileId']} for filename: {filename}")
                return f['fileId']
        logger.warning(f"Directory {filename} not found in fileList.")
        return 0
            
    async def _list_dir_in_files(
        self,
        files: Dict[str, Any],
        filename: str,
    ) -> bool:
        """判断目标文件是否在文件列表中"""
        logger.info(f"_list_dir_in_files(filename={filename})")
        for f in files['data']['fileList']:
            if f['type'] == 1 and f['filename'] == filename:
                logger.debug(f"Found directory {filename} in fileList.")
                return True
        logger.debug(f"Directory {filename} not found in fileList.")
        return False

    async def fetch_file(self, parentFileId: int, filename: str, lastFileId: Optional[int] = None, page: int = 1) -> Dict[str, Any]:
        """获取文件信息"""
        logger.info(f"Calling fetch_file(parentFileID={parentFileId}, filename={filename})")
        files = self.utils.get_cached_files(parentFileId=parentFileId, page=page)
        if not files:
            files = await self.api.list_files_v2(parentFileId=parentFileId, limit=100, lastFileId=lastFileId)
            self.utils.cache_files(files=files, parentFileId=parentFileId, page=page)
        for f in files['data']['fileList']:
            if f['type'] == 0 and f['filename'] == filename:    
                logger.debug(f"Found file {filename} in fileList.")
                return f
        if lastFileId != -1: # 文件名不在文件列表中，但有lastFileId，继续搜索
            logger.debug(f"Fetching more files for parentFileId={parentFileId} with lastFileId={lastFileId}")
            await self.fetch_file(parentFileId=parentFileId, filename=filename, lastFileId=lastFileId, page=page+1)   
        logger.error(f"Error: {filename} not found in {files['data']['fileList']}")
        return {}
    
    async def download_file(
        self,
        file_path: str,
        save_path: str,
        progress_bar: bool = True,
    ):
        """下载文件"""
        logger.info(f"Calling download_file(file_path={file_path}, save_path={save_path})")
        dirname = os.path.dirname(file_path)
        _, parentFileId = await self.list_dir(dir=dirname, return_parentFileId=True)
        file = await self.fetch_file(parentFileId=parentFileId, filename=os.path.basename(file_path))
        if file:
            logger.debug(f"Downloading file {file_path} to {save_path}")
            downlod_info = await self.api.download_file(fileId=file['fileId'])
            if downlod_info.get('code') == 0:
                logger.debug(f"Downloading file {file_path} to {save_path} started.")
                self.utils.download_file(url=downlod_info['data']['downloadUrl'], file_path=save_path, progress_bar=progress_bar)
            else:
                logger.error(f"Error: {downlod_info.get('message')}")
        else:
            logger.error(f"Error: {file_path} not found.")
        return downlod_info
        


@async_to_sync
async def main() -> None:
    from privacy import client_id, client_secret
    from _utils import Utils, time
    utils = Utils()
    logger.info("Starting main()")
    driver = Driver(client_id=client_id, client_secret=client_secret)
    start_time = time.time()
    dirs = await driver.list_dir(dir='/')
    

    
if __name__ == '__main__':
    _ = main()