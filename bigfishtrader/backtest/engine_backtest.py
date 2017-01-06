from bigfishtrader.event import EVENTS, FinalEvent


class EngineBackTest(object):
    def __init__(self, event_queue, engine, strategy, price_handler, portfolio_handler, trader):
        """
        :param event_queue:
        :param engine:
        :param strategy:
        :param price_handler:
        :param portfolio_handler:
        :param trader:
        :return:
        """
        self.event_queue = event_queue
        self.strategy = strategy
        self.price_handler = price_handler
        self.portfolio_handler = portfolio_handler
        self.portfolio = portfolio_handler.portfolio
        self.trader = trader
        self.engine = engine
        self.engine.register(self._handle_bar, stream=EVENTS.BAR, topic=".", priority=0)
        self.engine.register(self._handle_fill, stream=EVENTS.FILL, topic=".", priority=0)
        self.engine.register(self._handle_order, stream=EVENTS.ORDER, topic=".", priority=0)

    def run(self, start=None, end=None):
        import time
        self.price_handler.initialize(start, end)
        self.strategy.initialize_operation(
            self.event_queue, self.price_handler, self.portfolio
        )
        self.engine.start()
        total = 0
        count = 0
        while self.price_handler.running:
            st = time.clock()
            count += 1
            self.price_handler.next_stream()
            total += time.clock() - st
        print("Fetch data count: %s" % count)
        print("Fetch data average time: %f seconds" % (total / count))
        self.event_queue.put(FinalEvent())
        self.engine.join()
        self.engine.stop()
        # close all position when backtest end
        for position in self.portfolio.positions.copy().values():
            self.portfolio.close_position(
                position.ticker, position.price,
                position.quantity, self.portfolio.current_time()
            )
        return self.portfolio

    def _handle_bar(self, event, kwargs):
        self.portfolio_handler.on_bar(event)
        self.strategy.handle_data(self.portfolio, self.price_handler.get_instance())

    def _handle_order(self, event, kwargs):
        self.trader.on_order(event)

    def _handle_fill(self, event, kwargs):
        self.portfolio_handler.on_fill(event)
