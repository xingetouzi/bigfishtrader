from bigfishtrader.core import Handler, HandlerCompose
from bigfishtrader.event import FillEvent, EVENTS


class DummyExchange(HandlerCompose):
    """
    DummyExchange if a simulation of a real exchange.
    It handles OrderEvent(ORDER,LIMIT,STOP) and
    generate FillEvent which then be put into the event_queue
    """

    def __init__(self, event_queue, exchange_name=None, **ticker_information):
        """
        :param event_queue:
        :param exchange_name:
        :param ticker_information: ticker={'lever':10000,'deposit_rate':0.02}
        :return:
        """
        super(DummyExchange, self).__init__()
        self.event_queue = event_queue
        self.ticker_info = ticker_information
        self.exchange_name = exchange_name
        self.orders = []
        self._handlers = {
            "on_bar": Handler(self.on_bar, EVENTS.BAR, topic="", priority=100),
            "on_order": Handler(self.on_order, EVENTS.ORDER, topic=".", priority=0)
        }
        self.handle_order = {
            EVENTS.ORDER: self._fill_order,
            EVENTS.LIMIT: self._fill_limit,
            EVENTS.STOP: self._fill_stop
        }

    @staticmethod
    def calculate_commission(order, price):
        return 1

    @staticmethod
    def calculate_slippage(order, price):
        return 0

    def _put_fill(self, order, price, timestamp):
        fill = FillEvent(
            timestamp, order.ticker,
            order.action, order.quantity,
            price + self.calculate_slippage(order, price),
            self.calculate_commission(order, price),
            **self.ticker_info.get(order.ticker, {})
        )
        self.orders.remove(order)
        self.event_queue.put(fill)

    def on_cancel(self, event):
        """
        When a CancelEvent arrives, remove the orders that satisfy the event's condition
        :param event:
        :return:
        """
        for order in self.orders:
            if order.match(event.conditions):
                self.orders.remove(order)

    def _fill_order(self, order, bar):
        self._put_fill(order, bar.open, bar.time)

    def _fill_limit(self, order, bar):
        if order.action:
            if order.quantity > 0 and bar.low < order.price:
                price = order.price if bar.open >= order.price else bar.open
                self._put_fill(order, price, bar.time)
            elif order.quantity < 0 and bar.high > order.price:
                price = order.price if bar.open <= order.price else bar.open
                self._put_fill(order, price, bar.time)
        else:
            self._fill_stop(order, bar)

    def _fill_stop(self, order, bar):
        if order.action:
            if order.quantity > 0 and bar.high > order.price:
                price = order.price if bar.open <= order.price else bar.open
                self._put_fill(order, price, bar.time)
            elif order.quantity < 0 and bar.low < order.price:
                price = order.price if bar.open >= order.price else bar.open
                self._put_fill(order, price, bar.time)
        else:
            self._fill_limit(order, bar)

    def on_order(self, event, kwargs=None):
        """
        When an order arrives put it into self.orders
        :param event:
        :param kwargs:
        :return:
        """
        self.orders.append(event)

    def on_bar(self, bar_event, kwargs=None):
        """
        :param bar_event:
        :param kwargs:
        :return:
        """
        for order in self.orders:
            self.handle_order[order.type](order, bar_event)
