from django.utils import timezone
import datetime
import time
from dateutil.relativedelta import relativedelta
import math
import os
import uuid
from django.conf import settings
import bcrypt


# pybyte 单位表：(单位, 除数)。除数为 size 的换算基数，
# "b"（比特）按 1 字节 = 8 比特即 0.125 换算，其余为 1024 的幂。
_PYBYTE_UNITS = (
    ("b", 0.125),
    ("B", math.pow(1024, 0)),
    ("KB", math.pow(1024, 1)),
    ("MB", math.pow(1024, 2)),
    ("GB", math.pow(1024, 3)),
    ("TB", math.pow(1024, 4)),
    ("PB", math.pow(1024, 5)),
    ("EB", math.pow(1024, 6)),
    ("ZB", math.pow(1024, 7)),
    ("YB", math.pow(1024, 8)),
    ("BB", math.pow(1024, 9)),
    ("NB", math.pow(1024, 10)),
    ("DB", math.pow(1024, 11)),
    ("CB", math.pow(1024, 12)),
)


class Util:

    def timestamp(self):
        """
        获取整型时间戳
        :return:
        """
        return int(time.time())

    def now(self):
        return timezone.now()

    def timedelta(self, *args, **kwargs):
        return datetime.timedelta(*args, **kwargs)

    def month_start_time(self, year=None, month=None):
        if not year:
            year = timezone.now().year
        if not month:
            month = timezone.now().month
        return timezone.datetime(year=year, month=month, day=1)

    def date_to_timestamp(self, date: datetime.date):
        datetime_obj = datetime.datetime.combine(date, datetime.datetime.min.time())
        timestamp = int(time.mktime(datetime_obj.timetuple()))
        return timestamp

    @staticmethod
    def shift_date(date_str: str, years: int = 0, months: int = 0, days: int = 0) -> str:
        """
        调整日期，支持加减年/月/日

        :param date_str: 日期字符串，格式 "YYYY-MM-DD"
        :param years: 调整的年数，正数为加，负数为减
        :param months: 调整的月数，正数为加，负数为减
        :param days: 调整的天数，正数为加，负数为减
        :return: 调整后的日期字符串
        """
        date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        shifted = date_obj + relativedelta(years=years, months=months, days=days)
        return shifted.strftime("%Y-%m-%d")

    def params_clean(self, params: dict) -> dict:
        return {k: v for k, v in params.items() if v not in (None, "")}

    def pybyte(self, size, unit=None, dot=2):
        size = float(size)
        # 位 比特 bit
        if unit:
            for unit_name, divisor in _PYBYTE_UNITS:
                if unit == unit_name:
                    return str(round(size / divisor, dot))
            # 未知单位
            return False

        if 0 <= size < 1:
            return str(round(size / 0.125, dot)) + "b"
        # 字节 字节 Byte
        if 1 <= size < 1024:
            return str(round(size, dot)) + "B"
        # 千字节起按 1024 的幂分档，最后一档 CB 无上界
        for index in range(2, len(_PYBYTE_UNITS)):
            unit_name, divisor = _PYBYTE_UNITS[index]
            if index + 1 < len(_PYBYTE_UNITS):
                in_range = divisor <= size < _PYBYTE_UNITS[index + 1][1]
            else:
                in_range = divisor <= size
            if in_range:
                return str(round(size / divisor, dot)) + unit_name
        # 负数
        return False

    def generate_media_path(self, filename, u_folder="default"):
        str2 = uuid.uuid4().hex
        folder = str2[:2]
        directory_name = datetime.datetime.now().strftime("%Y/%m/" + folder)
        saved_path = os.path.join("media", u_folder, directory_name)
        relative_file_path = os.path.join(saved_path, filename)
        abs_path = os.path.join(settings.BASE_DIR, relative_file_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        return abs_path, "/" + relative_file_path.replace("\\", "/")

    def is_all_chinese(self, text):
        # 检查字符串是否全部由汉字组成
        return all("\u4e00" <= c <= "\u9fff" for c in text)

    def contains_chinese(self, text):
        # 检查字符串是否包含至少一个汉字
        return any("\u4e00" <= c <= "\u9fff" for c in text)

    def is_chinese_with_punctuation(self, char):
        # 基本汉字 + 中文常用标点（部分标点范围）
        ranges = [
            ("\u4e00", "\u9fff"),  # 汉字
            ("\u3000", "\u303f"),  # 中文标点（如、。《》）
            ("\uff00", "\uffef"),  # 全角符号（如＠！）
        ]
        return any(start <= char <= end for start, end in ranges)

    def hashpw(self, password: str):
        """密码加密"""
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def checkpw(self, password: str, hashed_password: str):
        """密码校验"""
        return bcrypt.checkpw(password.encode(), hashed_password.encode())
