from enum import Enum
from bigfishtrader.const import *
import nanotime


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
    EXIT = 999


OPEN_ORDER = 1
CLOSE_ORDER = 0


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
        self.local_time = nanotime.now()

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
    __slots__ = ["ticker", "time", "ask", "bid"]

    def __init__(self, ticker, timestamp, ask, bid):
        super(TickEvent, self).__init__(EVENTS.TICK, 1, timestamp)
        self.ticker = ticker
        self.ask = ask
        self.bid = bid


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
    __slots__ = ["ticker", "price", "time", "action", "quantity", "local_id", "status", "tag", "order_type",
                 "take_profit", "stop_lost"]

    def __init__(self, timestamp, ticker, action, quantity,
                 price=None, order_type=EVENTS.ORDER, tag=None,
                 local_id=0, take_profit=0, stop_lost=0, topic=''):
        super(OrderEvent, self).__init__(EVENTS.ORDER, 0, timestamp, topic)
        self.price = price
        self.ticker = ticker
        self.action = action
        self.quantity = quantity
        self.tag = tag
        self.local_id = local_id
        self.status = ORDERSTATUS.UNFILL
        self.order_type = order_type
        self.take_profit = take_profit
        self.stop_lost = stop_lost

    def match(self, **conditions):
        for key, value in conditions.items():
            if getattr(self, key, None) != value:
                return False

        return True


class CancelEvent(Event):
    """
    CancelEvent is created by a strategy when it wants to cancel an limit or stop order
    and it will be handled by Simulation or Trade section
    """
    __slots__ = ["conditions"]

    def __init__(self, topic='', **conditions):
        super(CancelEvent, self).__init__(EVENTS.CANCEL, 0, nanotime.now(), topic)
        self.conditions = conditions


class FillEvent(Event):
    """
    FillEvent is created by Simulation section
    when it receives an OrderEvent or by Trade section
    when it receives signals from the internet
    and it will be handled by Portfolio handler to
    update portfolio information
    """
    __slots__ = ["time", "ticker", "action", "quantity", "price", "profit", "commission", "lever", "deposit_rate",
                 "local_id", "external_id", "position_id", "fill_type"]

    def __init__(self, timestamp, ticker, action, quantity, price,
                 commission=0, lever=1, deposit_rate=1, fill_type='position',
                 local_id=None, position_id=None, external_id=None, topic=''):
        super(FillEvent, self).__init__(EVENTS.FILL, 0, timestamp, topic)
        self.ticker = ticker
        self.action = action
        self.quantity = quantity
        self.price = price
        self.profit = None
        self.commission = commission
        self.lever = lever
        self.deposit_rate = deposit_rate
        self.fill_type = fill_type
        self.position_id = position_id
        self.local_id = local_id
        self.external_id = external_id


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


class ExitEvent(Event):
    __slots__ = []

    def __init__(self):
        super(ExitEvent, self).__init__(EVENTS.EXIT, 999, nanotime.now())


if __name__ == '__main__':
    ee = ExitEvent
