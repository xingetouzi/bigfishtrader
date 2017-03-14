# encoding: utf-8

import copy
import pandas as pd

from bigfishtrader.const import ORDERSTATUS
from bigfishtrader.engine.handler import HandlerCompose, Handler
from bigfishtrader.event import EVENTS, OrderEvent
from bigfishtrader.models.data import OrderStatusData, Security, OrderReq
from bigfishtrader.context import ContextMixin
from bigfishtrader.order.style import *
from bigfishtrader.utils.api_support import api_method


class AbstractOrderHandler(HandlerCompose, ContextMixin):
    def __init__(self, context, environment, data):
        """

        Args:
            context:
            environment(bigfishtrader.environment.Environment):

        Returns:

        """
        super(AbstractOrderHandler, self).__init__()
        ContextMixin.__init__(self, context, environment, data)
        #  Order.clOrderID should be confirmed before this handler be called in working stream
        self._handlers["on_order"] = Handler(self.on_order, EVENTS.ORDER, topic=".", priority=-100)
        self._handlers["on_execution"] = Handler(self.on_execution, EVENTS.EXECUTION, topic=".", priority=-100)
        self._handlers["on_order_status"] = Handler(self.on_order_status, EVENTS.ORD_STATUS, topic=".", priority=-100)

    def on_order(self, order, kwargs=None):
        raise NotImplementedError

    def on_order_status(self, status, kwargs=None):
        raise NotImplementedError

    def on_execution(self, execution, kwargs=None):
        raise NotImplementedError

    def link_context(self):
        raise NotImplementedError


