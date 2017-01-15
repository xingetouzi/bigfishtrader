import oandapy
import pandas as pd
from bigfishtrader.quotation.base import AbstractPriceHandler
from bigfishtrader.event import ExitEvent, BarEvent


class OandaStream(oandapy.Streamer):
    def __init__(self, event_queue, enviornment='practise', access_token=None):
        super(OandaStream, self).__init__(enviornment, access_token)
        self.event_queue = event_queue

    def on_success(self, data):
        pass

    def on_error(self, data):
        pass


class OandaQuotation(AbstractPriceHandler):
    def __init__(
            self, event_queue, oanda_stream,
            mongo_client, trade_type='paper'
    ):
        super(OandaQuotation, self).__init__()
        self.event_queue = event_queue
        self.streamer = oanda_stream
        self.client = mongo_client
        self.type = trade_type

    def initialize(self, ticker, period, start=None, end=None):
        self.collection = self.client.Oanda['.'.join((ticker, period))]
        self.ticker = ticker
        self.period = period

        dt_filter = {}
        if start:
            dt_filter['$gte'] = start
        if end:
            dt_filter['$lte'] = end

        self.filter = {'datetime': dt_filter} if len(dt_filter) else {}

        if self.type == 'paper':
            self.cursor = self.collection.find(
                self.filter,
                projection=['datetime', 'closeMid', 'highMid', 'lowMid', 'openMid', 'volume']
            )
            self._instance = pd.DataFrame(
                list(
                    self.cursor
                )
            )
            self._instance.pop('_id')
            self.cursor = self._instance.iterrows()

    def next_stream(self):
        while self._is_running:
            try:
                bar = next(self.cursor)[1]
            except StopIteration:
                self.event_queue.put(ExitEvent())
                return

        event = BarEvent(
            self.ticker,
            bar['datetime'], bar['openMid'],
            bar['highMid'], bar['lowMid'],
            bar['closeMid'], bar['volume'],
        )

        self.event_queue.put(event)







