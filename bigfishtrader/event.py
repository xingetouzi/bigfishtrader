from enum import Enum
from bigfishtrader.const import *


class EVENTS(Enum):
    TICK = 0
    BAR = 1
    ORDER = 2
    FILL = 3
    LIMIT = 4
    STOP = 5
    CANCEL = 6
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
    __slots__ = ["type", "priority", "topic"]

    def __init__(self):
        self.type = None
        self.priority = 0
        self.topic = ""

    def set_priority(self, p=1):
        self.priority = p

    def __eq__(self, other):
        return self.priority == other.priority

    def __lt__(self, other):
        return self.priority < other.priority

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
        super(TickEvent, self).__init__()
        self.type = EVENTS.TICK
        self.set_priority(1)
        self.ticker = ticker
        self.time = timestamp
        self.ask = ask
        self.bid = bid


class BarEvent(Event):
    """
    BarEvent is created when a bar data arrived
    and will be handled by strategy and portfolio handler
    """
    __slots__ = ["ticker", "time", "open", "high", "low", "close", "volume"]

    def __init__(self, ticker, timestamp, openPrice, highPrice, lowPrice, closePrice, volume):
        super(BarEvent, self).__init__()
        self.type = EVENTS.BAR
        self.set_priority(1)
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
    __slots__ = ["ticker", "price", "time", "action", "quantity", "local_id", "status", "tag", "order_type"]

    def __init__(self, timestamp, ticker, action, quantity, price=None, order_type=EVENTS.ORDER, tag=None, local_id=0):
        super(OrderEvent, self).__init__()
        self.type = EVENTS.ORDER
        self.time = timestamp
        self.price = price
        self.ticker = ticker
        self.set_priority(0)
        self.action = action
        self.quantity = quantity
        self.tag = tag
        self.local_id = local_id
        self.status = ORDER_STATUS.UNFILL
        self.order_type = order_type

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

    def __init__(self, **conditions):
        super(CancelEvent, self).__init__()
        self.type = EVENTS.CANCEL
        self.set_priority(0)
        self.conditions = conditions


class FillEvent(Event):
    """
    FillEvent is created by Simulation section
    when it receives an OrderEvent or by Trade section
    when it receives signals from the internet
    and it will be handled by Portfolio handler to
    update portfolio information
    """
    __slots__ = ["time", "ticker", "action", "quantity", "price", "commission", "lever", "deposit_rate", "local_id"]

    def __init__(self, timestamp, ticker, action, quantity, price, commission=0, lever=1, deposit_rate=1):
        super(FillEvent, self).__init__()
        self.type = EVENTS.FILL
        self.time = timestamp
        self.ticker = ticker
        self.set_priority(0)
        self.action = action
        self.quantity = quantity
        self.price = price
        self.commission = commission
        self.lever = lever
        self.deposit_rate = deposit_rate
        self.local_id = None


class FinalEvent(Event):
    __slots__ = []

    def __init__(self):
        super(FinalEvent, self).__init__()
        self.set_priority(-1)
        self.type = EVENTS.EXIT


class ExitEvent(Event):
    __slots__ = []

    def __init__(self):
        super(ExitEvent, self).__init__()
        self.type = EVENTS.EXIT
        self.set_priority(999)
