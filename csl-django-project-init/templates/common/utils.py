# encoding=utf-8
import calendar
import datetime
import json
import math
import mimetypes
import os
import random
import re
import string
import time
import typing
import uuid
import zipfile
from dataclasses import asdict, dataclass, is_dataclass
from datetime import timedelta
from decimal import Decimal
from decimal import Decimal as D
from decimal import InvalidOperation
from pathlib import Path

from dateutil import rrule
from dateutil.parser import parse
from django.conf import settings
from django.core import serializers
from pypinyin import Style, pinyin


def remove_slash(file_path):
    return file_path[1:] if file_path.startswith('/') else file_path


def get_file_pathinfo(file_path):
    """
    获取文件信息
    :param file_path:
    :return:
    """
    # 去除首字母 /
    file_path = remove_slash(file_path)
    path = Path(file_path)
    return {
        'file_path': file_path,
        'file_dir': str(path.parent),
        'file_name': path.stem,
        'file_ext': path.suffix,
        'full_filename': path.name,
    }


def get_model_fields(model):
    json_str = serializers.serialize(
        "json",
        [
            model,
        ],
    )
    model_list = json.loads(json_str)
    if len(model_list) > 0:
        data = model_list.pop(0)
        data["fields"]["uuid"] = data["pk"]
        return data["fields"]
    else:
        return None


def get_models_fields(models):
    res_data = []
    if not models or len(models) == 0:
        return res_data
    json_str = serializers.serialize("json", models)
    model_list = json.loads(json_str)
    for model in model_list:
        model["fields"]["uuid"] = model["pk"]
        res_data.append(model["fields"])

    return res_data


def get_create_model_fields(obj):
    data = obj.__dict__
    del data["_state"]
    return data


def get_workdays_in_month(year=None, month=None):
    """
    :param year: 年份，默认是本年，可传int或str类型
    :param month: 月份，默认是本月，可传int或str类型
    :return: workdays , int类型
    """
    if year:
        year = int(year)
    else:
        year = datetime.date.today().year

    if month:
        month = int(month)
    else:
        month = datetime.date.today().month

    # 获取当月第一天的星期和当月的总天数
    first_day_week_day, month_range = calendar.monthrange(year, month)
    count = 0

    for i in range(1, month_range + 1):
        tmp_datetime = datetime.date(year=year, month=month, day=i)
        if tmp_datetime.isoweekday() not in [6, 7]:
            count = count + 1
    return count


def get_first_last_day_in_month(year=None, month=None):
    """
    :param year: 年份，默认是本年，可传int或str类型
    :param month: 月份，默认是本月，可传int或str类型
    :return: first_day: 当月的第一天，datetime.date类型
              last_day: 当月的最后一天，datetime.date类型
    """
    if year:
        year = int(year)
    else:
        year = datetime.date.today().year

    if month:
        month = int(month)
    else:
        month = datetime.date.today().month

    # 获取当月第一天的星期和当月的总天数
    first_day_week_day, month_range = calendar.monthrange(year, month)

    # 获取当月的第一天
    first_day = datetime.date(year=year, month=month, day=1)
    last_day = datetime.date(year=year, month=month, day=month_range)

    return first_day, last_day


def get_time_stamp():
    """
    获取整型时间戳
    :return:
    """
    return int(time.time())


def get_month_benin():
    """
    获取当月第一天
    :return:
    """
    month_now = time.localtime()
    month_begin = "%d-%02d-01" % (month_now.tm_year, month_now.tm_mon)
    return month_begin


def get_last_month_benin(now=None):
    """
    获取上个月第一天
    :return:
    """
    if not now:
        now = datetime.datetime.now()
    this_month_start = datetime.datetime(now.year, now.month, 1)
    last_month_end = this_month_start - timedelta(days=1)
    last_month_start = datetime.datetime(last_month_end.year, last_month_end.month, 1)
    return last_month_start


def get_day_timestamp(date_str):
    """
    根据日期，获取一天的起始和结束时间戳
    :param date_str:
    :return:
    """
    date = str(date_str).strip()
    time_array = time.strptime(date, "%Y-%m-%d")
    start_timestamp = int(time.mktime(time_array))
    end_timestamp = start_timestamp + 24 * 3600 - 1
    return start_timestamp, end_timestamp


