# encoding: utf-8

import threading
from datetime import datetime

from dateutil.parser import parse

from fxdayu.const import *
from fxdayu.models.data import ExecutionData

G = threading.local()
ID_WIDTH = 12  # 0xffffffffffff / (365 * 24 * 60 * 60 * 100000) = 89
THREAD_ID_WITH = 5  # 0xfffff = 1048575


class EVENTS(Enum):
    TICK = 0
    BAR = 1
    ORDER = 2
    EXECUTION = 3
    LIMIT = 4
    STOP = 5
    CANCEL = 6
    TIME = 7
    CONFIG = 8
    POSITION = 9
    ACCOUNT = 10
    ORD_STATUS = 11
    LOG = 12
    ERROR = 13
    INIT = 14
    SCHEDULE = 15
    EXIT = 999


class Event(object):
    """
    This is the base event class
    it implements the __lt__ and __gt__ function
    which compares its own priority and other event's priority
    Other events that extends from this class must set the 'priority' attribution
    """
    __slots__ = ["type", "priority", "topic", "time", "pid"]

    def __init__(self, _type, priority, timestamp, topic=""):
        self.type = _type
        self.priority = priority
        self.topic = topic
        self.time = timestamp
        self.pid = self.next_pid()

    @classmethod
    def next_pid(cls):
        # XXX in a thread, event keep in order, but not totally threading-safe
        global G
        try:
            G.count += 1
        except AttributeError:
            G.count = 1
        result = hex(threading.current_thread().ident)[2:].replace("L", "").zfill(THREAD_ID_WITH)
        result += hex(G.count)[2:].replace("L", "").zfill(ID_WIDTH)
        return result

    def to_dict(self):
        return {field: getattr(self, field) for field in self.__slots__}

    def __lt__(self, other):
        return (self.priority, self.time, self.pid) < (other.priority, other.time, other.pid)


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
            order(fxdayu.models.OrderReq):
            timestamp:
            topic:

        Returns:

        """
        if timestamp is None:
            timestamp = datetime.now()
        super(OrderEvent, self).__init__(EVENTS.ORDER, 0, timestamp, topic)
        self.data = order


class CancelEvent(Event):
    """
    CancelEvent is created by a strategy when it wants to cancel an limit or stop order
    and it will be handled by Simulation or Trade section
    """
    __slots__ = ["data"]

    def __init__(self, data, timestamp=None, topic=''):
        """

        Args:
            data(fxdayu.models.order.CancelReq):
            timestamp:
            topic:

        Returns:

        """
        if timestamp is None:
            timestamp = datetime.now()
        super(CancelEvent, self).__init__(EVENTS.CANCEL, 0, timestamp, topic)
        self.data = data


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
        """

        Args:
            execution(fxdayu.models.ExecutionData):
            timestamp:
            topic:

        Returns:

        """
        if timestamp is None:
            timestamp = datetime.now()
        super(ExecutionEvent, self).__init__(EVENTS.EXECUTION, 0, timestamp, topic)
        self.data = execution


class TimeEvent(Event):
    __slots__ = []

    def __init__(self, timestamp, topic=""):
        super(TimeEvent, self).__init__(EVENTS.TIME, 1, timestamp, topic)


class ScheduleEvent(Event):
    __slots__ = []

    def __init__(self, timestamp, topic=""):
        super(ScheduleEvent, self).__init__(EVENTS.SCHEDULE, 1, timestamp, topic)


class ConfigEvent(Event):
    __slots__ = ["config"]

    def __init__(self, timestamp, topic='', **config):
        super(ConfigEvent, self).__init__(EVENTS.CONFIG, -1, timestamp, topic)
        self.config = config


class ExitEvent(Event):
    __slots__ = []

    def __init__(self):
        super(ExitEvent, self).__init__(EVENTS.EXIT, 999, datetime.now())


class AccountEvent(Event):
    __slots__ = ["data"]

    def __init__(self, account, priority=0, timestamp=None, topic=""):
        if timestamp is None:
            timestamp = datetime.now()
        super(AccountEvent, self).__init__(EVENTS.ACCOUNT, priority, timestamp, topic)
        self.data = account


class PositionEvent(Event):
    """

    """
    __slots__ = ["data"]

    def __init__(self, position, priority=0, timestamp=None, topic=""):
        """

        Args:
            position(fxdayu.models.PositionData):
            priority:
            timestamp:
            topic:

        Returns:

        """
        if timestamp is None:
            timestamp = datetime.now()
        super(PositionEvent, self).__init__(EVENTS.POSITION, priority, timestamp, topic)
        self.data = position


class OrderStatusEvent(Event):
    __slots__ = ["data"]

    def __init__(self, ord_status, priority=0, timestamp=None, topic=""):
        """

        Args:
            ord_status(fxdayu.models.order.OrderStatusData):
            priority:
            timestamp:
            topic:

        Returns:

        """
        if timestamp is None:
            timestamp = datetime.now()
        super(OrderStatusEvent, self).__init__(EVENTS.ORD_STATUS, priority, timestamp, topic)
        self.data = ord_status


class LogEvent(Event):
    __slots__ = ["data"]

    def __init__(self, log, priority=0, topic=""):
        """

        Args:
            log(fxdayu.models.LogData):
            priority:
            topic:

        Returns:
            None
        """

        super(LogEvent, self).__init__(EVENTS.LOG, priority, parse(log.logTime), topic)
        self.data = log


class ErrorEvent(Event):
    __slots__ = ["data"]

    def __init__(self, error, priority=0, topic=""):
        """

        Args:
            error(fxdayu.models.ErrorData):
            priority:
            topic:

        Returns:
            None
        """
        super(ErrorEvent, self).__init__(EVENTS.ERROR, priority, parse(error.errorTime), topic)
        self.data = error


class InitEvent(Event):
    def __init__(self, priority=-1, timestamp=None):
        if timestamp is None:
            timestamp = datetime.now()
        super(InitEvent, self).__init__(EVENTS.INIT, priority, timestamp)
