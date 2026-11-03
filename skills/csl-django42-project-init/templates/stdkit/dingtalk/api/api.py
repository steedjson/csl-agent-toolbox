from stdkit.dingtalk.api.base import RestApi


class OapiV2UserGetuserinfoRequest(RestApi):
    def __init__(self):
        url = "https://oapi.dingtalk.com/topapi/v2/user/getuserinfo"
        RestApi.__init__(self, url)
        self.code = None

    def getHttpMethod(self):
        return "POST"

    def getapiname(self):
        return "dingtalk.oapi.v2.user.getuserinfo"


class OapiV2DepartmentListsubRequest(RestApi):
    def __init__(self):
        url = "https://oapi.dingtalk.com/topapi/v2/department/listsub"
        RestApi.__init__(self, url)
        self.dept_id = None
        self.language = None

    def getHttpMethod(self):
        return "POST"

    def getapiname(self):
        return "dingtalk.oapi.v2.department.listsub"


class OapiV2DepartmentGetRequest(RestApi):
    def __init__(self):
        url = "https://oapi.dingtalk.com/topapi/v2/department/get"
        RestApi.__init__(self, url)
        self.dept_id = None
        self.language = None

    def getHttpMethod(self):
        return "POST"

    def getapiname(self):
        return "dingtalk.oapi.v2.department.get"


class OapiUserListidRequest(RestApi):
    def __init__(self):
        url = "https://oapi.dingtalk.com/topapi/user/listid"
        RestApi.__init__(self, url)
        self.dept_id = None

    def getHttpMethod(self):
        return "POST"

    def getapiname(self):
        return "dingtalk.oapi.user.listid"


class OapiV2UserGetRequest(RestApi):
    def __init__(self):
        url = "https://oapi.dingtalk.com/topapi/v2/user/get"
        RestApi.__init__(self, url)
        self.language = None
        self.userid = None

    def getHttpMethod(self):
        return "POST"

    def getapiname(self):
        return "dingtalk.oapi.v2.user.get"
