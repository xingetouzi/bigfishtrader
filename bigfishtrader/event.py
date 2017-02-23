# encoding: utf-8

from datetime import datetime

import numpy as np

from bigfishtrader.const import *
from bigfishtrader.model import Fill


class EVENTS(Enum):
    TICK = 0
    BAR = 1
    ORDER = 2
    FILL = 3
    LIMIT = 4
    STOP = 5
    CANCEL = 6
    TIME = 7
    MODIFY = 8
    CONFIRM = 9
    CONFIG = 10
    RECALL = 11
    POSITION = 12
    ORD_STATUS = 13
    EXIT = 999


class Event(object):
    """
    This is the base event class
    it implements the __lt__ and __gt__ function
    which compares its own priority and other event's priority
    Other events that extends from this class must set the 'priority' attribution
    """
    __slots__ = ["type", "priority", "topic", "time", "local_time"]

    def __init__(self, _type, priority, timestamp, topic=""):
        self.type = _type
        self.priority = priority
        self.topic = topic
        self.time = timestamp
        self.local_time = datetime.now()

    def to_dict(self):
        return {field: getattr(self, field) for field in self.__slots__}

    def lt_time(self, other):
        if self.__eq__(other):
            return self.time < other.time or self.local_time < other.local_time
        else:
            return False

    def lt_local_time(self, other):
        if self.time == other.time:
            return self.local_time < other.local_time
        else:
            return False

    def __eq__(self, other):
        return self.priority == other.priority

    def __lt__(self, other):
        return self.priority < other.priority or self.lt_time(other)

    def __le__(self, other):
        return self.priority <= other.priority

    def __ge__(self, other):
        return self.priority >= other.priority

    def __gt__(self, other):
        return self.priority > other.priority


class TickEvent(Event):
    """
    TickEvent is created when a tick data arrived
    and will be handled by strategy and portfolio handler
    """
    __slots__ = ["ticker", "exchange", "last_price", "high_price", "open_price", "low_price",
                 "pre_close", "vwap_price", "upper_limit", "lower_limit", "depth", "ask_price",
                 "bid_price", "ask_volume", "bid_volume"]

    MAX_DEPTH = 10

    def __init__(self, timestamp=None, depth=MAX_DEPTH):
        if timestamp is None:
            timestamp = datetime.now()
        super(TickEvent, self).__init__(EVENTS.TICK, 1, timestamp)
        self.ticker = None
        self.exchange = None
        self.last_price = None
        self.high_price = None
        self.open_price = None
        self.high_price = None
        self.low_price = None
        self.pre_close = None
        self.vwap_price = None

        self.upper_limit = None
        self.lower_limit = None

        self.depth = depth
        self.ask_price = np.empty(self.depth)
        self.ask_price.fill(np.nan)
        self.bid_price = np.empty(self.depth)
        self.bid_price.fill(np.nan)
        self.ask_volume = np.empty(self.depth)
        self.ask_volume.fill(np.nan)
        self.bid_volume = np.empty(self.depth)
        self.bid_volume.fill(np.nan)


class BarEvent(Event):
    """
    BarEvent is created when a bar data arrived
    and will be handled by strategy and portfolio handler
    """
    __slots__ = ["ticker", "time", "open", "high", "low", "close", "volume"]

    def __init__(self, ticker, timestamp, openPrice, highPrice, lowPrice, closePrice, volume, topic=''):
        super(BarEvent, self).__init__(EVENTS.BAR, 1, timestamp, topic)
        self.ticker = ticker
        self.time = timestamp
        self.open = openPrice
        self.high = highPrice
        self.low = lowPrice
        self.close = closePrice
        self.volume = volume