def my_decimal_round(par, temp=2):
    """
    四舍五入
    :param temp:
    :param par:
    :return:
    """
    par = D(str(par))
    step = 10
    step1 = 1
    for i in range(temp):
        step *= 10
        step1 *= 10
    tmp_par = par * step
    tmp2 = tmp_par % 10
    if tmp2 >= 5:
        v = (int(tmp_par / 10) + 1) / step1
    else:
        v = (int(tmp_par / 10)) / step1
    return D(str(v))


def format_decimal_field_round(data, temp=2):
    """
    格式化数字字段并四舍五入
    :param temp:
    :param par:
    :return:
    """

    tmp_data = None

    if isinstance(data, dict):
        tmp_data = {}
        for k, v in data.items():
            if check_float_number(v):
                tmp_data[k] = my_decimal_round(v, temp)
            else:
                tmp_data[k] = v
    if isinstance(data, list):
        tmp_data = []
        for v in data:
            if check_float_number(v):
                tmp_data.append(my_decimal_round(v, temp))
            else:
                tmp_data[k] = v

    return tmp_data


# 合法地区码字典（部分示例）
AREA_CODES = {
    "11": "北京",
    "12": "天津",
    "13": "河北",
    "14": "山西",
    "15": "内蒙古",
    "21": "辽宁",
    "22": "吉林",
    "23": "黑龙江",
    "31": "上海",
    "32": "江苏",
    "33": "浙江",
    "34": "安徽",
    "35": "福建",
    "36": "江西",
    "37": "山东",
    "41": "河南",
    "42": "湖北",
    "43": "湖南",
    "44": "广东",
    "45": "广西",
    "46": "海南",
    "50": "重庆",
    "51": "四川",
    "52": "贵州",
    "53": "云南",
    "54": "西藏",
    "61": "陕西",
    "62": "甘肃",
    "63": "青海",
    "64": "宁夏",
    "65": "新疆",
    "71": "台湾",
    "81": "香港",
    "82": "澳门",
    "91": "国外",
}


def is_valid_id_card(id_card):
    """
    验证中国公民身份证号码是否有效（支持15位和18位）。
    """
    id_card = id_card.strip()

    if len(id_card) == 15:
        return _validate_15_digit(id_card)
    elif len(id_card) == 18:
        return _validate_18_digit(id_card)
    else:
        return False


def _validate_15_digit(id_card):
    """验证15位身份证号码"""
    if not re.fullmatch(r"\d{15}", id_card):
        return False

    area_code = id_card[:2]
    if area_code not in AREA_CODES:
        return False

    try:
        year = int("19" + id_card[6:8])
        month = int(id_card[8:10])
        day = int(id_card[10:12])
        datetime.datetime(year, month, day)
    except ValueError:
        return False

    return True


def _validate_18_digit(id_card):
    """验证18位身份证号码"""
    if not re.fullmatch(r"\d{17}[0-9Xx]", id_card):
        return False

    area_code = id_card[:2]
    if area_code not in AREA_CODES:
        return False

    try:
        year = int(id_card[6:10])
        month = int(id_card[10:12])
        day = int(id_card[12:14])
        datetime.datetime(year, month, day)
    except ValueError:
        return False

    weight_factors = [2 ** (18 - i) % 11 for i in range(1, 18)]
    checksum_map = ["1", "0", "X", "9", "8", "7", "6", "5", "4", "3", "2"]

    weighted_sum = 0
    for i in range(17):
        digit = int(id_card[i]) if id_card[i].isdigit() else 0
        weighted_sum += digit * weight_factors[i]

    checksum_index = weighted_sum % 11
    expected_checksum = checksum_map[checksum_index]

    if id_card[-1].upper() != expected_checksum:
        return False

    return True


def is_valid_resident_permit(id_card):
    """验证港澳台居民来往内地通行证"""
    return bool(re.fullmatch(r"[HMhm]\d{8}", id_card))


def is_valid_foreign_id(id_card):
    """验证外国人居留证（如 X/W 开头+8位数字）"""
    return bool(re.fullmatch(r"[XWxw]\d{8}", id_card))


