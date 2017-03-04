# encoding: utf-8
from enum import Enum
from bigfishtrader.engine.handler import Handler
from bigfishtrader.event import ExecutionEvent, RecallEvent, EVENTS
from bigfishtrader.model import ExecutionData
from bigfishtrader.const import ORDERTYPE, ACTION, ORDERSTATUS, DIRECTION, SIDE
from bigfishtrader.engine.base import AbstractRouter


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

    def _put_fill(self, order, price, timestamp, **kwargs):
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
        fill.reqTime = order.time
        fill.ticker = order.symbol
        fill.quantity = order.orderQty
        fill.action = order.action
        fill.price = price + self.calculate_slippage(order, price)
        fill.commission = self.calculate_commission(order, price)
        fill.order_id = order.clOrdID
        fill.position_id = order.clOrdID
        fill.side = SIDE.BUY.value if order.orderQty > 0 else SIDE.SELL.value
        for key, value in kwargs.items():
            setattr(fill, key, value)
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

    def _fill_stk(self, order):
        pass

    def _fill_order(self, order, bar, **kwargs):
        self._put_fill(order, bar.open, bar.name,
                       status=ORDERSTATUS.ALLTRADED.value,
                       exchange=self.ex_name(order), **kwargs)

    def _fill_limit(self, order, bar, **kwargs):
        """
        deal with limit order

        Args:
            order(bigfishtrader.model.OrderReq):
            bar:

        Returns:
            None
        """

        if order.orderQty > 0:
            self._low_fill(order, bar, **kwargs)
        else:
            self._up_fill(order, bar, **kwargs)

    def _fill_stop(self, order, bar, **kwargs):
        if order.orderQty > 0:
            self._up_fill(order, bar, **kwargs)
        else:
            self._low_fill(order, bar, **kwargs)

    def _up_fill(self, order, bar, **kwargs):
        """
        大于等于指定价格成交

        :param order:
        :param bar:
        :return:
        """
        if bar.open > order.price:
            self._put_fill(order, bar.open, bar.name,
                           status=ORDERSTATUS.ALLTRADED.value,
                           exchange=self.ex_name(order), **kwargs)

        elif bar.high > order.price:
            self._put_fill(order, order.price, bar.name,
                           status=ORDERSTATUS.ALLTRADED.value,
                           exchange=self.ex_name(order), **kwargs)

    def _low_fill(self, order, bar, **kwargs):
        """
        小于等于指定价格成交

        :param order:
        :param bar:
        :return:
        """
        if bar.open < order.price:
            self._put_fill(order, bar.open, bar.name,
                           status=ORDERSTATUS.ALLTRADED.value,
                           exchange=self.ex_name(order), **kwargs)
        elif bar.low < order.price:
            self._put_fill(order, order.price, bar.name,
                           status=ORDERSTATUS.ALLTRADED.value,
                           exchange=self.ex_name(order), **kwargs)

    def on_bar(self, event, kwargs=None):
        """
        :param event:
        :param kwargs:
        :return:
        """
        for order in self._orders.values():
            self.handle_order[order.ordType](order, event)

    def on_time(self, event, kwargs=None):
        for _id, order in self._orders.copy().items():
            self.handle_order[order.ordType](order, self._data.current(order.symbol))

    def on_order(self, event, kwargs=None):
        """


        Args:
            event(bigfishtrader.event.OrderEvent):
            kwargs:

        Returns:

        """
        order = event.data
        order.time = event.time
        self.event_queue.put(RecallEvent(order.time, order))  # 不管何种订单，都先返回已经挂单成功事件
        if order.ordType == ORDERTYPE.MARKET.value and self.deal_mode == BACKTESTDEALMODE.THIS_BAR_CLOSE:
            current = self._data.current(order.symbol)
            self._put_fill(order, current.close, current.name,
                           status=ORDERSTATUS.ALLTRADED.value,
                           exchange=self.ex_name(order)) # 直接成交
        else:
            self._orders[order.clOrdID] = order  # 放入交易所orderbook留给on_bar函数去处理成交

    @property
    def orders(self):
        return {_id: order.to_dict() for _id, order in self._orders.items()}

    @staticmethod
    def ex_name(order):
        return order.secType + 'exchange'

    def set_commission(self, per_share=0, per_value=0, min_cost=0, calculate_function=None):
        """
        设置佣金计算方法

        :param per_share(int|float): 每股收取佣金
        :param per_value(int|float): 根据成交额的百分比收取佣金
        :param min_cost(int|float): 每笔交易的最低佣金
        :param calculate_function(function): 自定义计算方法，需要传入order和price作为参数，返回佣金值
        :return:
        """

        if not calculate_function:
            if per_share:
                def calculate(order, price):
                    return max(order.orderQty*per_share, min_cost)
            elif per_value:
                def calculate(order, price):
                    return max(order.orderQty*per_value*price, min_cost)
            elif min_cost:
                def calculate(order, price):
                    return min_cost
            else:
                def calculate(order, price):
                    return 0

            self.calculate_commission = calculate

        else:
            self.calculate_commission = calculate_function

    def set_slippage(self, pct=0, function=None):
        """
        设置滑点

        :param pct(float): 当前价格滑点比例
        :param function:  自定义计算方法，需要传入order和price作为参数，返回滑点值(区分正负)
        :return:
        """
        if not function:
            self.calculate_slippage = lambda order, price: price*pct*(1 if order.orderQty > 0 else -1)

        else:
            setattr(self, 'calculate_slippage', function)


class PracticeExchange(DummyExchange):
    def __init__(self, event_queue, data, portfolio, exchange_name=None, **ticker_info):
        super(PracticeExchange, self).__init__(event_queue, data, exchange_name, **ticker_info)
        self.portfolio = portfolio

    def _put_fill(self, order, price, timestamp, **kwargs):
        if price != price:
            print("%s is not able to trade at %s" % (order.symbol, timestamp))
            return
        fill = ExecutionData()
        fill.time = timestamp
        fill.reqTime = order.time
        fill.ticker = order.symbol
        fill.quantity = order.orderQty
        fill.action = order.action
        fill.price = price + self.calculate_slippage(order, price)
        fill.commission = self.calculate_commission(order, price)
        fill.order_id = order.clOrdID
        fill.position_id = order.clOrdID
        fill.secType = order.secType
        fill.side = SIDE.BUY.value if order.orderQty > 0 else SIDE.SELL.value
        for key, value in kwargs.items():
            setattr(fill, key, value)
        for k, v in self.ticker_info.get(order.symbol, {}):
            setattr(fill, k, v)
        event = ExecutionEvent(fill, timestamp=timestamp, topic=order.symbol)
        self._orders.pop(order.clOrdID, None)
        self.portfolio.on_fill(event)
