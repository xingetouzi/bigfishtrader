# encoding: utf-8
from dictproxyhack import dictproxy

from bigfishtrader.portfolio.position import Position
from bigfishtrader.exception import QuantityException
from bigfishtrader.portfolio.base import AbstractPortfolio
from bigfishtrader.engine.handler import Handler
from bigfishtrader.event import EVENTS
import pandas as pd


class Portfolio(AbstractPortfolio):
    """
    create a Portfolio with initial cash equals init_cash

    Attributes:
        init_cash(float): initial cash.
        equity(float): account equity, account balance.
        closed_positions(list of Position): closed positions
        history(list): equity history, with the following formats:\n
            [{"datetime": XX, "equity": XX, "cash": XX}, ...]
        current_time(float): current timestamp
        positions(dict): portfolio's current positions
        __cash(float): account cash
        __time(float): record current time
    """

    def __init__(self, data, init_cash=100000):
        super(Portfolio, self).__init__()
        self.init_cash = init_cash
        self._id_ref = 0
        self._cash = init_cash
        self._positions = {}
        self._orders = {}
        self.closed_positions = []
        self.history = []
        self._data = data
        self._time = None
        self.__position_ref = 0

        self._handlers['on_time'] = Handler(self.on_time, EVENTS.TIME, priority=100)
        self._handlers['on_fill'] = Handler(self.on_fill, EVENTS.FILL, priority=100)

    @property
    def _next_position_id(self):
        self.__position_ref += 1
        return self.__position_ref

    @property
    def positions(self):
        return dictproxy(self._positions)

    @property
    def cash(self):
        return dictproxy(self._cash)

    @property
    def orders(self):
        return dictproxy(self._orders)

    @property
    def current_time(self):
        return self._time

    @property
    def equity(self):
        equity = self._cash
        for position in self._positions.values():
            equity += position.deposit + position.profit
        return equity

    def on_fill(self, event, kwargs=None):
        if event.action:
            self.open_position(
                event.ticker, event.price, event.quantity,
                event.time, event.commission,
                lever=event.lever, deposit_rate=event.deposit_rate
            )
        else:
            self.close_position(
                event.ticker, event.price, event.quantity,
                event.time, event.commission
            )

    def on_time(self, event, kwargs=None):
        self._time = event.time
        for ticker, position in self._positions.items():
            current = self._data.current(ticker)
            position.update(current['close'])
        self.log()

    def update_position(self, timestamp, ticker, price):
        """
        update a ticker's position with its latest quotation

        Args:
            timestamp: quotation timestamp
            ticker: quotation ticker
            price: quotations price

        Returns:
            None
        """
        self._time = timestamp
        position = self._positions.get(ticker, None)
        if position:
            position.update(price)

    def update_order(self, timestamp, order, price):
        self._time = timestamp
        order.update(price)

    def log(self):
        """
        log portfolio's equity and cash.

        Returns:
            None
        """
        self.history.append({'datetime': self._time, 'equity': self.equity, 'cash': self._cash})

    def open_order(self, order_id, ticker, price, quantity, open_time, commission=0, **kwargs):
        position = Position(
            ticker, price, quantity,
            open_time, commission, **kwargs
        )
        self._orders[order_id] = position
        self._cash -= (position.deposit + commission)

    def close_order(self, order_id, price, quantity, close_time, commission=0):
        position = self._orders.get(order_id, None)
        if position:
            if position.quantity * quantity < 0:
                raise QuantityException(quantity, position.quantity, 2)
            if position.quantity == quantity:
                position = self._orders.pop(order_id)
                position.close(price, close_time, commission)
                self._cash += position.deposit + position.profit - commission
                self.closed_positions.append(position)
            elif abs(quantity) < abs(position.quantity):
                new = position.separate(quantity, price)
                new.close(price, close_time, commission)
                self._cash += new.deposit + new.profit - commission
                self.closed_positions.append(new)
            else:
                raise QuantityException(quantity, position.quantity)

    def open_position(self, ticker, price, quantity, open_time, commission=0, **kwargs):
        """
        open a position

        Args:
            ticker:
            price:
            quantity:
            open_time:
            commission:
            **kwargs:

        Returns:
            Position: the opened position
        """
        position = Position(ticker, price, quantity, open_time, commission, **kwargs)
        self._cash -= (position.deposit + commission)

        if self._cash < 0:
            return None

        if ticker not in self._positions:
            self._positions[ticker] = position
            position.identifier = self._next_position_id
            result = position
        else:
            old = self._positions[ticker]
            if old.quantity * position.quantity > 0:
                old.merge(position)
                result = old
            else:
                raise QuantityException(old.quantity, position.quantity, 2)
        self.update_position(open_time, ticker, price)
        return result

    def close_position(self, ticker, price, quantity, close_time, commission=0):
        """
        close a position

        Args:
            ticker:
            price:
            quantity:
            close_time:
            commission:

        Returns:
            Position: the closed position
        """
        position = self._positions.get(ticker, None)

        if position:
            if quantity * position.quantity < 0:
                raise QuantityException(quantity, position.quantity, 2)
            if quantity == position.quantity:
                position = self._positions.pop(ticker)
                position.close(price, close_time, commission)
                self._cash += position.deposit + position.profit - commission
                self.closed_positions.append(position)
                return position
            elif abs(quantity) < abs(position.quantity):
                new = position.separate(quantity, price)
                new.close(price, close_time, commission)
                self._cash += new.deposit + new.profit - commission
                self.closed_positions.append(new)
                return new
            else:
                raise QuantityException(quantity, position.quantity)

    def confirm_position(self, confirmation):
        pass


class NewPortfolio(AbstractPortfolio):
    def __init__(self, data, init_cash=100000):
        super(NewPortfolio, self).__init__()
        self._data = data
        self._cash = init_cash
        self.init_cash = init_cash
        self._positions = {}
        self._locked_positions = {}
        self._handlers = {
            'on_recall': Handler(self.on_recall, EVENTS.RECALL)
        }

    @property
    def positions(self):
        return dictproxy(self._positions)

    @property
    def cash(self):
        return self._cash

    @property
    def security(self):
        security = {}
        for _id, position in self._positions.items():
            security[position.ticker] = security.get(position.ticker, 0) + position.quantity

        return security

    def _get_position(self, ticker):
        positions = {}
        for _id, position in self._positions.items():
            if position.ticker == ticker:
                positions[_id] = position

        return positions

    def lock(self, event, kwargs=None):
        order = event.order
        positions = self._get_position(order.ticker)
        for _id, position in positions.items():
            if order.local_id == _id:
                self._locked_positions[_id] = self._positions[_id]
                position.lock += order.quantity
                return

        quantity = 0
        for _id, position in positions.items():
            quantity += position.available_quantity
            if abs(quantity) <= abs(order.quantity):
                position.lock += position.available_quantity
            else:
                position.lock += quantity - order.quantity
                break

    def unlock(self, event, kwargs=None):
        pass

    def on_recall(self, event, kwargs=None):
        if event.lock:
            self.lock(event, kwargs)
        else:
            self.unlock(event, kwargs)

    def set_position(self, position):
        self._positions[position.position_id] = position

if __name__ == '__main__':
    p = NewPortfolio(None)
    p.set_position(
        Position('000001', 1000, 1000, '2016-01-01', order_id=100)
    )
    p.set_position(
        Position('000001', 1000, 1000, '2016-01-02', order_id=101)
    )
    p.set_position(
        Position('000001', 1000, 1000, '2016-01-03', order_id=102)
    )