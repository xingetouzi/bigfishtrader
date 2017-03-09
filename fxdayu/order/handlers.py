from dictproxyhack import dictproxy

from fxdayu.engine.handler import HandlerCompose, Handler
from fxdayu.event import EVENTS


class AbstractOrderHandler(HandlerCompose):
    def __init__(self):
        super(AbstractOrderHandler, self).__init__()

    def on_order(self, order, kwargs):
        pass

    def on_fill(self, order, kwargs):
        pass


class OrderBookHandler(AbstractOrderHandler):
    def __init__(self):
        super(OrderBookHandler, self).__init__()
        self._handlers["on_order"] = Handler(self.on_order, EVENTS.ORDER, topic=".", priority=-100)
        self._handlers["on_fill"] = Handler(self.on_fill, EVENTS.EXECUTION, topic=".", priority=-100)
        self._orders = {}
        self._fills = {}
        self._order_ref = 0
        self._fill_ref = 0

    @property
    def orders(self):
        return dictproxy(self._orders)

    @property
    def fills(self):
        return dictproxy(self._fills)

    def on_order(self, order, kwargs=None):
        """
        :param order: order event
        :type order: bigfishtrader.event.OrderEvent
        :param kwargs: other optional parameters
        :type kwargs: dict
        """
        self._order_ref += 1
        order.order_id = self._order_ref
        self._orders[order.order_id] = order

    def on_fill(self, fill, kwargs=None):
        """

        Args:
            fill(bigfishtrader.event.ExecutionEvent):
            kwargs:

        Returns:

        """
        self._fill_ref += 1
        fill.order_id = self._fill_ref
        self._fills[fill.order_id] = fill
