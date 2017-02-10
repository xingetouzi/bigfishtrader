# encoding=utf-8
from bigfishtrader.engine.handler import HandlerCompose
from datetime import datetime


class AbstractDataSupport(HandlerCompose):
    def __init__(self):
        super(AbstractDataSupport, self).__init__()

    def current(self, tickers, fields=None):
        """
        返回最新数据
        :param tickers:
        :param fields:
        :return:
        """
        raise NotImplementedError("should implement current()")

    def instance(
            self, tickers, fields, frequency,
            start=None, end=None, length=None
    ):
        """
        返回内存数据
        :param tickers:
        :param frequency:
        :param fields:
        :param start:
        :param end:
        :param length:
        :return:
        """
        raise NotImplementedError("should implement instance()")

    def history(
            self, tickers, frequency, fields=None,
            start=None, end=None, length=None
    ):
        """
        返回历史数据
        :param tickers:
        :param fields:
        :param frequency:
        :param start:
        :param end:
        :param length:
        :return:
        """
        raise NotImplementedError("should implement history()")

    @property
    def current_time(self):
        return datetime.now()
