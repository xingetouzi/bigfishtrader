from queue import Empty
from bigfishtrader.event import EVENTS


class BackTest(object):
    def __init__(self, event_queue, strategy, price_handler, portfolio_handler, trader):
        self.event_queue = event_queue
        self.strategy = strategy
        self.price_handler = price_handler
        self.portfolio_handler = portfolio_handler
        self.portfolio = portfolio_handler.portfolio
        self.trader = trader
        self.handle = {
            EVENTS.BAR: self._handle_bar,
            EVENTS.ORDER: self._handle_order,
            EVENTS.FILL: self._handle_fill
        }

    def run(self, start=None, end=None):
        self.price_handler.initialize(start, end)
        self.strategy.initialize_operation(
            self.event_queue, self.price_handler, self.portfolio
        )

        while self.price_handler.running:
            try:
                event = self.event_queue.get(timeout=0)
            except Empty:
                self.price_handler.next_stream()
            else:
                self.handle[event.type](event)
        # close all position when backtest end
        for position in self.portfolio.positions.copy().values():
            self.portfolio.close_position(
                position.ticker, position.price,
                position.quantity, self.portfolio.current_time()
            )

        return self.portfolio

    def _handle_bar(self, event):
        self.portfolio_handler.on_bar(event)
        self.strategy.handle_data(self.portfolio, self.price_handler.get_instance())

    def _handle_order(self, event):
        self.trader.on_order(event)

    def _handle_fill(self, event):
        self.portfolio_handler.on_fill(event)
