from collections import OrderedDict

from fxdayu.data.active_stock import ActiveDataSupport
from fxdayu.data.data_support import DataSupport
from fxdayu.modules.account.handlers import AccountHandler
from fxdayu.modules.order.handlers import OrderStatusHandler
from fxdayu.modules.portfolio.handlers import PortfolioHandler
from fxdayu.modules.security import SecurityPool
from fxdayu.modules.timer.real_timer import RealTimer
from fxdayu.modules.timer.simulation import TimeSimulation
from fxdayu.router import DummyExchange
from fxdayu.router.paper_exchange import PaperExchange
from fxdayu.trader.component import Component
from fxdayu.models.dao.engine import PersistenceEngine

DEVELOP_MODE = OrderedDict([
    ("data", Component("data", DataSupport, (Component.Lazy('context'), ), {})),
    ("timer", Component("timer", TimeSimulation, (), {'engine': Component.Lazy('engine')})),
    ("portfolio", Component("PortfolioHandler", PortfolioHandler, (), {})),
    ("router", Component("router", PaperExchange, (), {})),
    ("security_pool", Component("security_pool", SecurityPool, (), {})),
    ("account_handler", Component("account_handler", AccountHandler, (), {})),
    ("order_book_handler", Component("order_book_handler", OrderStatusHandler, (), {})),
    ("persistence", Component("persistence", PersistenceEngine, (), {}))
])

PORTFOLIO_CONFIG = {"host": "localhost",
                    "port": 27017,
                    "db": "portfolios",
                    "collection": "TradeDemo"}

TRADING_MODE = OrderedDict([
    ("data", Component("data", ActiveDataSupport, (),
                       {'external': "E:\\bigfishtrader\\fxdayu\data\local_mongo.json",
                        'cache': "E:\\bigfishtrader\\fxdayu\data\\remote_redis.json"})),
    ('timer', Component("timer", RealTimer, (), {})),
    ("portfolio", Component("PortfolioHandler", PortfolioHandler, (), {})),
    ("router", Component("router", DummyExchange, (), {})),
    ("security_pool", Component("security_pool", SecurityPool, (), {})),
    ("account_handler", Component("account_handler", AccountHandler, (), {})),
    ("order_book_handler", Component("order_book_handler", OrderStatusHandler, (), {})),
    ("persistence", Component("persistence", PersistenceEngine, ("sqlite:///db.sqlite", ), {}))
])

if __name__ == '__main__':
    from fxdayu.trader.trader import Trader

    trader = Trader(TRADING_MODE)
    trader.initialize().activate()