class OrderEvent(Event):
    """
    OrderEvent is created by a strategy when it wants to open an order and
    will be handled by Simulation or Trade section
    """
    __slots__ = ["data"]

    def __init__(self, order, timestamp=None, topic=""):
        """

        Args:
            order(bigfishtrader.model.Order):
            timestamp:
            topic:

        Returns:

        """
        super(OrderEvent, self).__init__(EVENTS.ORDER, 0, timestamp, topic)
        self.data = order

    def match(self, **conditions):
        for key, value in conditions.items():
            if getattr(self, key, None) != value:
                return False

        return True

    def to_fill(self, timestamp, price, commission=0, lever=1, deposit_rate=1,
                position_id=None, external_id=None, topic=''):
        order = self.data
        fill = Fill()
        fill.time = timestamp
        fill.ticker = order.symbol
        fill.action = order.action
        fill.quantity = order.orderQty
        fill.price = price
        fill.commission = commission
        fill.lever = lever
        fill.deposit_rate = deposit_rate
        fill.order_id = order.cliOrdID
        fill.position_id = position_id if position_id else order.cliOrdID
        fill.order_ext_id = external_id
        return FillEvent(fill, timestamp=fill.time, topic=topic)


class CancelEvent(Event):
    """
    CancelEvent is created by a strategy when it wants to cancel an limit or stop order
    and it will be handled by Simulation or Trade section
    """
    __slots__ = ["conditions"]

    def __init__(self, topic='', **conditions):
        super(CancelEvent, self).__init__(EVENTS.CANCEL, 0, datetime.now(), topic)
        self.conditions = conditions


class FillEvent(Event):
    """
    FillEvent is created by Simulation section
    when it receives an OrderEvent or by Trade section
    when it receives signals from the internet
    and it will be handled by Portfolio handler to
    update portfolio information
    """
    __slots__ = ["data"]

    def __init__(self, fill, timestamp=None, topic=''):
        if timestamp is None:
            super(FillEvent, self).__init__(EVENTS.FILL, 0, datetime.now(), topic)
        else:
            super(FillEvent, self).__init__(EVENTS.FILL, 0, timestamp, topic)
        self.data = fill


class TimeEvent(Event):
    __slots__ = []

    def __init__(self, timestamp, topic=""):
        super(TimeEvent, self).__init__(EVENTS.TIME, 1, timestamp, topic)


class ModifyEvent(Event):
    __slots__ = ["modify", "order_id"]

    def __init__(self, timestamp, order_id, topic='', **modify):
        super(ModifyEvent, self).__init__(EVENTS.MODIFY, 0, timestamp, topic)
        self.order_id = order_id
        self.modify = modify


class ConfirmEvent(Event):
    __slots__ = ["info"]

    def __init__(self, timestamp, topic='', **info):
        super(ConfirmEvent, self).__init__(EVENTS.CONFIRM, 0, timestamp, topic)
        self.info = info


class ConfigEvent(Event):
    __slots__ = ["config"]

    def __init__(self, timestamp, topic='', **config):
        super(ConfigEvent, self).__init__(EVENTS.CONFIG, -1, timestamp, topic)
        self.config = config


class RecallEvent(Event):
    __slots__ = ['order', 'lock']

    def __init__(self, timestamp, order, lock=True, topic=''):
        super(RecallEvent, self).__init__(EVENTS.RECALL, 0, timestamp, topic)
        self.order = order
        self.lock = lock


class ExitEvent(Event):
    __slots__ = []

    def __init__(self):
        super(ExitEvent, self).__init__(EVENTS.EXIT, 999, datetime.now())


class PositionEvent(Event):
    """

    """
    __slots__ = ["ticker", "exchange", "direction", "volume", "AxPrice"]

    def __init__(self, priority, timestamp):
        super(PositionEvent, self).__init__(EVENTS.POSITION, priority, timestamp)
        self.ticker = None
        self.exchange = None
        self.direction = None
        self.volume = None

    @property
    def cli_ticker(self):
        return self.exchange + self.ticker


class OrderStatusEvent(Event):
    __slots__ = []


if __name__ == '__main__':
    pass
