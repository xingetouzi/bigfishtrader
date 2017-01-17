# encoding: utf-8

import time
from bisect import bisect
from functools import wraps
from collections import deque
from datetime import datetime

from bigfishtrader.settings import CACHE_BACKEND, DATABASE
from vedis import Vedis
from redis import Redis
import pandas as pd

_BAR_FIELDS = ["datetime", "open", "high", "low", "close", "volume"]


def get_ticker_bar_data_from_df(df, timeframe, now=None, backtrack=1):
    if now is None:
        end_index = None
        start_index = -backtrack
    else:
        end_index = df["datetime"].searchsort(now, side="R")[0]
        start_index = end_index - backtrack
    return df[start_index:end_index]


class MemoryCacheProxy(object):
    def __init__(self, db, max_len):
        """

        Args:
            db: db interface
            max_len: max cache len

        Returns:

        """
        self._max_len = max_len
        self._cache = {}
        self._db = db

    def get_ticker_bar_data(self, ticker, timeframe, now, backtrack=1):
        if ticker not in self._cache:
            self._cache[ticker] = {
                "last": None,
                "datetime": deque(maxlen=self._max_len),
                "open": deque(maxlen=self._max_len),
                "high": deque(maxlen=self._max_len),
                "low": deque(maxlen=self._max_len),
                "close": deque(maxlen=self._max_len),
            }
        last = self._cache[ticker]["last"]
        dct = self._cache[ticker]
        df = self._db.get_ticker_bar_data(ticker, timeframe, last, now, self._max_len)
        for field in _BAR_FIELDS:
            dct[field].appendright(df[field])
        self._cache[ticker]["last"] = now
        return get_ticker_bar_data_from_df(pd.DataFrame(dct, columns=_BAR_FIELDS),
                                           timeframe, None, backtrack)


class RedisCacheProxy(object):
    def __init__(self, backend="Vedis"):
        self._backend = backend
        self._conn = None
        self.get_connection()

    def get_connection(self):
        if self._backend == "Vedis":
            self._conn = Vedis(":mem:")

    def _get_hash(self, key):
        if self._backend == "Vedis":
            return self._conn.Hash(key)

    def _get_list(self, key):
        if self._backend == "Vedis":
            return self._conn.List(key)

    @staticmethod
    def _get_timestamp(dt):
        return int(time.mktime(dt.timetuple()))

    def get_ticker_bar_data(self, func):
        @wraps(func)
        def wrapper(ticker, timeframe, start, end):
            prefix = ticker + "." + timeframe
            dct = self._get_hash(prefix + ".index")
            si = dct[self._get_timestamp(start)]
            ei = dct[self._get_timestamp(end)]
            if si and ei:
                si = int(si)
                ei = int(ei)
                df = pd.DataFrame(columns=_BAR_FIELDS)
                for field in _BAR_FIELDS:
                    df[field] = [self._get_list(prefix + "." + field)[index] for index in range(si, ei + 1)]
            else:
                df = func(ticker, timeframe, start, end)
                dt = df["datetime"].apply(lambda x: self._get_timestamp(x))
                temp = pd.Series(df.index.astype(str), index=dt.astype(str))
                try:
                    del self._conn[prefix + ".index"]
                except KeyError:
                    pass
                dct = self._get_hash(prefix + ".index")
                for key, value in temp.iteritems():
                    dct[key] = value
                for field in _BAR_FIELDS:
                    try:
                        del self._conn[prefix + "." + field]
                    except KeyError:
                        pass
                    lst = self._get_list(prefix + "." + field)
                    lst.extend(list(df[field].values))
            return df

        return wrapper


if __name__ == "__main__":
    from datetime import datetime, timedelta

    start = datetime(2015, 1, 1)
    dts = [start + timedelta(days=x) for x in range(366)]
    end = start + timedelta(days=x)
    bar_data = {
        "datetime": dts,
        "open": [2, 7] * (len(dts) / 2),
        "high": [4, 9] * (len(dts) / 2),
        "low": [1, 6] * (len(dts) / 2),
        "close": [3, 8] * (len(dts) / 2),
        "volume": [100, 200] * (len(dts) / 2),
    }
    df = pd.DataFrame(data=bar_data)
    proxy = RedisCacheProxy()


    def get_bar_data(ticker, timeframe, start, end):
        return df


    proxy_get_bar_data = proxy.get_ticker_bar_data(get_bar_data)

    print(proxy_get_bar_data("EURUSD", "D", start, end))
    st = time.time()
    print(proxy_get_bar_data("EURUSD", "D", start, end))
    for i in range(100):
        proxy_get_bar_data("EURUSD", "D", start, end)
    print(time.time() - st)
    st = time.time()
    for i in range(100):
        get_bar_data("EURUSD", "D", start, end)
    print(time.time() - st)
