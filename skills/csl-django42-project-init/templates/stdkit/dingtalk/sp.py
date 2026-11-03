import json
from enum import Enum
from alibabacloud_dingtalk.workflow_1_0 import models as workflow_models
from stdkit.dingtalk.client import DingTalk
from alibabacloud_tea_util import models as util_models


class EComponentName(Enum):
    TextField = "TextField"  # 单行输入框
    TextareaField = "TextareaField"  # 多行输入框
    NumberField = "NumberField"  # 数字输入框
    DDSelectField = "DDSelectField"  # 单选框
    DDMultiSelectField = "DDMultiSelectField"  # 多选框
    DDDateField = "DDDateField"  # 日期控件
    DDDateRangeField = "DDDateRangeField"  # 时间区间控件
    TextNote = "TextNote"  # 文字说明控件
    PhoneField = "PhoneField"  # 电话控件
    DDPhotoField = "DDPhotoField"  # 图片控件
    MoneyField = "MoneyField"  # 金额控件
    TableField = "TableField"  # 明细控件
    DDAttachment = "DDAttachment"  # 附件
    InnerContactField = "InnerContactField"  # 联系人控件
    DepartmentField = "DepartmentField"  # 部门控件
    RelateField = "RelateField"  # 关联审批单
    AddressField = "AddressField"  # 省市区控件
    StarRatingField = "StarRatingField"  # 评分控件
    FormRelateField = "FormRelateField"  # 关联控件


class DingtalkSP:
    def __init__(self):
        self.dingtalk = DingTalk()
        self.workflow_client = self.dingtalk.create_workflow_client()
        self._access_token = None

    @property
    def access_token(self):
        if getattr(self, "_access_token", None) is not None:
            return self._access_token
        return self.dingtalk.get_access_token()

    @access_token.setter
    def access_token(self, value):
        self._access_token = value

    def get_sp_detail(self, sp_id):
        get_process_instance_headers = workflow_models.GetProcessInstanceHeaders()
        get_process_instance_headers.x_acs_dingtalk_access_token = self.access_token
        get_process_instance_request = workflow_models.GetProcessInstanceRequest(process_instance_id=sp_id)

        response = self.workflow_client.get_process_instance_with_options(
            get_process_instance_request, get_process_instance_headers, util_models.RuntimeOptions()
        )
        return response

    def get_sp_schema(self, process_code) -> workflow_models.QuerySchemaByProcessCodeResponseBodyResult:
        query_schema_by_process_code_headers = workflow_models.QuerySchemaByProcessCodeHeaders()
        query_schema_by_process_code_headers.x_acs_dingtalk_access_token = self.access_token
        query_schema_by_process_code_request = workflow_models.QuerySchemaByProcessCodeRequest(
            process_code=process_code
        )
        response = self.workflow_client.query_schema_by_process_code_with_options(
            query_schema_by_process_code_request,
            query_schema_by_process_code_headers,
            util_models.RuntimeOptions(),
        )
        result = response.body.result
        return result

    def upload_attachment(self, originator_user_id, file_path, agent_id=None, parent_id="0", filename=None, union_id=None):
        return self.dingtalk.upload_approval_attachment(
            originator_user_id=originator_user_id,
            file_path=file_path,
            agent_id=agent_id,
            parent_id=parent_id,
            filename=filename,
            union_id=union_id,
        )

    @staticmethod
    def _get_component_type(params):
        component_type = params.get("component_type") or params.get("componentType") or params.get("type")
        if isinstance(component_type, EComponentName):
            return component_type.value
        return component_type

    def _build_attachment_value(self, originator_user_id, params, agent_id=None):
        value = params.get("value")
        if value is not None:
            if isinstance(value, str):
                return value
            return json.dumps(value, ensure_ascii=False)

        file_paths = params.get("file_paths")
        if not file_paths and params.get("file_path"):
            file_paths = [params["file_path"]]
        if not file_paths:
            return None
        if isinstance(file_paths, str):
            file_paths = [file_paths]

        filenames = params.get("filenames") or params.get("filename") or []
        if isinstance(filenames, str):
            filenames = [filenames]
        union_id = str(params.get("union_id") or "").strip()
        attachments = []
        for index, file_path in enumerate(file_paths):
            filename = filenames[index] if index < len(filenames) else None
            attachments.append(
                self.upload_attachment(
                    originator_user_id=originator_user_id,
                    file_path=file_path,
                    agent_id=params.get("agent_id") or agent_id,
                    parent_id=params.get("parent_id", "0"),
                    filename=filename,
                    union_id=union_id,
                )
            )
        return json.dumps(attachments, ensure_ascii=False)

    def submit_sp(self, originator_user_id, process_code, dept_id, params_list, agent_id=None):
        dept_id = dept_id if dept_id != 1 else -1
        start_process_instance_headers = workflow_models.StartProcessInstanceHeaders()
        start_process_instance_headers.x_acs_dingtalk_access_token = self.access_token

        form_component_values = []
        request_agent_id = agent_id
        for params in params_list:
            component_type = self._get_component_type(params)
            value = params.get("value")
            if component_type == EComponentName.DDAttachment.value:
                request_agent_id = self.dingtalk.get_agent_id(params.get("agent_id") or request_agent_id)
                value = self._build_attachment_value(originator_user_id, params, request_agent_id)
            if value is None:
                continue
            form_component_value = workflow_models.StartProcessInstanceRequestFormComponentValues(
                name=params["name"],
                value=value,
            )
            if component_type:
                form_component_value.component_type = component_type
            if params.get("id"):
                form_component_value.id = params["id"]
            biz_alias = params.get("biz_alias") or params.get("bizAlias")
            if biz_alias:
                form_component_value.biz_alias = biz_alias
            ext_value = params.get("ext_value") or params.get("extValue")
            if ext_value:
                form_component_value.ext_value = ext_value
            form_component_values.append(form_component_value)
        start_process_instance_request = workflow_models.StartProcessInstanceRequest(
            originator_user_id=originator_user_id,
            process_code=process_code,
            dept_id=dept_id,
            form_component_values=form_component_values,
        )
        if request_agent_id:
            start_process_instance_request.microapp_agent_id = int(request_agent_id)
        response = self.workflow_client.start_process_instance_with_options(
            start_process_instance_request, start_process_instance_headers, util_models.RuntimeOptions()
        )
        return response.body.instance_id
