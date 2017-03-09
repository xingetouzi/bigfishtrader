# encoding: utf-8

import time

import pandas as pd

from fxdayu.event import TickEvent
from fxdayu.quotation.base import AbstractPriceHandler


class ArtificialTickHandler(AbstractPriceHandler):
    def __init__(self, event_queue, symbol, interval=100):
        super(ArtificialTickHandler, self).__init__()
        self.ticker = symbol
        self._instance = pd.DataFrame()
        self._event_queue = event_queue
        self._symbol = symbol
        self._interval = interval
        self._last_time = time.time()
        self._is_running = False

    def run(self):
        """
        start to subscriber market data
        :return: None
        """
        if self._is_running:
            return
        self._is_running = True
        while self._is_running:
            self.next_stream()
            time.sleep(self._interval / 1000)

    def stop(self):
        if not self._is_running:
            self._is_running = False
        self._is_running = False

    def get_last_time(self):
        return self._last_time

    def get_instance(self):
        return self._instance

    def next_stream(self):
        timestamp = time.time()
        tick = TickEvent(self._symbol, timestamp, 3000, 3000)
        self._last_time = timestamp
        self._event_queue.put(tick)
