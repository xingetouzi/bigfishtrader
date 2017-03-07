# coding:utf-8
from bigfishtrader.engine.base import AbstractPortfolio, Handler
from bigfishtrader.model import OrderReq, Transaction
from bigfishtrader.const import *
from bigfishtrader.event import OrderEvent, EVENTS
from collections import defaultdict
import numpy as np


class Portfolio(AbstractPortfolio):
    def __init__(self, event_queue, data, init_cash=100000):
        super(Portfolio, self).__init__()
        self._event_queue = event_queue
        self._data = data
        self._cash = init_cash
        self.init_cash = init_cash
        self._positions = {}
        self._transactions = []
        self._history_pos = []
        self._history_eqt = []
        self._history_req = []
        self._id = 0

        self._handlers['on_time'] = Handler(self.on_time, EVENTS.TIME, priority=150)
        self._handlers['on_fill'] = Handler(self.on_fill, EVENTS.EXECUTION, priority=100)
        self._handlers['on_recall'] = Handler(self.on_recall, EVENTS.RECALL, priority=100)
        self._handlers['on_exit'] = Handler(self.on_exit, EVENTS.EXIT, priority=100)

        self.execution_handler = defaultdict(
            lambda: self.handle_STK,
            **{SecType.STK.value: self.handle_STK,
               SecType.CASH.value: self.handler_CASH}
        )

    @property
    def next_id(self):
        self._id += 1
        return self._id

    @property
    def cash(self):
        return self._cash

    @property
    def equity(self):
        return self._cash + sum([position.value for position in self._positions.values()])

    @property
    def transactions(self):
        return self._transactions

    @property
    def positions(self):
        return {symbol: position.show() for symbol, position in self._positions.items()}

    @property
    def history_pos(self):
        return self._history_pos

    @property
    def history_eqt(self):
        return self._history_eqt

    @property
    def history_req(self):
        return self._history_req

    def send_order(self, symbol, quantity, price=None, order_type=ORDERTYPE.MARKET, sec_type=SecType.STK, **kwargs):
        odr = OrderReq()
        odr.orderQty = quantity
        odr.symbol = symbol
        odr.ordType = order_type.value if isinstance(order_type, ORDERTYPE) else getattr(ORDERTYPE, order_type).value
        odr.price = price
        odr.secType = sec_type.value if isinstance(sec_type, SecType) else sec_type
        odr.clOrdID = self.next_id
        odr.time = self._data.current_time
        for key, value in kwargs.items():
            setattr(odr, key, value)

        self._event_queue.put(
            OrderEvent(odr, self._data.current_time)
        )

        return odr.clOrdID

    def order_to(self, symbol, quantity, **kwargs):
        position = self._positions.get(symbol, None)
        if position:
            quantity -= position.quantity
            if quantity:
                self.send_order(symbol, quantity, **kwargs)
        else:
            self.send_order(symbol, quantity, **kwargs)

    def order_pct(self, symbol, pct, **kwargs):
        price = self._data.current(symbol).close
        if not np.isnan(price):
            quantity = int(self.equity * pct / price)
            if quantity:
                self.send_order(symbol, quantity, **kwargs)

    def order_pct_to(self, symbol, pct, **kwargs):
        position = self._positions.get(symbol, None)

        if position:
            pct -= position.value / self.equity
            self.order_pct(symbol, pct, **kwargs)
        else:
            self.order_pct(symbol, pct, **kwargs)

    def handler_CASH(self, execution):
        transaction = Transaction(execution.time, execution.ticker, execution.action, execution.quantity,
                                  execution.price, commission=execution.commission, order_id=execution.order_id)
        transaction.reqTime = execution.reqTime
        transaction.status = execution.status
        transaction.side = execution.side
        transaction.exchange = execution.exchange
        transaction.lever = execution.lever
        transaction.deposit_rate = execution.deposit_rate

        position = self._positions.get(execution.ticker, None)
        if position:
            if position.quantity * execution.quantity > 0:
                new = LeverPosition(execution.ticker, execution.quantity,
                                    execution.price, execution.commission,
                                    execution.secType, execution.lever,
                                    execution.deposit_rate, execution.order_id)
                position += new
                self._cash -= new.deposit
            else:
                value = position.close(execution.price, -execution.quantity, execution.commission)
                print value
                self._cash += value
                if position.quantity == 0:
                    self._positions.pop(position.symbol)

        else:
            position = LeverPosition(execution.ticker, execution.quantity,
                                     execution.price, execution.commission,
                                     execution.secType, execution.lever,
                                     execution.deposit_rate, execution.order_id)
            self._cash -= position.deposit
            self._positions[position.symbol] = position

        self._transactions.append(transaction)

    def handle_STK(self, execution):
        transaction = Transaction(execution.time, execution.ticker, execution.action, execution.quantity,
                                  execution.price, commission=execution.commission, order_id=execution.order_id)
        transaction.reqTime = execution.reqTime
        transaction.status = execution.status
        transaction.action = execution.action
        transaction.side = execution.side
        transaction.exchange = execution.exchange

        if self._cash < transaction.value + execution.commission:
            return

        self._cash -= (transaction.value + execution.commission)

        position = self._positions.get(execution.ticker, None)
        if position:
            position += Position(execution.ticker, execution.quantity,
                                 execution.price, execution.commission,
                                 execution.secType)
            if position.quantity == 0:
                self._positions.pop(execution.ticker)
        else:
            position = Position(execution.ticker, execution.quantity,
                                execution.price, execution.commission,
                                execution.secType)
            self._positions[position.symbol] = position

        self._transactions.append(transaction)

    def on_fill(self, event, kwargs=None):
        execution = event.data
        self.execution_handler[execution.secType](execution)

    def on_time(self, event, kwargs=None):
        for symbol, position in self._positions.items():
            close = self._data.current(symbol).close
            if not np.isnan(close):
                position.price = close
        self._history_eqt.append({'time': event.time, 'equity': self.equity, 'cash': self._cash})

    def on_recall(self, event, kwargs=None):
        order = event.order
        self._history_req.append(order)

    def on_exit(self, event, kwargs=None):
        from bigfishtrader.model import ExecutionData
        for symbol, position in self._positions.copy().items():
            ed = ExecutionData()
            ed.ticker = symbol
            ed.secType = position.sec_type
            ed.quantity = -position.quantity
            ed.order_id = self.next_id
            ed.time = event.time
            ed.price = position.price
            ed.commission = 0
            ed.status = ORDERSTATUS.ALLTRADED.value
            ed.side = SIDE.BUY.value if ed.quantity > 0 else SIDE.SELL.value

            self.execution_handler[ed.secType](ed)