def is_valid_passport_number(passport):
    """验证护照号码"""
    passport = passport.strip().upper()

    # 常见护照格式：
    # G12345678、E12345678、P12345678、S12345678、D12345678
    pattern = r"^[GEDSPgedsp][0-9]{7,8}$"
    return bool(re.match(pattern, passport))


def is_valid_military_id(military_id):
    """验证军官证/武警证等军事人员证件"""
    military_id = military_id.strip()

    # 示例格式：军字第XXXXXX号、海字第XXXXXX号、空字第XXXXXX号、武字第XXXXXX号
    pattern = r"^(军|海|空|武)字第\d{6}号$"
    return bool(re.match(pattern, military_id))


def validate_identity_number(id_card):
    """
    统一身份验证接口，支持：
    - 中国大陆身份证（15/18位）
    - 港澳台居民证件（H/M开头+8位数字）
    - 外国人居留证（X/W开头+8位数字）
    - 护照号（G/E/P/S/D开头+7/8位数字）
    - 军官证（军字第XXXXXX号）

    Args:
        id_card (str): 身份证号码或证件号码。

    Returns:
        dict: 包含是否合法及证件类型的返回结果。
    """
    id_card = id_card.strip().upper()

    if is_valid_id_card(id_card):
        return {"valid": True, "type": "ID_CARD"}
    elif is_valid_resident_permit(id_card):
        return {"valid": True, "type": "RESIDENT_PERMIT"}
    elif is_valid_foreign_id(id_card):
        return {"valid": True, "type": "FOREIGN_ID"}
    elif is_valid_passport_number(id_card):
        return {"valid": True, "type": "PASSPORT"}
    elif is_valid_military_id(id_card):
        return {"valid": True, "type": "MILITARY_ID"}
    else:
        return {"valid": False, "type": None}


def check_phonenumber(phonenumber):
    """
    手机号码验证
    """
    p2 = re.compile(r"^0\d{2,3}\d{7,8}$|^1\d{10}$|^147\d{8}")
    phonematch = p2.match(phonenumber)

    if phonematch:
        return True
    else:
        return False


def check_float_number(string, has_minus=False):
    """
    判断输入的是否是整数或者小数
    :param string:
    :return:
    """
    if isinstance(string, (int, float)):
        return True
    s = str(string)
    if s.count(".") == 1:  # 判断小数点个数
        sl = s.split(".")  # 按照小数点进行分割
        left = sl[0]  # 小数点前面的
        right = sl[1]  # 小数点后面的
        if left.startswith("-") and left.count("-") == 1 and right.isdigit():
            lleft = left.split("-")[1]  # 按照-分割，然后取负号后面的数字
            if lleft.isdigit():
                return False
        elif left.isdigit() and right.isdigit():
            # 判断是否为正小数
            return True
    elif s.isdigit():
        s = int(s)
        if s != 0:
            return True
    return False


def get_rand_str(num=4, flag="num"):
    """
    获取随机的几位字符串
    :param flag:  num 数字 letter字母 num_letter 数字和字母
    :param num:
    :return:
    """
    if flag == "num":
        tmp_str = string.digits
    elif flag == "letter":
        tmp_str = string.ascii_letters
    else:
        tmp_str = string.ascii_letters + string.digits
    rand_str_arr = random.sample(tmp_str, num)
    return "".join(rand_str_arr)


# 判断一个unicode是否是汉字
def is_chinese_char(uchar):
    if "\u4e00" <= uchar <= "\u9fff":
        return True
    else:
        return False


# 判断一个unicode是否是数字
def is_number_char(uchar):
    if "\u0030" <= uchar <= "\u0039":
        return True
    else:
        return False


# 判断一个unicode是否是英文字母
def is_alphabet_char(uchar):
    if ("\u0041" <= uchar <= "\u005a") or ("\u0061" <= uchar <= "\u007a"):
        return True
    else:
        return False


# 判断是否非汉字，数字和英文字符
def is_other_char(uchar):
    if not (is_chinese_char(uchar) or is_number_char(uchar) or is_alphabet_char(uchar)):
        return True
    else:
        return False


# 检验密码字符是否合法
def check_pwd_char(chars):
    pwd_chars = string.punctuation + string.digits + string.ascii_letters
    is_sub = set(chars).issubset(set(pwd_chars))
    return is_sub


