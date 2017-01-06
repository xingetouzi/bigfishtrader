import time
from collections import deque

import numpy
import statsd

from bigfishtrader.event import EVENTS


class BaseTimer(object):
    def __init__(self, tick_timing=False):
        """
        :param tick_timing: flag to enable tick timing, default False
        :type tick_timing: bool
        """
        self._cache_order_time = None
        self._tick_timing = tick_timing

    def register(self, engine):
        """
        :param engine: engine
        :type engine: bigfishtrader.engine.core.Engine
        """
        engine.register(self.on_bar_start, EVENTS.BAR, topic="", priority=100)
        engine.register(self.on_bar_end, EVENTS.BAR, topic=".", priority=-100)
        engine.register(self.on_order, EVENTS.ORDER, topic="", priority=-100)
        engine.register(self.on_fill, EVENTS.ORDER, topic=".", priority=100)
        engine.register(self.on_tick_start, EVENTS.TICK, topic="", priority=100)
        engine.register(self.on_tick_end, EVENTS.TICK, topic="", priority=-100)

    def on_bar_start(self, bar, kwargs):
        kwargs["timestamp_bar_start"] = time.clock()

    def on_bar_end(self, bar, kwargs):
        kwargs["timestamp_bar_end"] = time.clock()
        self.count_bar(kwargs["timestamp_bar_end"] - kwargs["timestamp_bar_start"])

    def on_tick_start(self, tick, kwargs):
        kwargs["timestamp_tick_start"] = time.clock()

    def on_tick_end(self, tick, kwargs):
        kwargs["timestamp_tick_end"] = time.clock()
        self.count_tick(kwargs["timestamp_tick_end"] - kwargs["timestamp_tick_start"])

    def on_order(self, order, kwargs):
        # TODO this is a temporary method
        self._cache_order_time = time.clock()

    def on_fill(self, order, kwargs):
        self.count_order(time.clock() - self._cache_order_time)

    def count_bar(self, t):
        pass

    def count_order(self, t):
        pass

    def count_tick(self, t):
        pass


class CountTimer(BaseTimer):
    def __init__(self, tick_timing=False):
        super(CountTimer, self).__init__(tick_timing)
        self._ht_bar = deque(maxlen=100000)
        self._ht_order = deque(maxlen=100000)
        self._ht_tick = deque(maxlen=100000)
        self._tick_counts = 0
        self._bar_counts = 0
        self._order_counts = 0

    @property
    def avht_bar(self):
        return numpy.mean(self._ht_bar)

    @property
    def avht_order(self):
        return numpy.mean(self._ht_order)

    @property
    def avht_tick(self):
        return numpy.mean(self._ht_tick)

    @property
    def bar_counts(self):
        return self._bar_counts

    @property
    def order_counts(self):
        return self._order_counts

    @property
    def tick_counts(self):
        return self._tick_counts

    def count_bar(self, t):
        self._bar_counts += 1
        self._ht_bar.append(t)

    def count_order(self, t):
        self._order_counts += 1
        self._ht_order.append(t)

    def count_tick(self, t):
        self._tick_counts += 1
        self._ht_tick.append(t)


class StatsdTimer(BaseTimer):
    def __init__(self, host="localhost", port="8125", tick_timing=False):
        super(StatsdTimer, self).__init__(tick_timing)
        self._stats_client = statsd.StatsClient(host=host, port=port)

    def count_bar(self, t):
        self._stats_client.timing("trader.bar", t * 1000)

    def count_order(self, t):
        self._stats_client.timing("trader.order", t * 1000)

    def count_tick(self, t):
        self._stats_client.timing("trader.tick", t * 1000)
