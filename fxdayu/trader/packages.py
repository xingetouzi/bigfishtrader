from fxdayu.trader.trader import Component
from collections import OrderedDict
from fxdayu.data.data_support import DataSupport
from fxdayu.modules.timer.simulation import TimeSimulation
from fxdayu.modules.portfolio.handlers import PortfolioHandler
from fxdayu.modules.security import SecurityPool
from fxdayu.router import DummyExchange
from fxdayu.modules.account.handlers import AccountHandler
from fxdayu.modules.order.handlers import OrderStatusHandler
from fxdayu.context import ContextMixin
from fxdayu.engine.handler import HandlerCompose, Handler
from fxdayu.event import EVENTS


class Strategy(HandlerCompose, ContextMixin):
    def __init__(self, engine, context, environment, data):
        super(Strategy, self).__init__(engine)
        ContextMixin.__init__(self, context, environment, data)
        self._handlers['on_time'] = Handler(self.on_time, EVENTS.TIME)

    def link_context(self):
        pass

    def on_time(self, event, kwargs=None):
        print event.time


DEVELOP_MODE = OrderedDict([
    ("data", Component("data", DataSupport, (), {"context": Component.Lazy('context')})),
    ("timer", Component("timer", TimeSimulation, (), {'engine': Component.Lazy('engine')})),
    ("portfolio", Component("PortfolioHandler", PortfolioHandler, (), {})),
    ("router", Component("router", DummyExchange, (Component.Lazy('engine'),), {})),
    ("security_pool", Component("security_pool", SecurityPool, (), {})),
    ("account_handler", Component("account_handler", AccountHandler, (), {})),
    ("order_book_handler", Component("order_book_handler", OrderStatusHandler, (), {})),
    ("portfolio", Component("portfolio_handler", PortfolioHandler, (), {}))
])


if __name__ == '__main__':
    from fxdayu.trader import Trader
    from datetime import datetime

    trader = Trader(DEVELOP_MODE)
    trader.settings['strategy'] = Component('strategy', Strategy, (), {})

    trader.run(['000001'], 'D', datetime(2016, 1, 1), ticker_type='HS')