from fxdayu.trader.trader import Trader, Optimizer
from fxdayu.trader.component import Component
from fxdayu.trader.packages import DEVELOP_MODE
from datetime import datetime
from fxdayu.router import BACKTESTDEALMODE
from fxdayu.selector.selector import IntersectionAdmin, selector_wrapper, Selector, TimeRule
from fxdayu.selector.executor import EqualWeightAdmin, executor_wrapper, Executor
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


class Base(Selector):
    def __init__(self, priority=0):
        super(Base, self).__init__(TimeRule(5, isoweekday=5), priority)

    def start(self, pool, context, data):
        context.candle = {}
        for code in pool:
            context.candle[code] = data.history(code, length=10, fields='close')


class Upper(Base):

    def execute(self, pool, context, data):
        target = []
        for code in pool:
            candle = context.candle[code]
            if candle[-1] / candle.min() > 1.05:
                target.append(code)

        return target


class Rebalance(Executor):

    def execute(self, pool, context, data):
        target = []
        for code in pool:
            close = data.history(code, fields='close', length=5)
            if close[-1]/close[0] > 1.2:
                target.append(code)

        print context.current_time, target

        if len(pool):
            weight = 1.0/len(pool)
            return {c: weight for c in target}
        else:
            return {}


if __name__ == '__main__':

    trader = Trader(DEVELOP_MODE)
    trader['router'].kwargs['deal_model'] = BACKTESTDEALMODE.THIS_BAR_CLOSE
    trader.settings['selector'] = Component(
        'selector', selector_wrapper(topic='bar.close', priority=100)(IntersectionAdmin), (Upper(),), {}
    )
    trader.settings['executor'] = Component(
        'executor', executor_wrapper(topic='bar.close', priority=99)(EqualWeightAdmin), (Rebalance(),), {}
    )
    mdf = trader.initialize().modules['data']
    codes = [str(code[:6]) for code in mdf.client.client['HS'].collection_names()]

    trader.run(codes, 'D', datetime(2016, 1, 1), ticker_type='HS')

    print trader.performance.order_details

    # opt = Optimizer(DEVELOP_MODE)
    # opt['router'].kwargs['deal_model'] = BACKTESTDEALMODE.THIS_BAR_CLOSE
    # opt.settings['selector'] = Component('selector', SelectorHandler, (), {})
    # codes = [str(code[:6]) for code in MarketDataFreq(db='HS').client.db.collection_names()]
    #
    # print opt.run(codes, 'D', datetime(2016, 11, 1), ticker_type='HS',
    #               selector={'selectors': selectors, 'executors': [executors]})
