# encoding:utf-8
try:
    from Queue import PriorityQueue
except ImportError:
    from queue import PriorityQueue
import types

from bigfishtrader.engine.core import Engine
from bigfishtrader.context import Context
from bigfishtrader.portfolio.portfolio import OrderPortfolio, PositionPortfolio
from bigfishtrader.data.support import MultiDataSupport
from bigfishtrader.router.exchange import DummyExchange, PracticeExchange
from bigfishtrader.event import EVENTS


class ModelHandler(object):
    def __init__(self, *models):
        self.settings = list(models)
        self.series = [model[0] for model in self.models]
        self.models = {}
        self.initialized = False

    def __getitem__(self, item):
        return self.models[item]

    def __setitem__(self, key, value):
        self.models[key] = value

    def copy(self, *models):
        settings = self.settings
        for model in models:
            try:
                index = self.series.index(model[0])
            except ValueError:
                settings.append(model)
            else:
                settings[index] = model

        return ModelHandler(settings)

    def reset(self, *models):
        self.__init__(*models)

    def update(self, *models, **kwargs):
        for model in models:
            self._update(model)

    def _update(self, model_package):
        try:
            index = self.series.index(model_package[0])
        except ValueError:
            self.settings.append(model_package)
            self.series = [model[0] for model in self.models]
            return

        self.settings[index] = model_package

    def initialize(self):
        self.init_models()
        self.register_models()
        self.initialized = True

    def init_models(self):
        for name, model, kw in self.settings:
            if isinstance(model, (types.FunctionType, types.MethodType)):
                self.models[name] = model(self.models, **kw)
            else:
                self._init_model(name, model, **kw)

    def _init_model(self, name, model, **kwargs):
        self.models[name] = model(
            **dict(
                map(
                    lambda (key, value): (key, value(self.models))
                    if isinstance(value, (types.FunctionType, types.MethodType))
                    else (key, self.models.get(value, value)),
                    kwargs.items()
                )
            )
        )

    def register_models(self):
        engine = self.models['engine']
        for name, model in self.models.items():
            try:
                model.register(engine)
            except TypeError as te:
                if name == 'engine':
                    continue
                else:
                    raise te
            except AttributeError as ae:
                if name == 'event_queue':
                    continue
                else:
                    raise ae


class Trader(object):
    """
    用于自由组织模块并进行回测
    """

    def __init__(self):
        self.init_settings()
        self.initialized = False

    def init_settings(self):
        self.settings = {}
        self.models = {}
        self.default_settings = [
            ('event_queue', PriorityQueue, {}),
            ('engine', Engine, {'event_queue': 'event_queue'}),
            ('context', Context, {}),
            ('data', MultiDataSupport,
             {'context': 'context', 'event_queue': 'event_queue', 'port': 27017}),
            ('portfolio', lambda models, **kwargs: OrderPortfolio(models['data'], models['event_queue'], **kwargs), {}),
            ('router', DummyExchange, {'event_queue': 'event_queue', 'data': 'data'}),
        ]
        self.default = list(map(lambda x: x[0], self.default_settings))
        self['default'] = self.default_settings

    def __getitem__(self, item):
        self.default_settings = self.settings[item]
        self.default = list(map(lambda x: x[0], self.default_settings))

        return self

    def __setitem__(self, key, value):
        self.settings[key] = value

    def set_default(self, **models):
        """
        修改默认模块的初始化参数
        当前默认的模块有: event_queue, engine, context, data, portfolio, router
        输入的不是默认模块将抛出异常

        :param models: data={'port': 30001, ....}
            data模块在初始化时输入的port参数由默认参数改为30001
        :return:
        """

        for key, value in models.items():
            try:
                i = self.default.index(key)
            except ValueError:
                raise ValueError('model %s is not a default model' % key)

            self.default_settings[i][2].update(value)
        return self

    def initialize(self, *models, **settings):
        """

        :param models: tuple, 需要更改或添加的模块
            输入的格式为: (name, model, params)
                name: str, 模块名, 如果与默认模块相同会替换默认模块, 否则添加到模块列表的尾部
                model: type or function, 未初始化的模块或是一个返回模块对象的函数
                    function: 函数接收的第一个参数为models(包含了已生成模块的字典), params 作为其他参数输入
                params: dict, 模块生成所需的参数, 当模块需要其他模块作为参数时, 可直接以模块名为参数
        :param settings: 修改默认模块的参数
        :return: self
        """
        self.set_default(**settings)
        self._init_models(*models)
        self.register_models()
        self.initialized = True
        return self

    def _init_models(self, *models):
        """
        初始化模块, 模块将按输入的顺序初始化,
        优先初始化默认模块, 如果输入的模块中包含默认模块将替换默认模块, 否则将在默认模块之后初始化

        :param models: (name, model, params)
            name: str, 模块名称
            model: type<class>, 输入模块类型或方法而不是对象
            params: dict, 初始化时需要输入的参数
                当模块需要其他模块作为参数时, 可直接以模块名为参数

        :return:
        """

        model_setting = list(self.default_settings)
        for m in models:
            try:
                i = self.default.index(m[0])
                model_setting[i] = m
            except ValueError:
                model_setting.append(m)

        for m in model_setting:
            name, model, kw = m[0], m[1], m[2]

            if isinstance(model, (types.FunctionType, types.MethodType)):
                self.models[name] = model(self.models, **kw)
            else:
                self._init_model(name, model, **kw)

        self.models['context'].link(**self.models)

    def register_models(self):
        engine = self.models['engine']
        for name, model in self.models.items():
            try:
                model.register(engine)
            except TypeError as t:
                if name == 'engine':
                    continue
                else:
                    raise t
            except AttributeError as a:
                if name == 'event_queue':
                    continue
                else:
                    raise a

    def set_model(self, name, model, **kwargs):
        self._init_model(name, model, **kwargs)

    def _init_model(self, name, model, **kwargs):
        self.models[name] = model(
            **dict(
                map(
                    lambda (key, value): (key, value(self.models)) if isinstance(value, (types.FunctionType, types.MethodType))
                    else (key, self.models.get(value, value)),
                    kwargs.items()
                )
            )
        )

    def backtest(self, strategy, tickers, frequency, start=None, end=None, ticker_type=None,  **kwargs):
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

    def back_test(self, strategy, tickers, frequency, start=None, end=None, ticker_type=None,  **kwargs):
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

    def optimization(self, strategy, tickers, frequency, start=None, end=None, ticker_type=None,
                     models=(), settings={}, **params):
        portfolios = []
        for k in self.exhaustion(**params):
            portfolio = self.initialize(
                *models, **settings
            ).backtest(
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


class PracticeTrader(Trader):

    def init_settings(self):
        self.models = {}
        self.default_settings = [
            ('event_queue', PriorityQueue, {}),
            ('engine', Engine, {'event_queue': 'event_queue'}),
            ('context', Context, {}),
            ('data', MultiDataSupport,
             {'context': 'context', 'event_queue': 'event_queue', 'port': 27017}),
            ('portfolio', PositionPortfolio, {'data': 'data', 'event_queue': 'event_queue'}),
            ('router', PracticeExchange,
             {'event_queue': 'event_queue', 'data': 'data', 'portfolio': 'portfolio'})
        ]
        self.default = list(map(lambda x: x[0], self.default_settings))
        self.settings = {'default': self.default_settings}


if __name__ == '__main__':
    trader = Trader()
    for t in trader.exhaustion(a=range(0, 3), b=range(0, 5, 2)):
        print t
