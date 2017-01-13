from dictproxyhack import dictproxy

from bigfishtrader.engine.handler import HandlerCompose, Handler
from bigfishtrader.event import EVENTS


class OrderHandler(HandlerCompose):
    def __init__(self):
        super(OrderHandler, self).__init__()
        self._handlers["on_order"] = Handler(self.on_fill, EVENTS.ORDER, topic=".", priority=-100)
        self._handlers["on_fill"] = Handler(self.on_order, EVENTS.FILL, topic=".", priority=-100)

    def on_order(self, order, kwargs):
        pass

    def on_fill(self, order, kwargs):
        pass


class StorageOrderHandler(OrderHandler):
    def __init__(self, timing=True):
        super(StorageOrderHandler, self).__init__()
        self._orders = {}
        self._fills = {}
        self._order_ref = 0
        self._fill_ref = 0
        self.timing = timing

    @property
    def orders(self):
        return dictproxy(self._orders)

    @property
    def fills(self):
        return dictproxy(self._fills)

    def on_order(self, order, kwargs):
        """
        :param order: order event
        :type order: bigfishtrader.event.OrderEvent
        :param kwargs: other optional parameters
        :type kwargs: dict
        """
        self._order_ref += 1
        order.local_id = self._order_ref
        self._orders[order.local_id] = order

    def on_fill(self, fill, kwargs):
        self._fill_ref += 1
        fill.local_id = self._fill_ref
        self._fills[fill.local_id] = fill
