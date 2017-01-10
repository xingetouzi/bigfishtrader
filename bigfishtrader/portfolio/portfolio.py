from .position import Position
from ..exception import QuantityException
from bigfishtrader.portfolio.base import AbstractPortfolio

class Portfolio(AbstractPortfolio):
    def __init__(self, init_cash=100000):
        super(Portfolio, self).__init__()
        self.init_cash = init_cash
        self.__cash = init_cash
        self.equity = init_cash
        self.__positions = {}
        self.closed_positions = []
        self.history = []

    def current_time(self):
        return self.__time

    def update_position(self, timestamp, ticker, price):
        self.__time = timestamp
        position = self.__positions.get(ticker, None)
        if position:
            position.update(price)
            self.calculate_portfolio()

    def calculate_portfolio(self):
        self.equity = self.__cash
        for position in self.__positions.values():
            self.equity += position.deposit + position.profit

    def log(self):
        self.history.append({'datetime': self.__time, 'equity': self.equity, 'cash': self.__cash})

    def open_position(self, ticker, price, quantity, open_time, commission=0, **kwargs):
        position = Position(ticker, price, quantity, open_time, commission, **kwargs)
        self.__cash -= (position.deposit + commission)

        if self.__cash < 0:

            return

        if ticker not in self.__positions:
            self.__positions[ticker] = position
        else:
            old = self.__positions[ticker]
            if old.quantity * position.quantity > 0:
                old.merge(position)
            else:
                raise QuantityException(old.quantity, position.quantity, 2)
        self.update_position(open_time, ticker, price)

    def close_position(self, ticker, price, quantity, close_time, commission=0):
        position = self.__positions.get(ticker, None)

        if position:

            if quantity == position.quantity:
                position = self.__positions.pop(ticker)
                position.close(price, close_time, commission)
                self.__cash += position.deposit + position.profit - commission
                self.calculate_portfolio()
                self.closed_positions.append(position)

            elif abs(quantity) < abs(position.quantity):
                if quantity*position.quantity < 0:
                    raise QuantityException(quantity, position.quantity, 2)

                new = position.separate(quantity, price)
                new.close(price, close_time, commission)
                self.__cash += new.deposit + new.profit - commission
                self.calculate_portfolio()
                self.closed_positions.append(new)

            else:
                raise QuantityException(quantity, position.quantity)

    def get_positions(self):
        return self.__positions.copy()

    def get_cash(self):
        return self.__cash

    def confirm_position(self, confirmation):
        pass
