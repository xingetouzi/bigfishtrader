# encoding=utf-8
from bigfishtrader.engine.handler import HandlerCompose


class AbstractDataSupport(HandlerCompose):
    def __init__(self):
        super(AbstractDataSupport, self).__init__()

    def current(self, ticker, filed=None):
        """
        返回最新数据
        :param ticker:
        :param filed:
        :return:
        """
        raise NotImplementedError("should implement current()")

    def instance(
            self, ticker, period, filed,
            start=None, end=None, length=None
    ):
        """
        返回内存数据
        :param ticker:
        :param period:
        :param filed:
        :param start:
        :param end:
        :param length:
        :return:
        """
        raise NotImplementedError("should implement instance()")

    def history(
            self, ticker, period, filed,
            start=None, end=None, length=None
    ):
        """
        返回历史数据
        :param ticker:
        :param filed:
        :param period:
        :param start:
        :param end:
        :param length:
        :return:
        """
        raise NotImplementedError("should implement history()")