# encoding:utf-8
from __future__ import unicode_literals

import os
from collections import OrderedDict
from datetime import datetime

import pandas as pd
from pandas import ExcelWriter

from fxdayu.context import Context, ContextMixin
from fxdayu.engine import Engine
from fxdayu.engine.handler import HandlerCompose
from fxdayu.environment import *
from fxdayu.event import EVENTS
from fxdayu.performance import OrderAnalysis
from fxdayu.trader.component import Component
from fxdayu.trader.packages import DEVELOP_MODE
from fxdayu.utils.api_support import EnvironmentContext

OUTPUT_COLUMN_MAP = {
    "equity": OrderedDict([("datetime", "时间"), ("equity", "净值")]),
    "execution": OrderedDict([
        ("clOrdID", "报单编号"),
        ("time", "最后成交时间"),
        ("lastQty", "成交数"),
        ("lastPx", "成交均价"),
        ("commission", "手续费"),
    ]),
    "order": OrderedDict([
        ("clOrdID", "报单编号"),
        ("symbol", "合约"),
        ("side", "买卖"),
        ("action", "开平"),
        ("orderQty", "报单数"),
        ("ordStatus", "报单状态"),
        ("price", "报单价格"),
        ("leavesQty", "未成交数"),
        ("orderTime", "报单时间"),
        ("cancelTime", "撤销时间"),
        ("exchange", "交易所"),
    ])
}


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
            self.settings = DEVELOP_MODE
        self.initialized = False

    def __getitem__(self, item):
        return self.settings[item]

    def __setitem__(self, key, value):
        if isinstance(value, Component):
            self.settings[key] = value
        elif isinstance(value, tuple):
            self.settings[key] = Component(*value)
        else:
            raise TypeError("settings‘s value should be Component or tuple, not: %s" % type(value))

    def _register_modules(self):
        for name, module in self.modules.items():
            if hasattr(module, "register"):
                try:
                    module.register()
                except TypeError as te:
                    if not isinstance(module, (Engine, Environment, Context)):
                        raise te
                except KeyError as ke:
                    print(module)
                    if not isinstance(module, (Engine, Environment, Context)):
                        raise ke

    def initialize(self):
        """
        """
        for name, co in self.settings.items():
            args = [self.modules[para.name] if isinstance(para, Component.Lazy) else para for para in co.args]
            kwargs = {key: self.modules[para.name] if isinstance(para, Component.Lazy) else para for key, para in
                      co.kwargs.items()}
            if issubclass(co.constructor, HandlerCompose):
                args[:0] = [self.engine]
            try:
                self.modules[name] = co.constructor(*args, **kwargs)
            except:
                print("Component initialize Fail: %s %s %s" % (co.constructor, args, kwargs))
                raise
        for name, co in self.settings.items():
            if issubclass(co.constructor, ContextMixin):
                module = self.modules[name]
                module.set_context(self.context)
                module.set_environment(self.environment)
                module.set_data(self.modules["data"])
                module.link_context()
        self._register_modules()
        self.context.link(**self.modules)
        for name, co in self.settings.items():
            if issubclass(co.constructor, ContextMixin):
                module = self.modules[name]
                module.init()
        self.initialized = True
        return self

    def activate(self):
        context, data, engine = self.context, self.modules["data"], self.engine
        context.account = Environment()
        context.account.id = "BACKTEST"

        engine.set_context(self.environment_context)
        engine.start()
        engine.join()
        engine.stop()

    def run(self, symbols, frequency=None, start=None, end=None, ticker_type=None, params=None, save=False):
        if not self.initialized:
            self.initialize()

        context, data, engine = self.context, self.modules["data"], self.engine

        if params:
            for name, param in params.items():
                for key, value in param.items():
                    setattr(self.modules[name], key, value)

        data.init(symbols, frequency, start, end, ticker_type)
        self.modules['timer'].put_time()

        self.activate()

        return self.modules['portfolio']

    def use_file(self, filename, raw_code=False, params=None):
        context, data = self.context, self.modules["data"]
        strategy = self.environment.public.copy()

        if raw_code:
            exec (filename, strategy, strategy)
        else:
            with open(filename) as f:
                exec (f.read(), strategy, strategy)

        if params:
            for key, value in params.items():
                strategy[key] = value

        # TODO XXX
        handle_data = strategy.get("handle_data", None)

        def on_time(event, kwargs=None):
            if handle_data:
                handle_data(context, data)

        self.engine.register(on_time, EVENTS.TIME, topic="bar.close", priority=100)

        with self.environment_context:
            strategy["initialize"](context, data)

        return strategy

    def real_trade(self, filename, **kwargs):
        if not self.initialized:
            self.initialize()

        self.use_file(filename, **kwargs)
        self.activate()

    def back_test(self, filename, symbols, frequency=None,
                  start=None, end=None, db=None, params=None, save=False, raw_code=False):
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

        def on_stop(event, kwargs=None):
            self.perform
            self.modules["persistence"].close()

        context, data = self.context, self.modules["data"]
        data.init(symbols, frequency, start, end, db)
        self.use_file(filename, raw_code, params)
        self.modules['timer'].put_time()
        self.engine.register(on_stop, EVENTS.EXIT, priority=100)
        self.activate()

        if save:
            params = {} if not params else params
            name = os.path.basename(filename).split(".")[0]
            dt = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            pa = "&".join(map(lambda item: item[0] + "_" + str(item[1]), params.items()))
            path = "%s&%s&%s.xls" % (name, dt, pa)
            self._save_origin(path)

        return self.modules["portfolio"]

    def _save_origin(self, path):
        # if not self.initialized:
        #     raise ValueError("trader not initialized, no data to perform")

        writer = ExcelWriter(path, encoding="utf-8")
        pd.DataFrame(self.performance.equity).to_excel(writer, "净值")
        self.performance.order_details.to_excel(writer, "交易")
        writer.save()

    @property
    def perform(self):
        if not self.initialized:
            raise ValueError("trader not initialized, no data to perform")

        def reorganize(data_frame, key):
            return data_frame.rename_axis(OUTPUT_COLUMN_MAP[key], axis=1) \
                .reindex(columns=OUTPUT_COLUMN_MAP[key].values())

        def cal_avg_price(x):
            avg_price = (x["成交数"] * x["成交均价"]).sum() / x["成交数"].sum()
            return pd.Series(avg_price, index=["avg_price"])

        eqt = pd.DataFrame(self.modules["portfolio"].info)
        eqt = pd.Series(eqt["equity"].values, index=eqt["datetime"])
        execs = self.modules["order_book_handler"].get_executions(method="df")
        orders = self.modules["order_book_handler"].get_status(method="df")
        execs = reorganize(execs, "execution")
        orders = reorganize(orders, "order")
        execs_group = execs.groupby("报单编号")
        temp = pd.DataFrame()
        temp["成交均价"] = execs_group[["成交数", "成交均价"]].apply(cal_avg_price)["avg_price"]
        temp["成交数"] = execs_group["成交数"].sum()
        temp["手续费"] = execs_group["手续费"].sum()
        temp["最后成交时间"] = execs_group["最后成交时间"].last()
        # TODO 撤销和执行统一返回execution，最后成交时间和撤销时间统一
        temp.reset_index(inplace=True)
        temp = pd.merge(orders[["报单编号"]], temp, how="left", left_on=["报单编号"], right_on=["报单编号"])
        temp["成交均价"] = temp["成交均价"].fillna(0)
        temp["成交数"] = temp["成交数"].fillna(0).astype(int)
        temp["手续费"] = temp["手续费"].fillna(0)
        trades = pd.merge(orders, temp, how="left", left_on=["报单编号"], right_on=["报单编号"])
        trades["撤销时间"] = trades["撤销时间"].fillna(pd.NaT)
        trades["报单编号"] = trades["报单编号"].astype(int)
        trades.sort_values("报单编号", inplace=True)
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
