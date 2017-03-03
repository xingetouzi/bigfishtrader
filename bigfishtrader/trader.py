# encoding:utf-8
try:
    from Queue import PriorityQueue
except ImportError:
    from queue import PriorityQueue
from collections import OrderedDict
from bigfishtrader.event import EVENTS
import pandas as pd


OUTPUT_COLUMN_MAP = {
    'equity': OrderedDict([('time', '时间'), ('equity', '净值')]),
    'transaction': OrderedDict([('order_id', '报单编号'),
                               ('security', '合约'),
                               ('side', '买卖'),
                               ('action', '开平'),
                               ('status', '报单状态'),
                               ('reqPrice', '报单价格'),
                               ('reqQuantity', '报单数'),
                               ('ufQuantity', '未成交数'),
                               ('quantity', '成交数'),
                               ('reqTime', '报单时间'),
                               ('time', '最后成交时间'),
                               ('price', '成交均价'),
                               ('exchange', '交易所')])
}


def output(equity, transactions, path):
    from pandas import ExcelWriter
    writer = ExcelWriter(path, encoding='utf-8')

    eqt = equity.rename_axis(OUTPUT_COLUMN_MAP['equity'], 1).reindex(
        columns=OUTPUT_COLUMN_MAP['equity'].values()
    )
    eqt.to_excel(writer, '净值', index=False)

    trans = transactions.rename_axis(OUTPUT_COLUMN_MAP['transaction'], 1).reindex(
        columns=OUTPUT_COLUMN_MAP['transaction'].values()
    )
    trans.to_excel(writer, '交易', index=False)

    writer.save()


class Component(object):
    __slots__ = ["name", "constructor", "args", "kwargs"]

    class Lazy(object):
        def __init__(self, name):
            self.name = name

    def __init__(self, name, constructor, args, kwargs):
        self.name = name
        self.constructor = constructor
        self.args = args
        self.kwargs = kwargs

    def get(self, item):
        return self.Lazy(item)


class Trader(object):
    """
    用于自由组织模块并进行回测
    """

    def __init__(self, settings=None):
        self.settings = settings
        self.models = {}
        if not self.settings:
            self.init_settings()
        self.initialized = False

    def init_settings(self):
        from bigfishtrader.practice import basic
        self.settings = basic

    def __getitem__(self, item):
        return self.settings[item]

    def __setitem__(self, key, value):
        if isinstance(value, Component):
            self.settings[key] = value
        elif isinstance(value, tuple):
            self.settings[key] = Component(*value)
        else:
            raise TypeError("settings's value should be Component or tuple, not: %s" % type(value))

    def _register_models(self):
        engine = self.models['engine']
        for name, model in self.models.items():
            if name not in {"engine", "event_queue"}:
                model.register(engine)

    def initialize(self):
        """
        """
        for name, co in self.settings.items():
            args = [self.models[para.name] if isinstance(para, Component.Lazy) else para for para in co.args]
            kwargs = {key: self.models[para.name] if isinstance(para, Component.Lazy) else para for key, para in
                      co.kwargs.items()}
            self.models[name] = co.constructor(*args, **kwargs)
        self._register_models()
        self.models["context"].link(**self.models)
        self.initialized = True
        return self

    def back_test(self, strategy, tickers, frequency, start=None, end=None, ticker_type=None, params={}, out=True):
        """
        运行一个策略, 完成后返回一个账户对象

        :param strategy: 策略模块
        :param params: 需要修改的策略参数
        :return: Portfolio
        """
        if not self.initialized:
            self.initialize()

        context, data, engine = self.models['context'], self.models['data'], self.models['engine']

        data.init(tickers, frequency, start, end, ticker_type)
        context.tickers = tickers

        def on_time(event, kwargs=None):
            strategy.handle_data(context, data)

        self.models['engine'].register(on_time, EVENTS.TIME, topic='.', priority=100)

        for key, value in params.items():
            setattr(strategy, key, value)

        strategy.initialize(context, data)
        engine.start()
        engine.join()
        engine.stop()

        self.initialized = False
        if out:
            from datetime import datetime
            p = self.models['portfolio']
            output(
                pd.DataFrame(p.history_eqt),
                pd.DataFrame([transaction.to_dict() for transaction in p.transactions]),
                '%s&%s&%s.xls' % (strategy.__name__, datetime.now().strftime('%Y-%m-%d-%H-%M-%S'),
                                  '&'.join(map(lambda (key, value): key+'_'+str(value), params.items())))
            )
        # self.output()

        return self.models['portfolio']

    def output(self, path='back_test.xls'):
        from bigfishtrader.performance import WindowFactorPerformance, DataFrameExtended
        from pandas import ExcelWriter, Series, DataFrame

        p = self.models['portfolio']

        eqt = pd.DataFrame(
            p.history_eqt
        )
        eqt.index = eqt['time']
        eqt = eqt.rename_axis(OUTPUT_COLUMN_MAP['equity'], 1).reindex(
            columns=OUTPUT_COLUMN_MAP['equity'].values()
        )

        trans = pd.DataFrame(
            [transaction.to_dict() for transaction in p.transactions]
        ).rename_axis(OUTPUT_COLUMN_MAP['transaction'], 1).reindex(
            columns=OUTPUT_COLUMN_MAP['transaction'].values()
        )

        wfp = WindowFactorPerformance()
        wfp.set_equity(eqt['净值'])
        wfp.set_orders(trans)
        excel = ExcelWriter(path, encoding='utf-8')

        for ppty in ['pnl_compound_log_window', 'pnl_compound_ratio_window', 'pnl_simple_ratio_window',
                     'ar_window_simple', 'ar_window_compound', 'volatility_window_simple', 'volatility_window_compound',
                     'sharpe_ratio_window_simple', 'sharpe_ratio_window_compound', 'pnl', 'equity_ratio', 'pnl_ratio']:
            print ppty
            aatr = getattr(wfp, ppty, ppty+'not ready')
            if isinstance(aatr, dict):
                for key, value in aatr.items():
                    sheet = ppty+'_'+key
                    try:
                        value.to_excel(excel, sheet, encoding='utf-8')
                    except:
                        pass
            elif isinstance(aatr, Series):
                DataFrame(aatr).to_excel(excel, ppty, encoding='utf-8')
            elif isinstance(aatr, DataFrameExtended):
                aatr.to_excel(excel, ppty, encoding='utf-8')
        excel.save()


class Optimizer(object):
    def __init__(self, settings=None):
        self._trader = Trader(settings)

    def optimization(self, strategy, tickers, frequency, start=None, end=None, ticker_type=None,
                     models=(), settings=None, **params):
        if settings:
            self._trader.settings = settings

        portfolios = []
        for k in self.exhaustion(**params):
            portfolio = self._trader.initialize().back_test(
                strategy, tickers, frequency,
                start, end, ticker_type, params=k
            )

            k['portfolio'] = portfolio
            portfolios.append(k)

        return portfolios

    def exhaustion(self, **kwargs):
        """
        generator, 穷举所有的参数组合

        :param kwargs:
        :return: dict
        """
        key, values = kwargs.popitem()
        if len(kwargs):
            for value in values:
                for d in self.exhaustion(**kwargs):
                    d[key] = value
                    yield d
        else:
            for value in values:
                yield {key: value}


if __name__ == '__main__':
    from bokeh.plotting import figure, output_file, show

    pass
