from fxdayu.trader.trader import Trader, Component, Optimizer
from fxdayu.trader.packages import DEVELOP_MODE
from datetime import datetime
from fxdayu.selector.base import Selector, Executor, TimeRule
from fxdayu.router import BACKTESTDEALMODE
from fxdayu.selector.handler import SelectorHandler
from fxdayu.data.data_support import MarketDataFreq
import pandas as pd


class Timer(object):
    def __init__(self):
        self._log = [datetime.now()]
        self._count = 0

    def log(self, time):
        self._log.append(time)

    def count(self, x):
        self._count += x

    def __getitem__(self, item):
        if isinstance(item, slice):
            return self._log[item.stop if item.stop else -1] - self._log[item.start if item.start else 0]
        else:
            return self._log[item]


timer = Timer()


class NameSelector(Selector):

    def __init__(self):
        super(NameSelector, self).__init__(TimeRule(5, isoweekday=5))

    def start(self, context, data, **others):
        pool = []
        candle = {}
        for symbol in data._panels.keys():
            if data.can_trade(symbol):
                pool.append(symbol)
                candle[symbol] = data.history(symbol, fields='close', length=10)
        context.pool = pool
        context.candle = candle

    def end(self, context, data, **others):
        context.dct.setdefault('history', []).append({'datetime': context.current_time,
                                                      'pool': list(context.pool),
                                                      'number': len(context.pool)})

    def execute(self, context, data, **others):
        pass


class Upper(NameSelector):
    __name__ = 'upper'

    def execute(self, context, data, **others):
        pool = []
        for s in context.pool:
            close = context.candle[s]
            high, low = close.max(), close.min()
            if (high-low)/(high+low)*2 < 0.1:
                pool.append(s)

        context.pool = pool


class Lower(NameSelector):
    __name__ = 'lower'

    def execute(self, context, data, **others):
        pool = []
        for s in context.pool:
            close = context.candle[s]
            if close[-1]/close[0] > 1.05:
                pool.append(s)

        context.pool = pool


class Rebalance(Executor):

    __name__ = 'Rebalance'

    def __init__(self):
        super(Rebalance, self).__init__(TimeRule(5, isoweekday=5))

    def execute(self, context, data, environment):
        for s in context.portfolio.positions:
            if s not in context.pool:
                environment.order_target_percent(environment.sid(s), 0)

        if len(context.pool):
            pct = 1.0/len(context.pool)
        else:
            return

        for s in context.pool[:10]:
            environment.order_target_percent(environment.symbol(s), pct)
        print context.pool


if __name__ == '__main__':
    selectors = [[Upper()], [Lower()]]
    executors = [Rebalance()]
    # trader = Trader(DEVELOP_MODE)
    # trader['router'].kwargs['deal_model'] = BACKTESTDEALMODE.THIS_BAR_CLOSE
    # trader.settings['selector'] = Component('selector', SelectorHandler, (), {})
    # mdf = trader.initialize().modules['data']
    # codes = [str(code[:6]) for code in mdf.client.client['HS'].collection_names()]
    #
    # trader.run(codes, 'D', datetime(2016, 11, 1), ticker_type='HS',
    #            params={'selector': {'selectors': selectors, 'executors': executors}})
    #
    # print trader.performance.order_details

    opt = Optimizer(DEVELOP_MODE)
    opt['router'].kwargs['deal_model'] = BACKTESTDEALMODE.THIS_BAR_CLOSE
    opt.settings['selector'] = Component('selector', SelectorHandler, (), {})
    codes = [str(code[:6]) for code in MarketDataFreq(db='HS').client.db.collection_names()]

    print opt.run(codes, 'D', datetime(2016, 11, 1), ticker_type='HS',
                  selector={'selectors': selectors, 'executors': [executors]})
