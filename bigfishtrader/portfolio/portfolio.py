# encoding: utf-8
from dictproxyhack import dictproxy

from bigfishtrader.portfolio.position import Order, PositionHandler
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
        position = Order(
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
        position = Order(ticker, price, quantity, open_time, commission, **kwargs)
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
    def __init__(self, data, position_handler=None, init_cash=100000):
        super(NewPortfolio, self).__init__()
        self._data = data
        self._cash = init_cash
        self.init_cash = init_cash
        self.history = []
        self.closed_positions = []
        if position_handler:
            self._positions = position_handler
        else:
            self._positions = PositionHandler()
            self._handlers['on_recall'] = Handler(self._positions.on_recall, EVENTS.RECALL)

        self._handlers['on_time'] = Handler(self.on_time, EVENTS.TIME, priority=150)
        self._handlers['on_fill'] = Handler(self.on_fill, EVENTS.FILL, topic='', priority=100)
        self._handlers['on_exit'] = Handler(self.close_at_stop, EVENTS.EXIT, priority=200)

    @property
    def positions(self):
        return dictproxy(self._positions())

    @property
    def cash(self):
        return self._cash

    @property
    def equity(self):
        return self._cash + sum(
            map(
                lambda position: position.profit + position.deposit,
                self._positions().values()
            )
        )

    @property
    def holding(self):
        holding = {'cash': self._cash}
        for _id, position in self._positions():
            p_status = holding.setdefault(position.ticker, {})
            quantity = p_status.get('quantity', 0)
            p_status['quantity'] = quantity + position.quantity
            p_status['available'] = p_status.setdefault('available', 0) + position.available
            p_status['cost'] = (p_status.setdefault('cost', 0) * quantity +
                                position.quantity * position.price)/p_status['quantity']
        return holding

    @property
    def security(self):
        return self._positions.security

    def on_time(self, event, kwargs=None):
        self._time = event.time
        for position in self._positions().values():
            close = self._data.current(position.ticker).close
            if close == close:
                position.update(close)
        self.log()

    def log(self):
        """
        log portfolio's equity and cash.

        Returns:
            None
        """
        self.history.append({'datetime': self._time, 'equity': self.equity, 'cash': self._cash})

    def on_fill(self, event, kwargs=None):
        if event.action:
            self.open_position(
                event.position_id, event.ticker, event.price,
                event.quantity, event.time, event.commission,
                deposit_rate=event.deposit_rate, lever=event.lever
            )
        else:
            self.close_position(
                event.position_id, event.price,
                event.quantity, event.time,
                event.commission, event.external_id
            )

    def open_position(self, order_id, ticker, price, quantity, open_time, commission=0, **kwargs):
        position = Order(
            ticker, price, quantity, open_time,
            commission, order_id=order_id, **kwargs
        )

        self._cash -= (position.deposit + commission)

        if self._cash >= 0:
            self._positions[position.position_id] = position

    def close_position(self, order_id, price, quantity, close_time, commission=0, new_id=None):
        position = self._positions.pop(order_id)

        if position:
            if position.quantity * quantity <= 0:
                raise ValueError(
                    'position.quantity and quantity should both be positive or negative'
                )

            if position.quantity == quantity:
                position.close(price, close_time, commission)
                self._cash += position.deposit + position.profit - commission
                self.closed_positions.append(position)

            elif abs(position.quantity) > abs(quantity):
                closed_position = position.separate(quantity, price, new_id)
                closed_position.close(price, close_time, commission)
                self.closed_positions.append(closed_position)
                self._positions[position.position_id] = position

            else:
                raise ValueError(
                    'quantity to be close is larger than position.quantity'
                )

            # print 'close', position.show()
            # print close_time, self._data.current_time

    def separate_close(self, ticker, quantity):
        return self._positions.separate_close(ticker, quantity)

    def close_at_stop(self, event, kwargs=None):
        while len(self._positions):
            _id, position = self._positions.pop_item()
            position.close(position.price, self._time)
            self.closed_positions.append(position)


if __name__ == '__main__':
    from bigfishtrader.event import FillEvent, OrderEvent, RecallEvent
    portfolio = NewPortfolio(None)

    fill = FillEvent('2017-01-01', '000001', 1, 2000, 20,
                     local_id=1001, position_id=1001)
    fill_close = FillEvent('2017-01-01', '000001', 0, 1000, 20,
                     local_id=1001, position_id=1001, external_id=1002)

    o1 = OrderEvent('2017-01-01', '000001', 1, 1000, 21, EVENTS.LIMIT, local_id=1001)
    r1 = RecallEvent('2017-01-01', o1)

    portfolio.on_fill(fill)
    print portfolio.security

    portfolio._positions.on_recall(r1)
    print portfolio.security

    portfolio.on_fill(fill_close)
    print portfolio.security
