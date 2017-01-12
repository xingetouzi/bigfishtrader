# from bigfishtrader.operation import initialize_operation
from bigfishtrader.event import EVENTS


class Handler(object):
    __slots__ = ["func", "stream", "topic", "priority"]

    def __init__(self, func, stream, topic=".", priority=0):
        self.func = func
        self.stream = stream
        self.topic = topic
        self.priority = priority

    def register(self, engine):
        """
        :param engine: event engine
        :type engine: bigfishtrader.engine.core.Engine
        :return: None
        """
        engine.register(self.func, stream=self.stream, topic=self.topic, priority=self.priority)

    def unregister(self, engine):
        """
        :param engine: event engine
        :type engine: bigfishtreader.engine.core.Engine
        :return: None
        """
        engine.unregister(self.func, stream=self.stream, topic=self.topic)


class HandlerCompose(object):
    def __init__(self):
        self._handlers = {}

    @property
    def handler(self):
        return self._handlers

    def register(self, engine):
        for handler in self._handlers.values():
            handler.register(engine)

    def unregister(self, engine):
        for handler in self._handlers.values():
            handler.unregister(engine)


class BigFishTrader(object):
    def __init__(self, event_queue, engine, price_handler, portfolio_handler, order_handler, trade_handler):
        self.event_queue = event_queue
        self.engine = engine
        self.price_handler = price_handler
        self.portfolio_handler = portfolio_handler
        self.order_handler = order_handler
        self.portfolio = portfolio_handler.portfolio
        self.trade_handler = trade_handler
        if self.order_handler:
            self.order_handler.register(self.engine)
        if self.price_handler:
            self.price_handler.register(self.engine)
        if self.portfolio_handler:
            self.portfolio_handler.register(self.engine)
        if self.trade_handler:
            self.trade_handler.register(self.engine)
        # initialize_operation(self.event_queue, self.price_handler, self.portfolio)
        self.engine.register(self.on_tick, stream=EVENTS.TICK, topic=".", priority=0)

    def run(self):
        self.engine.start()
        self.price_handler.run()
        self.engine.join()
        self.engine.stop()

    def stop(self):
        self.engine.stop()

    def on_tick(self, event, kwargs):
        pass
