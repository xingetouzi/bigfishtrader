# encoding: utf-8
import pandas as pd
import os
from datetime import datetime
import logging

from ipyparallel import Client

from .trader import Trader

ROUND_MAP = {u"五年平均年收益": 2,
             u"净利回撤比": 2,
             u"夏普比率": 2,
             u"平均月收益": 2,
             u"年化收益标准差": 2,
             u"最大回撤率": 2,
             u"最大回撤比率": 2,
             u"最大回撤金额": 2,
             u"盈利因子": 2}


class Optimizer(object):
    def __init__(self, settings=None):
        self.settings = settings if settings else None

    def __getitem__(self, item):
        return self.settings[item]

    def __setitem__(self, item, value):
        self.settings[item] = value

    def run(self, symbols, frequency, start=None, end=None, ticker_type=None,
            sort=u"夏普比率", ascending=False, save=False, **params):
        result = []

        dct = {}
        for model, param in params.items():
            dct.update({'.'.join((model, key)): value for key, value in param.items()})

        for param in self.exhaustion(**dct):
            pa = self.split(param)
            trader = Trader(self.settings)
            trader.run(symbols, frequency, start, end, ticker_type, pa, save)
            op_dict = trader.output("strategy_summary", "risk_indicator")
            print(param, "accomplish")
            for p in op_dict.values():
                param.update(p)
            result.append(param)

        result = pd.DataFrame(result).sort_values(by=sort, ascending=ascending)
        return result

    @staticmethod
    def split(param):
        dct = {}
        for key, value in param.items():
            m, p = key.split('.')
            dct.setdefault(m, {})[p] = value
        return dct

    def optimization(self, filename, symbols, frequency,
                     start=None, end=None, ticker_type=None,
                     sort=u"夏普比率", ascending=False, save=False,
                     **params):
        result = []

        for param in self.exhaustion(**params):
            trader = Trader(self.settings)
            trader.back_test(
                filename, symbols, frequency,
                start, end, ticker_type, params=param, save=False
            )
            op_dict = trader.output("strategy_summary", "risk_indicator")
            print(param, "accomplish")
            for p in op_dict.values():
                param.update(p)
            result.append(param)

        result = pd.DataFrame(result).sort_values(by=sort, ascending=ascending)
        for key, value in ROUND_MAP.items():
            result[key] = result[key].round(value)

        if save:
            name = os.path.basename(filename).split(".")[0]
            dt = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            result.to_excel("Optimization_%s&%s.xls" % (name, dt), encoding="utf-8")
        print(result)
        return result

    def exhaustion(self, **kwargs):
        """
        generator, 穷举所有的参数组合

        :param kwargs:
        :return: dict
        """
        if kwargs:
            key, values = kwargs.popitem()
            for value in values:
                for d in self.exhaustion(**kwargs):
                    d[key] = value
                    yield d
        else:
            yield {}


class ParallelOptimizer(Optimizer):
    def __init__(self, url_file=None, profile=None, settings=None):
        super(ParallelOptimizer, self).__init__(settings)
        self.settings = settings if settings else {}
        self._client = Client(url_file=url_file, profile=profile)
        self._dview = self._client[:]
        self._lview = self._client.load_balanced_view()
        self._code = ""

    def open(self, filename):
        with open(filename) as f:
            self._code = f.read()

    def __getitem__(self, item):
        return self.settings[item]

    def __setitem__(self, item, value):
        self.settings[item] = value

    @staticmethod
    def run_trader(settings, code, param, runtime_meta):
        trader = Trader()

        for k, v in settings.items():
            trader[k].kwargs.update(v)
        symbols, frequency, start, end, ticker_type, save = runtime_meta
        trader.back_test(code, symbols, frequency, start, end, ticker_type, param, save, raw_code=True)
        op_dict = trader.output("strategy_summary", "risk_indicator")
        for p in op_dict.values():
            param.update(p)
        return param

    def run(self, symbols, frequency, start=None, end=None, ticker_type=None,
            sort=u"夏普比率", ascending=False, save=False, **paras):
        runtime_meta = (symbols, frequency, start, end, ticker_type, save)
        task = list(self.exhaustion(**paras))
        ars = []
        for item in task:
            ars.append(self._lview.apply_async(self.run_trader, self.settings, self._code, item, runtime_meta))
        self._lview.wait(ars)
        tmp = [ar.get() for ar in ars]
        result = pd.DataFrame(tmp).sort_values(by=sort, ascending=ascending)
        return result
