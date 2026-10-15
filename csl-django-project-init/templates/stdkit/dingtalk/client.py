# -*- coding: utf-8 -*-
import hashlib
import os
import time
import requests
from alibabacloud_dingtalk.oauth2_1_0.client import Client as OAuthClient
from alibabacloud_tea_openapi import models as openapi_models
from alibabacloud_dingtalk.oauth2_1_0 import models as oauth_models
from alibabacloud_dingtalk.workflow_1_0.client import Client as WorkflowClient
from alibabacloud_dingtalk.workflow_1_0 import models as dingtalkworkflow__1__0_models
from alibabacloud_dingtalk.storage_1_0.client import Client as StorageClient
from alibabacloud_dingtalk.storage_1_0 import models as dingtalkstorage__1__0_models

from django.conf import settings
from django.core.cache import cache
from stdkit.dingtalk.api import api as dingtalk_api
from stdkit.dingtalk import schema
import typing
from alibabacloud_dingtalk.calendar_1_0.client import Client as CalendarClient
from alibabacloud_dingtalk.calendar_1_0 import models as calendar_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_tea_util.client import Client as UtilClient
from stdkit.utils.utils import Util
from datetime import timezone as dt_timezone, timedelta
import logging

# 日志 logger 配置
logger = logging.getLogger("django")


