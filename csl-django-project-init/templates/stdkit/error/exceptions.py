from rest_framework.exceptions import APIException


class MyException(APIException):

    code = 200
    detail = None

    def __init__(self, detail=None, code=None):
        if detail is not None:
            self.detail = detail
        if code is not None:
            self.code = code
        super().__init__(self.detail, self.code)


class UnAuthenticatedException(MyException):

    code = 401
    detail = "Unauthenticated"


class ForbiddenException(MyException):

    code = 403
    detail = "Forbidden"


class NotFoundException(MyException):

    code = 404
    detail = "Not Found"


class BadRequestException(MyException):

    code = 400
    detail = "Invalid Argument"


class NotAuthException(MyException):

    code = 4001
    detail = "Not auth login"


class InvalidJwtErrorException(MyException):

    code = 4002
    detail = "Invalid jwt error"


class InternalErrorException(MyException):

    code = 500
    detail = "内部服务错误"


class TeapotErrorException(MyException):

    code = 418
    detail = "服务端拒绝访问"


class SuccessException(MyException):

    code = 200
    detail = "成功"
