import re
from tabnanny import check
import time
import json
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import date, datetime
import httpx


@dataclass
class RateLimit:
    """速率限制配置"""
    endpoint: str
    max_requests_per_second: int
    last_request_time: float = 0.0
    request_count: int = 0


class API:
    """123Driver API Moudle"""
    
    def __init__(self, client_id: str, client_secret: str, base_url: str = "https://open-api.123pan.com"):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = base_url.rstrip('/')
        self.access_token: str = ''
        self.token_expires_at: float = 0.0
        
        # 初始化速率限制配置
        self.rate_limits = {
            "api/v1/access_token": RateLimit("api/v1/access_token", 1),
            "api/v1/user/info": RateLimit("api/v1/user/info", 1),
            "api/v1/file/move": RateLimit("api/v1/file/move", 1),
            "api/v1/file/delete": RateLimit("api/v1/file/delete", 1),
            "api/v1/file/list": RateLimit("api/v1/file/list", 4),
            "api/v2/file/list": RateLimit("api/v2/file/list", 3),
            "upload/v1/file/mkdir": RateLimit("upload/v1/file/mkdir", 2),
            "upload/v1/file/create": RateLimit("upload/v1/file/create", 2),
            "upload/v1/file/upload_async_result": RateLimit("upload/v1/file/upload_async_result", 1),
            "api/v1/share/list": RateLimit("api/v1/share/list", 10),
            "api/v1/share/list/info": RateLimit("api/v1/share/list/info", 10),
            "api/v1/transcode/folder/info": RateLimit("api/v1/transcode/folder/info", 20),
            "api/v1/transcode/upload/from_cloud_disk": RateLimit("api/v1/transcode/upload/from_cloud_disk", 1),
            "api/v1/transcode/delete": RateLimit("api/v1/transcode/delete", 10),
            "api/v1/transcode/video/resolutions": RateLimit("api/v1/transcode/video/resolutions", 1),
            "api/v1/transcode/video": RateLimit("api/v1/transcode/video", 3),
            "api/v1/transcode/video/record": RateLimit("api/v1/transcode/video/record", 20),
            "api/v1/transcode/video/result": RateLimit("api/v1/transcode/video/result", 20),
            "api/v1/transcode/file/download": RateLimit("api/v1/transcode/file/download", 10),
            "api/v1/transcode/m3u8_ts/download": RateLimit("api/v1/transcode/m3u8_ts/download", 20),
            "api/v1/transcode/file/download/all": RateLimit("api/v1/transcode/file/download/all", 1)
        }
        
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def _enforce_rate_limit(self, endpoint: str):
        """强制执行速率限制"""
        if endpoint not in self.rate_limits:
            return
        
        rate_limit = self.rate_limits[endpoint]
        current_time = time.time()
        
        # 如果距离上次请求不足1秒，需要等待
        if current_time - rate_limit.last_request_time < 1.0:
            wait_time = 1.0 - (current_time - rate_limit.last_request_time)
            await asyncio.sleep(wait_time)
        
        # 检查是否超过每秒请求限制
        if rate_limit.request_count >= rate_limit.max_requests_per_second:
            # 等待到下一秒
            await asyncio.sleep(1.0)
            rate_limit.request_count = 0
        
        rate_limit.last_request_time = time.time()
        rate_limit.request_count += 1
    
    async def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {
            "Content-Type": "application/json",
            'Platform': 'open_platform'
        }
        
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        
        return headers
    
    async def _make_request(self, method: str, endpoint: str,headers: dict = {}, **kwargs) -> Dict[str, Any]:
        """发送HTTP请求"""
        await self._enforce_rate_limit(endpoint)
        
        url = f"{self.base_url}/{endpoint}"
        if not headers:
            headers = await self._get_headers()
        
        response = await self.client.request(
            method=method,
            url=url,
            headers=headers,
            **kwargs
        )
        
        response.raise_for_status()
        return response.json()
    
    async def get_access_token(self) -> Dict[str, Any]:
        """获取访问令牌"""
        data = {
            "clientID": self.client_id,
            "clientSecret": self.client_secret
        }
        
        response = await self._make_request("POST", "api/v1/access_token", json=data)
        if not response['code']:
            self.access_token = response['data']["access_token"]
            self.token_expires_at = datetime.fromisoformat(response['data']["expiredAt"]).timestamp()
            await self.save_access_token()
        return response
    
    async def save_access_token(self) -> None:
        """保存访问令牌"""
        with open("access_token.json", "w") as f:
            json.dump({"acceseToken": self.access_token, "expiredAt": self.token_expires_at}, f)
    
    def check_access_token(self) -> bool:
        """检查访问令牌是否有效"""
        try:
            with open("access_token.json", "r") as f:
                data = json.load(f)
            self.access_token = data["accessToken"]
            self.token_expires_at = data["expiredAt"]
            if self.token_expires_at < datetime.now().timestamp():
                return False
            return True
        except FileNotFoundError:
            return False
        
    async def refresh_access_token(self) -> None:
        """刷新访问令牌"""
        if not self.check_access_token():
            await self.get_access_token()
    
    async def get_user_info(self) -> Dict[str, Any]:
        """获取用户信息"""
        return await self._make_request("GET", "api/v1/user/info")
    
    async def get_file_info(self, fileId: int) -> Dict[str, Any]:
        """获取单个文件信息"""
        return await self._make_request("GET", f"api/v1/file/detail?fileId={fileId}")
    
    async def fet_files_info(self, fileIds: List[int]) -> Dict[str, Any]:
        """获取多个文件信息"""
        data = {"fileIDs": fileIds}
        return await self._make_request("POST", "api/v1/file/infos", json=data)
    
    async def move_file(self, fileIDs: List[int], toParentFileID: int) -> Dict[str, Any]:
        """移动文件"""
        data = {
            "fileIDs": fileIDs,
            "toParentFileID": toParentFileID
        }
        return await self._make_request("POST", "api/v1/file/move", json=data)
    
    async def rename_single_file(self, fileId: int, fileName: str) -> Dict[str, Any]:
        """单个文件重命名"""
        data = {
            "fileID": fileId,
            "fileName": fileName
        }
        return await self._make_request("PUT", "api/v1/file/name", json=data)
    
    async def rename_files(self, renameList: List[str]) -> Dict[str, Any]:
        """批量文件重命名"""
        data = {"renameList": renameList}
        return await self._make_request("POST", "api/v1/file/rename", json=data)
    
    async def file_trash(self, fileIDs: List[int]) -> Dict[Any, Any]:
        """文件移入回收站"""
        results = []
        batch_size = 100
        if len(fileIDs) > batch_size:
            for i in range(0, len(fileIDs), batch_size):
                batch = fileIDs[i:i+batch_size]
                data = {"fileIDs": batch}
                result = await self._make_request("POST", "api/v1/file/trash", json=data)
                results.append(result)
            return {i: result for i, result in enumerate(results)}
        else:
            data = {"fileIDs": fileIDs}
        return await self._make_request("POST", "api/v1/file/trash", json=data)
    
    async def recover_file(self, fileIDs: List[int]) -> Dict[Any, Any]:
        """从回收站恢复文件"""
        results = []
        batch_size = 100
        if len(fileIDs) > batch_size:
            for i in range(0, len(fileIDs), batch_size):
                batch = fileIDs[i:i+batch_size]
                data = {"fileIDs": batch}
                result = await self._make_request("POST", "api/v1/file/recover", json=data)
                results.append(result)
            return {i: result for i, result in enumerate(results)}
        else:
            data = {"fileIDs": fileIDs}
            return await self._make_request("POST", "api/v1/file/recover", json=data)
    
    async def delete_file(self, fileIDs: List[int]) -> Dict[Any, Any]:
        """彻底删除文件"""
        results = []
        batch_size = 100
        if len(fileIDs) > batch_size:
            for i in range(0, len(fileIDs), batch_size):
                batch = fileIDs[i:i+batch_size]
                data = {"fileIDs": batch}
                result = await self._make_request("POST", "api/v1/file/delete", json=data)
                results.append(result)
            return {i: result for i, result in enumerate(results)}
        else:
            data = {"fileIDs": fileIDs}
            return await self._make_request("POST", "api/v1/file/delete", json=data)
    
    async def list_files_v1(self, parentFileId: int = 0, page: int = 1, limit: int = 100, orderBy: str = "file_name", orderDirection: str = "asc", trashed: bool = False, searchData: Optional[str] = None) -> Dict[str, Any]:
        """获取文件列表 (v1)"""
        params = {
            "parentFileId": parentFileId,
            "page": page,
            "limit": limit,
            "orderBy": orderBy,
            "orderDirection": orderDirection,
            "trashed": int(trashed)
        }
        if searchData:
            params["searchData"] = searchData
        return await self._make_request("GET", "api/v1/file/list", params=params)
    
    async def list_files_v2(self, parentFileId: int = 0, limit: int = 100, searchData: Optional[str] = None, searchMode: Optional[int] = None, lastFileId: Optional[int] = None) -> Dict[str, Any]:
        """获取文件列表 (v2)"""
        params: Dict[str, Any] = {
            "parentFileId": parentFileId,
            "limit": limit
        }
        if searchData is not None:
            params["searchData"] = searchData
        if searchMode is not None:
            params["searchMode"] = searchMode
        if lastFileId is not None:
            params["lastFileId"] = lastFileId
        return await self._make_request("GET", "api/v2/file/list", params=params)
    
    async def create_folder(self, name: str, parentID: int = 0) -> Dict[str, Any]:
        """创建文件夹"""
        data = {"name": name, "parentID": parentID}
        return await self._make_request("POST", "upload/v1/file/mkdir", json=data)
    
    async def create_file_v1(self, parentFileID: int, filename: str, etag: str, size: int, duplicate: int = 1, containDir: bool = False) -> Dict[str, Any]:
        """创建文件 (v1)"""
        data = {
            "parentFileID": parentFileID,
            "filename": filename,
            "etag": etag,
            "size": size,
            "duplicate": duplicate,
            "containDir": containDir
        }
        return await self._make_request("POST", "upload/v1/file/create", json=data)
    
    async def get_upload_url_v1(self, preuploadID: str, sliceNo: int) -> Dict[str, Any]:
        """获取上传URL (v1)"""
        data = {
            "preuploadID": preuploadID,
            "sliceNo": sliceNo
        }
        return await self._make_request("POST", "upload/v1/file/get_upload_url", json=data)
    
    async def list_upload_parts_v1(self, preuploadID: str) -> Dict[str, Any]:
        """列举已上传分片 (v1)"""
        data = {"preuploadID": preuploadID}
        return await self._make_request("POST", "upload/v1/file/list_upload_parts", json=data)
    
    async def upload_complete_v1(self, preuploadID: str) -> Dict[str, Any]:
        """完成上传 (v1)"""
        data = {"preuploadID": preuploadID}
        return await self._make_request("POST", "upload/v1/file/upload_complete", json=data)
    
    async def upload_async_result_v1(self, preuploadID: str) -> Dict[str, Any]:
        """异步轮询获取上传结果(v1)"""
        data = {"preuploadID": preuploadID}
        return await self._make_request("POST", "upload/v1/file/upload_async_result", json=data)
    
    async def create_file_v2(self, parentFileID: int, filename: str, etag: str, size: int, duplicate: int = 1, containDir: bool = False) -> Dict[str, Any]:
        """创建文件 (v2)"""
        data = {
            "parentFileID": parentFileID,
            "filename": filename,
            "etag": etag,
            "size": size,
            "duplicate": duplicate,
            "containDir": containDir
        }
        return await self._make_request("POST", "upload/v2/file/create", json=data)
    
    async def upload_slice_v2(self, preuploadID: str, sliceNo: int, sliceMD5: str, slice: bytes) -> Dict[str, Any]:
        """上传分片 (v2)"""
        headers = await self._get_headers()
        headers["Content-Type"] = "multipart/form-data"
        data = {
            "preuploadID": preuploadID,
            "sliceNo": sliceNo,
            "sliceMD5": sliceMD5,
            "slice": slice
        }
        return await self._make_request("POST", "upload/v2/file/slice", headers=headers, data=data)
    
    async def upload_complete_v2(self, preuploadID: str) -> Dict[str, Any]:
        """上传完毕 (v2)"""
        data = {"preuploadID": preuploadID}
        return await self._make_request("POST", "upload/v2/file/complete", json=data)
    
    async def get_upload_domain_v2(self):
        """获取上传域名 (v2)"""
        return await self._make_request("GET", "upload/v2/file/domain")
    
    async def single_upload_v2(self, parentFileID: int, filename: str, etag: str, size: int, file: bytes, duplicate: int = 1, containDir: bool = False) -> Dict[str, Any]:
        """单步上传文件 (v2)"""
        data = {
            "parentFileID": parentFileID,
            "filename": filename,
            "etag": etag,
            "size": size,
            "duplicate": duplicate,
            "containDir": containDir
        }
        return await self._make_request("POST", "upload/v2/file/single/create", json=data, data=file)
    
    async def create_offline_downlod(self, url: str,  dirID: int, fileName: Optional[str] = None, callBackUrl: Optional[str] = None) -> Dict[str, Any]:
        """创建离线下载任务"""
        data: Dict[str, Any] = {
            "url": url,
            "dirID": dirID,
            "fileName": fileName
        }
        if callBackUrl is not None:
            data["callBackUrl"] = callBackUrl
        return await self._make_request("POST", "/api/v1/offline/download", json=data)
    
    async def offline_progress(self, taskID: int) -> Dict[str, Any]:
        """离线下载进度"""
        params = {"taskID": taskID}
        return await self._make_request("GET", "/api/v1/offline/download/progress", params=params)
    
    async def share_payment_files(self, shareName: str, fileIDList: str, payAmount: int, resourceDesc: str, isReward: bool|int = False) -> Dict[str, Any]:
        """分享付费文件"""
        data = {
            "shareName": shareName,
            "fileIDList": fileIDList,
            "payAmount": payAmount,
            "resourceDesc": resourceDesc,
            "isReward": int(isReward)
        }
        return await self._make_request("POST", "/api/v1/share/content-payment/create", json=data)
    
    async def create_share(self, shareName: str, shareExpire: int,  fileIDList: str, sharePwd: Optional[str] = None, trafficSwitch: Optional[int] = None, trafficLimitSwitch: Optional[int] = None, trafficLimit: Optional[int] = None) -> Dict[str, Any]:
        """创建分享"""
        data: Dict[str, Any] = {    
            "shareName": shareName, 
            "shareExpire": shareExpire,
            "fileIDList": fileIDList,
        }
        if sharePwd is not None:
            data["sharePwd"] = sharePwd
        if trafficSwitch is not None:
            data["trafficSwitch"] = trafficSwitch
        if trafficLimitSwitch is not None:
            data["trafficLimitSwitch"] = trafficLimitSwitch
        if trafficLimit is not None:
            data["trafficLimit"] = trafficLimit
        return await self._make_request("POST", "api/v1/share/create", json=data)
    
    async def edit_share(self, shareIdList: List[int], trafficSwitch: Optional[int] = None, trafficLimitSwitch: Optional[int] = None, trafficLimit: Optional[int] = None) -> Dict[str, Any]:
        """编辑分享"""
        data: Dict[str, Any] = {    
            "shareIdList": shareIdList,
        }
        if trafficSwitch is not None:
            data["trafficSwitch"] = trafficSwitch
        if trafficLimitSwitch is not None:
            data["trafficLimitSwitch"] = trafficLimitSwitch
        if trafficLimit is not None:
            data["trafficLimit"] = trafficLimit
        return await self._make_request("PUT", "api/v1/share/list/info", json=data)

    async def get_share_list(self, limit: int = 100, lastShareId: int = 0) -> Dict[str, Any]:
        """获取分享列表"""
        params = {"limit": limit, "lastShareId": lastShareId}
        return await self._make_request("GET", "api/v1/share/list", params=params)
    
    async def get_transcode_folder_info(self, folder_path: str) -> Dict[str, Any]:
        """获取转码文件夹信息"""
        params = {"folder_path": folder_path}
        return await self._make_request("GET", "api/v1/transcode/folder/info", params=params)
    
    async def upload_from_cloud_disk(self, source_path: str, target_path: str) -> Dict[str, Any]:
        """从云盘上传文件进行转码"""
        data = {
            "source_path": source_path,
            "target_path": target_path
        }
        return await self._make_request("POST", "api/v1/transcode/upload/from_cloud_disk", json=data)
    
    async def delete_transcode(self, transcode_id: str) -> Dict[str, Any]:
        """删除转码任务"""
        data = {"transcode_id": transcode_id}
        return await self._make_request("POST", "api/v1/transcode/delete", json=data)
    
    async def get_video_resolutions(self) -> Dict[str, Any]:
        """获取视频分辨率列表"""
        return await self._make_request("GET", "api/v1/transcode/video/resolutions")
    
    async def transcode_video(self, file_path: str, resolution: str, output_format: str = "mp4") -> Dict[str, Any]:
        """转码视频"""
        data = {
            "file_path": file_path,
            "resolution": resolution,
            "output_format": output_format
        }
        return await self._make_request("POST", "api/v1/transcode/video", json=data)
    
    async def get_transcode_record(self, transcode_id: str) -> Dict[str, Any]:
        """获取转码记录"""
        params = {"transcode_id": transcode_id}
        return await self._make_request("GET", "api/v1/transcode/video/record", params=params)
    
    async def get_transcode_result(self, transcode_id: str) -> Dict[str, Any]:
        """获取转码结果"""
        params = {"transcode_id": transcode_id}
        return await self._make_request("GET", "api/v1/transcode/video/result", params=params)
    
    async def download_transcode_file(self, transcode_id: str, file_path: str) -> Dict[str, Any]:
        """下载转码文件"""
        params = {
            "transcode_id": transcode_id,
            "file_path": file_path
        }
        return await self._make_request("GET", "api/v1/transcode/file/download", params=params)
    
    async def download_m3u8_ts(self, m3u8_url: str, ts_file: str) -> Dict[str, Any]:
        """下载M3U8 TS文件"""
        params = {
            "m3u8_url": m3u8_url,
            "ts_file": ts_file
        }
        return await self._make_request("GET", "api/v1/transcode/m3u8_ts/download", params=params)
    
    async def download_all_transcode_files(self, transcode_id: str) -> Dict[str, Any]:
        """下载所有转码文件"""
        params = {"transcode_id": transcode_id}
        return await self._make_request("GET", "api/v1/transcode/file/download/all", params=params)
    
    async def close(self):
        """关闭客户端"""
        await self.client.aclose()