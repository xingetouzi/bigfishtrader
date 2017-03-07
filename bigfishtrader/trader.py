# encoding:utf-8
try:
    from Queue import PriorityQueue
except ImportError:
    from queue import PriorityQueue
from collections import OrderedDict
from bigfishtrader.event import EVENTS
from bigfishtrader.performance import OrderAnalysis
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
                               ('commission', '手续费'),
                               ('lever', '杠杆'),
                               ('exchange', '交易所')])
}


ROUND_MAP = {u'五年平均年收益': 2,
             u'净利回撤比': 2,
             u'夏普比率': 2,
             u'平均月收益': 2,
             u'年化收益标准差': 2,
             u'最大回撤率': 2,
             u'最大回撤比率': 2,
             u'最大回撤金额': 2,
             u'盈利因子': 2}


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
        self.performance = OrderAnalysis()

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

    def back_test(self, strategy, symbols, frequency, start=None, end=None, ticker_type=None, params={}, save=False):
        """
        运行一个策略, 完成后返回一个账户对象

        :param strategy: 策略模块
        :param params: 需要修改的策略参数
        :return: Portfolio
        """
        if not self.initialized:
            self.initialize()

        context, data, engine = self.models['context'], self.models['data'], self.models['engine']

        data.init(symbols, frequency, start, end, ticker_type)
        context.tickers = symbols

        def on_time(event, kwargs=None):
            strategy.handle_data(context, data)

        self.models['engine'].register(on_time, EVENTS.TIME, topic='.', priority=100)

        for key, value in params.items():
            setattr(strategy, key, value)

        strategy.initialize(context, data)
        engine.start()
        engine.join()
        engine.stop()

        self.perform()

        if save:
            from datetime import datetime
            path = '%s&%s&%s.xls' % (strategy.__name__, datetime.now().strftime('%Y-%m-%d-%H-%M-%S'),
                                     '&'.join(map(lambda (key, value): key+'_'+str(value), params.items())))
            self._save_origin(path)

        return self.models['portfolio']

    def _save_origin(self, path):
        if not self.initialized:
            raise ValueError('trader not initialized, no data to perform')

        from pandas import ExcelWriter
        writer = ExcelWriter(path, encoding='utf-8')
        pd.DataFrame(self.performance.equity).to_excel(writer, '净值')
        self.performance._orders.to_excel(writer, '交易')
        writer.save()

    def perform(self):
        if not self.initialized:
            raise ValueError('trader not initialized, no data to perform')

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
        trans['成交数'], trans['报单数'] = trans['成交数'].abs(), trans['报单数'].abs()

        self.performance.set_equity(eqt['净值'])
        self.performance.set_orders(trans)
        return self.performance

    def output(self, *args):
        return {attr: getattr(self.performance, attr, None) for attr in args}


class Optimizer(object):
    def __init__(self, settings=None):
        if settings:
            self.settings = settings
        else:
            from bigfishtrader.practice import basic
            self.settings = basic

    def __getitem__(self, item):
        return self.settings[item]

    def optimization(self, strategy, symbols, frequency,
                     start=None, end=None, ticker_type=None,
                     sort=u'夏普比率', ascending=False, save=False,
                     **params):
        result = []

        for param in self.exhaustion(**params):
            trader = Trader(self.settings)
            trader.back_test(
                strategy, symbols, frequency,
                start, end, ticker_type, params=param, save=False
            )
            op_dict = trader.output('strategy_summary', 'risk_indicator')
            print(param, 'accomplish')
            for p in op_dict.values():
                param.update(p)
            result.append(param)

        result = pd.DataFrame(result).sort_values(by=sort, ascending=ascending)
        for key, value in ROUND_MAP.items():
            result[key] = result[key].round(value)

        if save:
            from datetime import datetime
            result.to_excel(
                'Optimization_%s&%s.xls' % (strategy.__name__, datetime.now().strftime('%Y-%m-%d-%H-%M-%S')),
                encoding='utf-8'
            )

        print(result)
        return result

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
