# encoding:utf-8
from collections import OrderedDict

from fxdayu.context import Context, ContextMixin
from fxdayu.data.support import MultiDataSupport
from fxdayu.engine import Engine
from fxdayu.event import EVENTS
from fxdayu.engine.handler import HandlerCompose
from fxdayu.modules.account.handlers import AccountHandler
from fxdayu.modules.order.handlers import OrderBookHandler
from fxdayu.modules.portfolio.handlers import PortfolioHandler
from fxdayu.modules.security import SecurityPool
from fxdayu.environment import *
from fxdayu.router.exchange import DummyExchange
from fxdayu.utils.api_support import EnvironmentContext


class Component(object):
    __slots__ = ["name", "constructor", "args", "kwargs"]

    class Lazy(object):
        def __init__(self, name):
            self.name = name

    def __init__(self, name, constructor, args, kwargs):
        self.name = name
        self.constructor = constructor
        self.args = args
        self.kwargs = kwargs

    def get(self, item):
        return self.Lazy(item)


class Trader(object):
    """
    用于自由组织模块并进行回测
    """

    def __init__(self):
        self.engine = Engine()
        self.context = Context(self.engine)
        self.context.register(self.engine)
        self.environment = Environment()
        self.environment_context = EnvironmentContext(self.environment)
        self.settings = {}
        self.models = {}
        self._init_settings()
        self.initialized = False

    def _init_settings(self):
        self.settings = OrderedDict([
            ('data', Component(
                'data',
                MultiDataSupport,
                (),
                {
                    'context': self.context,
                    'event_queue': self.engine,
                    'port': 27017
                }
            )),
            ('portfolio', Component(
                'PortfolioHandler',
                PortfolioHandler,
                (),
                {}
            )),
            ('router', Component(
                'router',
                DummyExchange,
                (self.engine, ),
                {}
            )),
        ])
        self.settings["security_pool"] = Component(
            "security_pool", SecurityPool, (), {}
        )
        self.settings["account_handler"] = Component(
            "account_handler", AccountHandler, (), {}
        )
        self.settings["order_book_handler"] = Component(
            "order_book_handler", OrderBookHandler,
            (), {}
        )
        self.settings["portfolio"] = Component(
            "portfolio_handler", PortfolioHandler, (), {}
        )

    def __getitem__(self, item):
        return self.settings[item]

    def __setitem__(self, key, value):
        if isinstance(value, Component):
            self.settings[key] = value
        elif isinstance(value, tuple):
            self.settings[key] = Component(*value)
        else:
            raise TypeError("settings's value should be Component or tuple, not: %s" % type(value))

    def _register_models(self):
        for name, model in self.models.items():
            if hasattr(model, "register"):
                model.register(self.engine)

    def initialize(self):
        """
        """
        for name, co in self.settings.items():
            args = [self.models[para.name] if isinstance(para, Component.Lazy) else para for para in co.args]
            kwargs = {key: self.models[para.name] if isinstance(para, Component.Lazy) else para for key, para in
                      co.kwargs.items()}
            if issubclass(co.constructor, ContextMixin):
                args[:0] = [self.context, self.environment, self.models["data"]]
            if issubclass(co.constructor, HandlerCompose):
                args[:0] = [self.engine]
            self.models[name] = co.constructor(*args, **kwargs)
        self._register_models()
        self.context.link(**self.models)
        self.initialized = True
        return self

    def back_test(self, filename, tickers, frequency, start=None, end=None, ticker_type=None, **kwargs):
        """
        运行一个策略, 完成后返回一个账户对象

        :param filename: 策略模块
        :param kwargs: 需要修改的策略参数
        :return: Portfolio
        """
        if not self.initialized:
            raise Exception('Models not initialized, please call initialize()')

        context, data, engine = self.context, self.models['data'], self.engine
        strategy = self.environment.dct.copy()
        for key, value in kwargs.items():
            strategy["key"] = value
        execfile(filename, strategy, strategy)
        data.init(tickers, frequency, start, end, ticker_type)
        context.tickers = tickers

        # TODO XXX
        context.account = Environment()
        context.account.id = "BACKTEST"

        def on_time(event, kwargs=None):
            strategy["handle_data"](context, data)

        self.engine.register(on_time, EVENTS.TIME, topic='bar.close', priority=100)

        strategy["initialize"](context, data)
        engine.start()
        engine.join()
        engine.stop()

        self.initialized = False

        return self.models['portfolio']


class Optimizer(object):
    def __init__(self):
        self._trader = Trader()

    def optimization(self, strategy, tickers, frequency, start=None, end=None, ticker_type=None,
                     models=(), settings=None, **params):
        if settings is None:
            settings = {}
        portfolios = []
        for k in self.exhaustion(**params):
            portfolio = self._trader.initialize().backtest(
                strategy, tickers, frequency,
                start, end, ticker_type, **k
            )

            k['portfolio'] = portfolio
            portfolios.append(k)

        return portfolios

    def exhaustion(self, **kwargs):
        """
        generator, 穷举所有的参数组合

        :param kwargs:
        :return: dict
        """
        key, values = kwargs.popitem()
        if len(kwargs):
            for value in values:
                for d in self.exhaustion(**kwargs):
                    d[key] = value
                    yield d
        else:
            for value in values:
                yield {key: value}


if __name__ == '__main__':
    pass
