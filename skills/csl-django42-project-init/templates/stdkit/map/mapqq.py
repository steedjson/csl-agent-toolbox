import requests
from django.conf import settings


class MapQq:

    DEFAULT_KEY = "LL7BZ-HOD36-IRHSQ-MGL2I-UJEIS-KPB3B"

    def __init__(self, key=None):
        self._key = key

    @property
    def key(self):
        if self._key:
            return self._key
        return getattr(settings, "MAP_QQ_KEY", "") or self.DEFAULT_KEY

    def get_geocoder(self, longitude, latitude):
        """
        通过取经纬度获取位置信息
        :param longitude: 经度
        :param latitude: 纬度
        :return:
        """
        url = "https://apis.map.qq.com/ws/geocoder/v1/"
        params = {"key": self.key, "location": "%s,%s" % (latitude, longitude)}
        rs_data = {}
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                resp = response.json()
                # 用 .get 读键：服务端业务错误/异常响应可能缺字段或类型不符
                if int(resp.get("status", -1)) == 0:
                    # status==0 时原样透传 result（含空 dict / None），与历史行为一致
                    rs_data = resp.get("result") if isinstance(resp, dict) else {}
        except (requests.RequestException, ValueError, TypeError, KeyError, AttributeError):
            # 网络异常/超时/JSON 解析失败/响应结构异常：返回既有空形态
            return {}
        return rs_data

    def get_address_component(self, longitude, latitude):
        """
        通过取经纬度获取地址
        :param longitude: 经度
        :param latitude: 纬度
        :return:
        """
        map_key = "address_component"
        result = self.get_geocoder(longitude, latitude)
        address_component = result.get(map_key, {})
        return address_component


mapqq = MapQq()
