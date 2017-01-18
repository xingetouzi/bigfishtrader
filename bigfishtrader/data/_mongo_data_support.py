# encoding: utf-8

from datetime import timedelta
from collections import OrderedDict, Iterable

import pandas as pd
from dictproxyhack import dictproxy

from bigfishtrader.event import TimeEvent, ExitEvent
from bigfishtrader.data.mongo_support import connect
from bigfishtrader.data.base import AbstractDataSupport
from bigfishtrader.data.cache import MemoryCacheProxy
from bigfishtrader.data.support import PanelDataSupport

_BAR_FIELDS_MAP = OrderedDict([
    ("datetime", "datetime"),
    ("openMid", "open"),
    ("highMid", "high"),
    ("lowMid", "low"),
    ("closeMid", "close"),
    ("volume", "volume"),
])


class MongoDataSupport(AbstractDataSupport):
    def __init__(self, db="admin", **info):
        super(MongoDataSupport, self).__init__()
        self._client = connect(**info)
        self._db = db
        self._tickers = {}
        self._start = None
        self._end = None
        self._limit = None
        self._timeframe = None
        self._max_backtrack = None
        self._cache = {}
        self._ds = None
        self._initialized = False

    def init(self, tickers, timeframe, start, end, limit=None, max_backtrack=50):
        self._initialized = True
        self._tickers = list(tickers)
        self._start = start
        self._end = end
        self._limit = None
        self._timeframe = timeframe
        self._max_backtrack = max_backtrack
        self._cache = MemoryCacheProxy(self, max_backtrack)

    def _fetch_ticker_bar_data(self, db, ticker, timeframe, dt_filter=None):
        collection = self._client[db][ticker + "." + timeframe]
        if dt_filter is None:
            dt_filter = {}
            if self._start:
                dt_filter['$gte'] = self._start
            if self._end:
                dt_filter['$lte'] = self._end

        filter_ = {'datetime': dt_filter} if len(dt_filter) else {}
        if len(dt_filter) == 2:
            frame = pd.DataFrame(
                list(
                    collection.find(
                        filter_, projection=_BAR_FIELDS_MAP.keys()
                    ).sort([('datetime', 1)])
                )
            ).rename_axis(_BAR_FIELDS_MAP, axis=1).reindex(columns=_BAR_FIELDS_MAP.values())
        else:
            # TODO 回补数据应该只支持向前回补固定条数，如果是向前回补，这样的写法是不正确的,会返回时间靠前的limit
            frame = pd.DataFrame(
                list(
                    collection.find(
                        filter_, projection=_BAR_FIELDS_MAP.keys()
                    ).sort([('datetime', 1)]).limit(self._limit)
                )
            ).rename_axis(_BAR_FIELDS_MAP, axis=1).reindex(columns=_BAR_FIELDS_MAP.values())
        frame.index = frame["datetime"]
        return frame

    def fetch_data(self):
        if not self._initialized:
            raise RuntimeError("MongoDataSupport hasn't been initialized!")
        temp = {}
        for ticker in self._tickers:
            temp[ticker] = self._fetch_ticker_bar_data(self._db, ticker, self._timeframe)
        self._ds = PanelDataSupport(pd.Panel(temp), None)

    def set_context(self, context):
        if not self._ds:
            self.fetch_data()
        self._ds.set_context(context)

    def instance(self, tickers, fields, frequency, start=None, end=None, length=None):
        if not self._ds:
            self.fetch_data()
        return self._ds.instance(tickers, fields, frequency, start=start, end=end, length=length)

    def history(self, tickers, fields, frequency, start=None, end=None, length=None):
        if not self._ds:
            self.fetch_data()
        return self._ds.history(tickers, fields, frequency, start=start, end=end, length=length)

    def current(self, tickers, fields=None):
        if not self._ds:
            self.fetch_data()
        return self._ds.current(tickers, fields=fields)

    def timedelta(self):
        if self._timeframe == "D":
            return timedelta(days=1)
        elif self._timeframe == "M":
            return timedelta(minutes=1)

    def push_time_events(self, queue):
        timedelta_ = self.timedelta()
        time_events = [TimeEvent(t.to_pydatetime() + timedelta_) for t in self._ds.date_index()]
        queue.put(time_events)

    def subscribe(self, ticker, frequency, start=None, end=None, ticker_type=None):
        if ticker_type is None:
            ticker_type = self._db
        if start or end:
            dt_filter = {}
            if start:
                dt_filter['$gte'] = start
            if end:
                dt_filter['$gte'] = end
            frame = self._fetch_ticker_bar_data(ticker_type, ticker, frequency, dt_filter)
        else:
            frame = self._fetch_ticker_bar_data(ticker_type, ticker, frequency)

        self._ds.insert(ticker, frame, frequency)


