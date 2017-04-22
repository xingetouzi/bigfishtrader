import logging
import time

from fxdayu.event import EVENTS, InitEvent
from fxdayu.router.paper_exchange import PaperExchange
from fxdayu.trader.trader import Trader, Component
from fxdayu.vnpy.gateway import GATEWAY_DICT

logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)

last_time = time.time()


class RuntimeTrader(Trader):
    def __init__(self):
        super(RuntimeTrader, self).__init__()

    def _init_settings(self):
        super(RuntimeTrader, self)._init_settings()
        self.settings[""] = Component(
            "router", PaperExchange, (), {}
        )
        self.settings["ib_router"] = Component(
            "ib_router", GATEWAY_DICT["IB"].gateway, (), {}
        )

    def connect(self):
        self.modules["router"].connect()

    def _run(self, filename):
        if not self.initialized:
            raise Exception('Models not initialized, please call initialize()')
        context, data, engine = self.context, self.modules['data'], self.modules['engine']
        strategy = execfile(filename, self.environment.public)

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

        # self.modules["engine"].register(on_time, EVENTS.TIME, topic='.', priority=100)
        self.modules["engine"].register(on_time, EVENTS.TICK, topic=".", priority=100)
        self.modules["engine"].register(on_log, EVENTS.LOG, topic="")
        self.modules["engine"].register(on_error, EVENTS.ERROR, topic="")
        # self.modules["engine"].register(on_position, EVENTS.POSITION, topic="")
        # self.modules["engine"].register(on_account, EVENTS.ACCOUNT, topic="")
        # self.modules["engine"].register(on_tick, EVENTS.TICK, topic="")
        engine.start()
        self.connect()
        time.sleep(5)
        self.environment.initialize(self.context, data)
        self.modules["router"].subscribe_contract(self.environment.symbol("EUR.USD"))
        engine.join()

    def run(self, filename):
        with self.environment_context:
            self._run(filename)

    def stop(self):
        self.modules["engine"].stop()


if __name__ == "__main__":
    import os

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_strategy.py")
    trader = RuntimeTrader()
    trader.initialize()
    trader.run(path)
