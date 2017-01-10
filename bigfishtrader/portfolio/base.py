# encoding=utf-8
from bigfishtrader.core import HandlerCompose


class AbstractPortfolioHandler(HandlerCompose):
    def on_bar(self, event, kwargs=None):
        """
        处理BarEvent
        :param event:
        :param kwargs:
        :return:
        """
        raise NotImplementedError("Should implement on_bar")

    def on_tick(self, event, kwargs=None):
        """
        处理TickEvent
        :param event:
        :param kwargs:
        :return:
        """
        raise NotImplementedError("Should implement on_tick")

    def on_fill(self, event, kwargs=None):
        """
        处理FillEvent
        :param event:
        :param kwargs:
        :return:
        """
        raise NotImplementedError("Should implement on_fill")


class AbstractPortfolio(HandlerCompose):
    def get_positions(self):
        """
        返回当前持仓，用户调用
        :return:
        """
        raise NotImplementedError("Should implement get_positions")

    def get_cash(self):
        """
        返回当前账户现金，用户调用
        :return:
        """
        raise NotImplementedError("Should implement get_cash")