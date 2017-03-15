# encoding: utf-8

try:
    from Queue import Empty
except ImportError:
    from queue import Empty

from fxdayu.event import EVENTS


class BackTest(object):
    def __init__(self, event_queue, strategy, price_handler, portfolio_handler, router):
        self.event_queue = event_queue
        self.strategy = strategy
        self.price_handler = price_handler
        self.portfolio_handler = portfolio_handler
        self.portfolio = portfolio_handler.portfolio
        self.router = router
        self.handle = {
            EVENTS.BAR: self._handle_bar,
            EVENTS.ORDER: self._handle_order,
            EVENTS.EXECUTION: self._handle_fill,
            EVENTS.LIMIT: self._handle_order,
            EVENTS.STOP: self._handle_order,
            EVENTS.CANCEL: self.router.on_cancel,
            EVENTS.EXIT: self._exit
        }

    def init_params(self, **params):
        for key, value in params.items():
            setattr(self.strategy, key, value)

    def run(self, start=None, end=None, **params):
        self.price_handler.initialize(start, end)
        self.strategy.initialize_operation(
            self.event_queue, self.price_handler,
            self.portfolio, self.router
        )
        self.init_params(**params)

        self.strategy.initialize()

        while self.price_handler.running or self.event_queue.qsize():
            try:
                event = self.event_queue.get(timeout=0)
            except Empty:
                self.price_handler.next_stream()
            else:
                self.handle[event.type](event)

        return self.portfolio

    def _exit(self, event):

        for position in self.portfolio.get_positions().values():
            self.portfolio.close_position(
                position.ticker, position.price,
                position.quantity, self.portfolio.current_time
            )

    def _handle_bar(self, event):
        self.router.on_bar(event)
        self.portfolio_handler.on_bar(event)
        self.strategy.handle_data(self.portfolio, self.price_handler.get_instance(event.ticker))

    def _handle_order(self, event):
        self.router.on_order(event)

    def _handle_fill(self, event):
        self.portfolio_handler.on_execution(event)
