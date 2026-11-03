# -*- coding: utf-8 -*-
import uuid
import json
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.profile import region_provider

from aliyunsdkdysmsapi.request.v20170525 import SendSmsRequest
from django.conf import settings

"""
短信业务调用接口示例，版本号：v20170525
"""

# 注意：不要更改
REGION = "cn-hangzhou"
PRODUCT_NAME = "Dysmsapi"
DOMAIN = "dysmsapi.aliyuncs.com"

_acs_client = None


def _get_acs_client():
    global _acs_client
    if _acs_client is None:
        config = getattr(settings, "ALIYUN_SMS_CONFIG", None) or {}
        _acs_client = AcsClient(config["id"], config["secret"], REGION)
        region_provider.add_endpoint(PRODUCT_NAME, REGION, DOMAIN)
    return _acs_client


def _send_sms_info(business_id, phone_numbers, sign_name, template_code, template_param=None):
    smsRequest = SendSmsRequest.SendSmsRequest()
    smsRequest.set_TemplateCode(template_code)
    if template_param is not None:
        smsRequest.set_TemplateParam(template_param)
    smsRequest.set_OutId(business_id)
    smsRequest.set_SignName(sign_name)
    smsRequest.set_PhoneNumbers(phone_numbers)
    return _get_acs_client().do_action_with_exception(smsRequest)


def aly_send_sms(mobile, template_id, params):
    status = False
    # uuid4 为随机 UUID；uuid1 含 MAC 地址与时间戳，可推测主机信息
    business_id = uuid.uuid4()
    sign_name = settings.ALIYUN_SMS_CONFIG["name"]
    try:
        sms_info = _send_sms_info(business_id, mobile, sign_name, template_id, params)
        if isinstance(sms_info, bytes):
            sms_info = sms_info.decode("utf-8")
        rc_request = json.loads(sms_info)
        if rc_request.get("Code") == "OK":
            status = True
    except Exception:
        # SDK 调用/响应解析失败：按既有语义返回 False，不向上抛
        return False
    return status