def check_email(email):
    """
    邮箱验证
    """
    p2 = re.compile(r"^\w+@(\w+\.)+(com|cn|net)$")
    email_search = p2.search(email)

    if email_search:
        return True
    else:
        return False


def check_mobile(mobile):
    """
    手机号码验证
    """
    p2 = re.compile(r"^1\d{10}$")
    mobile = p2.match(mobile)

    if mobile:
        return True
    else:
        return False


def get_week_name(date):
    """
    日期转化成星期
    :param date:
    :return:
    """
    week_name_list = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    date = datetime.datetime.strptime(date, "%Y-%m-%d")
    week_name = week_name_list[date.weekday()]
    return week_name


def get_d_h_m_sec(start_date, end_date):
    """
    获取两个日期差 返回 天、时、分、秒
    :param start_date:
    :param end_date:
    :return: 天、时、分、秒
    """
    if not start_date or not end_date:
        return 0, 0, 0, 0
    days = (end_date - start_date).days
    sec = (end_date - start_date).seconds
    m = sec // 60
    sec = sec % 60
    h = m // 60
    m = m % 60
    return days, h, m, sec


def get_months_diff_datetime(start_date, end_date):
    """
    获取两个日期差 返回 月数
    :param start_date:
    :param end_date:
    :return: 月数
    """
    if not start_date or not end_date:
        return 0
    months = rrule.rrule(rrule.MONTHLY, dtstart=start_date, until=end_date).count()
    return months


def get_years_diff_datetime(start_date, end_date):
    """
    获取两个日期差 返回 年数
    :param start_date:
    :param end_date:
    :return: 年数
    """
    if not start_date or not end_date:
        return 0
    years = rrule.rrule(rrule.YEARLY, dtstart=start_date, until=end_date).count()
    return years


def get_months_diff_date(date1, date2):
    if isinstance(date1, str) and isinstance(date2, str):
        year1 = datetime.datetime.strptime(date1[0:10], "%Y-%m-%d").year
        year2 = datetime.datetime.strptime(date1[0:10], "%Y-%m-%d").year
        month1 = datetime.datetime.strptime(date1[0:10], "%Y-%m-%d").month
        month2 = datetime.datetime.strptime(date1[0:10], "%Y-%m-%d").month
    else:
        year1 = date1.year
        year2 = date2.year
        month1 = date1.month
        month2 = date2.month
    num = (year1 - year2) * 12 + (month1 - month2)
    return num


def get_week_begin_datetime():
    """
    return datetime;
    """
    now = datetime.datetime.now()
    d = now - datetime.timedelta(days=now.isoweekday() - 1)
    return datetime.datetime(d.year, d.month, d.day)


def for_tuple_to_dict(tup):
    """
    把数据库中定义的tople转换成dict
    :param tup:
    :return:
    """
    rs_data = {}
    for value in list(tup):
        if list(value)[0] not in rs_data.keys():
            rs_data[list(value)[0]] = list(value)[1]
    return rs_data


