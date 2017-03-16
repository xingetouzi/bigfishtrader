# encoding: utf-8
from enum import Enum

from fxdayu.const import ORDERTYPE, ACTION, ORDERSTATUS
from fxdayu.engine.handler import Handler
from fxdayu.event import ExecutionEvent, RecallEvent, EVENTS
from fxdayu.models.data import ExecutionData
from fxdayu.router.base import AbstractRouter
from fxdayu.context import ContextMixin


class BACKTESTDEALMODE(Enum):
    THIS_BAR_CLOSE = 0
    NEXT_BAR_OPEN = 1


class DummyExchange(AbstractRouter, ContextMixin):
    """
    DummyExchange if a simulation of a real exchange.
    It handles OrderEvent(ORDER,LIMIT,STOP) and
    generate FillEvent which then be put into the event_queue
    """

    def link_context(self):
        pass

    def __init__(self, engine, context, environment, data, exchange_name=None,
                 deal_model=BACKTESTDEALMODE.NEXT_BAR_OPEN,
                 **ticker_information):
        """
        :param event_queue:
        :param exchange_name:
        :param ticker_information: ticker={'lever':10000,'deposit_rate':0.02}
        :return:
        """
        super(DummyExchange, self).__init__(engine)
        ContextMixin.__init__(self, context, environment, data)
        self.ticker_info = ticker_information
        self.exchange_name = exchange_name
        self.deal_mode = deal_model
        self._orders = {}
        self._handlers = {
            "on_order": Handler(self.on_order, EVENTS.ORDER, topic="", priority=0),
            "on_time": Handler(self.on_time, EVENTS.TIME, topic="bar.open", priority=200),
        }
        self.handle_order = {
            ORDERTYPE.MARKET.value: self._execute_market,
            ORDERTYPE.LIMIT.value: self._execute_limit,
            ORDERTYPE.STOP.value: self._execute_stop
        }
        self._order_id = 0
        self.account = "BACKTEST"
        self.gateway = "BACKTEST"

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

    def _put_execution(self, order, price, timestamp):
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
        execution.clOrderID = order.clOrdID
        execution.execID = order.clOrdID
        execution.account = order.account
        execution.gateway = order.gateway
        execution.position_id = order.clOrdID
        for k, v in self.ticker_info.get(order.symbol, {}):
            setattr(execution, k, v)
        event = ExecutionEvent(execution, timestamp=timestamp, topic=order.symbol)
        self._orders.pop(order.clOrdID, None)
        self.engine.put(event)

    def on_cancel(self, event, kwargs=None):
        """
        When a CancelEvent arrives, remove the orders that satisfy the event's condition
        :param event:
        :return:
        """
        cancels = []
        for order in self._orders.values():
            if order.match(event.conditions):
                cancels.append(order.cliOrdID)
        for _id in cancels:
            self._orders.pop(_id, None)

    def _execute_market(self, order, bar):
        self._put_execution(order, bar.open, bar.name)

    def _execute_limit(self, order, bar):
        """
        deal with limit order

        Args:
            order(fxdayu.models.OrderReq):
            bar:

        Returns:
            None
        """
        if order.action == ACTION.OPEN.value:
            self._limit_open(order, bar)
        elif order.action == ACTION.CLOSE.value:
            self._stop_open(order, bar)

    def _execute_stop(self, order, bar):
        if order.action == ACTION.OPEN.value:
            self._stop_open(order, bar)
        elif order.action == ACTION.CLOSE.value:
            self._limit_open(order, bar)

    def _limit_open(self, order, bar):
        """
        deal with limit open order

        Args:
            order(fxdayu.models.OrderReq):
            bar:

        Returns:
            None
        """

        if order.orderQty > 0 and bar.low < order.price:
            price = order.price if bar.open >= order.price else bar.open
            self._put_execution(order, price, bar.name)
        elif order.orderQty < 0 and bar.high > order.price:
            price = order.price if bar.open <= order.price else bar.open
            self._put_execution(order, price, bar.name)

    def _stop_open(self, order, bar):
        """
        Args:
            order(fxdayu.models.OrderReq):
            bar:

        Returns:
            None
        """
        if order.orderQty > 0 and bar.high > order.price:
            price = order.price if bar.open <= order.price else bar.open
            self._put_execution(order, price, bar.name)
        elif order.orderQty < 0 and bar.low < order.price:
            price = order.price if bar.open >= order.price else bar.open
            self._put_execution(order, price, bar.name)

    def on_time(self, event, kwargs=None):
        for _id, order in self._orders.items():
            self.handle_order[order.ordType](order, self.data.current(order.symbol))

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
        self.engine.put(RecallEvent(order.transactTime, order))  # 不管何种订单，都先返回已经挂单成功事件
        if order.ordType == ORDERTYPE.MARKET.value and self.deal_mode == BACKTESTDEALMODE.THIS_BAR_CLOSE:
            current = self.data.current(order.symbol)
            self._put_execution(order, current.close, current.name)  # 直接成交
        else:
            self._orders[order.clOrdID] = order  # 放入交易所orderbook留给on_bar函数去处理成交

    def get_orders(self):
        return {_id: order.to_dict() for _id, order in self._orders.items()}