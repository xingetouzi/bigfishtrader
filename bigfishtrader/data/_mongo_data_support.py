# encoding: utf-8

from datetime import timedelta, datetime
from collections import OrderedDict

import pandas as pd
from dictproxyhack import dictproxy

from bigfishtrader.event import TimeEvent, ExitEvent
from bigfishtrader.data.mongo_support import connect
from bigfishtrader.data.base import AbstractDataSupport
from bigfishtrader.data.cache import MemoryCacheProxy
from bigfishtrader.data.support import PanelDataSupport, MultiPanelData

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

    def history(self, tickers, frequency, fields=None, start=None, end=None, length=None):
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
    def __init__(self, context=None, event_queue=None, host='localhost', port=27017, users={}, db=None, **kwargs):
        super(MultiDataSupport, self).__init__()
        self._db = db
        self._client = self.connect(host, port, users, **kwargs)
        self._panel_data = MultiPanelData(context)
        self._initialized = False
        self.tickers = {}
        self.event_queue = event_queue

        self.mapper = {}
        self.bar_general = ['open', 'high', 'low', 'close', 'volume', 'datetime']
        self.set_bar_map(
            'Oanda',
            ("open", "openMid"),
            ("high", "highMid"),
            ("low", "lowMid"),
            ("close", "closeMid"),
        )

    def init(self, tickers, frequency, start=None, end=None, ticker_type=None):
        """
        初始化，包括设置主品种和时间周期

        :param tickers: str or list
        :param frequency: str
        :param start: datetime
        :param end: datetime
        :param ticker_type: str, MongoDB database name
        :return:
        """

        self._initialized = False
        self._db = ticker_type
        self.subscribe(tickers, frequency, start, end, ticker_type)
        self._initialized = True
        if self.event_queue:
            self.put_time_events(self.event_queue)

    def subscribe(self, tickers, frequency, start=None, end=None, ticker_type=None):
        """
        回测时获取数据，如果调用时未初始化，会将此次调用视为初始化

        :param tickers: str or list
        :param frequency: str
        :param start: datetime
        :param end: datetime
        :param ticker_type: str, MongoDB database name
        :return:
        """

        frames = {}

        if isinstance(tickers, str):
            tickers = [tickers]
        for ticker in tickers:
            frames[ticker] = self._subscribe(ticker, frequency, start, end, ticker_type)

        if self._initialized:
            self._panel_data.insert(frequency, **frames)
        else:
            self._panel_data.init(frequency, **frames)
            self._db = ticker_type
            self._initialized = True

    def _subscribe(self, ticker, frequency, start=None, end=None, ticker_type=None):
        """
        被subscribe()调用，获取其请求的数据

        :param ticker: str
        :param frequency: str
        :param start: datetime
        :param end: datetime
        :param ticker_type: str, MongoDB database name
        :return:
        """

        if ticker_type is None:
            ticker_type = self._db
        frame = self.history_db(ticker, frequency, start=start, end=end, ticker_type=ticker_type)
        self.tickers.setdefault(ticker, []).append(frequency)
        return frame

    def cancel_subscribe(self, tickers, frequency):
        if isinstance(tickers, str):
            self._panel_data.drop(frequency, tickers)
            self.tickers[frequency].remove(tickers)
        elif isinstance(tickers, list):
            self._panel_data.drop(frequency, *tickers)
            f = self.tickers[frequency]
            for ticker in tickers:
                f.remove(ticker)

    def current(self, tickers, fields=None, **kwargs):
        """
        获取最新数据

        :param tickers: str or list
        :param fields: str or list, [close, open, high, low, volume]
        :return: float, series or DataFrame
        """
        try:
            return self._panel_data.current(tickers, fields)
        except KeyError:
            f = self._panel_data.frequency
            t = self.current_time
            if isinstance(tickers, str):
                return self.history_db(
                    tickers, f, end=t, length=1, **kwargs
                )
            elif isinstance(tickers, list):
                return pd.DataFrame(
                    dict(map(
                        lambda ticker: (ticker, self.history_db(ticker, f, end=t, length=1, **kwargs)),
                        tickers
                    ))
                )

    def history(
            self, tickers, frequency, fields=None,
            start=None, end=None, length=None
    ):
        """
        获取历史数据

        :param tickers: str or list
        :param frequency: str
        :param fields: str or list, [close, open, high, low, volume]
        :param start: datetime
        :param end: datetime
        :param length: int
        :return: float, series or DataFrame
        """
        if end and end > self._panel_data.context.current_time:
            end = self._panel_data.context.current_time

        try:
            data = self._panel_data.history(
                tickers, frequency, fields,
                start, end, length
            )
            if length:
                if not self.match_length(data, length):
                    raise KeyError()

            return data

        except KeyError:
            if not end:
                end = self.current_time

            if isinstance(tickers, str):
                return self.history_db(tickers, frequency, fields, start, end, length)
            elif isinstance(tickers, list):
                frames = {}
                for ticker in tickers:
                    frames[ticker] = self.history_db(ticker, frequency, fields, start, end, length)
                return pd.Panel.from_dict(frames)

    @staticmethod
    def match_length(frame, length):
        if isinstance(frame, (pd.DataFrame, pd.Series)):
            if len(frame.dropna(how='all')) != length:
                return False
            else:
                return True
        elif isinstance(frame, pd.Panel):
            if len(frame.major_axis) != length:
                return False
            else:
                return True
        else:
            return False

    def put_time_events(self, queue):
        for time_ in self._panel_data.major_axis:
            queue.put(TimeEvent(time_, ''))
        queue.put(ExitEvent())

    def put_limit_time(self, queue, topic, **condition):
        for time_ in self._panel_data.major_axis:
            if self._time_match(time_, **condition):
                queue.put(TimeEvent(time_, topic))

    @staticmethod
    def _time_match(time, **condition):
        import types
        for key, value in condition.items():
            attr = getattr(time, key)
            if isinstance(attr, (
                    types.MethodType, types.FunctionType, types.BuiltinMethodType, types.BuiltinFunctionType
            )):
                attr = attr()
            if attr != value:
                return False

        return True

    def history_db(self, ticker, frequency, fields=None, start=None, end=None, length=None, ticker_type=None):
        """
        获取MongoDB中的历史行情数据，该方法被history()和_subscribe()调用，也可由用户直接调用。

        :param ticker: str
        :param frequency: str
        :param fields: str or list, [close, open, high, low, volume]
        :param start: datetime
        :param end: datetime
        :param length: int
        :param ticker_type:
        :return:
        """
        dt_filter = {}
        col_name = '.'.join((ticker, frequency))
        if start:
            dt_filter['$gte'] = start
        if end:
            dt_filter['$lte'] = end

        filter_ = {'datetime': dt_filter} if len(dt_filter) else {}

        ticker_type = self._db if not ticker_type else ticker_type
        fields, mapper, columns = self.key_map_transfer(fields, ticker_type)

        if not length:
            frame = self._from_mongo(
                ticker_type, col_name, filter_, fields, sort=[(fields[-1], 1)]
            )
        else:
            if start:
                frame = self._from_mongo(
                    ticker_type, col_name, filter_, fields,
                    limit=length, sort=[(fields[-1], 1)]
                )
            else:
                frame = self._from_mongo(
                    ticker_type, col_name, filter_, fields,
                    limit=length, sort=[(fields[-1], -1)]
                ).iloc[::-1]

        frame = frame.rename_axis(mapper, 1).reindex(columns=columns)
        frame.index = frame.pop('datetime')
        return frame if len(frame) != 1 else frame.iloc[0]

    def key_map_transfer(self, fields, ticker_type):
        if fields:
            fields = fields if isinstance(fields, list) else [fields]
            fields.append('datetime')
        else:
            fields = self.bar_general

        mapper = self.mapper.get(ticker_type, None)
        if mapper:
            positive, negative = mapper
            return [positive.get(field, field) for field in fields], negative, fields
        else:
            return fields, {}, fields

    def set_bar_map(self, name, *mapper, **mappers):
        """

        :param name: str, mongo database name
        :param mapper: tuple, 格式转换方式: ('close', 'closeMid'), ('open', 'openMid') ...

        :return:
        """

        positive = dict(mapper, **mappers)
        negative = dict()
        for item in positive.items():
            negative[item[1]] = item[0]
        self.mapper[name] = [positive, negative]

    def _from_mongo(self, db, col_name, filter_, projection=None, *args, **kwargs):
        """
        从MongoDB中读取数据整理成DataFrame返回

        :param db: str
        :param col_name: str
        :param filter_: dict
        :param projection: list
        :param args:
        :param kwargs:
        :return: DataFrame
        """
        frame = pd.DataFrame(
            list(
                self._client[db][col_name].find(filter_, projection, *args, **kwargs)
            )
        )
        try:
            frame.pop('_id')
        except KeyError:
            raise KeyError("Unable to find required data in %s.%s, please check your MongoDB" % (db, col_name))

        return frame

    @property
    def current_time(self):
        return self._panel_data.current_time

    def can_trade(self, ticker):
        current = self.current(ticker)
        if current.name == self.current_time and current.close == current.close:
            return True
        else:
            return False
