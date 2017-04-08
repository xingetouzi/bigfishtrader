# encoding: utf-8

from collections import OrderedDict
import copy

from enum import Enum

from fxdayu.const import OrderType, OrderAction, OrderStatus
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

    EVENT_TO_ENGINE = True
    # To decide whether put event to engine or schedule it manually.
    # manually schedule it may make back test faster.

    def __init__(self, engine, context, environment, data, exchange_name=None,
                 deal_model=BACKTESTDEALMODE.NEXT_BAR_OPEN,
                 **ticker_information):
        """
        :param event_queue:
        :param exchange_name:
        :param ticker_information: ticker={'lever':10000,'deposit_rate':0.02}
        :return:
        """
        super(PaperExchange, self).__init__(engine)
        ContextMixin.__init__(self, context, environment, data)
        self.ticker_info = ticker_information
        self.exchange_name = exchange_name
        self.deal_mode = deal_model
        self._orders = OrderedDict()
        self._handlers = {
            "on_order": Handler(self.on_order, EVENTS.ORDER, topic="", priority=0),
            "on_time": Handler(self.on_time, EVENTS.TIME, topic="bar.open", priority=200),
            "on_execution": Handler(self.on_execution, EVENTS.EXECUTION, priority=0)
        }
        self.handle_order = {
            OrderType.MARKET: self._execute_market,
            OrderType.LIMIT: self._execute_limit,
            OrderType.STOP: self._execute_stop
        }
        self._order_id = 0
        self.account = "BACK_TEST"
        self.gateway = "BACK_TEST"

    @property
    def next_order_id(self):
        self._order_id += 1
        return self._order_id

    def handle_price(self, price, timestamp):
        for order in self._orders.values():
            self.handle_order[OrderType(order.ordType)](order, price, timestamp)

    def _execute_market(self, order, price, timestamp):
        return self._make_execution(order, price, timestamp)

    def _execute_limit(self, order, price, timestamp):
        if order.orderQty > 0 and price < order.price:
            return self._make_execution(order, order.price, timestamp)
        elif order.orderQty < 0 and price > order.price:
            return self._make_execution(order, order.price, timestamp)

    def _execute_stop(self, order, price, timestamp):
        if order.orderQty > 0 and price > order.price:
            return self._make_execution(order, order.price, timestamp)
        elif order.orderQty < 0 and price < order.price:
            return self._make_execution(order, order.price, timestamp)

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
        for k, v in self.ticker_info.get(order.symbol, {}):
            setattr(execution, k, v)
        self._orders.pop(order.clOrdID, None)
        event = ExecutionEvent(execution, timestamp=timestamp, topic=order.symbol)
        return event

    def on_cancel(self, event, kwargs=None):
        """
        When a CancelEvent arrives, remove the orders that satisfy the event's condition
        :param event:
        :return:
        """
        pass

    def _put(self, event):
        if event:
            if self.EVENT_TO_ENGINE:
                self.engine.put(event)

    def on_time(self, event, kwargs=None):
        for order in self._orders.values():
            self._put(self.handle_order[order.ordType](order, self.data.current(order.symbol)))

    def on_order(self, event, kwargs=None):
        """

        Args:
            event(fxdayu.event.OrderEvent):
            kwargs:

        Returns:

        """
        order = event.data
        order.clOrdID = str(self.next_order_id)  # 由于VNPY的设计，id由ROUTER设定，故这里由exchange分配order id
        order.account = self.account
        order.gateway = self.gateway
        if order.ordType == OrderType.MARKET.value and self.deal_mode == BACKTESTDEALMODE.THIS_BAR_CLOSE:
            current = self.data.current(order.symbol)
            self._put(self._make_execution(order, current.close, current.name))  # 直接成交
        else:
            self._orders[order.clOrdID] = order  # 放入交易所blotter留给on_bar函数去处理成交

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
