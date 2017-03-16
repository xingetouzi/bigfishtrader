import logging
import time

from fxdayu.context import ContextMixin, Context
from fxdayu.environment import Environment
from fxdayu.event import EVENTS, InitEvent
from fxdayu.modules.account.handlers import AccountHandler
from fxdayu.modules.order.handlers import OrderStatusHandler
from fxdayu.modules.security import SecurityPool
from fxdayu.position.handlers import PortfolioHandler
from fxdayu.trader import Trader, Component
from fxdayu.utils.api_support import EnvironmentContext

logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)

last_time = time.time()


class NewBackTrader(Trader):
    def __init__(self):
        super(NewBackTrader, self).__init__()
        self.context = Context()
        self.environment = Environment()
        self.environment_context = EnvironmentContext(self.environment)
        self.initialized = False

    def initialize(self):
        """
        """
        for name, co in self.settings.items():
            args = [self.models[para.name] if isinstance(para, Component.Lazy) else para for para in co.args]
            kwargs = {key: self.models[para.name] if isinstance(para, Component.Lazy) else para for key, para in
                      co.kwargs.items()}
            if issubclass(co.constructor, ContextMixin):
                self.models[name] = co.constructor(self.context, self.environment, self.models["data"], *args, **kwargs)
                self.models[name].link_context()
            else:
                self.models[name] = co.constructor(*args, **kwargs)
        self._register_models()
        self.context.link(**self.models)
        self.initialized = True
        return self

    def _init_settings(self):
        super(NewBackTrader, self)._init_settings()
        self.settings["security_pool"] = Component(
            "security_pool", SecurityPool, (), {}
        )
        self.settings["account_handler"] = Component(
            "account_handler", AccountHandler, (), {}
        )
        self.settings["order_book_handler"] = Component(
            "order_book_handler", OrderStatusHandler,
            (Component.Lazy("engine"),), {}
        )
        self.settings["portfolio"] = Component(
            "portfolio_handler", PortfolioHandler, (), {}
        )

    def on_init(self, event, kwargs=None):
        kwargs["context"] = self.context
        kwargs["environment"] = self.environment

    def connect(self):
        self.models["router"].connect()

    def _run(self, filename):
        if not self.initialized:
            raise Exception('Models not initialized, please call initialize()')
        context, data, engine = self.context, self.models['data'], self.models['engine']
        self.models["engine"].register(self.on_init, EVENTS.INIT, topic="", priority=1000)
        strategy = execfile(filename, self.environment.dct)

        def on_time(event, kwargs=None):
            self.environment.handle_data(context, data)

        def on_error(event, kwargs=None):
            error = event.data
            logging.error(" ".join([
                error.gateway, error.errorTime, str(error.errorID),
                error.errorMsg, error.additionalInfo
            ]))

        def on_log(event, kwargs=None):
            log = event.data
            logging.info(" ".join([
                log.gateway, log.logTime, log.logContent
            ]))

        def on_position(event, kwargs=None):
            position = event.data
            print("position:\n %s" % position.to_dict(ordered=True))

        def on_account(event, kwargs=None):
            account = event.data
            print("account:\n %s" % account.to_dict(ordered=True))

        def on_tick(event, kwargs=None):
            """

            Args:
                event(fxdayu.event.TickEvent):
                kwargs:

            Returns:
                None
            """
            global last_time

            self.context.symbol = self.environment.symbol("EUR.USD")
            if time.time() - last_time >= 2:
                position = self.context.portfolio.positions.get(self.context.symbol.sid, None)
                if position:
                    print("P: %s, %s" % (position.volume, position.frozenVolume))
                else:
                    print("P: 0, 0")
                if position and position.volume > 0:
                    self.environment.order(self.context.symbol.sid, -20000)
                    last_time = time.time()
                    print("SELL")
                else:
                    self.environment.order(self.context.symbol.sid, 20000)
                    last_time = time.time()
                    print("BUY")

        # self.models["engine"].register(on_time, EVENTS.TIME, topic='.', priority=100)
        self.models["engine"].register(on_time, EVENTS.TICK, topic=".", priority=100)
        self.models["engine"].register(on_log, EVENTS.LOG, topic="")
        self.models["engine"].register(on_error, EVENTS.ERROR, topic="")
        # self.models["engine"].register(on_position, EVENTS.POSITION, topic="")
        # self.models["engine"].register(on_account, EVENTS.ACCOUNT, topic="")
        # self.models["engine"].register(on_tick, EVENTS.TICK, topic="")
        engine.start()
        self.connect()
        time.sleep(5)
        self.models["event_queue"].put(InitEvent())
        time.sleep(5)
        self.environment.initialize(self.context, data)
        self.models["router"].subscribe_contract(self.environment.symbol("EUR.USD"))
        engine.join()
        self.initialized = False

    def run(self, filename):
        with self.environment_context:
            self._run(filename)

    def stop(self):
        self.models["engine"].stop()

    def back_test(self, filename, tickers, frequency, start=None, end=None,
                  ticker_type=None, **kwargs):
        if not self.initialized:
            raise Exception('Models not initialized, please call initialize()')

        context, data, engine = self.context, self.models['data'], self.models['engine']
        strategy = self.environment.dct.copy()
        for key, value in kwargs.items():
            strategy["key"] = value
        execfile(filename, strategy, strategy)
        data.init(tickers, frequency, start, end, ticker_type)
        context.tickers = tickers

        # TODO XXX
        context.account = Environment()
        context.account.id = "hahaha"

        def on_time(event, kwargs=None):
            strategy["handle_data"](context, data)

        self.models['engine'].register(on_time, EVENTS.TIME, topic='bar.close', priority=100)

        strategy["initialize"](context, data)
        engine.start()
        engine.join()
        engine.stop()

        self.initialized = False

        return self.models['portfolio']


if __name__ == "__main__":
    import os
    import pandas as pd
    from datetime import datetime

    pwd = os.path.dirname(os.path.abspath(__file__))
    path = os.path.abspath(__file__)
    trader = NewBackTrader()
    trader["data"].kwargs.update({"port": 27018, "host": "192.168.0.103"})
    p = trader.initialize().back_test(
        path,
        ['000001'], 'D', datetime(2016, 1, 1),
        ticker_type='HS', fast=10, slow=15
    )
    equity = (pd.DataFrame(
        p.info
    ))
    equity.to_csv(os.path.join(pwd, "result", "equity.csv"), index=False, encoding="utf-8")
    position = (pd.DataFrame(
        p.history)
    )
    position.to_csv(os.path.join(pwd, "result", "position.csv"), index=False, encoding="utf-8")
    execution = pd.DataFrame(trader.models["order_book_handler"].get_executions(method="df"))
    execution.to_csv(os.path.join(pwd, "result", "execution.csv"), encoding="utf-8")