class MultiDataSupport(AbstractDataSupport):
    def __init__(self, context, db="admin", **info):
        super(MultiDataSupport, self).__init__()
        self._db = db
        self._client = connect(**info)
        self._panels = {}
        self.context = context

    def init(self, tickers, frequency, start=None, end=None):
        self._frequency = frequency
        self.subscribe(tickers, frequency, start, end)

    def subscribe(self, tickers, frequency, start=None, end=None):
        if isinstance(tickers, str):
            tickers = [tickers]

        panel = self._panels.get(frequency, None)
        if panel is not None:
            for ticker in tickers:
                panel[ticker] = self._subscribe(ticker, frequency, start, end)
        else:
            frame_dict = {}
            for ticker in tickers:
                frame_dict[ticker] = self._subscribe(ticker, frequency, start, end)
            self._panels[frequency] = pd.Panel.from_dict(frame_dict)

    def _subscribe(self, ticker, frequency, start=None, end=None, ticker_type=None):
        if ticker_type is None:
            ticker_type = self._db
        collection = self._client[ticker_type]['.'.join((ticker,frequency))]
        dt_filter = {}
        if start:
            dt_filter['$gte'] = start
        if end:
            dt_filter['$lte'] = end

        filter_ = {'datetime': dt_filter} if len(dt_filter) else {}

        frame = pd.DataFrame(
            list(
                collection.find(filter_, projection=_BAR_FIELDS_MAP.keys())
            )
        ).rename_axis(_BAR_FIELDS_MAP, axis=1).reindex(columns=_BAR_FIELDS_MAP.values())
        frame.index = frame['datetime']
        return frame

    def cancel_subscribe(self, tickers, frequency):
        panel = self._panels[frequency]
        tickers = [tickers] if isinstance(tickers, str) else tickers
        for ticker in tickers:
            panel.pop(ticker)

    def current(self, tickers, fields=_BAR_FIELDS_MAP.values()):
        panel = self._panels[self._frequency]
        end = pd.to_datetime(self.context.current_time)
        index = panel.major_axis.searchsorted(end, 'left')

        if isinstance(tickers, str):
            frame = panel[tickers]
            return frame[fields].iloc[index]
        elif isinstance(tickers, Iterable):
            panel = panel[tickers]
            return panel.iloc[:, index, :]

    def history(
            self, tickers, fields, frequency,
            start=None, end=None, length=None
    ):
        if isinstance(tickers, str):
            tickers = [tickers]
        panel = self._panels[frequency]
        if start:
            start = pd.to_datetime(start)
            begin = panel.major_axis.searchsorted(start)
            if length:
                if len(tickers) == 1:
                    return panel[tickers[0]][fields].iloc[begin:begin+length]
                else:
                    return panel[tickers][:, begin:begin+length, fields]

            else:
                end = pd.to_datetime(end) if end else pd.to_datetime(self.context.current_time)
                stop = panel.major_axis.searchsorted(end)
                if panel.major_axis[stop] <= end:
                    stop += 1
                if len(tickers) == 1:
                    frame = panel[tickers[0]]
                    return frame.iloc[begin:stop][fields]
                else:
                    panel = panel[tickers]
                    return panel[:, begin:stop, fields]
        if end:
            end = pd.to_datetime(end)
            stop = panel.major_axis.searchsorted(end)
            if panel.major_axis[stop] <= end:
                    stop += 1
            if length:
                if len(tickers) == 1:
                    return panel[tickers[0]][fields].iloc[stop-length:stop]
                else:
                    return panel[tickers][:, stop-length:stop, fields]
            elif start:
                start = pd.to_datetime(start)
                begin = panel.major_axis.searchsorted(start)
                if len(tickers) == 1:
                    frame = panel[tickers[0]]
                    return frame.iloc[begin:stop][fields]
                else:
                    panel = panel[tickers]
                    return panel[:, begin:stop, fields]
            else:
                if len(tickers) == 1:
                    return panel[tickers[0]][fields].iloc[:stop]
                else:
                    return panel[tickers][:, :stop, fields]
        elif length:
            end = pd.to_datetime(self.context.current_time)
            stop = panel.major_axis.searchsorted(end)
            if panel.major_axis[stop] <= end:
                    stop += 1
            if len(tickers) == 1:
                return panel[tickers[0]][fields].iloc[stop-length:stop]
            else:
                return panel[tickers][:, stop-length:stop, fields]
        else:
            raise TypeError('history() takes at least one param among start, end and length')

    def put_time_events(self, queue):
        for time_ in self._panels[self._frequency].major_axis:
            queue.put(TimeEvent(time_, ''))
        queue.put(ExitEvent())

    def put_limit_time(self, queue, topic, **condition):
        for time_ in self._panels[self._frequency].major_axis:
            if self._time_match(time_, **condition):
                queue.put(TimeEvent(time_, topic))

    @staticmethod
    def _time_match(time, **condition):
        for key, value in condition.items():
            if getattr(time, key) != value:
                return False

        return True

    def data_base(self, ticker, frequency, field=None, start=None, end=None, ticker_type=None):
        dt_filter = {}
        if start:
            dt_filter['$gte'] = start
        if end:
            dt_filter['$lte'] = end

        filter_ = {'datetime': dt_filter} if len(dt_filter) else {}

        ticker_type = self._db if not ticker_type else ticker_type
        field = _BAR_FIELDS_MAP.keys() if field is None else field


        frame = pd.DataFrame(
            list(
                self._client[ticker_type]['.'.join((ticker, frequency))].find(
                    filter_,
                    projection=field
                )
            )
        )
        frame.pop('_id')
        return frame



