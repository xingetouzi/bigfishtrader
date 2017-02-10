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
        返回当前持仓，用户调用

        Returns:
            当前持仓
        Raises:
            NotImplementedError: Should implement get_positions
        """
        raise NotImplementedError("Should implement get_positions")

    @property
    def cash(self):
        """
        返回当前账户现金，用户调用

        Returns:
            当前账户现金
        Raises:
            NotImplementedError: Should implement get_cash
        """
        raise NotImplementedError("Should implement get_cash")

    def get_security(self, *args):
        pass