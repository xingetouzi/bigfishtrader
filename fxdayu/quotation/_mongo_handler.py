# encoding=utf-8
import pandas as pd

from fxdayu.engine.handler import Handler
from fxdayu.event import BarEvent, ExitEvent, EVENTS
from fxdayu.quotation.base import AbstractPriceHandler


class MongoHandler(AbstractPriceHandler):
    """
    This price handler is based on MongoDB
    It only support single backtest
    In the backtest, the next_stream is called
    when the event_queue is empty and it then
    get a bar data from mongo client and transfer
    it into a BarEvent then put the BarEvent into the event_queue
    """

    def __init__(self, collection, ticker, event_queue, trader=None, fetchall=False, data_support=None):
        super(MongoHandler, self).__init__()
        self.collection = collection
        self.event_queue = event_queue
        self.ticker = ticker
        self._instance_data = pd.DataFrame()
        self._fetchall = fetchall
        self.last_time = None
        self.trader = trader
        self.cursor = None
        self.data_support = data_support
        self._handlers["on_bar"] = Handler(self.on_bar, EVENTS.BAR, topic="", priority=100)

    def initialize(self, start=None, end=None):
        dt_filter = {}
        if start:
            dt_filter['$gte'] = start
        if end:
            dt_filter['$lte'] = end

        if len(dt_filter):
            self.cursor = self.collection.find(
                {'datetime': dt_filter},
                projection=['datetime', 'openMid', 'highMid', 'lowMid', 'closeMid', 'volume']
            ).sort([('datetime', 1)])
        else:
            self.cursor = self.collection.find(
                projection=['datetime', 'openMid', 'highMid', 'lowMid', 'closeMid', 'volume']
            ).sort([('datetime', 1)])
        if self._fetchall:
            self._instance_data = pd.DataFrame(list(self.cursor),
                                               columns=["datetime", "openMid", "highMid", "lowMid", "closeMid",
                                                        "volume"])
            self.cursor = self._instance_data.iterrows()

            '''data 过渡版本'''
            if self.data_support:
                self.data_support.set_instance(self.collection.name, self._instance_data)

    def get_last_time(self):
        return self.last_time

    def get_last_price(self, ticker):
        return self._instance_data['closeMid'].values[-1]

    def next_stream(self):
        try:
            bar = next(self.cursor)
        except StopIteration:
            self.event_queue.put(ExitEvent())
            self.stop()
            return
        if self._fetchall:
            bar = bar[1]
        else:
            bar.pop('_id')
            self._instance_data = self._instance_data.append(bar, ignore_index=True)

            '''data 过渡版本'''
            if self.data_support:
                self.data_support.set_instance(self.collection.name, self._instance_data)

        bar_event = BarEvent(
            self.ticker,
            bar['datetime'], bar['openMid'],
            bar['highMid'], bar['lowMid'],
            bar['closeMid'], bar['volume'],
        )
        self.event_queue.put(bar_event)

    def get_instance(self, ticker=None):
        if self._fetchall:
            return self._instance_data[self._instance_data['datetime'] <= self.last_time]
        else:
            return self._instance_data

    def get_ticker(self):
        return self.ticker

    def on_bar(self, event, kwargs=None):
        self.last_time = event.time


class MultipleHandler(AbstractPriceHandler):
    def __init__(self, client, event_queue, **collections):
        super(MultipleHandler, self).__init__()
        self.client = client
        self.event_queue = event_queue
        self._generate_collections(**collections)

    def _generate_collections(self, **collections):
        self.collections = []
        for db in collections:
            for col in collections[db]:
                self.collections.append(self.client[db][col])

    def next_stream(self):
        pass

    def get_instance(self, ticker):
        pass


if __name__ == '__main__':
    pass