if __name__ == "__main__":
    from datetime import datetime

    setting = {
        "host": "192.168.1.103",
        "port": 27018,
        "db": "Oanda",
    }

    # data = MongoDataSupport(**setting)
    # data.init(["EUR_USD", "GBP_USD"], "D", datetime(2014, 1, 1), datetime(2015, 1, 1))

    class Context(object):
        pass

    context = Context()

    data = MultiDataSupport(context, **setting)

    print(data.data_base('EUR_USD', 'D', field=['closeMid'], start=datetime(2016, 1, 1), end=datetime(2017, 1, 1)))
    # context.real_bar_num = 20
    # data.set_context(context)
    # print(data.current("EUR_USD", "open"))
    # print("\n")
    # print(data.current("EUR_USD", ["open", "close"]))
    # print("\n")
    # print(data.current(["EUR_USD", "GBP_USD"], "open"))
    # print("\n")
    # print(data.current(["EUR_USD", "GBP_USD"], ["open", "close"]))
    # print("\n<test history>:")
    # print(data.history("EUR_USD", "open", "D", length=4))
    # print("\n")
    # print(data.history("EUR_USD", ["open", "close"], "D", length=4))
    # print("\n")
    # print(data.history(["EUR_USD", "GBP_USD"], "open", "D", length=4))
    # print("\n")
    # print(data.history(["EUR_USD", "GBP_USD"], ["open", "close"], "D", length=4))
    # print("\n<test start,end and length>:")
    # print(data.history(["EUR_USD", "GBP_USD"], "open", "D", start=datetime(2014, 3, 2), length=5))
    # print("\n")
    # print(data.history(["EUR_USD", "GBP_USD"], "open", "D", end=datetime(2014, 4, 1), length=5))
    # print("\n")
    # print(data.history(["EUR_USD", "GBP_USD"], "open", "D", start=datetime(2014, 3, 2), end=datetime(2014, 4, 1)))
