import pandas as pd
from bigfishtrader.event import BarEvent, ExitEvent
from bigfishtrader.price_handler.base import AbstractPriceHandler


class MongoHandler(AbstractPriceHandler):
    """
    This price handler is based on MongoDB
    It only support single backtest
    In the backtest, the next_stream is called
    when the event_queue is empty and it then
    get a bar data from mongo client and transfer
    it into a BarEvent then put the BarEvent into the event_queue
    """

    def __init__(self, collection, ticker, event_queue, trader=None):
        self.collection = collection
        self.event_queue = event_queue
        self.ticker = ticker
        self._instance_data = pd.DataFrame()
        self.last_time = None
        self.trader = trader
        self.running = False
        self.cursor = None

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

        self.running = True

    def get_last_time(self):
        return self.last_time

    def get_last_price(self, ticker):
        return self._instance_data['closeMid'].values[-1]

    def next_stream(self):
        try:
            bar = next(self.cursor)
        except StopIteration:
            self.event_queue.put(
                ExitEvent()
            )
            self.running = False
            return

        bar.pop('_id')
        bar_event = BarEvent(
            self.ticker,
            bar['datetime'], bar['openMid'],
            bar['highMid'], bar['lowMid'],
            bar['closeMid'], bar['volume']
        )
        self.last_time = bar['datetime']
        self._instance_data = self._instance_data.append(bar, ignore_index=True)
        self.event_queue.put(bar_event)

    def get_instance(self):
        return self._instance_data


class MultipleHandler(AbstractPriceHandler):
    def __init__(self, client, event_queue, **collections):
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

    def get_instance(self):
        pass


if __name__ == '__main__':
    pass
