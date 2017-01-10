from bigfishtrader.portfolio.portfolio import Portfolio
from bigfishtrader.core import HandlerCompose, Handler
from bigfishtrader.event import OPEN_ORDER, CLOSE_ORDER, EVENTS


class PortfolioHandler(HandlerCompose):
    """
    This class is to handle Portfolio,
    including updating portfolio when a BAR, a TICK
    or a FILL event arrives
    """

    def __init__(self, event_queue, init_cash=100000, portfolio=None):
        super(PortfolioHandler, self).__init__()
        self.event_queue = event_queue
        self.portfolio = portfolio if portfolio is not None \
            else Portfolio(init_cash)
        self._handlers["on_bar"] = Handler(self.on_bar, EVENTS.BAR, topic=".", priority=10)
        self._handlers["on_tick"] = Handler(self.on_tick, EVENTS.TICK, topic=".", priority=10)
        self._handlers["on_fill"] = Handler(self.on_fill, EVENTS.FILL, topic="", priority=10)
        # self._handlers["on_confirm"] = Handler(self.on_confirm, EVENTS.CANCEL, topic=".", priority=100)

    def on_bar(self, event, kwargs=None):
        self.portfolio.update_position(event.time, event.ticker, event.close)
        self.portfolio.log()

    def on_tick(self, event, kwargs=None):
        pass

    def on_fill(self, event, kwargs=None):
        if event.action == OPEN_ORDER:
            self.portfolio.open_position(
                event.ticker, event.price,
                event.quantity, event.time,
                event.commission
            )
        elif event.action == CLOSE_ORDER:
            self.portfolio.close_position(
                event.ticker, event.price,
                event.quantity, event.time,
            )

    def on_confirm(self, event, kwargs=None):
        pass