def pybyte(size, unit=None, dot=2):
    size = float(size)
    # 位 比特 bit
    if unit:
        if unit == "b":
            human_size = str(round(size / 0.125, dot))
        # 字节 字节 Byte
        elif unit == "B":
            human_size = str(round(size, dot))
        # 千字节 千字节 Kilo Byte
        elif unit == "KB":
            human_size = str(round(size / math.pow(1024, 1), dot))
        # 兆字节 兆 Mega Byte
        elif unit == "MB":
            human_size = str(round(size / math.pow(1024, 2), dot))
        # 吉字节 吉 Giga Byte
        elif unit == "GB":
            human_size = str(round(size / math.pow(1024, 3), dot))
        # 太字节 太 Tera Byte
        elif unit == "TB":
            human_size = str(round(size / math.pow(1024, 4), dot))
        # 拍字节 拍 Peta Byte
        elif unit == "PB":
            human_size = str(round(size / math.pow(1024, 5), dot))
        # 艾字节 艾 Exa Byte
        elif unit == "EB":
            human_size = str(round(size / math.pow(1024, 6), dot))
        # 泽它字节 泽 Zetta Byte
        elif unit == "ZB":
            human_size = str(round(size / math.pow(1024, 7), dot))
        # 尧它字节 尧 Yotta Byte
        elif unit == "YB":
            human_size = str(round(size / math.pow(1024, 8), dot))
        # 千亿亿亿字节 Bront Byte
        elif unit == "BB":
            human_size = str(round(size / math.pow(1024, 9), dot))
        # 百万亿亿亿字节 Dogga Byte
        elif unit == "NB":
            human_size = str(round(size / math.pow(1024, 10), dot))
        # 十亿亿亿亿字节 Dogga Byte
        elif unit == "DB":
            human_size = str(round(size / math.pow(1024, 11), dot))
        # 万亿亿亿亿字节 Corydon Byte
        elif unit == "CB":
            human_size = str(round(size / math.pow(1024, 12), dot))
        # 负数
        else:
            human_size = False
    else:
        if 0 <= size < 1:
            human_size = str(round(size / 0.125, dot)) + "b"
        # 字节 字节 Byte
        elif 1 <= size < 1024:
            human_size = str(round(size, dot)) + "B"
        # 千字节 千字节 Kilo Byte
        elif math.pow(1024, 1) <= size < math.pow(1024, 2):
            human_size = str(round(size / math.pow(1024, 1), dot)) + "KB"
        # 兆字节 兆 Mega Byte
        elif math.pow(1024, 2) <= size < math.pow(1024, 3):
            human_size = str(round(size / math.pow(1024, 2), dot)) + "MB"
        # 吉字节 吉 Giga Byte
        elif math.pow(1024, 3) <= size < math.pow(1024, 4):
            human_size = str(round(size / math.pow(1024, 3), dot)) + "GB"
        # 太字节 太 Tera Byte
        elif math.pow(1024, 4) <= size < math.pow(1024, 5):
            human_size = str(round(size / math.pow(1024, 4), dot)) + "TB"
        # 拍字节 拍 Peta Byte
        elif math.pow(1024, 5) <= size < math.pow(1024, 6):
            human_size = str(round(size / math.pow(1024, 5), dot)) + "PB"
        # 艾字节 艾 Exa Byte
        elif math.pow(1024, 6) <= size < math.pow(1024, 7):
            human_size = str(round(size / math.pow(1024, 6), dot)) + "EB"
        # 泽它字节 泽 Zetta Byte
        elif math.pow(1024, 7) <= size < math.pow(1024, 8):
            human_size = str(round(size / math.pow(1024, 7), dot)) + "ZB"
        # 尧它字节 尧 Yotta Byte
        elif math.pow(1024, 8) <= size < math.pow(1024, 9):
            human_size = str(round(size / math.pow(1024, 8), dot)) + "YB"
        # 千亿亿亿字节 Bront Byte
        elif math.pow(1024, 9) <= size < math.pow(1024, 10):
            human_size = str(round(size / math.pow(1024, 9), dot)) + "BB"
        # 百万亿亿亿字节 Dogga Byte
        elif math.pow(1024, 10) <= size < math.pow(1024, 11):
            human_size = str(round(size / math.pow(1024, 10), dot)) + "NB"
        # 十亿亿亿亿字节 Dogga Byte
        elif math.pow(1024, 11) <= size < math.pow(1024, 12):
            human_size = str(round(size / math.pow(1024, 11), dot)) + "DB"
        # 万亿亿亿亿字节 Corydon Byte
        elif math.pow(1024, 12) <= size:
            human_size = str(round(size / math.pow(1024, 12), dot)) + "CB"
        # 负数
        else:
            human_size = False
            # raise ValueError('{}() takes number than or equal to 0, but less than 0 given.'.format(pybyte.__name__))
    return human_size


def is_excel_file(absolute_file_path):
    mimetype, _ = mimetypes.guess_type(absolute_file_path)
    file_type = mimetype.lower()
    if file_type in [
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
    ]:
        return True
    return False


