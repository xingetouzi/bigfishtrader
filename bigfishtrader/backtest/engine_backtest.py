from bigfishtrader.event import EVENTS


class EngineBackTest(object):
    def __init__(self, event_queue, engine, strategy, price_handler, portfolio_handler, router):
        """
        :param event_queue:
        :param engine:
        :param strategy:
        :param price_handler:
        :param portfolio_handler:
        :type portfolio_handler: bigfishtrader.portfolio.handlers.PortfolioHandler
        :param router:
        :type router: bigfishtrader.core.HandlerCompose
        :return:
        """
        self.event_queue = event_queue
        self.strategy = strategy
        self.price_handler = price_handler
        self.portfolio_handler = portfolio_handler
        self.portfolio = portfolio_handler.portfolio
        self.router = router
        self.engine = engine
        self.router.register(engine)
        self.portfolio_handler.register(engine)
        self.price_handler.register(engine)
        self.engine.register(self._handle_bar, stream=EVENTS.BAR, topic=".", priority=0)

    def run(self, start=None, end=None):
        import time
        st = time.time()
        self.price_handler.initialize(start, end)
        self.strategy.initialize_operation(
            self.event_queue, self.price_handler, self.portfolio, self.router
        )
        self.strategy.initialize()
        self.engine.start()
        self.price_handler.run()
        count = len(self.price_handler.get_instance())
        total = time.time() - st
        print("Fetch data count: %s" % count)
        print("Fetch data average time: %f seconds" % (total / count))
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
        self.strategy.handle_data(self.portfolio, self.price_handler.get_instance(self.price_handler.get_ticker()))