class DingTalk:
    def __init__(self, corp_id=None, client_id=None, client_secret=None):
        self.corp_id = corp_id or settings.DINGTALK_CONFIG["corp_id"]
        self.client_id = client_id or settings.DINGTALK_CONFIG["crm"]["client_id"]
        self.client_secret = client_secret or settings.DINGTALK_CONFIG["crm"]["client_secret"]
        self.auth_client = self.create_auth_client()

    def create_auth_client(self) -> OAuthClient:
        config = openapi_models.Config()
        config.protocol = "https"
        config.region_id = "central"
        return OAuthClient(config)

    def create_workflow_client(self) -> WorkflowClient:
        config = openapi_models.Config()
        config.protocol = "https"
        config.region_id = "central"
        return WorkflowClient(config)

    def create_storage_client(self) -> StorageClient:
        config = openapi_models.Config()
        config.protocol = "https"
        config.region_id = "central"
        return StorageClient(config)

    def create_calendar_client(self) -> CalendarClient:
        config = openapi_models.Config()
        config.protocol = "https"
        config.region_id = "central"
        return CalendarClient(config)

    def get_agent_id(self, agent_id=None):
        if agent_id:
            return int(agent_id)

        dingtalk_config = getattr(settings, "DINGTALK_CONFIG", {})
        crm_config = dingtalk_config.get("crm", {})
        agent_id = crm_config.get("agent_id") or dingtalk_config.get("agent_id")
        if not agent_id:
            raise ValueError("agent_id is required for DingTalk approval attachment upload")
        return int(agent_id)

    def get_access_token(self) -> str:
        ckey = "crm:dingtalk:access_token:{}:{}".format(self.corp_id, self.client_id)
        access_token = cache.get(ckey)
        if not access_token:
            request = oauth_models.GetAccessTokenRequest(
                app_key=self.client_id, app_secret=self.client_secret
            )
            response = self.auth_client.get_access_token(request)
            access_token = response.body.access_token
            expires_in = int(getattr(response.body, "expire_in", None) or 7200)
            cache.set(ckey, access_token, max(expires_in - 200, 60))
        return access_token

    def get_user_info_by_code(self, code) -> schema.UserInfo:
        access_token = self.get_access_token()
        request = dingtalk_api.OapiV2UserGetuserinfoRequest()
        request.code = code
        response = request.getResponse(access_token)

        if response["errcode"] != 0:
            raise Exception(response["errmsg"])

        user_info = schema.UserInfo(
            name=response["result"]["name"],
            userid=response["result"]["userid"],
        )
        return user_info

    def get_all_departments(self, dept_id=None):
        all_departments = []

        # 获取当前部门的下一级部门列表
        departments = self.get_department_list(dept_id)

        for department in departments:
            all_departments.append(department)

            # 递归地获取每个下级部门的所有子部门
            sub_departments = self.get_all_departments(department.dept_id)
            all_departments.extend(sub_departments)

        return all_departments

    def get_department_list(self, dept_id=None) -> typing.List[schema.DepartmentInfo]:
        access_token = self.get_access_token()
        request = dingtalk_api.OapiV2DepartmentListsubRequest()
        if dept_id:
            request.dept_id = dept_id

        response = request.getResponse(access_token)

        if response["errcode"] != 0:
            raise Exception(response["errmsg"])

        result = []
        for item in response["result"]:
            result.append(
                schema.DepartmentInfo(dept_id=item["dept_id"], name=item["name"], parent_id=item["parent_id"])
            )
        return result

    def get_department_info(self, dept_id) -> schema.DepartmentInfo:
        access_token = self.get_access_token()
        request = dingtalk_api.OapiV2DepartmentGetRequest()
        request.dept_id = dept_id

        response = request.getResponse(access_token)

        if response["errcode"] != 0:
            raise Exception(response["errmsg"])

        return schema.DepartmentInfo(
            dept_id=response["result"]["dept_id"],
            name=response["result"]["name"],
            parent_id=response["result"].get("parent_id"),
            org_dept_owner=response["result"].get("org_dept_owner"),
            order=response["result"]["order"],
        )

    def get_user_id_list(self, dept_id) -> typing.List[str]:
        access_token = self.get_access_token()
        request = dingtalk_api.OapiUserListidRequest()
        request.dept_id = dept_id

        response = request.getResponse(access_token)

        if response["errcode"] != 0:
            raise Exception(response["errmsg"])

        return response["result"].get("userid_list", [])

    def get_user_info(self, user_id) -> schema.UserInfo:
        access_token = self.get_access_token()
        request = dingtalk_api.OapiV2UserGetRequest()
        request.userid = user_id

        response = request.getResponse(access_token)

        if response["errcode"] != 0:
            raise Exception(response["errmsg"])

        return schema.UserInfo(
            name=response["result"]["name"],
            unionid=response["result"]["unionid"],
            userid=response["result"]["userid"],
            dept_id_list=response["result"]["dept_id_list"],
            avatar=response["result"].get("avatar"),
            job=response["result"].get("title"),
        )

    def create_calendar(self, user_id, summary, start_time, attendees):
        client = self.create_calendar_client()
        create_event_headers = calendar_models.CreateEventHeaders()
        create_event_headers.x_acs_dingtalk_access_token = self.get_access_token()
        extra = {"noChatNotification": "false", "noPushNotification": "false"}
        online_meeting_info = calendar_models.CreateEventRequestOnlineMeetingInfo(type="dingtalk")
        attendee_list = []
        for attendee in attendees:
            attendee_list.append(
                calendar_models.CreateEventRequestAttendees(
                    id=attendee["id"], is_optional=attendee["is_optional"]
                )
            )

        tz = dt_timezone(timedelta(hours=8))
        start_time = start_time.replace(tzinfo=tz)
        start = calendar_models.CreateEventRequestStart(
            date_time=start_time.isoformat(), time_zone="Asia/Shanghai"  # '2021-09-20T10:15:30+08:00'
        )
        end = calendar_models.CreateEventRequestEnd(
            date_time=(start_time + Util().timedelta(minutes=30)).isoformat(),  # '2021-09-20T10:15:30+08:00'
            time_zone="Asia/Shanghai",
        )
        create_event_request = calendar_models.CreateEventRequest(
            summary=summary,
            start=start,
            end=end,
            is_all_day=False,
            attendees=attendee_list,
            online_meeting_info=online_meeting_info,
            extra=extra,
        )
        response = client.create_event_with_options(
            user_id, "primary", create_event_request, create_event_headers, util_models.RuntimeOptions()
        )
        return response.body.id

    def get_process_instance_ids(
        self, process_code, start_time, end_time, next_token=0, max_results=10, user_ids=None, statuses=None
    ):
        """
        获取审批实例ID列表
        https://open.dingtalk.com/document/orgapp/obtain-an-approval-list-of-instance-ids
        :param process_code: 审批流程模板唯一标识
        :param start_time: 审批实例开始时间，Unix时间戳，单位毫秒。
        :param end_time: 审批实例结束时间，Unix时间戳，单位毫秒。
        :param next_token: 分页游标。如果是首次调用，该参数传0。如果是非首次调用，该参数传上次调用时返回的nextToken。
        :param max_results: 分页参数，每页大小，最多传20。
        :param user_ids: ["String"] 发起人userId列表，最大列表长度为10。
        :param statuses: ["String"] 流程实例状态：RUNNING：审批中 TERMINATED：已撤销 COMPLETED：审批完成
        :return: {
            "result" : {
            "list" : [ "123" ],
            "nextToken" : "10"
            },
            "success" : true
        }
        """
        if not user_ids:
            user_ids = []
        if not statuses:
            statuses = ["COMPLETED"]
        client = self.create_workflow_client()
        list_process_instance_ids_headers = dingtalkworkflow__1__0_models.ListProcessInstanceIdsHeaders()
        access_token = self.get_access_token()
        list_process_instance_ids_headers.x_acs_dingtalk_access_token = access_token
        list_process_instance_ids_request = dingtalkworkflow__1__0_models.ListProcessInstanceIdsRequest(
            process_code=process_code,  # 审批流程模板唯一标识
            start_time=start_time,  # 开始时间 毫秒
            end_time=end_time,  # 结束时间 毫秒
            next_token=next_token,  # 分页标记，第一次请求不填，后续请求填上一次请求返回的next_token值
            max_results=max_results,  # 分页大小，最大100
            user_ids=user_ids,  # 发起人userid列表
            statuses=statuses,  # 审批状态列表
        )
        try:
            rs = client.list_process_instance_ids_with_options(
                list_process_instance_ids_request,
                list_process_instance_ids_headers,
                util_models.RuntimeOptions(),
            )
            if rs.status_code == 200:
                return rs.body
            else:
                logger.error(f"获取审批模版{process_code}实例ID列表失败")
        except Exception as err:
            # err 中含有 code 和 message 属性，可帮助开发定位问题
            if not UtilClient.empty(err.code) and not UtilClient.empty(err.message):
                logger.error("error_code: %s, error: %s", err.code, err.message)
            return None

    @staticmethod
    def _get_file_md5(file_path):
        md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                md5.update(chunk)
        return md5.hexdigest()

    def _retry_call(self, func, desc, log_args=(), max_retries=2, interval=2):
        """执行 func，失败时按 interval 秒重试，重试耗尽后抛出最后一次异常。

        :param func: 无参可调用对象，成功时返回结果
        :param desc: 日志前缀，后面拼接 "(attempt %d/%d): %s" 三个占位
        :param log_args: 插入到 attempt 参数之前的额外日志参数
        :param max_retries: 最大重试次数，总尝试次数为 max_retries + 1
        :param interval: 重试间隔（秒）
        """
        for attempt in range(max_retries + 1):
            try:
                return func()
            except Exception as err:
                logger.error(
                    desc + " (attempt %d/%d): %s",
                    *(tuple(log_args) + (attempt + 1, max_retries + 1, err))
                )
                if attempt < max_retries:
                    time.sleep(interval)
                else:
                    raise

    def upload_approval_attachment(
        self,
        originator_user_id,
        file_path,
        agent_id=None,
        parent_id="0",
        filename=None,
        timeout=60,
        union_id=None,
    ):
        """
        上传审批附件，返回可提交给 DDAttachment 控件的附件信息。
        :param originator_user_id: 审批发起人 userId
        :param file_path: 本地附件路径
        :param agent_id: 钉钉应用 agentId，默认读取 settings.DINGTALK_CONFIG
        :param parent_id: 审批附件空间目录，默认根目录 0
        :param filename: 提交到钉盘的文件名，默认使用本地文件名
        :param timeout: 上传 OSS 的超时时间
        :param union_id: 审批发起人 unionId，钉钉硬性要求，GetFileUploadInfo/CommitFile 均必传
        :return: {"spaceId": "...", "fileId": "...", "fileName": "...", "fileSize": "...", "fileType": "..."}
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError(file_path)

        union_id = str(union_id or "").strip()
        if not union_id:
            raise ValueError("缺少发起人 unionId，无法上传审批附件")

        access_token = self.get_access_token()
        agent_id = self.get_agent_id(agent_id)
        filename = filename or os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        file_md5 = self._get_file_md5(file_path)
        file_type = os.path.splitext(filename)[1].lstrip(".")

        workflow_client = self.create_workflow_client()
        storage_client = self.create_storage_client()
        runtime = util_models.RuntimeOptions()

        # Step 1: 获取审批附件空间
        def _get_space_id():
            get_space_headers = dingtalkworkflow__1__0_models.GetAttachmentSpaceHeaders()
            get_space_headers.x_acs_dingtalk_access_token = access_token
            get_space_request = dingtalkworkflow__1__0_models.GetAttachmentSpaceRequest(
                agent_id=agent_id,
                user_id=originator_user_id,
            )
            space_response = workflow_client.get_attachment_space_with_options(
                get_space_request, get_space_headers, runtime,
            )
            return str(space_response.body.result.space_id)

        space_id = self._retry_call(_get_space_id, "获取审批附件空间失败")

        # Step 2: 获取上传信息
        def _get_upload_info():
            upload_headers = dingtalkstorage__1__0_models.GetFileUploadInfoHeaders()
            upload_headers.x_acs_dingtalk_access_token = access_token
            upload_request = dingtalkstorage__1__0_models.GetFileUploadInfoRequest(
                multipart=False,
                protocol="HEADER_SIGNATURE",
                union_id=union_id,
                option=dingtalkstorage__1__0_models.GetFileUploadInfoRequestOption(
                    pre_check_param=dingtalkstorage__1__0_models.GetFileUploadInfoRequestOptionPreCheckParam(
                        md_5=file_md5,
                        name=filename,
                        parent_id=str(parent_id),
                        size=file_size,
                    )
                ),
            )
            return storage_client.get_file_upload_info_with_options(
                space_id, upload_request, upload_headers, runtime,
            ).body

        upload_info = self._retry_call(_get_upload_info, "获取附件上传信息失败")

        if not upload_info.header_signature_info:
            raise ValueError("DingTalk did not return header_signature_info")
        resource_urls = upload_info.header_signature_info.resource_urls or []
        if not resource_urls:
            raise ValueError("DingTalk did not return file upload resource url")

        # Step 3: PUT 上传文件到 OSS（只能使用钉钉返回的签名头，附加 Content-Type 等未参与签名的头会导致 403）
        headers = dict(upload_info.header_signature_info.headers or {})
        with open(file_path, "rb") as f:
            response = requests.put(resource_urls[0], data=f, headers=headers, timeout=timeout)
        response.raise_for_status()

        # Step 4: commit 提交文件（OSS PUT 已成功，commit 失败会导致文件孤立，记录 upload_key 便于排查）
        upload_key = upload_info.upload_key

        def _commit_file():
            commit_headers = dingtalkstorage__1__0_models.CommitFileHeaders()
            commit_headers.x_acs_dingtalk_access_token = access_token
            commit_request = dingtalkstorage__1__0_models.CommitFileRequest(
                name=filename,
                parent_id=str(parent_id),
                upload_key=upload_key,
                union_id=union_id,
                option=dingtalkstorage__1__0_models.CommitFileRequestOption(
                    size=file_size,
                ),
            )
            return storage_client.commit_file_with_options(
                space_id, commit_request, commit_headers, runtime,
            ).body.dentry

        dentry = self._retry_call(
            _commit_file, "附件 commit 失败 upload_key=%s", log_args=(upload_key,)
        )

        return {
            "spaceId": space_id,
            "fileId": str(dentry.id),
            "fileName": filename,
            "fileSize": str(file_size),
            "fileType": file_type,
        }

    def get_space_with_download_auth(
        self, process_instance_id: str, file_id: str, with_comment_attachment: bool = False
    ) -> typing.Optional[str]:
        """
        获取审批附件下载授权链接（新版接口）
        https://open.dingtalk.com/document/development/download-an-approval-attachment
        :param process_instance_id: 审批实例ID
        :param file_id: 文件fileId，从审批实例详情中获取
        :param with_comment_attachment: 是否包含评论中的附件
        :return: OSS下载链接(downloadUri)，失败返回None
        """

        access_token = self.get_access_token()
        url = "https://api.dingtalk.com/v1.0/workflow/processInstances/spaces/files/urls/download"
        headers = {
            "x-acs-dingtalk-access-token": access_token,
            "Content-Type": "application/json",
        }
        body = {
            "processInstanceId": process_instance_id,
            "fileId": str(file_id),
        }
        if with_comment_attachment:
            body["withCommentAttatchment"] = True

        try:
            resp = requests.post(url, json=body, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            result = data.get("result", {})
            download_uri = result.get("downloadUri")
            if download_uri:
                return download_uri
            logger.error(
                f"获取审批附件下载授权失败: {data}, "
                f"process_instance_id={process_instance_id}, file_id={file_id}"
            )
        except requests.RequestException as e:
            logger.error(
                "获取审批附件下载授权请求异常: %s, process_instance_id=%s, file_id=%s",
                e, process_instance_id, file_id,
            )
        except Exception as e:
            logger.error(
                "获取审批附件下载授权异常: %s, process_instance_id=%s, file_id=%s",
                e, process_instance_id, file_id,
            )
        return None

    def get_sp_attachment_file(
        self, process_instance_id: str, file_id: str, real_file_name: str, file_type: str, abs_path: str, rel_path: str, with_comment_attachment: bool = False
    ) -> typing.Optional[str]:
        """
        获取审批附件
        :param process_instance_id: 审批实例ID
        :param file_id: 文件fileId，从审批实例详情中获取
        :param real_file_name: 真实文件名
        :param file_type: 文件类型
        :param abs_path: 文件绝对路径
        :param rel_path: 文件相对路径
        :param with_comment_attachment: 是否包含评论中的附件
        :return: 下载链接(file_path)，失败返回None
        """

        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                download_uri = self.get_space_with_download_auth(process_instance_id, file_id, with_comment_attachment)
                if not download_uri:
                    if attempt < max_retries:
                        time.sleep(2)
                        continue
                    return None
            except Exception as e:
                logger.error(f"附件下载异常: {e} (attempt {attempt + 1}/{max_retries + 1})")
                if attempt < max_retries:
                    time.sleep(2)
                    continue
                return None
            break

        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                # 从 OSS 下载链接获取文件内容
                response = requests.get(download_uri, timeout=60)
                if response.status_code != 200:
                    logger.error(
                        f"附件OSS下载失败: status={response.status_code}, download_uri={download_uri} "
                        f"(attempt {attempt + 1}/{max_retries + 1})"
                    )
                    if attempt < max_retries:
                        time.sleep(2)
                        continue
                    return None

                with open(abs_path, "wb") as f:
                    f.write(response.content)

                # 如果 download_uri 以 .file 结尾（加密临时链接），需用真实文件名重命名
                if download_uri.rstrip("/").endswith(".file") and real_file_name:
                    # 用真实文件名和后缀替换（官方文档要求）
                    final_ext = f".{file_type}" if file_type else os.path.splitext(real_file_name)[1]
                    base_name = os.path.splitext(real_file_name)[0]
                    final_filename = f"{base_name}{final_ext}"
                    final_abs_path = os.path.join(os.path.dirname(abs_path), final_filename)
                    final_rel_path = os.path.join(os.path.dirname(rel_path), final_filename)

                    os.rename(abs_path, final_abs_path)
                    logger.info(
                        f"附件加密链接已下载并用真实文件名重命名: "
                        f"{os.path.basename(abs_path)} -> {final_filename}"
                    )
                    return final_rel_path

                return rel_path
            except Exception as e:
                logger.error(f"附件下载异常: {e} (attempt {attempt + 1}/{max_retries + 1})")
                if attempt < max_retries:
                    time.sleep(2)
                    continue
                return None
