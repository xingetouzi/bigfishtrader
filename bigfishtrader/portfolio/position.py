# encoding: utf-8


class Position(object):
    """
    This class presents the position of a single ticker

    update() is called when a new price data (Tick or Bar) arrives
    or when the position is to be closed

    separate() is called when the portfolio handler has to
    close part of this position.

    """

    def __init__(self, ticker, price, quantity, open_time, commission=0, lever=1, deposit_rate=1):
        self.ticker = ticker
        self.open_price = price
        self.price = price
        self.quantity = quantity
        self.commission = commission
        self.open_time = open_time
        self.lever = lever
        self.deposit_rate = deposit_rate
        self.deposit = abs(self.open_price*self.quantity*lever*deposit_rate)
        self.profit = 0
        self.close_price = None
        self.close_time = None

    def update(self, price):
        self.price = price
        self.profit = (price - self.open_price) * self.quantity * self.lever

    def close(self, price, timestamp, commission=0):
        self.commission += commission
        self.close_time = timestamp
        self.close_price = price
        self.update(price)

    def merge(self, other):
        quantity = self.quantity + other.quantity
        self.open_price = (self.open_price * self.quantity + other.quantity * other.open_price) / quantity
        self.commission = self.commission + other.commission
        self.deposit = self.deposit + other.deposit
        self.quantity = quantity

    def separate(self, quantity, price):
        """
        Separate this position into 2 position
        Return the position which has the input quantity
        and the other remains itself

        :param quantity:
        :param price:
        :return:
        """

        new_position = Position(self.ticker, self.open_price,
                                quantity, self.open_time,
                                self.commission*quantity/self.quantity, self.lever,
                                self.deposit_rate)
        new_position.update(price)
        self.quantity -= quantity
        self.deposit -= new_position.deposit
        self.commission -= new_position.commission
        self.update(price)
        return new_position

    def show(self):
        return {
            'ticker': self.ticker,
            'open_price': self.open_price,
            'open_time': self.open_time,
            'quantity': self.quantity,
            'profit': self.profit,
            'deposit': self.deposit,
            'close_time': self.close_time,
            'close_price': self.close_price,
            'commission': self.commission
        }
