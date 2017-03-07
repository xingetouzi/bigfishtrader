import logging
import time
from bigfishtrader.trader import Trader, Component
from bigfishtrader.vt.ctpGateway.ctpGateway import CtpGateway
from bigfishtrader.vt.ibGateway.ibGateway import IbGateway
from bigfishtrader.event import EVENTS
from bigfishtrader.contract import ContractPool
from bigfishtrader.environment import Environment
from bigfishtrader.context import ContextMixin, Context
from bigfishtrader.const import GATEWAY

logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)


class RuntimeTrader(Trader):
    def __init__(self):
        super(RuntimeTrader, self).__init__()
        self.context = Context()
        self.environment = Environment()

    def initialize(self):
        """
        """
        for name, co in self.settings.items():
            args = [self.models[para.name] if isinstance(para, Component.Lazy) else para for para in co.args]
            kwargs = {key: self.models[para.name] if isinstance(para, Component.Lazy) else para for key, para in
                      co.kwargs.items()}
            if issubclass(co.constructor, ContextMixin):
                self.models[name] = co.constructor(self.context, self.environment, *args, **kwargs)
                self.models[name].link_context()
            else:
                self.models[name] = co.constructor(*args, **kwargs)
        self._register_models()
        self.context.link(**self.models)
        self.initialized = True
        return self

    def init_settings(self):
        super(RuntimeTrader, self).init_settings()
        self.settings["contract_pool"] = Component(
            "contract_pool", ContractPool, (), {}
        )
        self.settings["router"] = Component(
            "router", IbGateway, (Component.Lazy("engine"),), {}
        )

    def connect(self):
        self.models["router"].connect()

    def run(self, strategy):
        if not self.initialized:
            raise Exception('Models not initialized, please call initialize()')
        context, data, engine = self.context, self.models['data'], self.models['engine']

        def on_time(event, kwargs=None):
            strategy.handle_data(context, data)

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

        last_time = time.time()

        def on_tick(event, kwargs=None):
            """

            Args:
                event(bigfishtrader.event.TickEvent):
                kwargs:

            Returns:
                None
            """
            global last_time


            last_time = time.time()

            tick = event.data
            print("tick: \n")
            print(tick.askPrice)
            print(tick.bidPrice)

        self.models["engine"].register(on_time, EVENTS.TIME, topic='.', priority=100)
        self.models["engine"].register(on_log, EVENTS.LOG, topic="")
        self.models["engine"].register(on_error, EVENTS.ERROR, topic="")
        self.models["engine"].register(on_position, EVENTS.POSITION, topic="")
        self.models["engine"].register(on_account, EVENTS.ACCOUNT, topic="")
        self.models["engine"].register(on_tick, EVENTS.TICK, topic="")
        strategy.initialize(context, data)
        engine.start()
        self.connect()
        self.models["router"].subscribe_contract(self.environment.contract("EUR.USD"))
        engine.join()

    def stop(self):
        self.models["engine"].stop()


if __name__ == "__main__":
    class S(object):
        def initialize(self, context, data):
            pass

        def handle_data(self, context, data):
            print(data)


    trader = RuntimeTrader()
    trader.initialize()
    trader.run(S())
