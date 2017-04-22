# encoding: utf-8
import copy
from collections import OrderedDict

import numpy as np
from enum import Enum

from fxdayu.const import OrderType, OrderAction, OrderStatus, Direction
from fxdayu.engine.handler import Handler
from fxdayu.event import EVENTS, ExecutionEvent, OrderStatusEvent
from fxdayu.models.data import ExecutionData
from fxdayu.router.base import AbstractRouter
from fxdayu.context import ContextMixin
from fxdayu.utils.api_support import api_method


class BACKTESTDEALMODE(Enum):
    THIS_BAR_CLOSE = 0
    NEXT_BAR_OPEN = 1


class PaperExchange(AbstractRouter, ContextMixin):
    """
    DummyExchange if a simulation of a real exchange.
    It handles OrderEvent(ORDER,LIMIT,STOP) and
    generate FillEvent which then be put into the event_queue
    """

    def __init__(self, engine, context, environment, data, exchange_name=None,
                 deal_model=BACKTESTDEALMODE.NEXT_BAR_OPEN):
        """
        Args:
            engine:
            context:
            environment:
            data:
            exchange_name:
            deal_model:
        """
        super(PaperExchange, self).__init__(engine)
        ContextMixin.__init__(self)
        self.exchange_name = exchange_name
        self.deal_mode = deal_model
        self._orders = OrderedDict()
        self._handlers = {
            "on_order": Handler(self.on_order, EVENTS.ORDER, topic="", priority=0),
            "on_time": Handler(self.on_time, EVENTS.TIME, topic="bar.open", priority=200),
            "on_execution": Handler(self.on_execution, EVENTS.EXECUTION, priority=0),
            "on_cancel": Handler(self.on_cancel, EVENTS.CANCEL, priority=0)
        }
        self.handle_order = {
            OrderType.MARKET.value: self._execute_market,
            OrderType.LIMIT.value: self._execute_limit,
            OrderType.STOP.value: self._execute_stop
        }
        self._order_id = 0

    @property
    def next_order_id(self):
        self._order_id += 1
        return self._order_id

    @staticmethod
    def calculate_commission(order, price):
        return 1

    @staticmethod
    def calculate_slippage(order, price):
        return 0

    def _make_status(self, order_id, execution=None, canceled=False):
        """

        Args:
            order_id: order_id
            execution(fxdayu.models.data.ExecutionData):
            canceled(bool)
        Returns:

        """
        old = self.environment.get_order_status(order_id)
        status = copy.copy(old)
        if canceled:
            status.ordStatus = OrderStatus.CANCELLED.value
            status.leavesQty = 0
            status.cancelTime = self.context.current_time
        else:
            if execution:
                status.cumQty += execution.lastQty
            # TODO 没有计算成交均价
            status.leavesQty = status.orderQty - status.cumQty
            if status.cumQty:
                if status.leavesQty:
                    status.ordStatus = OrderStatus.PARTTRADED.value
                else:
                    status.ordStatus = OrderStatus.ALLTRADED.value
            else:
                status.ordStatus = OrderStatus.NOTTRADED.value
        event = OrderStatusEvent(status, timestamp=self.context.current_time)
        return event

    def _make_execution(self, order, price, timestamp):
        """

        Args:
            order(fxdayu.models.OrderReq):
            price:
            timestamp:

        Returns:

        """
        if price != price:
            print("%s is not able to trade at %s" % (order.symbol, timestamp))
            return
        execution = ExecutionData()
        execution.time = timestamp
        execution.symbol = order.symbol
        execution.side = order.side
        execution.cumQty = order.orderQty
        execution.leavesQty = 0
        execution.lastQty = order.orderQty
        execution.action = order.action
        execution.lastPx = price + self.calculate_slippage(order, price)
        execution.commission = self.calculate_commission(order, price)
        execution.clOrdID = order.clOrdID
        execution.execID = order.clOrdID
        execution.account = order.account
        execution.exchange = order.exchange
        execution.gateway = order.gateway
        execution.position_id = order.clOrdID
        event = ExecutionEvent(execution, timestamp=timestamp, topic=order.symbol)
        return event

    def on_cancel(self, event, kwargs=None):
        """
        """
        cancel = event.data
        order_id = cancel.orderID
        cl_ord_id = order_id.split(".")[-1]
        if self._orders.pop(cl_ord_id, None):
            self.put(self._make_status(order_id, canceled=True))

    def _execute_market(self, order, bar):
        return self._make_execution(order, bar.open, bar.name)

    def _execute_limit(self, order, bar):
        """
        deal with limit order

        Args:
            order(fxdayu.models.OrderReq):
            bar:

        Returns:
            None
        """
        side = Direction(order.side)
        if side == Direction.LONG and bar.low < order.price:
            price = order.price if bar.open > order.price else bar.open
            return self._make_execution(order, price, bar.name)
        elif side == Direction.SHORT and bar.high > order.price:
            price = order.price if bar.open < order.price else bar.open
            return self._make_execution(order, price, bar.name)

    def _execute_stop(self, order, bar):
        side = Direction(order.side)
        if side == Direction.LONG and bar.high > order.price:
            price = order.price if bar.open <= order.price else bar.open
            return self._make_execution(order, price, bar.name)
        elif side == Direction.SHORT and bar.low < order.price:
            price = order.price if bar.open >= order.price else bar.open
            return self._make_execution(order, price, bar.name)

    def _put_execution(self, event):
        self.engine.put(event)

    def on_time(self, event, kwargs=None):
        executed = []
        for order in self._orders.values():
            event = self.handle_order[order.ordType](order, self.data.current(order.symbol))
            if event:
                executed.append(order.clOrdID)
                self._put_execution(event)
        for order in executed:
            self._orders.pop(order, None)

    def on_order(self, event, kwargs=None):
        """

        Args:
            event(fxdayu.event.OrderEvent):
            kwargs:

        Returns:

        """
        order = event.data
        if order.ordType == OrderType.MARKET.value and self.deal_mode == BACKTESTDEALMODE.THIS_BAR_CLOSE:
            self._orders.pop(order.clOrdID, None)  # modify order
            current = self.data.current(order.symbol)
            self._put(self._make_execution(order, current.close, current.name))  # 直接成交
        else:
            self._orders[order.clOrdID] = order  # 放入交易所orderbook留给on_bar函数去处理成交

    def on_execution(self, event, kwargs=None):
        execution = event.data
        self.engine.put(self._make_status(execution.gClOrdID, execution))

    def get_orders(self):
        return {_id: order.to_dict() for _id, order in self._orders.items()}

    def link_context(self):
        self.environment.set_private("make_execution", self._make_execution)
        self.environment['set_commission'] = self.set_commission
        self.environment['set_slippage'] = self.set_slippage

    @api_method
    def set_commission(self, per_value=0, per_share=0, min_cost=0, function=None):
        if function is None:
            def commission(order, price):
                return max(order.orderQty * (price * per_value + per_share), min_cost)

            setattr(self, 'calculate_commission', commission)
        else:
            setattr(self, 'calculate_commission', function)

    @api_method
    def set_slippage(self, pct=0, function=None):
        if function is None:
            setattr(self, 'calculate_slippage',
                    lambda order, price: price * pct if order.orderQty > 0 else -price * pct)
        else:
            setattr(self, 'calculate_slippage', function)
