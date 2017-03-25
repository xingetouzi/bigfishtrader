from fxdayu.trader.trader import Trader, Component
from datetime import datetime
from fxdayu.selector.base import Selector, Executor
from fxdayu.router import BACKTESTDEALMODE
from fxdayu.selector.admin import SelectorAdmin
from fxdayu.selector.handler import SelectorHandler
from fxdayu.data.data_support import MarketDataFreq
import pandas as pd


class NameSelector(Selector):

    def start(self, context, data, **others):
        pool = []
        for symbol in data._panels.keys():
            if data.can_trade(symbol):
                pool.append(symbol)
        context.pool = pool

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
            close = data.history(s, fields='close', length=10)
            high, low = close.max(), close.min()
            if (high-low)/(high+low)*2 < 0.1:
                pool.append(s)

        context.pool = pool


class Lower(NameSelector):
    __name__ = 'lower'

    def execute(self, context, data, **others):
        pool = []
        for s in context.pool:
            close = data.history(s, fields='close', length=10)
            if close[-1]/close[0] > 1.05:
                pool.append(s)

        context.pool = pool


class Rebalance(Executor):

    def execute(self, context, data, environment):
        print context.current_time
        for s in context.portfolio.positions:
            if s not in context.pool:
                environment.order_target_percent(environment.symbol(s), 0)

        if len(context.pool):
            pct = 1.0/len(context.pool)
        else:
            return

        for s in context.pool:
            environment.order_target_percent(environment.symbol(s), pct)


if __name__ == '__main__':
    rule = lambda t: t.isoweekday() == 5
    selectors = [Upper(rule, priority=0), Lower(rule, priority=1)]
    executors = [Rebalance(rule)]
    trader = Trader()
    trader['router'].kwargs['deal_model'] = BACKTESTDEALMODE.THIS_BAR_CLOSE
    trader.settings['selector'] = Component('selector', SelectorHandler, (), {})
    mdf = trader.initialize().modules['data']
    codes = [str(code[:-2]) for code in mdf.client.client['HS'].collection_names()]

    trader.run(codes, 'D', datetime(2016, 1, 1), ticker_type='HS',
               params={'selector': {'selectors': selectors, 'executors': executors}})

    print trader.performance.order_details
    # print pd.DataFrame(trader.context.dct['history']).set_index('datetime')

#
# time = datetime(2016, 1, 2)
#
#
# class Context(object):
#
#     dct = {}
#     current_time = time
#
#
# class MDF(MarketDataFreq):
#
#     @property
#     def time(self):
#         global context
#         return context.current_time
#
#
# if __name__ == '__main__':
#     rule = lambda t: t.isoweekday() == 5
#     selectors = [Upper(rule, priority=0), Lower(rule, priority=1)]
#     admin = SelectorAdmin(Upper(rule, priority=0), Lower(rule, priority=1))
#     mdf = MDF(db='HS')
#     context = Context()
#     codes = [str(code[:-2]) for code in mdf.client.db.collection_names()]
#     mdf.init(codes, 'D', datetime(2016, 1, 1), db='HS')
#     for t in mdf.all_time:
#         context.current_time = t
#         admin.on_time(t, context, mdf)
#
#     print pd.DataFrame(context.dct['history']).set_index('datetime')


