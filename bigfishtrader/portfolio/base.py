# encoding=utf-8
from bigfishtrader.engine.handler import HandlerCompose


class AbstractPortfolioHandler(HandlerCompose):
    """
    PortfolioHandler的抽象基类。
    """
    def on_bar(self, event, kwargs=None):
        """
        处理BarEvent

        Args:
            event(bigfishtrader.event.BarEvent): BarEvent
            kwargs(dict): 共享数据字典
        Returns:
            None
        Raises:
            NotImplementedError: Should implement on_bar
        """
        raise NotImplementedError("Should implement on_bar")

    def on_tick(self, event, kwargs=None):
        """
        处理TickEvent

        Args:
            event(bigfishtrader.event.TickEvent): TickEvent
            kwargs(dict): 共享数据字典
        Returns:
            None
        Raises:
            NotImplementedError: Should implement on_tick
        """
        raise NotImplementedError("Should implement on_tick")

    def on_fill(self, event, kwargs=None):
        """
        处理FillEvent

        Args:
            event(bigfishtrader.event.FillEvent): FillEvent
            kwargs(dict): 共享数据字典

        Returns:
            None
        Raises:
            NotImplementedError: Should implement on_fill
        """
        raise NotImplementedError("Should implement on_fill")


class AbstractPortfolio(HandlerCompose):
    """
    Portfolio的抽象基类。
    """

    @property
    def positions(self):
        """
        返回当前持仓对象

        :return: dict, {ticker: position} or {order_id: order}
        """
        raise NotImplementedError("Should implement get_positions")

    @property
    def cash(self):
        """
        返回当前可用现金

        :return: float
        """

        raise NotImplementedError("Should implement get_cash")

    @property
    def equity(self):
        """
        返回当前账户净值

        :return: float
        """
        return None

    @property
    def security(self):
        """
        返回当前可用持仓

        :return: dict, {ticker: available_quantity}
        """
        return None

    @property
    def history(self):
        """
        返回历史持仓

        :return:
        """
        return None

    @property
    def info(self):
        """
        返回账户历史信息

        :return:
        """
        return None

    @property
    def consignations(self):
        """
        返回委托记录

        :return:
        """
        return None

    @property
    def trades(self):
        """
        返回成交记录

        :return:
        """
        return None

    def send_open(self, **kwargs):
        """
        开仓
        :param kwargs: 参数，根据经纪商或交易所不同会有改动
        :return:
        """
        pass

    def send_close(self, **kwargs):
        """
        平仓
        :param kwargs: 参数，根据经纪商或交易所不同会有改动
        :return:
        """
        pass

    def cancel_order(self, **kwargs):
        """
        取消订单
        :param kwargs: 参数，根据经纪商或交易所不同会有改动
        :return:
        """
        pass
