from fxdayu.data.handler import MongoHandler, RedisHandler
from fxdayu.engine.handler import HandlerCompose
from threading import Thread
from fxdayu.data.resampler import Resampler
from datetime import datetime, date, time
import pandas as pd


def reshape(data):
    if isinstance(data, pd.DataFrame):
        if len(data) == 1:
            return data.iloc[0]
        elif len(data.columns):
            return data.iloc[:, 0]
        else:
            return data
    elif isinstance(data, pd.Panel):
        if len(data.major_axis) == 1:
            return data.iloc[:, 0, :]
        elif len(data.minor_axis) == 1:
            return data.iloc[:, :, 0]
        else:
            return data
    else:
        return data


def shaper(function):
    def shaped(*args, **kwargs):
        return reshape(function(*args, **kwargs))
    return shaped


class ActiveStockData(object):

    BOTH = 0
    EXTERNAL = 1
    CACHE = 2
    FIELDS = ['open', 'high', 'low', 'close', 'volume']

    def __init__(self, cache=None, external=None):
        if isinstance(cache, dict):
            self.cache = RedisHandler(**cache)
        elif isinstance(cache, RedisHandler):
            self.cache = cache
        else:
            self.cache = RedisHandler()

        if isinstance(external, dict):
            self.external = MongoHandler(**external)
        elif isinstance(external, MongoHandler):
            self.external = external
        else:
            self.external = MongoHandler()

        self.resampler = Resampler()
        self.today = datetime.combine(date.today(), time())
        self.reader = {self.BOTH: self._read_both,
                       self.EXTERNAL: self._read_external,
                       self.CACHE: self._read_cache}
        self._listen = None

    def _read_both(self, symbol, fields, start, end, length):
        cache = self._read_cache(symbol, fields, start, end, length)
        external = self._read_external(symbol, fields, start, end, length)
        return pd.concat((external, cache))

    def _read_cache(self, symbol, fields, start, end, length):
        return self.cache.read(symbol, start=start, end=end, length=length, fields=fields)

    def _read_external(self, symbol, fields, start, end, length):
        if 'datetime' not in fields:
            f = ['datetime']
            f.extend(fields)
            return self.external.read(symbol, start=start, end=end, length=length, projection=f)
        else:
            return self.external.read(symbol, start=start, end=end, length=length, projection=fields)

    @shaper
    def history(self, symbols, frequency=None, fields=None, start=None, end=None, length=None):
        if not fields:
            fields = self.FIELDS

        if frequency:
            if length:
                length = self.resampler.expand_length(length, frequency)
            if isinstance(symbols, str):
                return self.resampler.resample(
                    self._history(symbols, fields, start, end, length),
                    frequency
                )
            elif isinstance(symbols, (list, tuple)):
                return pd.Panel.from_dict({symbol: self.resampler.resample(
                    self._history(symbols, fields, start, end, length),
                    frequency
                ) for symbol in symbols})
            else:
                return self.resampler.resample(
                    self._history(symbols, fields, start, end, length),
                    frequency
                )
        else:
            if isinstance(symbols, str):
                return self._history(symbols, fields, start, end, length)
            elif isinstance(symbols, (list, tuple)):
                return pd.Panel.from_dict(
                    {symbol: self._history(symbol, fields, start, end, length) for symbol in symbols}
                )
            else:
                return self._history(symbols, fields, start, end, length)

    def _history(self, symbol, fields=None, start=None, end=None, length=None):
        how, reconsider = self.range(start, end, length)
        data = self.reader[how](symbol, fields, start, end, length)
        if reconsider:
            if len(data) < length:
                if how == self.EXTERNAL:
                    cache = self._read_cache(symbol, fields, start, end, length-len(data))
                    return pd.concat([data, cache])
                elif how == self.CACHE:
                    external = self._read_external(symbol, fields, start, end, length-len(data))
                    return pd.concat([external, data])
                else:
                    return data
            else:
                return data
        else:
            return data

    def current(self, symbols, frequency=None):
        return self.history(symbols, frequency, length=1)

    def range(self, start, end, length):
        if end:
            if end < self.today:
                return self.EXTERNAL, False
            else:
                if start:
                    if start > self.today:
                        return self.CACHE, False
                    else:
                        return self.BOTH, False
                elif length:
                    return self.CACHE, True
                else:
                    return self.BOTH, False
        elif start:
            if start < self.today:
                if length:
                    return self.EXTERNAL, True
                else:
                    return self.BOTH, False
            else:
                if length:
                    return self.CACHE, False
                else:
                    return self.CACHE, False
        else:
            return self.range(start, datetime.now(), length)

    def subscribe(self, *args, **kwargs):
        self.cache.subscribe(*args, **kwargs)

    def listen(self, function):
        self._listen = Thread(target=self.cache.listen, args=(function,))
        self._listen.start()


class ActiveDataSupport(HandlerCompose, ActiveStockData):
    def __init__(self, engine, *args, **kwargs):
        super(ActiveDataSupport, self).__init__(engine)
        ActiveStockData.__init__(self, **kwargs)


if __name__ == '__main__':
    mh = MongoHandler('192.168.0.103', 30000, db='TradeStock')

    asd = ActiveStockData(external=mh)
    print asd.current(['sh600036', 'sh600000'])