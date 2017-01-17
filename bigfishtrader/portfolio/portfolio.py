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
        self.__id_ref = 0
        self.__cash = init_cash
        self.__positions = {}
        self.closed_positions = []
        self.history = []
        self.__time = None
        self.__position_ref = 0

    @property
    def _next_position_id(self):
        self.__position_ref += 1
        return self.__position_ref

    @property
    def positions(self):
        return dictproxy(self.__positions)

    @property
    def current_time(self):
        return self.__time

    @property
    def equity(self):
        equity = self.__cash
        for position in self.__positions.values():
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
        self.__time = timestamp
        position = self.__positions.get(ticker, None)
        if position:
            position.update(price)

    def log(self):
        """
        log portfolio's equity and cash.

        Returns:
            None
        """
        self.history.append({'datetime': self.__time, 'equity': self.equity, 'cash': self.__cash})

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
        self.__cash -= (position.deposit + commission)

        if self.__cash < 0:
            return None

        if ticker not in self.__positions:
            self.__positions[ticker] = position
            position.identifier = self._next_position_id
            result = position
        else:
            old = self.__positions[ticker]
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
        position = self.__positions.get(ticker, None)

        if position:
            if quantity * position.quantity < 0:
                    raise QuantityException(quantity, position.quantity, 2)
            if quantity == position.quantity:
                position = self.__positions.pop(ticker)
                position.close(price, close_time, commission)
                self.__cash += position.deposit + position.profit - commission
                self.closed_positions.append(position)
                return position
            elif abs(quantity) < abs(position.quantity):
                new = position.separate(quantity, price)
                new.close(price, close_time, commission)
                self.__cash += new.deposit + new.profit - commission
                self.closed_positions.append(new)
                return new
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
        return dictproxy(self.__positions)

    def get_cash(self):
        """
        get portfolio's current cash

        Returns:
            float: current cash of this portfolio
        """
        return self.__cash

    def confirm_position(self, confirmation):
        pass