class OrderBookHandler(AbstractOrderHandler):
    def __init__(self, context, environment, data, event_queue):
        super(OrderBookHandler, self).__init__(context, environment, data)
        self._adapter = OrderReqAdapter(context, environment)
        self._orders = {}
        self._open_orders = {}
        self._executions = {}
        self._order_status = {}
        self._event_queue = event_queue

    def on_order(self, event, kwargs=None):
        """
        Args:
            event(bigfishtrader.event.OrderEvent): order event
            kwargs(dict): other optional parameters

        Returns:

        """
        order = event.data
        if order.clOrdID:
            self._orders[order.gClOrdID] = order
            if order.gSymbol not in self._open_orders:
                self._open_orders[order.gSymbol] = []
            self._open_orders[order.gSymbol].append(order)
            status = OrderStatusData()
            status.exchange = order.exchange
            status.symbol = order.symbol
            status.clOrdID = order.clOrdID
            status.action = order.action
            status.side = order.side
            status.price = order.price
            status.orderQty = order.orderQty
            status.leavesQty = order.orderQty
            status.ordStatus = ORDERSTATUS.GENERATE.value
            status.gateway = order.gateway
            status.account = order.account
            self._order_status[status.gClOrdID] = status
        else:
            pass  # TODO warning Order send failed

    def on_execution(self, event, kwargs=None):
        """

        Args:
            event(bigfishtrader.event.ExecutionEvent):
            kwargs:

        Returns:

        """
        execution = event.data
        self._executions[execution.execID] = event

    def on_order_status(self, event, kwargs=None):
        """

        Args:
            event(bigfishtrader.event.OrderStatusEvent):
            kwargs:

        Returns:
            None
        """
        status_new = event.data
        status_old = self._order_status[status_new.gClOrdID]
        status_old.ordStatus = status_new.ordStatus
        status_old.cumQty = status_new.cumQty
        status_old.leavesQty = status_new.leavesQty
        status_old.orderTime = status_new.orderTime
        status_old.cancelTime = status_new.cancelTime
        if status_new.ordStatus == ORDERSTATUS.ALLTRADED.value or status_new.ordStatus == ORDERSTATUS.CANCELLED.value:
            order = self._orders[status_new.gClOrdID]
            try:
                self._open_orders[order.gSymbol].remove(order)
            except ValueError:
                pass

    def get_order_status(self, order):
        """

        Args:
            order:

        Returns:
            bigfishtrader.models.data.OrderStatusData
        """
        return self._order_status.get(order, None)

    def get_order(self, order):
        return copy.copy(self._orders[order])

    def get_open_orders(self, security):
        if isinstance(security, Security):
            security = security.sid
        if security is None:
            return copy.deepcopy(self._open_orders)
        elif security in self._open_orders:
            return copy.deepcopy(self._open_orders[security])
        else:
            return {}

    def _miss_security(self):
        pass  # TODO warning

    def get_executions(self, method="df"):
        if method == "df":
            return pd.DataFrame(list(map(lambda x: x.to_dict(ordered=True), self._executions)))
        elif method == "list":
            return copy.deepcopy(self._executions)

    @api_method
    def order(self, security, amount, limit_price=None, stop_price=None, style=None):
        if not style:
            if limit_price and stop_price:
                style = StopLimitOrder(limit_price, stop_price)
            elif limit_price:
                style = LimitOrder(limit_price)
            elif stop_price:
                style = StopOrder(stop_price)
            else:
                style = MarketOrder()
        order = self._adapter.parse(security, amount, style)
        if order:
            event = OrderEvent(order)
            self._event_queue.put(event)
            return order
        else:
            self._miss_security()

    def order_target(self, security, amount, style=None):
        if not isinstance(security, Security):
            security = self.environment.symbol(security)
        amount = int(amount)
        if security:
            position = self.context.portfolio.positions.get(security.sid)
            if position:
                volume = position.volume
            else:
                volume = 0
            delta = amount - volume
            if delta != 0:
                return self.order(security, delta, style=style)
            else:
                return None
        else:
            self._miss_security()

    def _value2shares(self, security, value):
        # TODO 完成实时的current和history遍写
        point = self.data.current(security.symbol, ["close"])
        point_value = security.point_value if hasattr(security, "point_value") else 1
        return int(value / point / point_value)

    def _percent2shares(self, security, percent):
        value = self.context.portfolio.cash * percent
        return self._value2shares(security, value)

    def order_value(self, security, value, style=None):
        if not isinstance(security, Security):
            security = self.environment.symbol(security)
        if security:
            return self.order(security, self._value2shares(security, value), style=style)
        else:
            self._miss_security()

    def order_target_value(self, security, value, style=None):
        if not isinstance(security, Security):
            security = self.environment.symbol(security)
        if security:
            return self.order_target(security, self._value2shares(security, value), style=style)
        else:
            self._miss_security()

    def order_percent(self, security, percent, style=None):
        if not isinstance(security, Security):
            security = self.environment.symbol(security)
        if security:
            return self.order(security, self._percent2shares(security, percent), style=style)
        else:
            self._miss_security()

    def order_target_percent(self, security, percent, style=None):
        if not isinstance(security, Security):
            security = self.environment.symbol(security)
        if security:
            return self.order_target(security, self._percent2shares(security, percent), style=style)
        else:
            self._miss_security()

    def cancel_order(self, order):
        if isinstance(order, OrderReq):
            order = order.clOrdID
        else:
            return

    def link_context(self):
        # find order
        self.environment["get_order"] = self.get_order
        self.environment["get_open_orders"] = self.get_open_orders

        # place order
        self.environment["order"] = self.order
        self.environment["order_target"] = self.order_target
        self.environment["order_value"] = self.order_value
        self.environment["order_target_value"] = self.order_target_value
        self.environment["order_percent"] = self.order_percent
        self.environment["order_target_percent"] = self.order_target_percent
        self.environment["get_order_status"] = self.get_order_status
        self.environment["cancel_order"] = self.cancel_order

        # style
        self.environment["MarketOrder"] = MarketOrder
        self.environment["StopOrder"] = MarketOrder
        self.environment["LimitOrder"] = LimitOrder
        self.environment["StopLimitOrder"] = StopLimitOrder
