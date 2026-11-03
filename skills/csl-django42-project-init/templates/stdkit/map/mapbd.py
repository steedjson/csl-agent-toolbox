import requests
from django.conf import settings


class MapBd:

    DEFAULT_AK = "nmbyl7vt1MrI3w5ZMvZWA3dooTQDypG4"

    def __init__(self, ak=None):
        self._ak = ak

    @property
    def ak(self):
        if self._ak:
            return self._ak
        return getattr(settings, "MAP_BD_AK", "") or self.DEFAULT_AK

    def _require_ak(self):
        if not self.ak:
            raise ValueError("MAP_BD_AK is not configured")
        return self.ak

    def get_lng_lat_by_address(self, address, output="json"):
        """
        通过地址获取经纬度
        :param address: 地址
        :param output: json/xml
        :return:
        """
        url = "https://api.map.baidu.com/geocoding/v3/"
        # _require_ak() 在 try 之外：配置缺失需 fail fast，不被网络异常捕获吞掉
        params = {"ak": self._require_ak(), "output": output, "address": address}
        rs_data = {"lng": "", "lat": ""}
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                resp = response.json()
                # 用 .get 读键：服务端业务错误/异常响应可能缺字段或类型不符
                if int(resp.get("status", -1)) == 0:
                    location = resp.get("result", {}).get("location")
                    if location:
                        rs_data = location
        except (requests.RequestException, ValueError, TypeError, KeyError, AttributeError):
            # 网络异常/超时/JSON 解析失败/响应结构异常：返回既有空形态
            return {"lng": "", "lat": ""}
        return rs_data

    def change_lng_lat(self, lng, lat):
        """
        经纬度转换 GCJ02 转换百度
        :param lng: 经度
        :param lat: 纬度
        :return:
        """
        url = "https://api.map.baidu.com/geoconv/v1/"
        # _require_ak() 在 try 之外：配置缺失需 fail fast，不被网络异常捕获吞掉
        get_post = {"coords": "%s,%s" % (lng, lat), "ak": self._require_ak(), "from": 3, "to": 5}
        try:
            response = requests.get(url, params=get_post, timeout=10)
            # 成功拿到响应即原样透传 response.json()（含非 dict），与历史行为一致
            return response.json()
        except (requests.RequestException, ValueError, TypeError, KeyError, AttributeError):
            # 网络异常/超时/JSON 解析失败：返回既有空形态
            return {}

    def reverse_geocoding(self, lat, lng):
        """
        逆地理编码
        :param lng: 纬度
        :param lat: 经度
        :return:
        """
        url = "https://api.map.baidu.com/reverse_geocoding/v3/"
        # _require_ak() 在 try 之外：配置缺失需 fail fast，不被网络异常捕获吞掉
        get_post = {
            "location": "%s,%s" % (lng, lat),
            "ak": self._require_ak(),
            "output": "json",
            "coordtype": "bd09ll",
            "extensions_town": "true",
            "extensions_road": "true",
        }
        try:
            response = requests.get(url, params=get_post, timeout=10)
            # 成功拿到响应即原样透传 response.json()（含非 dict），与历史行为一致
            return response.json()
        except (requests.RequestException, ValueError, TypeError, KeyError, AttributeError):
            # 网络异常/超时/JSON 解析失败：返回既有空形态
            return {}


class Geopy:

    def get_two_lng_lat_distance(self, a=None, b=None):
        """
        获取坐标a和b之间的距离
        :param a: ["经度","纬度"]
        :param b: ["经度","纬度"]
        :return: km
        """
        if not a or not b:
            return 0
        a = tuple(reversed(a))
        b = tuple(reversed(b))
        try:
            from geopy.distance import geodesic
            return geodesic(a, b).km
        except Exception:
            return 0
