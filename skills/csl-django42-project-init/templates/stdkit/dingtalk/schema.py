from dataclasses import dataclass, field
import typing


@dataclass
class UserInfo:
    name: str
    userid: str
    unionid: str = None
    dept_id_list: typing.List[int] = field(default_factory=list)
    avatar: str = None
    job: str = None


@dataclass
class DepartmentInfo:
    dept_id: int
    name: str
    parent_id: int
    org_dept_owner: str = None
    order: int = None
