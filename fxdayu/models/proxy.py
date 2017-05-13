import copy

from fxdayu.const import OrderStatus, OrderType
from fxdayu.models.order import OrderReq


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
            self._new_order = OrderReq()
            self._new_order.gateway = self._order_req.gateway
            self._new_order.account = self._order_req.account
            self._new_order.clOrdID = self._order_req.clOrdID
            self._new_order.exchange = self._order_req.exchange
            self._new_order.security = self._order_req.security
            self._new_order.symbol = self._order_req.symbol
            self._new_order.side = self._order_req.side
            self._new_order.action = self._order_req.action
            self._new_order.orderQty = self._order_req.orderQty
            self._new_order.ordType = self._order_req.ordType
            self._new_order.price = self._order_req.price
            self._new_order.stopPx = self._order_req.stopPx
            self._new_order.timeInForce = self._order_req.timeInForce
            self._new_order.transactTime = self._order_req.transactTime
            self._new_order.expireTime = self._order_req.expireTime

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
        if self._new_order:
            return self._new_order.price
        else:
            return self._order_req.price

    @price.setter
    def price(self, value):
        if value != self._order_req.price:
            self._copy()
            self._new_order.price = value

    def send(self):
        if self._new_order and self.status not in {OrderStatus.PARTTRADED, OrderStatus.ALLTRADED,
                                                   OrderStatus.CANCELLED}:
            # print("%s\n%s" % (self._new_order.to_dict(), self._order_req.to_dict()))
            self._sender.send_order(self._new_order)
            self._new_order = None

    def cancel(self):
        if self.status not in {OrderStatus.ALLTRADED, OrderStatus.CANCELLED}:
            self._sender.cancel_order(self._order_req.gClOrdID)
