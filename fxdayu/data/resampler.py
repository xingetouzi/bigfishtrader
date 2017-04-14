# encoding:utf-8
from datetime import timedelta
import pandas as pd


class TimeEdge():
    def __init__(self, edge):
        self.edge = edge
        self.start = None
        self.end = None

    def range(self, end):
        self.end = end
        self.start = self.edge(end)
        return end

    def __call__(self, x):
        self.range(x[-1])
        return pd.DatetimeIndex(
            reversed(map(self.scheduler, reversed(x)))
        )

    def scheduler(self, t):
        if t < self.end and (t > self.start):
            return self.end
        else:
            return self.range(t)


MIN1FACTOR = {'min': 1, 'H': 60, 'D': 240, 'W': 240*5, 'M': 240*5*31}
STOCK_GROUPER = {
    'W': TimeEdge(lambda x: x.replace(hour=0, minute=0)-timedelta(days=x.weekday())),
    'H': TimeEdge(lambda x: x.replace(minute=30, hour=x.hour if x.minute > 30 else x.hour-1) if x.hour < 12
                  else x.replace(minute=0, hour=x.hour if x.minute != 0 else x.hour-1))
    }

RESAMPLE_MAP = {'high': 'max',
                'low': 'min',
                'close': 'last',
                'open': 'first',
                'volume': 'sum'}


class Resampler(object):

    def __init__(self, grouper=STOCK_GROUPER, factor=MIN1FACTOR):
        self.grouper = grouper
        self.factor = factor

    def resample(self, data, how):
        grouper = self.grouper.get(how, None)
        if grouper:
            return data.groupby(grouper).agg(RESAMPLE_MAP)
        else:
            return data.resample(how, label='right', closed='right').agg(RESAMPLE_MAP).dropna()

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

    def expand_length(self, length, frequency):
        n, w = self.f_period(frequency)
        return length*n*self.factor[w]


if __name__ == '__main__':
    from fxdayu.data.handler import MongoHandler
    from datetime import datetime

    mh = MongoHandler(db='CN')
    candle = mh.read('000001.1min', end=datetime(2016, 2, 1))
    rsl = Resampler()

    print rsl.resample(candle, 'H').iloc[30: 20]

