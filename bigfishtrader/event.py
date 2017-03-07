# encoding: utf-8

from datetime import datetime

import numpy as np

from bigfishtrader.const import *
from bigfishtrader.model import ExecutionData


class EVENTS(Enum):
    TICK = 0
    BAR = 1
    ORDER = 2
    EXECUTION = 3
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
    SCHEDULE = 14
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
            return self.time < other.time or self.lt_local_time(other)
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
    __slots__ = ["data"]

    MAX_DEPTH = 10

    def __init__(self, tick, timestamp=None, topic=""):
        if timestamp is None:
            timestamp = datetime.now()
        super(TickEvent, self).__init__(EVENTS.TICK, 1, timestamp, topic)
        self.data = tick


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
            order(bigfishtrader.model.OrderReq):
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
                sec_type=None, position_id=None, external_id=None, topic=''):
        order = self.data
        fill = ExecutionData()
        fill.time = timestamp
        fill.ticker = order.symbol
        fill.action = order.action
        fill.quantity = order.orderQty
        fill.secType = self.data.secType if self.data.secType != EMPTY_UNICODE else SecType.STK.value
        fill.price = price
        fill.commission = commission
        fill.lever = lever
        fill.deposit_rate = deposit_rate
        fill.order_id = order.clOrdID
        fill.position_id = position_id if position_id else order.clOrdID
        fill.order_ext_id = external_id
        return ExecutionEvent(fill, timestamp=fill.time, topic=topic)


class CancelEvent(Event):
    """
    CancelEvent is created by a strategy when it wants to cancel an limit or stop order
    and it will be handled by Simulation or Trade section
    """
    __slots__ = ["conditions"]

    def __init__(self, topic='', **conditions):
        super(CancelEvent, self).__init__(EVENTS.CANCEL, 0, datetime.now(), topic)
        self.conditions = conditions


class ExecutionEvent(Event):
    """
    FillEvent is created by Simulation section
    when it receives an OrderEvent or by Trade section
    when it receives signals from the internet
    and it will be handled by Portfolio handler to
    update portfolio information
    """
    __slots__ = ["data"]

    def __init__(self, execution, timestamp=None, topic=''):
        if timestamp is None:
            super(ExecutionEvent, self).__init__(EVENTS.EXECUTION, 0, datetime.now(), topic)
        else:
            super(ExecutionEvent, self).__init__(EVENTS.EXECUTION, 0, timestamp, topic)
        self.data = execution


class TimeEvent(Event):
    __slots__ = []

    def __init__(self, timestamp, topic=""):
        super(TimeEvent, self).__init__(EVENTS.TIME, 1, timestamp, topic)

    def lt_local_time(self, other):
        if self.time > other.time:
            return False
        elif isinstance(other, ScheduleEvent):
            return not other.ahead
        else:
            return self.local_time < other.local_time

class ScheduleEvent(Event):
    __slots__ = ['ahead']

    def __init__(self, timestamp, topic="", ahead=False):
        super(ScheduleEvent, self).__init__(EVENTS.SCHEDULE, 1, timestamp, topic)
        self.ahead = ahead

    def lt_time(self, other):
        if self.__eq__(other):
            if self.time < other.time:
                return True
            elif self.time == other.time:
                return self.ahead
            else:
                return False
        else:
            return False


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
    __slots__ = ["data"]

    def __init__(self, position, priority=0, timestamp=None, topic=""):
        if timestamp is None:
            timestamp = datetime.now()
        super(PositionEvent, self).__init__(EVENTS.POSITION, priority, timestamp, topic)
        self.data = position


class OrderStatusEvent(Event):
    __slots__ = ["data"]

    def __init__(self, ord_status, priority=0, timestamp=None, topic=""):
        if timestamp is None:
            timestamp = datetime.now()
        super(OrderStatusEvent, self).__init__(EVENTS.ORD_STATUS, priority, timestamp, topic)
        self.data = ord_status