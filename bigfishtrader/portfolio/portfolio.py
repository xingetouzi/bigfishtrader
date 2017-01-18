# encoding: utf-8
from dictproxyhack import dictproxy

from .position import Position
from ..exception import QuantityException
from bigfishtrader.portfolio.base import AbstractPortfolio


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

    def __init__(self, init_cash=100000):
        super(Portfolio, self).__init__()
        self.init_cash = init_cash
        self._id_ref = 0
        self._cash = init_cash
        self._positions = {}
        self._orders = {}
        self.closed_positions = []
        self.history = []
        self._time = None

    @property
    def positions(self):
        return dictproxy(self._positions)

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
            None
        """
        position = Position(ticker, price, quantity, open_time, commission, **kwargs)
        self._cash -= (position.deposit + commission)

        if self._cash < 0:
            return

        if ticker not in self._positions:
            self._positions[ticker] = position
        else:
            old = self._positions[ticker]
            if old.quantity * position.quantity > 0:
                old.merge(position)
            else:
                raise QuantityException(old.quantity, position.quantity, 2)
        self.update_position(open_time, ticker, price)

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
            None
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
            elif abs(quantity) < abs(position.quantity):
                new = position.separate(quantity, price)
                new.close(price, close_time, commission)
                self._cash += new.deposit + new.profit - commission
                self.closed_positions.append(new)
            else:
                raise QuantityException(quantity, position.quantity)

    def get_positions(self):
        """
        get portfolio's current positions

        Returns:
            dict: current positions of this portfolio, a dict of which
                key is position's ticker,
                value is :class:`bigfishtrader.portfolio.position.Position`.
        """
        return dictproxy(self._positions)

    def get_cash(self):
        """
        get portfolio's current cash

        Returns:
            float: current cash of this portfolio
        """
        return self._cash

    def confirm_position(self, confirmation):
        pass
