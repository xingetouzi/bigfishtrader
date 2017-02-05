# encoding=utf-8
from bigfishtrader.data.base import AbstractDataSupport
from bigfishtrader.event import TimeEvent, ExitEvent
from bigfishtrader.data.support import MultiPanelData
from datetime import datetime
import pandas
import tushare


FIELDS = ['datetime', 'open', 'high', 'close', 'low', 'volume']


class TushareDataSupport(AbstractDataSupport):
    def __init__(self, panel_support=None):
        super(TushareDataSupport, self).__init__()
        self._panel_data = panel_support if panel_support else MultiPanelData(None)
        self._initialized = False

    def init(self, tickers, frequency, start=None, end=None, **kwargs):
        """

        :param tickers: str或list, 需要的品种名称或品种列表
        :param frequency: 周期, D=日k线 W=周 M=月 5=5分钟 15=15分钟 30=30分钟 60=60分钟
        :param start: datetime, 开始时间
        :param end: datetime, 结束时间, 缺省代表到最近的时间
        :param kwargs: 其他非必需信息, 因品种不同所需不同
        :return:
        """
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
        freq = frequency[:-3] if 'min' in frequency else frequency

        if isinstance(tickers, str):
            frames[tickers] = self._subscribe(tickers, freq, start, end, **kwargs)
        elif isinstance(tickers, list):
            for ticker in tickers:
                frames[ticker] = self._subscribe(ticker, freq, start, end, **kwargs)
        else:
            raise TypeError('Type of tickers must be str or list, not %s' % type(tickers))

        if self._initialized:
            self._panel_data.insert(frequency, **frames)
        else:
            return frames

    def _subscribe(self, ticker, frequency, start=None, end=None, **kwargs):
        source = kwargs.pop('source', 'tushare')

        if source == 'csv':
            frame = self.from_csv(ticker, frequency, **kwargs)
        else:
            frame = self.from_tushare(ticker, frequency, start, end, **kwargs)

        format_ = '%Y-%m-%d'
        if len(frame['date'].values[-1]) > 11:
            format_ = ' '.join((format_, '%H:%M'))

        frame['datetime'] = pandas.to_datetime(
            frame.pop('date'),
            format=format_
        )
        frame.index = frame['datetime']

        if source == "csv":
            if start:
                frame = frame[frame.index >= start]
            if end:
                frame = frame[frame.index <= end]

        return frame

    @staticmethod
    def from_csv(ticker, frequency, **kwargs):
        path = kwargs.pop('path', '')
        frame = pandas.read_csv(path+'_'.join((ticker, frequency))+'.csv')
        return frame

    @staticmethod
    def from_tushare(ticker, frequency, start=None, end=None, **kwargs):
        save = kwargs.pop('save', False)
        frame = tushare.get_k_data(ticker, start, end, frequency, **kwargs)
        if save:
            frame.to_csv('_'.join((ticker, frequency))+'.csv', index=False,)
        return frame

    def current(self, tickers, fields=FIELDS):
        """

        :param tickers: str或list, 需要的品种名称或品种列表
        :param fields: 需要的返回值, 默认为['datetime', 'open', 'high', 'close', 'low', 'volume']
        :return:
        """
        return self._panel_data.current(tickers, fields)

    def history(
            self, tickers, frequency, fields=FIELDS,
            start=None, end=None, length=None
    ):
        """

        :param tickers: str或list, 需要的品种名称或品种列表
        :param frequency: 周期
        :param fields: 需要返回的值, 默认为['datetime', 'open', 'high', 'close', 'low', 'volume']
        :param start: 开始时间
        :param end: 结束时间
        :param length: 所需bar的长度

        :return:
        """
        return self._panel_data.history(
            tickers,  frequency, fields,
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
    tsdata = TushareDataSupport(MultiPanelData(None))
    tsdata.init(['000001', '000002'], 'D', '2016-01-01')
    # tsdata.subscribe(['000001', '000002'], 'W', '2016-01-01')
    # print('--------- test current() ---------')
    # print(tsdata.current(['000001', '000002'], ['open', 'close']))
    # print(tsdata.current('000002', ['open', 'high', 'low', 'close']))
    #
    # print('------------------ test history() ------------------')
    # print(tsdata.history('000001', 'D', start=datetime(2016, 12, 15), end=datetime(2017, 1, 15)))
    # print(tsdata.history('000001', 'D', start=datetime(2017, 1, 1)))
    # print(tsdata.history('000001', 'D', end=datetime(2016, 1, 15)))
    # print(tsdata.history('000001', 'D', start=datetime(2017, 1, 1), length=3))
    # print(tsdata.history('000001', 'D', end=datetime(2017, 1, 1), length=3))
    # print(tsdata.history('000001', 'D', length=3))
    # print(tsdata.history(['000001', '000002'], 'D', length=3))
    # print(tsdata.history('000001', 'W', start=datetime(2016, 12, 15), end=datetime(2017, 1, 15)))
    # print(tsdata.history(['000001', '000002'], 'W', start=datetime(2016, 12, 15), end=datetime(2017, 1, 15)))
    # print(tsdata.history('000001', 'D'))

