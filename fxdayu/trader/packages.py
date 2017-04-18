from fxdayu.trader.trader import Component
from collections import OrderedDict
from fxdayu.data.data_support import DataSupport
from fxdayu.data.active_stock import ActiveDataSupport
from fxdayu.modules.timer.simulation import TimeSimulation
from fxdayu.modules.timer.real_timer import RealTimer
from fxdayu.modules.portfolio.handlers import PortfolioHandler
from fxdayu.modules.security import SecurityPool
from fxdayu.router import DummyExchange
from fxdayu.modules.account.handlers import AccountHandler
from fxdayu.modules.order.handlers import OrderStatusHandler
from fxdayu.context import ContextMixin
from fxdayu.engine.handler import HandlerCompose, Handler
from fxdayu.event import EVENTS


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


TRADING_MODE = OrderedDict([
    ("data", Component("data", ActiveDataSupport, (),
                       {'external': {'host': '192.168.0.103', 'port': 30000, 'db': 'TradeStock'}})),
    ('timer', Component("timer", RealTimer, (), {}))
])


if __name__ == '__main__':
    from fxdayu.trader.trader import Trader

    trader = Trader(TRADING_MODE)
    trader.initialize().activate()