class Position(object):
    __slots__ = [
        'symbol', 'quantity', 'price', 'commission',
        'sec_type', 'avg_cost', 'available'
    ]

    def __init__(self, symbol, quantity, price, commission, sec_type):
        self.symbol = symbol
        self.quantity = quantity
        self.price = price
        self.commission = commission
        self.sec_type = sec_type
        self.avg_cost = price
        self.available = quantity

    def __add__(self, other):
        return self.append(other)

    def __radd__(self, other):
        if not other:
            return self
        else:
            return self.append(other)

    @property
    def value(self):
        return self.quantity * self.price

    @property
    def profit(self):
        return self.quantity * (self.price - self.avg_cost)

    def append(self, other):
        if isinstance(other, Position):
            if self.symbol == other.symbol:
                if self.quantity * other.quantity > 0:
                    self.avg_cost = (self.value + other.value) / (self.quantity + other.quantity)
                else:
                    if abs(self.quantity) < abs(other.quantity):
                        self.avg_cost = other.avg_cost

                self.quantity += other.quantity
                self.commission += other.commission
                self.available += other.available
                return self

            else:
                raise ValueError(
                    "self.symbol = %s, other.symbol = %s, symbol is different" % (self.symbol, other.symbol)
                )

        else:
            raise TypeError("Type of other is %s, not <Position>, unable to append" % type(other))

    to_show = ['symbol', 'quantity', 'value', 'commission', 'profit', 'sec_type']

    def show(self, *args):
        if len(args):
            return {key: self.__getattribute__(key) for key in args}
        else:
            return {key: self.__getattribute__(key) for key in self.to_show}


class LeverPosition(Position):
    __slots__ = ['lever', 'deposit_rate', 'deposit']

    def __init__(self, symbol, quantity, price, commission, sec_type, lever, deposit_rate, order_id):
        super(LeverPosition, self).__init__(symbol, quantity, price, commission, sec_type)
        self.lever = lever
        self.deposit_rate = deposit_rate
        self.deposit = abs(price * quantity * lever * deposit_rate)

    def append(self, other):
        if isinstance(other, LeverPosition):
            if self.symbol == other.symbol:
                if self.quantity * other.quantity > 0:
                    self.avg_cost = \
                        (self.price*self.quantity + other.price*other.quantity) / (self.quantity + other.quantity)
                else:
                    if abs(self.quantity) < abs(other.quantity):
                        self.avg_cost = other.avg_cost

                self.quantity += other.quantity
                self.commission += other.commission
                self.available += other.available
                self.deposit += other.deposit
                return self

            else:
                raise ValueError(
                    "self.symbol = %s, other.symbol = %s, symbol is different" % (self.symbol, other.symbol)
                )

        else:
            raise TypeError("Type of other is %s, not <LeverPosition>, unable to append" % type(other))

    @property
    def value(self):
        return self.deposit + self.profit

    @property
    def profit(self):
        return (self.price - self.avg_cost) * self.quantity * self.lever

    def close(self, price, quantity, commission):
        deposit = quantity/self.quantity * self.deposit
        profit = quantity*(price - self.avg_cost)*self.lever
        self.deposit -= deposit
        self.quantity -= quantity
        return deposit + profit
