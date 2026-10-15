# 钉钉模块使用说明

`stdkit.dingtalk` 封装了钉钉 OAuth、通讯录、日程、审批、审批附件上传和附件下载能力。模块默认依赖 Django 配置中的 `DINGTALK_CONFIG`。

## 基础配置

在 Django settings 中配置钉钉应用信息：

```python
DINGTALK_CONFIG = {
    "corp_id": "dingxxxxxxxxxxxx",
    "agent_id": 123456789,
    "crm": {
        "client_id": "dingxxxx",
        "client_secret": "xxxxxxxx",
        "agent_id": 123456789,
    },
}
```

`DingTalk` 默认读取 `DINGTALK_CONFIG["crm"]["client_id"]` 和 `DINGTALK_CONFIG["crm"]["client_secret"]` 获取 access token。审批附件上传需要 `agent_id`，调用时可显式传入，也可使用配置中的 `crm.agent_id` 或顶层 `agent_id`。

## 常用客户端

```python
from stdkit.dingtalk.client import DingTalk

dingtalk = DingTalk()
access_token = dingtalk.get_access_token()

user = dingtalk.get_user_info("manager123")
departments = dingtalk.get_all_departments()
```

`DingTalk` 还提供 `create_workflow_client()`、`create_storage_client()`、`create_calendar_client()`，用于创建官方 SDK 客户端。

## 上传审批附件

审批附件不能直接提交本地文件路径。需要先上传到审批附件空间，再把返回的附件信息作为 `DDAttachment` 控件值提交。

```python
from stdkit.dingtalk.client import DingTalk

attachment = DingTalk().upload_approval_attachment(
    originator_user_id="manager123",
    file_path="/tmp/test.pdf",
    agent_id=123456789,
    filename="测试附件.pdf",
)
```

返回结构示例：

```python
{
    "spaceId": "123",
    "fileId": "file_xxx",
    "fileName": "测试附件.pdf",
    "fileSize": "2048",
    "fileType": "pdf",
}
```

## 提交带附件审批

使用 `DingtalkSP.submit_sp()` 提交审批。普通字段保持原格式；附件字段设置 `type` 或 `component_type` 为 `DDAttachment`。

```python
from stdkit.dingtalk.sp import DingtalkSP, EComponentName

instance_id = DingtalkSP().submit_sp(
    originator_user_id="manager123",
    process_code="PROC-XXXXXXXX",
    dept_id=-1,
    agent_id=123456789,
    params_list=[
        {"name": "标题", "value": "带附件审批"},
        {
            "name": "附件",
            "type": EComponentName.DDAttachment,
            "file_path": "/tmp/test.pdf",
            "filename": "测试附件.pdf",
        },
    ],
)
```

多个附件使用 `file_paths` 和可选的 `filenames`：

```python
params_list = [
    {
        "name": "附件",
        "type": "DDAttachment",
        "file_paths": ["/tmp/a.pdf", "/tmp/b.xlsx"],
        "filenames": ["合同.pdf", "明细.xlsx"],
    },
]
```

如果附件已提前上传，也可以直接传 `value`：

```python
sp = DingtalkSP()
attachment = sp.upload_attachment("manager123", "/tmp/test.pdf", agent_id=123456789)

sp.submit_sp(
    originator_user_id="manager123",
    process_code="PROC-XXXXXXXX",
    dept_id=-1,
    agent_id=123456789,
    params_list=[
        {"name": "附件", "type": "DDAttachment", "value": [attachment]},
    ],
)
```

`value` 如果是 list 或 dict，会自动转换为 JSON 字符串；如果已经是 JSON 字符串，会原样提交。

## 下载审批附件

从审批实例详情中获取 `fileId` 后，可下载附件：

```python
from stdkit.dingtalk.client import DingTalk

rel_path = DingTalk().get_sp_attachment_file(
    process_instance_id="proc-xxx",
    file_id="file_xxx",
    real_file_name="附件.pdf",
    file_type="pdf",
    abs_path="/tmp/附件.pdf",
    rel_path="/tmp/附件.pdf",
)
```

## 注意事项

- 审批模板中的控件 `name` 必须与 `params_list` 中的 `name` 完全一致。
- 附件上传依赖审批、钉盘/存储相关权限；权限不足会在获取附件空间、获取上传信息或提交文件时失败。
- `dept_id` 为 `1` 时会自动转换为 `-1`，兼容根部门提交流程。
- `file_path` 必须是服务端可访问的本地文件路径。
- 默认附件空间目录 `parent_id` 为 `"0"`；如租户返回目录校验错误，可在附件参数中传入实际 `parent_id`。
