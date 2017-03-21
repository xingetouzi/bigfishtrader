# encoding:utf-8
from collections import OrderedDict
from datetime import datetime
import os

import pandas as pd
from pandas import ExcelWriter

from fxdayu.context import Context, ContextMixin
from fxdayu.engine import Engine
from fxdayu.event import EVENTS
from fxdayu.engine.handler import HandlerCompose
from fxdayu.modules.account.handlers import AccountHandler
from fxdayu.modules.order.handlers import OrderStatusHandler
from fxdayu.modules.portfolio.handlers import PortfolioHandler
from fxdayu.modules.security import SecurityPool
from fxdayu.environment import *
from fxdayu.router import DummyExchange
from fxdayu.utils.api_support import EnvironmentContext
from fxdayu.performance import OrderAnalysis
from fxdayu.modules.timer.simulation import TimeSimulation
from fxdayu.data.data_support import DataSupport


OUTPUT_COLUMN_MAP = {
    "equity": OrderedDict([("datetime", "时间"), ("equity", "净值")]),
    "execution": OrderedDict([("clOrderID", "报单编号"),
                              ("symbol", "合约"),
                              ("side", "买卖"),
                              ("action", "开平"),
                              ("leavesQty", "未成交数"),
                              ("lastQty", "成交数"),
                              ("time", "最后成交时间"),
                              ("lastPx", "成交均价"),
                              ("commission", "手续费"),
                              ("exchange", "交易所")]),
    "order": OrderedDict([("clOrdID", "报单编号"),
                          ("orderQty", "报单数"),
                          ("ordStatus", "报单状态"),
                          ("price", "报单价格"),
                          ("orderTime", "报单时间")
                        ])
}

