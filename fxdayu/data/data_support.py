from fxdayu.data.handler import MongoHandler
from fxdayu.engine.handler import HandlerCompose
from datetime import datetime, timedelta
import pandas as pd
from collections import Iterable


OANDA_MAPPER = {'open': 'openMid',
                'high': 'highMid',
                'low': 'lowMid',
                'close': 'closeMid'}


class MarketData(object):

    def __init__(self, client=None, host='localhost', port=27017, users={}, db=None, **kwargs):
        self.client = client if client else MongoHandler(host, port, users, db, **kwargs)
        self.read = self.client.read
        self.write = self.client.write
        self.inplace = self.client.inplace
        self.initialized = False
        self.frequency = None
        self._panels = {}
        self.mapper = {}

        self._db = self.client.db

    @property
    def time(self):
        return datetime.now()

    def init(self, symbols, frequency, start=None, end=None, db=None):
        result = self._read_db(symbols, frequency, ['open', 'high', 'low', 'close', 'volume'], start, end, None, db)
        if isinstance(result, pd.Panel):
            self._panels[frequency] = result
        elif isinstance(result, pd.DataFrame):
            self._panels[frequency] = pd.Panel.from_dict({symbols[0]: result})
        self.frequency = frequency
        self._db = db if db else self.client.db
        self.initialized = True

    def current(self, symbol=None):
        panel = self._panels[self.frequency]

        try:
            if symbol is None:
                symbol = list(panel.items)
                if len(symbol) == 1:
                    symbol = symbol[0]
            if not isinstance(symbol, (tuple, list)):
                if symbol not in panel.items:
                    raise KeyError()
                else:
                    index = self.search_axis(panel.major_axis, self.time)
                    return panel[symbol].iloc[index]
            if isinstance(symbol, list):
                for s in symbol:
                    if s not in panel.items:
                        raise KeyError()

            index = self.search_axis(panel.major_axis, self.time)
            return panel[symbol].iloc[:, index]
        except KeyError:
            return self._read_db(symbol, self.frequency, None, None, self.time, 1, self._db)[symbol].iloc[:, -1]

    def history(self, symbol=None, frequency=None, fields=None, start=None, end=None, length=None, db=None):
        if frequency is None:
            frequency = self.frequency
        try:
            if symbol is None:
                symbol = list(self._panels[frequency].items)
            result = self._read_panel(symbol, frequency, fields, start, end, length)
            if self.match(result, symbol, length):
                return result
            else:
                raise KeyError()
        except KeyError:
            if symbol is None:
                symbol = list(self._panels[self.frequency].items())
            if end is None:
                end = self.time
            result = self._read_db(symbol, frequency, fields, start, end, length, db if db else self._db)
            if isinstance(result, pd.Panel) and len(result.minor_axis) == 1:
                return result.iloc[:, :, 0]
            else:
                return result

    def _read_panel(self, symbol, frequency, fields, start, end, length):
        panel = self._panels[frequency]
        major_slice = self.major_slice(panel.major_axis, self.time, start, end, length)
        result = self._find(panel, symbol, major_slice, fields if fields else slice(None))
        return result

    def _read_db(self, symbols, frequency, fields, start, end, length, db):
        symbols = [symbols] if isinstance(symbols, str) else symbols
        if fields is None:
            fields = ['datetime', 'open', 'high', 'low', 'close', 'volume']
        elif isinstance(fields, str):
            fields = ['datetime', fields]
        elif 'datetime' not in fields:
            fields.append('datetime')

        mapper = self.mapper.get(db, {})
        trans_map = {item[1]: item[0] for item in mapper.items()}
        result = {}
        for symbol in symbols:
            result[symbol] = self.client.read(
                '.'.join((symbol, frequency)),
                db, 'datetime', start, end, length,
                projection=fields
            )

        if len(result) == 1:
            frame = result[symbols[0]]
            if len(frame.columns) > 1:
                return frame.rename_axis(trans_map, axis=1)
            else:
                return frame[frame.columns[0]]
        elif len(result) > 1:
            return pd.Panel(result).rename_axis(trans_map, axis='minor_axis')

        return pd.Panel(result)

    @staticmethod
    def match(result, items, length):
        if length:
            if isinstance(result, (pd.DataFrame, pd.Series)):
                if len(result) == length:
                    return True
                else:
                    return False
            elif isinstance(result, pd.Panel):
                if (len(items) == len(result.items)) and (len(result.major_axis) == length):
                    return True
                else:
                    return False
            else:
                return False
        else:
            return True

    @staticmethod
    def _find(panel, item, major, minor):
        if item is not None:
            if isinstance(item, str):
                frame = panel[item]
                return frame[minor].iloc[major]
            else:
                panel = panel[item]
                return panel[:, major, minor]
        else:
            if len(panel.items) == 1:
                return panel[panel.items[0]][minor].iloc[major]
            else:
                return panel[:, major, minor]

    @staticmethod
    def search_axis(axis, time):
        index = axis.searchsorted(time)
        if index < len(axis):
            if axis[index] <= time:
                return index
            else:
                return index - 1
        else:
            return len(axis) - 1

    def major_slice(self, axis, now, start, end, length):
        last = self.search_axis(axis, now)

        if end:
            end = self.search_axis(axis, end)
            if end > last:
                end = last
        else:
            end = last

        if start:
            start = axis.searchsorted(pd.to_datetime(start))
            if length:
                if start + length <= end+1:
                    return slice(start, start+length)
                else:
                    return slice(start, end+1)
            else:
                return slice(start, end+1)
        elif length:
            end += 1
            if end < length:
                raise KeyError()
            return slice(end-length, end)
        else:
            return slice(0, end+1)

    @property
    def all_time(self):
        return self._panels[self.frequency].major_axis

    def can_trade(self, symbol):
        current = self.current(symbol)
        if current.name == self.time and current.volume > 0:
            return True
        else:
            return False


