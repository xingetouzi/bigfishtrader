# encoding:utf-8
import requests
import json


class Client(object):
    """
    简易通联数据接口，初始化时需要输入相关配置信息。

    请求数据: request()
    """

    def __init__(self, info):
        """

        :param info: str or dict,
            配置信息, 可直接输入dict, 如果输入的是str则认为是文件地址, 并以json格式打开
            dict格式:
            {
                "token": "your_token",
                "api": {
                    "api_name": "api_url",
                    ...
                }
            }
            api相关: https://api.wmcloud.com/docs/pages/viewpage.action?pageId=2392676

        :return:
        """

        self.dome = "https://api.wmcloud.com/data/v1"
        if isinstance(info, str):
            with open(info) as f:
                info = json.load(f)
                f.close()

        self.header = {'Authorization': ' '.join(('Bearer', info['token']))}
        self.api = info['api']

    def request(self, api, **kwargs):
        """
        向通联请求数据, 如果收到的是json格式则转成dict返回

        :param api: str, 输入的配置信息中 api 的 api_name
        :param kwargs:  api所需参数，更多信息: https://api.wmcloud.com/docs/pages/viewpage.action?pageId=2392676
        :return: str or dict
        """
        url = self.request_url(api, **kwargs)
        response = requests.get(url, headers=self.header)
        try:
            return json.loads(response.text)
        except Exception:
            return response.text

    def request_url(self, api, **kwargs):
        params = '&'.join(map(
            lambda (key, value): '='.join((key, self.fields_join(value))),
            kwargs.items()
        ))
        url = self.dome + self.api[api] + '?' + params
        return url

    @staticmethod
    def fields_join(fields):
        if isinstance(fields, list):
            return ','.join(fields)
        else:
            return fields


if __name__ == '__main__':
    client = Client('D:/bigfishtrader/bigfishtrader/data/wmcloud_account.json')
    print client.request('getSecID', field='secID', ticker='IF1701', assetClass='fu')
