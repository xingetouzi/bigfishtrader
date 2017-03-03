# encoding:utf-8
from bigfishtrader.engine.handler import HandlerCompose, Handler


class AbstractPortfolio(HandlerCompose):

    @property
    def cash(self):
        """
        返回当前账户现金

        :return:
        """
        raise NotImplementedError("Should implement cash()")

    @property
    def equity(self):
        """
        返回当前账户资产

        :return:
        """
        raise NotImplementedError("Should implement equity()")

    @property
    def positions(self):
        """
        返回当前账户持仓

        :return:
        """
        raise NotImplementedError("Should implement position()")

    @property
    def transactions(self):
        """
        返回账户成交记录

        :return:
        """
        raise NotImplementedError("Should implement transactions()")

    @property
    def history_eqt(self):
        """
        返回资金曲线

        :return:
        """
        raise NotImplementedError("Should implement history_eqt()")

    @property
    def history_pos(self):
        """
        返回历史持仓

        :return:
        """
        raise NotImplementedError("Should implement history_pos()")

    @property
    def history_req(self):
        """
        返回历史请求

        :return:
        """
        raise NotImplementedError("Should implement history_req()")


    def send_order(self, *args, **kwargs):
        """
        发送订单

        :param args:
        :param kwargs:
        :return:
        """
        raise NotImplementedError("Should implement send_order()")


class AbstractRouter(HandlerCompose):

    @property
    def orders(self):
        """
        返回未成交订单

        :return:
        """
        raise NotImplementedError("Should implement orders()")

    def set_commission(self, *args, **kwargs):
        pass

    def set_slippage(self, *args, **kwargs):
        pass


class AbstractDataSupport(HandlerCompose):

    def init(self, *args, **kwargs):
        """
        被engine调用完成数据初始化

        :param args:
        :param kwargs:
        :return:
        """

    def current(self, *args, **kwargs):
        """
        返回指定品种最近一根K线

        :param args:
        :param kwargs:
        :return:
        """
        raise NotImplementedError("Should implement current()")

    def history(self, *args, **kwargs):
        """
        返回指定品种指定时间的K线

        :param args:
        :param kwargs:
        :return:
        """
        raise NotImplementedError("Should implement history()")

    @staticmethod
    def connect(host='localhost', port=27017, users={}, **kwargs):
        """
        连接MongoDB，返回MongoClient对象

        :param host:
        :param port:
        :param users: 权限相关，格式: {'db_name': {'name': XXX, 'password': *********} ....}
        :param kwargs: MongoDB其他信息
        :return:
        """
        from pymongo import MongoClient

        client = MongoClient(host, port, **kwargs)

        for db, user in users.items():
            client[db].authenticate(user['name'], user['password'])

        return client