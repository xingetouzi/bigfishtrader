import copy

from fxdayu.const import OrderStatus, OrderType


class OrderSenderMixin(object):
    def send_order(self, order):
        raise NotImplementedError

    def cancel_order(self, order):
        raise NotImplementedError


class OrderProxy(object):
    def __init__(self, req, status, sender):
        """


        Args:
            req(fxdayu.models.order.OrderReq):
            status(fxdayu.models.order.OrderStatusData):
            sender(OrderSenderMixin):

        Returns:

        """
        self._order_req = req
        self._order_stat = status
        self._sender = sender
        self._new_order = None

    def _copy(self):
        if self._new_order is None:
            self._new_order = copy.copy(self._order_req)

    @property
    def id(self):
        return self._order_req.gClOrdID

    @property
    def security(self):
        return self._order_req.security

    @property
    def create_time(self):
        return self._order_req.transactTime

    @property
    def style(self):
        return OrderType(self._order_req.ordType)

    @property
    def status(self):
        return OrderStatus(self._order_stat.ordStatus)

    @property
    def cum_qty(self):
        return self._order_stat.cumQty

    @property
    def leaves_qty(self):
        return self._order_stat.leavesQty

    @property
    def is_open(self):
        return self._order_stat.leavesQty > 0

    @property
    def can_modify(self):
        return self.status in {OrderStatus.GENERATE, OrderStatus.TRIGGERED, OrderStatus.NOTTRADED}

    @property
    def quantity(self):
        return self._order_stat.orderQty

    @quantity.setter
    def quantity(self, value):
        if value != self._order_req.price:
            self._copy()
            self._new_order.orderQty = value

    @property
    def price(self):
        return self._new_order.price

    @price.setter
    def price(self, value):
        if value != self._order_req.price:
            self._copy()
            self._new_order.price = value

    def send(self):
        if self._new_order:
            self._sender.send_order(self._new_order)
            self._new_order = None

    def cancel(self):
        self._sender.cancel_order(self._order_req.gClOrdID)