def zip_dir(dir_name, zip_filename):
    """
    压缩指定文件夹
    :param dir_name: 目标文件夹路径
    :param zip_filename: 压缩文件保存路径+xxxx.zip
    :return: 无
    """
    zip_obj = zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED)
    for path, dir_names, filenames in os.walk(dir_name):
        # 去掉目标跟路径，只对目标文件夹下边的文件及文件夹进行压缩
        fpath = path.replace(dir_name, "")
        for filename in filenames:
            zip_obj.write(os.path.join(path, filename), os.path.join(fpath, filename))
    zip_obj.close()

    # filelist = []
    # if os.path.isfile(dir_name):
    #     filelist.append(dir_name)
    # else:
    #     for root, dirs, files in os.walk(dir_name):
    #         # 去掉目标跟路径，只对目标文件夹下边的文件及文件夹进行压缩
    #         # fpath = root.replace(dirname, '')
    #         for name in files:
    #             filelist.append(os.path.join(root, name))
    #
    # zf = zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED)
    # for tar in filelist:
    #     arc_name = tar[len(dir_name):]
    #     # print arc_name
    #     zf.write(tar, arc_name)
    # zf.close()


# 获取已有文件目录下新的文件路径
def get_file_media_path(file_name):
    _, ext = os.path.splitext(file_name)
    path, _ = os.path.split(file_name)
    str2 = uuid.uuid4().hex
    filename = str2[2:10] + "_" + str(random.randint(1000, 9999))
    filename = filename + ext
    relative_file_path = os.path.join(path, filename)
    return relative_file_path


# 获取字符串首字母
def get_first_letter(name: str, rs_type=str.isalnum):
    """
    :param name: string
    :param rs_type:
        isalnum: 只保留字母和数字
        isalpha：只保留字母
        isalnum：只保留数字
        如果想保留数字0-9和小数点’.’ 则需要自定义函数
        ''.join(filter(lambda ch: ch in ‘0123456789.’, name))
    :return:
    """
    name = name.replace(" ", "")
    first_letter = ""
    for initial in pinyin(name, style=Style.FIRST_LETTER):
        if initial:
            first_letter += initial[0].upper()
    # 只保留数字和
    first_letter = "".join(filter(rs_type, first_letter))
    return first_letter


def get_client_ip(request):
    """从请求对象中获取客户端IP"""
    real_ip = request.META.get("X-Real-IP")
    if real_ip:
        return real_ip
    xff = request.META.get("X-Forwarded-For")
    if xff:
        return xff
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0]
    return request.META.get("REMOTE_ADDR")


def generate_media_path(filename, u_folder="default"):
    str2 = uuid.uuid4().hex
    folder = str2[:2]
    directory_name = datetime.datetime.now().strftime("%Y/%m/" + folder)
    saved_path = os.path.join("media", u_folder, directory_name)
    relative_file_path = os.path.join(saved_path, filename)
    abs_path = os.path.join(settings.BASE_DIR, relative_file_path)
    directory = os.path.dirname(relative_file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)
    return abs_path, "/" + relative_file_path


def build_tree(items: typing.List[typing.Union[dict, dataclass]]):
    tmp_items = items.copy()
    items = []
    for item in tmp_items:
        if is_dataclass(item):
            item = asdict(item)
        items.append(item)
    # 元素格式：{'id': 1, 'parentid': 0, "order": 111}
    # 创建一个临时字典，方便根据 id 查找节点
    nodes = {item["dept_id"]: item for item in items}

    # 初始化每个节点的 children 和 parentids 属性
    for node in items:
        node["children"] = []
        node["parent_ids"] = []

    root = {"dept_id": 1, "parent_id": 0, "children": [], "parent_ids": []}

    for node in items:
        parent_id = node["parent_id"]
        if parent_id == 1:
            root["children"].append(node)
            continue
        # 将当前节点加入其父节点的 children 列表中
        parent_node = nodes[parent_id]
        parent_node["children"].append(node)

    def assign_parents(node, parent_list):
        node["parent_ids"] = parent_list.copy()
        for child in node["children"]:
            assign_parents(child, parent_list + [node["dept_id"]])

    if root:
        assign_parents(root, [])

    return root


def flatten_tree(node):
    flat_list = []

    def traverse(node):
        flat_list.append(
            {
                "dept_id": node["dept_id"],
                "parent_id": node["parent_id"],
                "parent_ids": node["parent_ids"],
            }
        )
        for child in node["children"]:
            traverse(child)

    traverse(node)
    return flat_list


