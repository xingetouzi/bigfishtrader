from bigfishtrader.quotation.base import AbstractPriceHandler
from bigfishtrader.event import ExitEvent, BarEvent, TickEvent
from datetime import datetime
from threading import Thread
import pandas as pd
import oandapy
import pytz
import json


class OandaStream(oandapy.Streamer):
    def __init__(self, event_queue, account_info=None):
        super(OandaStream, self).__init__(account_info['environment'], account_info['access_token'])
        self.info = account_info
        self.event_queue = event_queue
        self.tz = pytz.timezone("Asia/Shanghai")

    def on_success(self, data):
        if 'tick' in data:
            ticker = data['tick']
            self.event_queue.put(
                TickEvent(
                    ticker['instrument'],
                    datetime.strptime(ticker['time'], '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=pytz.utc).astimezone(
                        tz=self.tz),
                    ticker['ask'], ticker['bid']
                )
            )

    def on_error(self, data):
        print data


class OandaQuotation(AbstractPriceHandler):
    def __init__(
            self, event_queue, oanda_stream,
            mongo_client, trade_type='paper'
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
            return self._instance
        elif self.type == 'trade':
            return pd.DataFrame()

    def run(self):
        if self.type == 'paper':
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
    try:
        from Queue import Queue
    except ImportError:
        from queue import Queue
    from threading import Thread
    import json


    def process(q):
        while True:
            event = q.get()
            dct = event.to_dict()
            print(dct["time"].isoformat())
            # print(json.dumps(dct, indent=4, ensure_ascii=False, sort_keys=True))


    qu = Queue()
    account_info = json.load(open('../bigfish_oanda.json'))

    stream = OandaStream(qu, account_info)

    def produce(account):
        stream.rates(account_info['account_id'], ['EUR_USD'])


    thread = Thread(target=produce, args=(account_info, ))
    thread.start()
    process(qu)
