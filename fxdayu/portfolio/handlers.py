# encoding:utf-8

from fxdayu.engine.handler import Handler
from fxdayu.event import OPEN_ORDER, CLOSE_ORDER, EVENTS
from fxdayu.portfolio.base import AbstractPortfolioHandler
from fxdayu.portfolio.portfolio import Portfolio


class PortfolioHandler(AbstractPortfolioHandler):
    """
    This class is to handle Portfolio,
    including updating portfolio when a BAR, a TICK
    or a FILL event arrives.

    Args:
        event_queue(PriorityQueue): event queue.
        init_cash(float): the initial cash of the portfolio.
        portfolio(fxdayu.portfolio.portfolio.Portfolio): portfolio can be import outside if needed

    Attributes:
        event_queue(PriorityQueue): event queue which this PortfolioHandler register its event
            handler on, and put events to this queue to communicate with other component.
        portfolio(fxdayu.portfolio.portfolio.Portfolio): the portfolio of this PortfolioHandler.
    """

    def __init__(self, event_queue, data_support, init_cash=100000, portfolio=None):
        super(PortfolioHandler, self).__init__()
        self.event_queue = event_queue
        self.data = data_support
        self.portfolio = portfolio if portfolio is not None \
            else Portfolio(init_cash)
        # self._handlers["on_bar"] = Handler(self.on_bar, EVENTS.BAR, topic=".", priority=10)
        # self._handlers["on_tick"] = Handler(self.on_tick, EVENTS.TICK, topic=".", priority=10)
        self._handlers["on_fill"] = Handler(self.on_fill, EVENTS.EXECUTION, topic="", priority=10)
        self._handlers["on_time"] = Handler(self.on_time, EVENTS.TIME, topic="", priority=10)
        # self._handlers["on_confirm"] = Handler(self.on_confirm, EVENTS.CANCEL, topic=".", priority=100)

    def on_bar(self, event, kwargs=None):
        """
        update portfolio's positions to calculate equity and record it on every Bar

        Args:
            event(fxdayu.event.BarEvent): BarEvent
            kwargs: dict for sharing data

        Returns:
            None
        """
        self.portfolio.update_position(event.time, event.ticker, event.close)
        self.portfolio.log()

    def on_tick(self, event, kwargs=None):
        pass

    def on_fill(self, event, kwargs=None):
        """
        update portfolio's positions when there is a FillEvent

        Args:
            event(fxdayu.event.ExecutionEvent): FillEvent
            kwargs(dict): dict for sharing data

        Returns:
            None
        """
        fill = event.data
        if fill.fill_type == 'position':
            if fill.action == OPEN_ORDER:
                position = self.portfolio.open_position(
                    fill.ticker, fill.price,
                    fill.quantity, fill.time,
                    fill.commission
                )
                if position:
                    fill.position_id = position.identifier
            elif fill.action == CLOSE_ORDER:
                position = self.portfolio.close_position(
                    fill.ticker, fill.price,
                    fill.quantity, fill.time,
                    fill.commission
                )
                fill.profit = position.profit
                fill.position_id = position.identifier
        elif fill.fill_type == 'order':
            if fill.action == OPEN_ORDER:
                self.portfolio.open_order(
                    fill.order_ext_id, fill.ticker, fill.price,
                    fill.quantity, fill.time, fill.commission,
                    lever=fill.lever, deposit_rate=fill.deposit_rate
                )
            elif fill.action == CLOSE_ORDER:
                self.portfolio.close_order(
                    fill.order_ext_id, fill.price, fill.quantity,
                    fill.time, fill.commission
                )

    def on_confirm(self, event, kwargs=None):
        pass

    def on_time(self, event, kwargs=None):
        for ticker in self.portfolio.positions:
            current = self.data.current(ticker)
            self.portfolio.update_position(current['datetime'], ticker, current['close'])
            self.portfolio.log()
        for order in self.portfolio.orders.values():
            current = self.data.current(order.ticker)
            self.portfolio.update_order(current['datetime'], order, current['close'])
            self.portfolio.log()