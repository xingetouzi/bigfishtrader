# encoding=utf-8
from bigfishtrader.core import HandlerCompose


class AbstractPriceHandler(HandlerCompose):
    def next_stream(self):
        """
        推送下一个数据
        :return:
        """
        raise NotImplementedError("Should implement next_stream()")

    def get_instance(self, ticker):
        """
        获取指定品种的最新数据
        :param ticker:
        :return:
        """
        raise NotImplementedError("Should implement get_instance()")

    def get_last_time(self):
        """
        获取最新时间
        :return:
        """
        raise NotImplementedError("Should implement get_last_time()")

    def get_ticker(self):
        """
        返回记录的ticker
        :return:
        """
        raise NotImplementedError("Should implement get_ticker()")