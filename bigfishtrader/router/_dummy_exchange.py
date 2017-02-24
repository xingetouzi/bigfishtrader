# encoding: utf-8
from enum import Enum
from bigfishtrader.engine.handler import Handler
from bigfishtrader.event import ExecutionEvent, RecallEvent, EVENTS
from bigfishtrader.model import ExecutionData
from bigfishtrader.const import ORDERTYPE, ACTION
from bigfishtrader.router.base import AbstractRouter


class BACKTESTDEALMODE(Enum):
    THIS_BAR_CLOSE = 0
    NEXT_BAR_OPEN = 1


class DummyExchange(AbstractRouter):
    """
    DummyExchange if a simulation of a real exchange.
    It handles OrderEvent(ORDER,LIMIT,STOP) and
    generate FillEvent which then be put into the event_queue
    """

    def __init__(self, event_queue, data, exchange_name=None, deal_model=BACKTESTDEALMODE.NEXT_BAR_OPEN,
                 **ticker_information):
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
        self.deal_mode = deal_model
        self._data = data
        self._orders = {}
        self._handlers = {
            "on_bar": Handler(self.on_bar, EVENTS.BAR, topic="", priority=100),
            "on_order": Handler(self.on_order, EVENTS.ORDER, topic="", priority=0),
            "on_time": Handler(self.on_time, EVENTS.TIME, priority=200),
        }
        self.handle_order = {
            ORDERTYPE.MARKET.value: self._fill_order,
            ORDERTYPE.LIMIT.value: self._fill_limit,
            ORDERTYPE.STOP.value: self._fill_stop
        }

    @staticmethod
    def calculate_commission(order, price):
        return 1

    @staticmethod
    def calculate_slippage(order, price):
        return 0

    def _put_fill(self, order, price, timestamp):
        """

        Args:
            order(bigfishtrader.model.OrderReq):
            price:
            timestamp:

        Returns:

        """
        if price != price:
            print("%s is not able to trade at %s" % (order.symbol, timestamp))
            return
        fill = ExecutionData()
        fill.time = timestamp
        fill.ticker = order.symbol
        fill.quantity = order.orderQty
        fill.action = order.action
        fill.price = price + self.calculate_slippage(order, price)
        fill.commission = self.calculate_commission(order, price)
        fill.order_id = order.clOrdID
        fill.position_id = order.clOrdID
        for k, v in self.ticker_info.get(order.symbol, {}):
            setattr(fill, k, v)
        event = ExecutionEvent(fill, timestamp=timestamp, topic=order.symbol)
        self._orders.pop(order.clOrdID, None)
        self.event_queue.put(event)

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

    def _fill_order(self, order, bar):
        self._put_fill(order, bar.open, bar.name)

    def _fill_limit(self, order, bar):
        """
        deal with limit order

        Args:
            order(bigfishtrader.model.OrderReq):
            bar:

        Returns:
            None
        """
        if order.action == ACTION.OPEN.value:
            self._limit_open(order, bar)
        elif order.action == ACTION.CLOSE.value:
            self._stop_open(order, bar)

    def _fill_stop(self, order, bar):
        if order.action == ACTION.OPEN.value:
            self._stop_open(order, bar)
        elif order.action == ACTION.CLOSE.value:
            self._limit_open(order, bar)

    def _limit_open(self, order, bar):
        """
        deal with limit open order

        Args:
            order(bigfishtrader.model.OrderReq):
            bar:

        Returns:
            None
        """

        if order.orderQty > 0 and bar.low < order.price:
            price = order.price if bar.open >= order.price else bar.open
            self._put_fill(order, price, bar.name)
        elif order.orderQty < 0 and bar.high > order.price:
            price = order.price if bar.open <= order.price else bar.open
            self._put_fill(order, price, bar.name)

    def _stop_open(self, order, bar):
        """
        Args:
            order(bigfishtrader.model.OrderReq):
            bar:

        Returns:
            None
        """
        if order.orderQty > 0 and bar.high > order.price:
            price = order.price if bar.open <= order.price else bar.open
            self._put_fill(order, price, bar.name)
        elif order.orderQty < 0 and bar.low < order.price:
            price = order.price if bar.open >= order.price else bar.open
            self._put_fill(order, price, bar.name)

    def on_bar(self, event, kwargs=None):
        """
        :param event:
        :param kwargs:
        :return:
        """
        for order in self._orders.values():
            self.handle_order[order.ordType](order, event)

    def on_time(self, event, kwargs=None):
        for _id, order in self._orders.items():
            self.handle_order[order.ordType](order, self._data.current(order.symbol))

    def on_order(self, event, kwargs=None):
        """


        Args:
            event(bigfishtrader.event.OrderEvent):
            kwargs:

        Returns:

        """
        order = event.data
        self.event_queue.put(RecallEvent(order.transactTime, order))  # 不管何种订单，都先返回已经挂单成功事件
        if order.ordType == ORDERTYPE.MARKET and self.deal_mode == BACKTESTDEALMODE.THIS_BAR_CLOSE:
            current = self._data.current(order.symbol)
            self._put_fill(order, current.close, current.name)  # 直接成交
        else:
            self._orders[order.clOrdID] = order  # 放入交易所orderbook留给on_bar函数去处理成交

    def get_orders(self):
        return {_id: order.to_dict() for _id, order in self._orders.items()}


class PracticeExchange(DummyExchange):
    def __init__(self, event_queue, data, portfolio, exchange_name=None, **ticker_info):
        super(PracticeExchange, self).__init__(event_queue, data, exchange_name, **ticker_info)
        self.portfolio = portfolio

    def _put_fill(self, order, price, timestamp):
        if price != price:
            print("%s is not able to trade at %s" % (order.symbol, timestamp))
            return
        fill = ExecutionData()
        fill.time = timestamp
        fill.ticker = order.symbol
        fill.quantity = order.orderQty
        fill.action = order.action
        fill.price = price + self.calculate_slippage(order, price)
        fill.commission = self.calculate_commission(order, price)
        fill.order_id = order.clOrdID
        fill.position_id = order.clOrdID
        for k, v in self.ticker_info.get(order.symbol, {}):
            setattr(fill, k, v)
        event = ExecutionEvent(fill, timestamp=timestamp, topic=order.symbol)
        self._orders.pop(order.clOrdID, None)
        self.portfolio.on_fill(event)
