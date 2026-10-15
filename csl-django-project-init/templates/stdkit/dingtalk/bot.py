import requests
import json
import logging
from typing import List, Dict, Union
from enum import Enum
from django.conf import settings
from django.core.cache import cache

# 日志 logger 配置
logger = logging.getLogger("django")


class MessageType(Enum):
    """消息类型枚举"""

    TEXT = "sampleText"  # 文本消息
    MARKDOWN = "sampleMarkdown"  # markdown消息
    IMAGE = "sampleImageMsg"  # 图片消息
    ACTION_CARD = "sampleActionCard"  # 卡片消息
    LINK = "sampleLink"  # 链接消息


class DingRemindType(Enum):
    """Ding通知类型枚举"""

    App = 1  # 应用内Ding
    SMS = 2  # 短信Ding
    Phone = 3  # 电话Ding


class DingTalkAppBotV2:
    """钉钉应用机器人V2版本实现"""

    def __init__(self, app_key=None, app_secret=None, robot_code=None):
        """
        初始化钉钉应用机器人
        :param app_key: 应用的AppKey
        :param app_secret: 应用的AppSecret
        :param robot_code: 机器人的robotCode
        """
        dingtalk_config = getattr(settings, "DINGTALK_CONFIG", None) or {}
        crm_config = dingtalk_config.get("crm") or {}
        self.app_key = app_key or crm_config.get("client_id")
        self.app_secret = app_secret or crm_config.get("client_secret")
        self.robot_code = robot_code or crm_config.get("robot_code")
        self.access_token = None
        self.token_expires_at = 0
        self.base_url = "https://api.dingtalk.com"

    def _get_access_token(self) -> str:
        """获取访问令牌"""
        ckey = "crm:dingtalk:access_token:{}".format(self.app_key)
        access_token = cache.get(ckey)
        if access_token:
            return access_token
        url = f"{self.base_url}/v1.0/oauth2/accessToken"
        headers = {"Content-Type": "application/json"}
        data = {"appKey": self.app_key, "appSecret": self.app_secret}

        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            result = response.json()

            if "accessToken" in result:
                self.access_token = result["accessToken"]
                cache.set(ckey, self.access_token, 7000)
                return self.access_token
            else:
                msg = f"获取access_token失败: {result}"
                logger.error(msg)
        except requests.exceptions.RequestException as e:
            msg = f"请求access_token失败: {str(e)}"
            logger.error(msg)

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头

        凭证缺失时直接抛错（与 map 模块 _require_ak 的处理一致）：继续发请求
        只会得到远端 401，本地无明确失败信号，排障成本更高。
        """
        access_token = self._get_access_token()
        if not access_token:
            raise ValueError("获取钉钉 access_token 失败，无法构造请求头")
        return {"x-acs-dingtalk-access-token": access_token, "Content-Type": "application/json"}

    def send_message(
        self,
        user_ids: Union[str, List[str]],
        msg_content: Union[str, Dict],
        msg_type: Union[str, MessageType] = MessageType.TEXT,
    ) -> str:
        """
        发送工作通知消息
        :param user_ids: 接收者的用户ID或ID列表
        :param msg_content: 消息内容
        :param msg_type: 消息类型(使用MessageType枚举)
        :return: 任务ID
        """
        url = f"{self.base_url}/v1.0/robot/oToMessages/batchSend"

        # 处理用户ID格式
        if isinstance(user_ids, str):
            receiver_ids = [user_ids]
        else:
            receiver_ids = user_ids

        if not receiver_ids:
            return

        # 处理消息类型
        if isinstance(msg_type, str):
            msg_type = MessageType(msg_type)

        # 构建消息内容
        msg = self._build_message(msg_type, msg_content)

        data = {
            "robotCode": self.robot_code,
            "userIds": receiver_ids,
            "msgKey": msg_type.value,
            "msgParam": json.dumps(msg),
        }

        try:
            response = requests.post(url, headers=self._get_headers(), json=data, timeout=30)
            result = response.json()

            if "processQueryKey" in result:
                return result["processQueryKey"]
            else:
                msg = f"发送消息失败: {result}"
                logger.error(msg)
        except requests.exceptions.RequestException as e:
            msg = f"请求失败: {str(e)}"
            logger.error(msg)

    def _build_message(self, msg_type: MessageType, content: Union[str, Dict]) -> Dict:
        """构建消息内容"""
        if msg_type == MessageType.TEXT:
            if isinstance(content, str):
                return {"content": content}
            return content

        elif msg_type == MessageType.MARKDOWN:
            if isinstance(content, str):
                return {"title": "通知", "text": content}
            return content

        elif msg_type == MessageType.ACTION_CARD:
            if not isinstance(content, dict):
                raise ValueError("actionCard类型消息必须提供完整的卡片配置")
            return content

        elif msg_type == MessageType.LINK:
            if not isinstance(content, dict):
                raise ValueError("link类型消息必须提供完整的链接配置")
            return content

        elif msg_type == MessageType.IMAGE:
            if not isinstance(content, dict):
                raise ValueError("image类型消息必须提供图片配置")
            return content

        else:
            raise ValueError(f"不支持的消息类型: {msg_type}")

    def send_group_message(
        self,
        open_conversation_id: str,
        msg_content: Union[str, Dict],
        msg_type: Union[str, MessageType] = MessageType.TEXT,
    ) -> str:
        """
        发送群聊消息
        :param open_conversation_id: 群会话ID
        :param msg_content: 消息内容
        :param msg_type: 消息类型(使用MessageType枚举)
        :return: 消息ID
        """
        url = f"{self.base_url}/v1.0/robot/groupMessages/send"

        if isinstance(msg_type, str):
            msg_type = MessageType(msg_type)

        msg = self._build_message(msg_type, msg_content)

        data = {
            "robotCode": self.robot_code,
            "openConversationId": open_conversation_id,
            "msgKey": msg_type.value,
            "msgParam": json.dumps(msg),
        }

        try:
            response = requests.post(url, headers=self._get_headers(), json=data, timeout=30)
            response.raise_for_status()
            result = response.json()
            return result.get("messageId", "")
        except requests.exceptions.RequestException as e:
            msg = f"发送群消息失败: {str(e)}"
            logger.error(msg)

    def send_ding_message(
        self,
        user_ids: Union[str, List[str]],
        msg: str,
        remind_type: Union[int, DingRemindType] = DingRemindType.App,
    ) -> str:
        """
        发送ding消息
        :param user_ids: 接收者的用户ID或ID列表
        :param msg_content: 消息内容
        :param remind_type: 提醒类型(使用DingRemindType枚举)
        :return: 任务ID
        """
        url = f"{self.base_url}/v1.0/robot/ding/send"

        # 处理用户ID格式
        if isinstance(user_ids, str):
            receiver_ids = [user_ids]
        else:
            receiver_ids = user_ids

        if not receiver_ids:
            return

        # 处理消息类型
        if isinstance(remind_type, int):
            remind_type = DingRemindType(remind_type)

        data = {
            "robotCode": self.robot_code,
            "receiverUserIdList": receiver_ids,
            "remindType": remind_type.value,
            "content": msg,
        }

        try:
            response = requests.post(url, headers=self._get_headers(), json=data, timeout=30)
            result = response.json()

            if "openDingId" in result:
                return result["openDingId"]
            else:
                error_msg = f"发送消息失败: {result}"
                logger.error(error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"请求失败: {str(e)}"
            logger.error(error_msg)
