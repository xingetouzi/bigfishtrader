from bigfishtrader.data.base import AbstractDataSupport
from bigfishtrader.event import TimeEvent, ExitEvent
from datetime import datetime
import logging
import pandas
import tushare


FIELDS = ['datetime', 'open', 'high', 'close', 'low', 'volume']


class TushareDataSupport(AbstractDataSupport):
    def __init__(self, panel_support):
        super(TushareDataSupport, self).__init__()
        self._panel_data = panel_support
        self._initialized = False

    def init(self, tickers, frequency, start=None, end=None, **kwargs):
        self._initialized = False
        frames = self.subscribe(tickers, frequency, start, end, **kwargs)
        self._panel_data.init(frequency, **frames)
        self._initialized = True

    def subscribe(self, tickers, frequency, start=None, end=None, **kwargs):
        if isinstance(start, datetime):
            start = start.strftime('%Y-%m-%d')
        if isinstance(end, datetime):
            end = end.strftime('%Y-%m-%d')

        frames = {}

        if isinstance(tickers, str):
            frames[tickers] = self._subscribe(tickers, frequency, start, end)
        elif isinstance(tickers, list):
            for ticker in tickers:
                frames[ticker] = self._subscribe(ticker, frequency, start, end)
        else:
            raise TypeError('Type of tickers must be str or list, not %s' % type(tickers))

        if self._initialized:
            self._panel_data.insert(frequency, **frames)
        else:
            return frames

    def _subscribe(self, ticker, frequency, start=None, end=None, **kwargs):
        frame = tushare.get_k_data(ticker, start, end, frequency, **kwargs)

        format_ = '%Y-%m-%d'
        if frequency.isdigit():
            format_ = ' '.join((format_, '%H:%M'))

        frame['datetime'] = pandas.to_datetime(
            frame.pop('date'),
            format=format_
        )
        frame.index = frame['datetime']

        return frame

    def current(self, tickers, fields=FIELDS):
        return self._panel_data.current(tickers, fields)

    def history(
            self, tickers, frequency, fields=FIELDS,
            start=None, end=None, length=None
    ):
        return self._panel_data.history(
            tickers, fields, frequency,
            start, end, length
        )

    def instance(
            self, tickers, fields, frequency,
            start=None, end=None, length=None
    ):
        pass

    def put_time_event(self, queue):
        for dt in self._panel_data.major_axis:
            queue.put(
                TimeEvent(dt)
            )
        queue.put(ExitEvent())

    def put_limit_time(self, queue, topic, **condition):
        for time_ in self._panel_data.major_axis:
            if self._time_match(time_, **condition):
                queue.put(TimeEvent(time_, topic))

    @staticmethod
    def _time_match(time, **condition):
        for key, value in condition.items():
            if getattr(time, key) != value:
                return False
        return True


if __name__ == '__main__':
    from bigfishtrader.data.support import MultiPanelData

    tsdata = TushareDataSupport(MultiPanelData(None))
    tsdata.init(['000001', '000002'], 'D', '2016-01-01')
    tsdata.subscribe(['000001', '000002'], 'W', '2016-01-01')

    print '--------- test current() ---------'
    print tsdata.current(['000001', '000002'], ['open', 'close'])
    print tsdata.current('000002', ['open', 'high', 'low', 'close'])

    print '------------------ test history() ------------------'
    print tsdata.history('000001', 'D', start=datetime(2016, 12, 15), end=datetime(2017, 1, 15))
    print tsdata.history('000001', 'D', start=datetime(2017, 1, 1))
    print tsdata.history('000001', 'D', end=datetime(2016, 1, 15))
    print tsdata.history('000001', 'D', start=datetime(2017, 1, 1), length=3)
    print tsdata.history('000001', 'D', end=datetime(2017, 1, 1), length=3)
    print tsdata.history('000001', 'D', length=3)
    print tsdata.history(['000001', '000002'], 'D', length=3)
    print tsdata.history('000001', 'W', start=datetime(2016, 12, 15), end=datetime(2017, 1, 15))
    print tsdata.history(['000001', '000002'], 'W', start=datetime(2016, 12, 15), end=datetime(2017, 1, 15))

    print '------------------ test error ------------------'
    try:
        print tsdata.history('000001', 'D')
    except Exception as e:
        logging.warn(e.message)