class DataSupport(HandlerCompose, MarketData):

    def __init__(self, engine, context, client=None, host='localhost', port=27017, users={}, db=None, **kwargs):
        super(DataSupport, self).__init__(engine)
        MarketData.__init__(self, client, host, port, users, db, **kwargs)
        self.context = context

    @property
    def time(self):
        return self.context.current_time


SAMPLE_MAP = {'open': 'first',
              'high': 'max',
              'low': 'min',
              'close': 'last',
              'volume': 'sum'}


def function(x):
    # print list(reversed(x.values))
    return x.values


class MarketDataFreq(MarketData):

    fields = list(SAMPLE_MAP.keys())

    def __init__(self, client=None, host='localhost', port=27017, users={}, db=None, **kwargs):
        super(MarketDataFreq, self).__init__(client, host, port, users, db, **kwargs)
        self.sample_factor = {'min': 1, 'H': 60, 'D': 240, 'W': 240*5, 'M': 240*5*31}
        self.grouper = {'W': lambda x: x.replace(hour=15, minute=0, second=0) + timedelta(5-x.isoweekday()),
                        'H': lambda x: (x.replace(hour=x.hour+1, minute=0) if x.minute != 0 else x) if x.hour > 12
                        else x.replace(hour=x.hour+1, minute=30) if x.minute > 30 else x.replace(minute=30)}

    def init(self, symbols, frequency, start=None, end=None, db=None):
        if isinstance(symbols, str):
            self._panels[symbols] = self._read_db(symbols, frequency,
                                                  ['open', 'high', 'low', 'close', 'volume'],
                                                  start, end, None, db)

        elif isinstance(symbols, Iterable):
            for symbol in symbols:
                self._panels[symbol] = self._read_db(symbol, frequency,
                                                     ['open', 'high', 'low', 'close', 'volume'],
                                                     start, end, None, db)
        self.frequency = frequency
        self.initialized = True
        self._db = db

    def _read_db(self, symbol, frequency, fields, start, end, length, db):
        if fields is None:
            fields = ['datetime', 'open', 'high', 'low', 'close', 'volume']
        elif isinstance(fields, str):
            fields = ['datetime', fields]
        elif 'datetime' not in fields:
            fields.append('datetime')

        mapper = self.mapper.get(db, {})
        trans_map = {item[1]: item[0] for item in mapper.items()}

        result = self.client.read(
            '.'.join((symbol, frequency)),
            db, 'datetime', start, end, length,
            projection=fields
        ).rename_axis(trans_map, axis=1)

        return result

    def current(self, symbol=None):
        return self.history(symbol, length=1)

    def history(self, symbol=None, frequency=None, fields=None, start=None, end=None, length=None, db=None):
        if symbol is None:
            symbol = self._panels.keys()

        if fields is None:
            fields = self.fields

        if frequency is None or (frequency == self.frequency):
            if isinstance(symbol, str):
                return self._find_panel(symbol, fields, start, end, length)
            else:
                return self._dimension({s: self._find_panel(s, fields, start, end, length) for s in symbol},
                                       length, fields)
        else:
            n, w = self.f_period(frequency)
            grouper = self.grouper.get(w, None)
            if isinstance(symbol, str):
                return self.resample(symbol, frequency, fields, start, end, length, n, w, grouper)
            else:
                return self._dimension(
                    {s: self.resample(s, frequency, fields, start, end, length, n, w, grouper) for s in symbol},
                    length, fields
                )

    @staticmethod
    def _dimension(dct, length, fields):
        if length == 1:
            if isinstance(fields, str):
                return pd.Series(dct)
            else:
                return pd.DataFrame(dct)
        elif isinstance(fields, str):
            return pd.DataFrame(dct)
        else:
            return pd.Panel(dct)

    def major_slice(self, axis, now, start, end, length):
        last = self.search_axis(axis, now)

        if end:
            end = self.search_axis(axis, end)
            if end > last:
                end = last
        else:
            end = last

        if length:
            if length == 1:
                return end
            elif start:
                if start + length <= end+1:
                    return slice(start, start+length)
                else:
                    return slice(start, end+1)
            else:
                end += 1
                if end < length:
                    raise KeyError()
                return slice(end-length, end)
        elif start:
            return slice(start, end+1)
        else:
            return slice(0, end+1)

    def _find_panel(self, symbol, fields, start, end, length):
        try:
            frame = self._panels[symbol]
            time_slice = self.major_slice(frame.index, self.time, start, end, length)
            return frame.iloc[time_slice][fields]
        except KeyError:
            if isinstance(fields, str):
                result = self._read_db(symbol, self.frequency, fields, start, end, length, self._db)[fields]
            else:
                result = self._read_db(symbol, self.frequency, fields, start, end, length, self._db)

            return result if length != 1 else result.iloc[0]

    def resample(self, symbol, frequency, fields, start, end, length, n, w, grouper):
        frame = self._find_panel(symbol, fields, start, end, length*n*self.sample_factor[w] if length else None)

        if grouper is not None:
            return frame.groupby(grouper).agg({'high': 'max',
                                               'low': 'min',
                                               'close': 'last',
                                               'open': 'first',
                                               'volume': 'sum'})
        else:
            return frame.resample(frequency).agg({'high': 'max',
                                                  'low': 'min',
                                                  'close': 'last',
                                                  'open': 'first',
                                                  'volume': 'sum'})

    def hour_rs(self, symbol, frequency, fields, start, end, length):
        pass

    @staticmethod
    def week_rs(frame, frequency):
        def grouper(x):
            return x.replace(hour=15, minute=0, second=0) + timedelta(5-x.isoweekday())

        return frame.groupby(grouper).agg({'high': 'max',
                                           'low': 'min',
                                           'close': 'last',
                                           'open': 'first',
                                           'volume': 'sum'})

    @staticmethod
    def regular_rs(frame, frequency):
        return frame.resample(frequency).agg({'high': 'max',
                                              'low': 'min',
                                              'close': 'last',
                                              'open': 'first',
                                              'volume': 'sum'})

    @staticmethod
    def f_period(frequency):
        n = ''
        w = ''
        for f in frequency:
            if f.isdigit():
                n += f
            else:
                w += f

        return (int(n) if len(n) else 1), w

    @property
    def all_time(self):
        all_ = []
        for item in self._panels.items():
            all_.extend(filter(lambda x: x not in all_, item[1].index))

        return sorted(all_)

    def can_trade(self, symbol):
        try:
            return self.time in self._panels[symbol].index
        except KeyError:
            try:
                data = self.client.read('.'.join((symbol, self.frequency)), self._db, end=self.time, length=1)
                if data.index[0] == self.time:
                    return True
            except KeyError:
                return False

            return False


if __name__ == '__main__':
    ds = MarketDataFreq(db='HS')
    ds.init(['000001', '000009'], 'D', start=datetime(2016, 1, 1), db='HS')
    ds.sample_factor['W'] = 5
    print ds.history('000001', 'W', length=4)