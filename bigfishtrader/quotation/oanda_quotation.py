from bigfishtrader.quotation.base import AbstractPriceHandler
from bigfishtrader.event import ExitEvent, BarEvent, TickEvent
from datetime import datetime
from threading import Thread
import pandas as pd
import oandapy
import json


class OandaStream(oandapy.Streamer):
    def __init__(self, event_queue, account_info=None):
        super(OandaStream, self).__init__(account_info['environment'], account_info['access_token'])
        self.info = account_info
        self.event_queue = event_queue

    def on_success(self, data):
        if 'tick' in data:
            ticker = data['tick']
            self.event_queue.put(
                TickEvent(
                    ticker['instrument'],
                    datetime.strptime(ticker['time'], '%Y-%m-%dT%H:%M:%S.%fZ'),
                    ticker['ask'], ticker['bid']
                )
            )

    def on_error(self, data):
        print data


class OandaQuotation(AbstractPriceHandler):
    def __init__(
            self, event_queue, oanda_stream,
            mongo_client, trade_type='practice'
    ):
        super(OandaQuotation, self).__init__()
        self.event_queue = event_queue
        self.streamer = oanda_stream
        self.live_streams = {}
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

        if self.type == 'practice':
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
            return self._instance
        elif self.type == 'live':
            return pd.DataFrame()

    def run(self):
        if self.type == 'practice':
            super(OandaQuotation, self).run()
        elif self.type == 'live':
            thread = Thread(
                target=self.streamer.rates, name=self.ticker,
                kwargs={
                    'account_id': self.streamer.info['account_id'],
                    'instruments': [self.ticker]
                }
            )
            thread.start()
            self.live_streams[self.ticker] = thread



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



if __name__ == '__main__':
    account_info = json.load(open('D:/bigfishtrader/live_account.json'))
    stream = OandaStream(None, account_info)
    stream.rates(account_info['account_id'], ['EUR_USD'])