ROUND_MAP = {u"五年平均年收益": 2,
             u"净利回撤比": 2,
             u"夏普比率": 2,
             u"平均月收益": 2,
             u"年化收益标准差": 2,
             u"最大回撤率": 2,
             u"最大回撤比率": 2,
             u"最大回撤金额": 2,
             u"盈利因子": 2}


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

    def __init__(self, settings=None):
        self.engine = Engine()
        self.context = Context(self.engine)
        self.context.register()
        self.environment = Environment()
        self.environment_context = EnvironmentContext(self.environment)
        self.performance = OrderAnalysis()
        self.modules = {'context': self.context,
                        'engine': self.engine,
                        'environment': self.environment}
        if settings:
            self.settings = settings
        else:
            self._init_settings()
        self.initialized = False

    def _init_settings(self):
        self.settings = OrderedDict([
            ("data", Component(
                "data",
                DataSupport,
                (),
                {
                    "context": self.context,
                    # "event_queue": self.engine,
                    # "port": 27017
                }
            )),
            ("timer", Component(
                "timer",
                TimeSimulation,
                (),
                {'engine': self.engine}
            )),
            ("portfolio", Component(
                "PortfolioHandler",
                PortfolioHandler,
                (),
                {}
            )),
            ("router", Component(
                "router",
                DummyExchange,
                (self.engine,),
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
            "order_book_handler", OrderStatusHandler,
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
            raise TypeError("settings‘s value should be Component or tuple, not: %s" % type(value))

    def _register_models(self):
        for name, module in self.modules.items():
            if hasattr(module, "register"):
                try:
                    module.register()
                except TypeError:
                    if isinstance(module, (Engine, Environment, Context)):
                        pass

    def initialize(self):
        """
        """
        for name, co in self.settings.items():
            args = [self.modules[para.name] if isinstance(para, Component.Lazy) else para for para in co.args]
            kwargs = {key: self.modules[para.name] if isinstance(para, Component.Lazy) else para for key, para in
                      co.kwargs.items()}
            if issubclass(co.constructor, ContextMixin):
                args[:0] = [self.context, self.environment, self.modules["data"]]
            if issubclass(co.constructor, HandlerCompose):
                args[:0] = [self.engine]
            self.modules[name] = co.constructor(*args, **kwargs)
        self._register_models()
        self.context.link(**self.modules)
        self.initialized = True
        return self

    def run(self, symbols, frequency, start=None, end=None, ticker_type=None, params={}, save=False):
        if not self.initialized:
            self.initialize()

        context, data, engine = self.context, self.modules["data"], self.engine

        for name, param in params.items():
            for key, value in param.items():
                setattr(self.modules[name], key, value)

        data.init(symbols, frequency, start, end, ticker_type)

        engine.set_context(self.environment_context)
        self.modules['timer'].put_time()
        engine.start()
        engine.join()
        engine.stop()
        self.perform()

        return self.modules['portfolio']

    def back_test(self, filename, symbols, frequency, start=None, end=None, ticker_type=None, params=None, save=False):
        """
        运行一个策略, 完成后返回一个账户对象

        Args:
            filename:
            symbols:
            frequency:
            start:
            end:
            ticker_type:
            params:
            save:
        """
        if not self.initialized:
            self.initialize()

        context, data, engine = self.context, self.modules["data"], self.engine
        strategy = self.environment.public.copy()
        if params:
            for key, value in params.items():
                strategy["key"] = value
        execfile(filename, strategy, strategy)
        data.init(symbols, frequency, start, end, ticker_type)
        context.tickers = symbols

        # TODO XXX
        context.account = Environment()
        context.account.id = "BACKTEST"

        def on_time(event, kwargs=None):
            strategy["handle_data"](context, data)

        self.engine.register(on_time, EVENTS.TIME, topic="bar.close", priority=100)

        with self.environment_context:
            strategy["initialize"](context, data)

        self.modules['timer'].put_time()
        engine.set_context(self.environment_context)
        engine.start()
        engine.join()
        engine.stop()
        self.perform()
        if save:
            name = os.path.basename(filename).split(".")[0]
            dt = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            pa = "&".join(map(lambda item: item[0] + "_" + str(item[1]), params.items()))
            path = "%s&%s&%s.xls" % (name, dt, pa)
            self._save_origin(path)
        self.initialized = False

        return self.modules["portfolio"]

    def _save_origin(self, path):
        if not self.initialized:
            raise ValueError("trader not initialized, no data to perform")

        writer = ExcelWriter(path, encoding="utf-8")
        pd.DataFrame(self.performance.equity).to_excel(writer, "净值")
        self.performance.order_details.to_excel(writer, "交易")
        writer.save()

    def perform(self):
        if not self.initialized:
            raise ValueError("trader not initialized, no data to perform")

        def reorganize(data_frame, key):
            return data_frame.rename_axis(OUTPUT_COLUMN_MAP[key], axis=1) \
                .reindex(columns=OUTPUT_COLUMN_MAP[key].values())

        eqt = pd.DataFrame(self.modules["portfolio"].info)
        eqt = pd.Series(eqt["equity"].values, index=eqt["datetime"])
        execs = self.modules["order_book_handler"].get_executions(method="df")
        orders = self.modules["order_book_handler"].get_status(method="df")
        execs = reorganize(execs, "execution")
        orders = reorganize(orders, "order")
        trades = pd.merge(orders, execs, how="left", left_on=["报单编号"], right_on=["报单编号"])
        self.performance.set_equity(eqt)
        self.performance.set_orders(trades)
        return self.performance

    def output(self, *args):
        return {attr: getattr(self.performance, attr, None) for attr in args}

    def save_performance(self, *args):
        w = pd.ExcelWriter("performance&%s.xls" % datetime.now().strftime("%Y-%m-%d-%H-%M-%S"))

        def iter_save(dict_like, name=None):
            for key, data in dict_like.items():
                table = key if not name else name + "_" + key
                if isinstance(data, dict):
                    iter_save(data, key)
                    continue
                elif isinstance(data, pd.Series):
                    data = pd.DataFrame(data)

                try:
                    data.to_excel(w, table)
                except Exception as e:
                    print(e.message)
                    print("%s can not be saved as .xls file" % table)
                    print(data)

        iter_save(self.output(*args))
        w.save()


class Optimizer(object):
    def __init__(self, settings=None):
        if settings:
            self.settings = {}

    def __getitem__(self, item):
        return self.settings[item]

    def __setitem__(self, item, value):
        self.settings[item] = value

    def optimization(self, filename, symbols, frequency,
                     start=None, end=None, ticker_type=None,
                     sort=u"夏普比率", ascending=False, save=False,
                     **params):
        result = []

        for param in self.exhaustion(**params):
            trader = Trader(self.settings)
            trader.back_test(
                filename, symbols, frequency,
                start, end, ticker_type, params=param, save=False
            )
            op_dict = trader.output("strategy_summary", "risk_indicator")
            print(param, "accomplish")
            for p in op_dict.values():
                param.update(p)
            result.append(param)

        result = pd.DataFrame(result).sort_values(by=sort, ascending=ascending)
        for key, value in ROUND_MAP.items():
            result[key] = result[key].round(value)

        if save:
            name = os.path.basename(filename).split(".")[0]
            dt = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            result.to_excel("Optimization_%s&%s.xls" % (name, dt), encoding="utf-8")
        print(result)
        return result

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


if __name__ == "__main__":
    pass