def object_to_dict(obj):
    """
    将对象及其所有嵌套对象（包括 JSON 字符串）递归地转换为字典
    """
    # 如果对象是 JSON 字符串，尝试将其解析为字典或列表
    if isinstance(obj, str):
        try:
            parsed = json.loads(obj)  # 解析 JSON 字符串
            return object_to_dict(parsed)  # 递归处理解析后的内容
        except json.JSONDecodeError:
            pass  # 如果不是 JSON 字符串，保留原始字符串

    # 如果对象有 __dict__ 属性，表示是普通 Python 对象
    if hasattr(obj, "__dict__"):
        return {key: object_to_dict(value) for key, value in obj.__dict__.items()}

    # 如果对象是列表或元组，递归处理每个元素
    elif isinstance(obj, (list, tuple)):
        return [object_to_dict(item) for item in obj]

    # 如果对象是字典，递归处理每个键值对
    elif isinstance(obj, dict):
        return {key: object_to_dict(value) for key, value in obj.items()}

    # 如果对象是其他原生类型（如 int, float, str, None 等），直接返回
    else:
        return obj


def load_decimal(value) -> Decimal:
    try:
        amount = Decimal(value) if value is not None else None
    except InvalidOperation:
        amount = None  # 或者 raise 异常，根据业务逻辑处理

    return amount


def str_to_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return value.lower() in ("true", "1", "yes")


def normalize_month(month_str: typing.Union[datetime.datetime, str]) -> str:
    if isinstance(month_str, datetime.datetime):
        return month_str.strftime("%Y-%m")

    # 去除前后空格
    month_str = month_str.strip()

    # 匹配形如 201501
    if re.fullmatch(r"\d{6}", month_str):
        return f"{month_str[:4]}-{month_str[4:6]}"

    # 匹配形如 2015-01 或 2015/01
    match = re.match(r"^(\d{4})[-/](\d{1,2})$", month_str)
    if match:
        year, month = match.groups()
        return f"{year}-{int(month):02d}"

    raise ValueError(f"无法识别的日期格式: {month_str}")


def fill_merged_header(header_row):
    """
    把一级表头里的 None 填充为前一个非 None 值
    例如: ('月份', '人工', None, None, '差旅', None)
    变成: ('月份', '人工', '人工', '人工', '差旅', '差旅')
    """
    filled = []
    last_val = None
    for val in header_row:
        if val is not None:
            last_val = str(val).strip()
        filled.append(last_val)
    return filled


def is_all_chinese(text):
    # 检查字符串是否全部由汉字组成
    return all("\u4e00" <= c <= "\u9fff" for c in text)


def contains_chinese(text):
    # 检查字符串是否包含至少一个汉字
    return any("\u4e00" <= c <= "\u9fff" for c in text)


def is_chinese_with_punctuation(char):
    # 基本汉字 + 中文常用标点（部分标点范围）
    ranges = [
        ("\u4e00", "\u9fff"),  # 汉字
        ("\u3000", "\u303f"),  # 中文标点（如、。《》）
        ("\uff00", "\uffef"),  # 全角符号（如＠！）
    ]
    return any(start <= char <= end for start, end in ranges)


def parse_date_enhanced(date_str):
    """增强版日期解析，支持更多格式"""
    if not date_str:
        return None
    if not isinstance(date_str, str):
        return date_str
    formats = [
        "%Y-%m-%d %H:%M:%S",  # 2025-04-01 00:00:00
        "%Y/%m/%d",  # 2025/2/20
        "%Y/%m",  # 2025/2
        "%Y.%m.%d",  # 2023.3.1
        "%Y.%m",  # 2023.3
        "%Y",  # 2023
        "%Y年%m月%d日",  # 2023年3月1日
        "%Y年%m月",  # 2023年3月
    ]

    for fmt in formats:
        try:
            dt = datetime.datetime.strptime(date_str, fmt)
            # 特殊处理不完整日期
            if fmt in ("%Y/%m", "%Y.%m", "%Y"):
                return dt.replace(month=1 if fmt == "%Y" else dt.month, day=1).date()
            return dt
        except ValueError:
            continue

    # 最终尝试使用dateutil（需要安装：pip install python-dateutil）
    try:
        return parse(date_str)
    except ImportError as e:
        print(f"无法解析日期字符串：{date_str},{str(e)}")
        pass
    except Exception as e:
        print(f"无法解析日期字符串：{date_str},{str(e)}")
        pass
    return None
