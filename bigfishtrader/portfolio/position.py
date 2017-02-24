# encoding: utf-8
from bigfishtrader.engine.handler import HandlerCompose, Handler
from bigfishtrader.event import EVENTS


class Order(object):
    """
    This class presents an existing order in the portfolio.

    Commonly, it will be created by a portfolio when the portfolio handles a FillEvent

    update() is called when a new TimeEvent arrives

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

    __slots__ = ["identifier", "ticker", "open_price", "open_time", "price", "quantity", "deposit", "close_price",
                 "close_time", "commission", "lever", "deposit_rate", "position_id", "lock"]

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
        self.position_id = order_id
        self.lock = 0

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

    def separate(self, quantity, price, new_id=None):
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

        new_position = Order(
            self.ticker, self.open_price, quantity, self.open_time,
            self.commission * quantity / self.quantity, self.lever,
            self.deposit_rate, order_id=self.position_id
        )
        new_position.identifier = self.identifier
        new_position.update(price)

        if new_id:
            self.position_id = new_id

        self.lock -= quantity if self.lock >= quantity else 0
        self.quantity -= quantity
        self.deposit -= new_position.deposit
        self.commission -= new_position.commission
        self.update(price)
        return new_position

    def show(self, *args):
        """
        get the position's content in dict form.

        Returns:
            dict: a dict contains the position's content
        """
        if len(args) == 0:
            args = [
                "ticker", "open_price", "open_time", "price", "quantity", "deposit", "close_price",
                "close_time", "commission", "lever", "deposit_rate", "position_id", 'profit'
            ]

        return dict([(key, self.__getattribute__(key)) for key in args])

    @property
    def available(self):
        return self.quantity - self.lock


class Position(object):
    """
    持仓对象，对应的管理模式为以ticker管理

    """

    __slots__ = ['ticker', 'quantity', 'commission', 'cost_price', 'price',
                 'locked', 'others']

    def __init__(self, ticker, quantity, price, commission=0, lock=0, **others):
        """

        :param ticker: str, 品种名
        :param quantity: float or int, 数量
        :param price: float, 价格
        :param commission: float or int, 佣金
        :param lock: float or int, 被锁数量
        :param others:
        :return:
        """
        self.ticker = ticker
        self.quantity = quantity
        self.commission = commission
        self.cost_price = price
        self.price = price
        self.locked = lock
        self.others = others

    @property
    def available(self):
        """
        当前可交易数量
        :return:
        """
        return self.quantity - self.locked

    @property
    def profit(self):
        """
        当前累计利润
        :return:
        """
        return self.quantity * (self.price - self.cost_price)

    @property
    def value(self):
        """
        当前净值
        :return:
        """
        return self.quantity * self.price

    @property
    def cost(self):
        """
        当前持仓成本
        :return:
        """
        return self.cost_price * self.quantity

    def __add__(self, other):
        if isinstance(other, Position):
            if self.ticker == other.ticker:
                self.append(other.price, other.quantity, other.commission)
                self.locked += other.locked
                return self
            else:
                raise ValueError("tickers of the 2 positions (%s and %s) are not equal" % (self.ticker, other.ticker))
        else:
            raise TypeError("The type of other is %s not Position" % type(other))

    def append(self, price, quantity, commission=0):
        """
        对同一品种增加仓位
        :param price: float or int, 成交价格
        :param quantity: float or int, 成交数量
        :param commission: float or int, 成交佣金
        :return:
        """
        self.cost_price = (self.quantity * self.cost_price + quantity * price)/(self.quantity + quantity)
        self.quantity += quantity
        self.commission += commission

    def close(self, price, quantity, commission=0):
        """
        对当前品种平仓
        :param price: 成交价格
        :param quantity: 成交数量
        :param commission: 成交佣金
        :return:
        """
        self.unlock(quantity)
        self.price = price
        value = self.value
        self.quantity -= quantity
        self.cost_price = (value - self.value)/self.quantity if self.quantity else 0
        self.commission += commission
        return price*quantity

    def lock(self, quantity):
        if quantity * self.locked >= 0:
            self.locked += quantity
        else:
            raise ValueError('Direction Error')

    def unlock(self, quantity):
        if quantity * self.locked >= 0:
            if abs(self.locked) > abs(quantity):
                self.locked -= quantity
            else:
                self.locked = 0
        else:
            raise ValueError('Direction Error')

    def show(self, *args):
        return dict(
            map(lambda attr: (attr, getattr(self, attr)), args)
        )


class OrderHandler(HandlerCompose):
    def __init__(self):
        super(OrderHandler, self).__init__()
        self._positions = {}
        self._handlers['on_recall'] = Handler(self.on_recall, EVENTS.RECALL)

    def __getitem__(self, item):
        return self._positions[item]

    def __setitem__(self, key, value):
        self._positions[key] = value

    def __call__(self, *args, **kwargs):
        return self._positions

    def __len__(self):
        return len(self._positions)

    def pop_item(self):
        return self._positions.popitem()

    def get(self, key, default=None):
        return self._positions.get(key, default)

    def pop(self, key, default=None):
        return self._positions.pop(key, default)

    def pop_ticker(self, key, default=None):
        positions = {}
        for _id, position in self._positions.copy().items():
            if position.ticker == key:
                positions[_id] = self._positions.pop(_id)

        return positions

    def from_ticker(self, ticker):
        positions = {}
        for _id, position in self._positions.items():
            if position.ticker == ticker:
                positions[_id] = position

        return positions

    def lock(self, order, kwargs=None):
        position = self._positions.get(order.clOrdID, None)
        if position:
            if position.available / order.quantity >= 1:
                position.lock += order.quantity

    def unlock(self, order, kwargs=None):
        position = self._positions.get(order.local_id, None)
        if position:
            if position.lock / order.quantity >= 1:
                position.lock -= order.quantity

    def on_recall(self, event, kwargs=None):
        if event.lock:
            self.lock(event.order, kwargs)
        else:
            self.unlock(event.order, kwargs)

    @property
    def security(self):
        security = {}
        for position in self._positions.values():
            security[position.ticker] = security.get(position.ticker, 0) + position.available
        return security

    def separate_close(self, ticker, close_quantity):
        quantity = 0
        for _id, position in self.from_ticker(ticker).items():
            available = position.available
            if (available == 0) or (available * close_quantity < 0):
                continue

            quantity += available
            if abs(quantity) < abs(close_quantity):
                yield _id, available

            elif quantity == close_quantity:
                yield _id, available
                raise StopIteration

            else:
                yield _id, quantity - close_quantity
                raise StopIteration

        raise StopIteration


if __name__ == '__main__':
    from bigfishtrader.event import OrderEvent, RecallEvent, CLOSE_ORDER
    from datetime import datetime

    p = Order('000001', 15, 2000, datetime(2017, 1, 1), order_id=101)
    p2 = Order('000001', 15, 2000, datetime(2017, 1, 1), order_id=102)
    p3 = Order('000001', 15, 2000, datetime(2017, 1, 1), order_id=103)
    p4 = Order('000001', 15, -2000, datetime(2017, 1, 1), order_id=104)
    ph = OrderHandler()
    ph[101] = p
    ph[102] = p2
    ph[103] = p3
    ph[104] = p4
    for _id, quantity in ph.separate_close('000001', 3000):
        o1 = OrderEvent(datetime.now(), '000001', CLOSE_ORDER, quantity, 20, EVENTS.LIMIT, order_id=_id)
        r1 = RecallEvent(o1.time, o1)
        ph.on_recall(r1)
    for _id, quantity in ph.separate_close('000001', -1000):
        o1 = OrderEvent(datetime.now(), '000001', CLOSE_ORDER, quantity, 20, EVENTS.LIMIT, order_id=_id)
        r1 = RecallEvent(o1.time, o1)
        ph.on_recall(r1)

    print ph.security
