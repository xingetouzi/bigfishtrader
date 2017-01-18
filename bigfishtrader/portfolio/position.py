# encoding: utf-8


class Position(object):
    """
    This class presents the position of a single ticker

    update() is called when a new price data (Tick or Bar) arrives
    or when the position is to be closed

    separate() is called when the portfolio handler has to
    close part of this position.

    Attributes:
        identifier: identity of positions
        ticker: the position's ticker (also called: symbol, instrument)
        open_price: open price of the position
        open_time: open time of the position
        price: the ticker's last price
        quantity: quantity of position
        profit: profit calculating according to the ticker's current price and open price
        deposit: margin
        close_price: close price of the position
        close_time: close time of the position
        commission: commission
        lever: leverage
        deposit_rate: margin rate
    """


    __slots__ = ["identifier", "ticker", "open_price", "open_time", "price", "quantity", "profit", "deposit", "close_price",
                 "close_time", "commission", "lever", "deposit_rate", "order_id"]

    def __init__(self, ticker, price, quantity, open_time, commission=0, lever=1, deposit_rate=1, order_id=None):
        self.identifier = None
        self.ticker = ticker
        self.open_price = price
        self.price = price
        self.quantity = quantity
        self.commission = commission
        self.open_time = open_time
        self.lever = lever
        self.deposit_rate = deposit_rate
        self.deposit = abs(self.open_price * self.quantity * lever * deposit_rate)
        self.close_price = None
        self.close_time = None
        self.order_id = order_id

    @property
    def profit(self):
        return (self.price - self.open_price) * self.quantity * self.lever

    def update(self, price):
        """
        update the current price

        Args:
            price(float): current price
        Returns:
            None
        """
        self.price = price

    def close(self, price, timestamp, commission=0):
        """
        close the entire position with the ticker's current price, timestamp and commission

        Args:
            price(float): the ticker's current price
            timestamp(float): timestamp now
            commission(float): trading commission
        Returns:
            None

        """
        self.commission += commission
        self.close_time = timestamp
        self.close_price = price
        self.update(price)

    def merge(self, other):
        """
        merge a position of same ticker as this position,
        this position will change and other remain itself.

        Args:
            other: other position of same ticker
        Returns:
            None
        """
        quantity = self.quantity + other.quantity
        self.open_price = (self.open_price * self.quantity + other.quantity * other.open_price) / quantity
        self.commission = self.commission + other.commission
        self.deposit = self.deposit + other.deposit
        self.quantity = quantity

    def separate(self, quantity, price):
        """
        Separate this position into 2 position
        Return the position which has the input quantity
        and the other remains itself.

        Args:
            quantity(float): quantity
            price(float): price
        Returns:
            Position: new position which has the input quantity
        """

        new_position = Position(self.ticker, self.open_price,
                                quantity, self.open_time,
                                self.commission * quantity / self.quantity, self.lever,
                                self.deposit_rate, order_id=self.order_id)
        new_position.identifier = self.identifier
        new_position.update(price)
        self.quantity -= quantity
        self.deposit -= new_position.deposit
        self.commission -= new_position.commission
        self.update(price)
        return new_position

    def show(self):
        """
        get the position's content in dict form.

        Returns:
            dict: a dict contains the position's content
        """

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
