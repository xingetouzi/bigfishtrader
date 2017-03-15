# encoding:utf-8
try:
    from Queue import PriorityQueue
except ImportError:
    from queue import PriorityQueue
import types
from collections import OrderedDict

from fxdayu.engine.core import Engine
from fxdayu.context import Context
from fxdayu.portfolio.portfolio import OrderPortfolio, PositionPortfolio
from fxdayu.data.support import MultiDataSupport
from fxdayu.router.exchange import DummyExchange, PracticeExchange
from fxdayu.event import EVENTS


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
        self.settings = {}
        self.models = {}
        self.init_settings()
        self.initialized = False

    def init_settings(self):
        self.settings = OrderedDict([
            ('event_queue', Component('event_queue', PriorityQueue, (), {})),
            ('engine', Component('engine', Engine, (), {'event_queue': Component.Lazy('event_queue')})),
            ('context', Component('context', Context, (), {})),
            ('data', Component('data', MultiDataSupport, (), {
                'context': Component.Lazy('context'),
                'event_queue': Component.Lazy('event_queue'),
                'port': 27017
            })),
            ('portfolio', Component('portfolio', PositionPortfolio, (
                Component.Lazy("event_queue"), Component.Lazy("data")
            ), {})),
            ('router', Component('router', DummyExchange, (
                Component.Lazy("event_queue"), ), {})),
        ])

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
        engine = self.models['engine']
        for name, model in self.models.items():
            if hasattr(model, "register") and name not in {"engine", "event_queue"}:
                model.register(engine)

    def initialize(self):
        """
        """
        for name, co in self.settings.items():
            args = [self.models[para.name] if isinstance(para, Component.Lazy) else para for para in co.args]
            kwargs = {key: self.models[para.name] if isinstance(para, Component.Lazy) else para for key, para in
                      co.kwargs.items()}
            self.models[name] = co.constructor(*args, **kwargs)
        self._register_models()
        self.models["context"].link(**self.models)
        self.initialized = True
        return self

    def backtest(self, strategy, tickers, frequency, start=None, end=None, ticker_type=None, **kwargs):
        """
        运行一个策略，完成后返回账户

        :param strategy: Strategy, 继承自策略基类的策略
        :param tickers: str or list, 品种, 可以是单个也可以是多个
        :param frequency: str, 时间周期, 以数据库中的命名为准
        :param start: datetime, 开始时间
        :param end: datetime, 结束时间
        :param ticker_type: 品种类型, 以数据库中的 db name 为准
        :param kwargs: 策略运行时需要修改的策略参数
        :return: Portfolio
        """
        if not self.initialized:
            raise Exception('Models not initialized, please call initialize()')

        context, data = self.models['context'], self.models['data']

        data.init(tickers, frequency, start, end, ticker_type)
        context.tickers = [tickers] if isinstance(tickers, str) else tickers

        s = strategy(**self.models)
        s.register(self.models['engine'])
        s.init_params(**kwargs)
        s.initialize()

        engine = self.models['engine']
        engine.start()
        engine.join()
        engine.stop()

        self.initialized = False

        print(kwargs, 'accomplish')

        return self.models['portfolio']

    def back_test(self, strategy, tickers, frequency, start=None, end=None, ticker_type=None, **kwargs):
        """
        运行一个策略, 完成后返回一个账户对象

        :param strategy: 策略模块
        :param kwargs: 需要修改的策略参数
        :return: Portfolio
        """
        if not self.initialized:
            raise Exception('Models not initialized, please call initialize()')

        context, data, engine = self.models['context'], self.models['data'], self.models['engine']

        data.init(tickers, frequency, start, end, ticker_type)
        context.tickers = tickers

        def on_time(event, kwargs=None):
            strategy.handle_data(context, data)

        self.models['engine'].register(on_time, EVENTS.TIME, topic='.', priority=100)

        for key, value in kwargs.items():
            setattr(strategy, key, value)

        strategy.initialize(context, data)
        engine.start()
        engine.join()
        engine.stop()

        self.initialized = False

        return self.models['portfolio']


class PracticeTrader(Trader):
    def init_settings(self):
        super(PracticeTrader, self).init_settings()
        self.settings["router"] = Component("router", PracticeExchange, (), {
            'event_queue': Component.Lazy('event_queue'),
            'data': Component.Lazy('data'),
            'portfolio': Component.Lazy('portfolio'),
        })


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
    from bokeh.plotting import figure, output_file, show

    pass
