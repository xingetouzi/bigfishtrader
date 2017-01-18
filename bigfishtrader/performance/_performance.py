# encoding: utf-8
import math
from collections import OrderedDict

from functools import wraps, partial
from weakref import WeakKeyDictionary
import numpy as np
import pandas as pd
import pytz

from bigfishtrader.const import DIRECTION, ACTION

__all__ = ["Performance", "WindowFactorPerformance", "ReportSheet"]

FLOAT_ERR = 1e-7


class DataFrameExtended(pd.DataFrame):
    def __init__(self, data=None, index=None, columns=None, dtype=None,
                 copy=False, total=None, title=''):
        super(DataFrameExtended, self).__init__(data=data, index=index, columns=columns, dtype=dtype, copy=copy)
        self.__total = total
        self.__title = title

    def __get_total(self):
        return self.__total

    def __set_total(self, value):
        self.__total = value

    def __get_title(self):
        return self.__title

    def __set_title(self, value):
        self.__title = value

    total = property(__get_total, __set_total)
    titie = property(__get_title, __set_title)


def _get_percent_from_log(n, factor=1):
    return (math.exp(n * factor) - 1) * 100


def _deal_float_error(dataframe, fill=0):
    dataframe[abs(dataframe) <= FLOAT_ERR] = fill
    return dataframe


def cache_calculator(func):
    # XXX 由于python的垃圾回收机制只有引用计数，不像java一样也使用缩圈的拓扑算法，需要用弱引用防止内存泄漏,
    # 弱引用字典还会在垃圾回收发生时自动删除字典中所对应的键值对
    cache = WeakKeyDictionary()

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if self in cache:
            _, count = cache[self]
            if count == self._count:
                return cache[self][0]
        cache[self] = (func(self, *args, **kwargs), self._count)
        return cache[self][0]

    return wrapper


class Performance(object):
    def __init__(self):
        self.equity = pd.Series()
        self._fills = pd.Series()
        self.base = 100000
        self._currency = "$"
        self._count = 0

    def _update(self, equity):
        self.equity = equity
        self.equity.index.name = "datetime"
        self.equity.name = "rate"
        self._count += 1

    @property
    @cache_calculator
    def pnl(self):
        return self.equity - self.base

    @property
    @cache_calculator
    def equity_ratio(self):
        return self.equity / self.base

    @property
    @cache_calculator
    def pnl_radio(self):
        return self.equity / self.base - 1

    def set_equity(self, value, base=None):
        if not isinstance(value, pd.Series):
            raise RuntimeWarning("value should be pd.Series")
        if not base:
            base = self.base
        else:
            self.base = base
        self._update(value)

    def set_pnl(self, value, base=None):
        if not isinstance(value, pd.Series):
            raise RuntimeWarning("value should be pd.Series")
        if not base:
            base = self.base
        else:
            self.base = base
        self._update(base + value)

    def set_equity_ratio(self, value, base=None):
        if not isinstance(value, pd.Series):
            raise RuntimeWarning("value should be pd.Series")
        if not base:
            base = self.base
        else:
            self.base = base
        self._update(base * value)

    def set_pnl_radio(self, value, base=None):
        if not isinstance(value, pd.Series):
            raise RuntimeWarning("value should be pd.Series")
        if not base:
            base = self.base
        else:
            self.base = base
        self._update(value * base + base)

    def set_fills(self, fills):
        self._fills = fills

    def set_currency(self, currency):
        self._currency = currency


class WindowFactorPerformance(Performance):
    def __init__(self):
        super(WindowFactorPerformance, self).__init__()
        self._precision = 4
        self._annual_factor = 250
        self._column_names = {'M': (lambda x: OrderedDict(sorted(x.items(), key=lambda t: t[0])))(
            {1: ('month1', '1个月'), 3: ('month3', '3个月'), 6: ('month6', '6个月'), 12: ('month12', '1年')})}

    def _roll_exp(self, sample):
        calculator = lambda x: x['rate'] / x['trade_days']
        ts = sample
        result = DataFrameExtended([], index=ts.index.rename('time'))
        for key, value in self._column_names['M'].items():
            result[value[0]] = pd.rolling_sum(ts, key).apply(calculator, axis=1)
        result.total = calculator(ts.sum())
        return result

    def _roll_std(self, sample):
        calculator = lambda x: (x['rate_square'] - x['rate'] * x['rate'] / x['trade_days']) \
                               / (x['trade_days'] - (x['trade_days'] > 1))
        ts = (lambda x: pd.DataFrame(
            dict(rate=x['rate'],
                 rate_square=(x['rate'] * x['rate']),
                 trade_days=x['trade_days']))
              .resample('MS').sum())(sample)
        result = DataFrameExtended([], index=ts.index.rename('time'))
        # TODO numpy.sqrt np自带有开根号运算
        for key, value in self._column_names['M'].items():
            # XXX 开根号运算会将精度缩小一半，必须在此之前就处理先前浮点运算带来的浮点误差
            result[value[0]] = _deal_float_error(ts.rolling(key).sum().apply(calculator, axis=1)) ** 0.5
        result.total = (lambda x: int(abs(x) > FLOAT_ERR) * x)(calculator(ts.sum())) ** 0.5
        return _deal_float_error(result)

    @property
    @cache_calculator
    def pnl_log_window_compound(self):
        result = {}
        result['R'] = self.equity_ratio  # 'R' means raw
        # TODO 对爆仓情况的考虑
        if result['R'].min() <= 0:
            result['D'], self.__index_daily = \
                (lambda x, y: (pd.DataFrame({x.name: x, 'trade_days': y}).dropna(), x.index))(
                    *(lambda x, y: (x - x.shift(1).fillna(method='ffill').fillna(y), x.notnull().astype('int')))(
                        *(lambda x: (x, x[0]))(
                            result['R'].resample('D', label='left').last() * 0
                        )
                    )
                )

        else:
            # 由于是取了对数，日收率是以复利的方式计算
            result['D'], self.__index_daily = \
                (lambda x, y: (pd.DataFrame({x.name: x, 'trade_days': y}).dropna(), x.index))(
                    *(lambda x, y: (x - x.shift(1).fillna(method='ffill').fillna(y), x.notnull().astype('int')))(
                        *(lambda x: (x, x[0]))(
                            result['R'].resample('D', label='left').last().apply(math.log)
                        )
                    )
                )
        result['W'] = result['D'].resample('W-MON').sum().dropna()
        result['M'] = result['D'].resample('MS').sum().dropna()
        return result

    @property
    @cache_calculator
    def pnl_ratio_window_compound(self):
        """
        :return:
        """
        result = {}
        result['D'] = \
            (lambda x: pd.DataFrame(
                {'rate': x['rate'].apply(partial(_get_percent_from_log)),
                 'trade_days': x['trade_days']}))(
                self.pnl_log_window_compound['D']
            )
        result['W'] = result['D'].resample('W-MON').sum().dropna()
        result['M'] = result['D'].resample('MS').sum().dropna()
        return result

    @property
    @cache_calculator
    def pnl_ratio_window_simple(self):
        result = {}
        result['R'] = self.equity_ratio
        # TODO 对爆仓情况的考虑
        if result['R'].min() <= 0:
            result['D'], self.__index_daily = \
                (lambda x, y: (pd.DataFrame({x.name: x, 'trade_days': y}).dropna(), x.index))(
                    *(lambda x, y: (x - x.shift(1).fillna(method='ffill').fillna(y), x.notnull().astype('int')))(
                        *(lambda x: (x, x[0]))(
                            result['R'].resample('D', label='left').last() * 0
                        )
                    )
                )
        else:
            # 由于是取了对数，日收率是以复利的方式计算
            result['D'], self.__index_daily = \
                (lambda x, y: (pd.DataFrame({x.name: x, 'trade_days': y}).dropna(), x.index))(
                    *(lambda x, y: (x - x.shift(1).fillna(method='ffill').fillna(y), x.notnull().astype('int')))(
                        *(lambda x: (x, x[0]))(
                            result['R'].resample('D', label='left').last() * 100 - 100
                        )
                    )
                )
        result['W'] = result['D'].resample('W-MON').sum().dropna()
        result['M'] = result['D'].resample('MS').sum().dropna()
        return result

    @property
    @cache_calculator
    def ar_window_simple(self):
        calculator = lambda x: (x['rate'] / x['trade_days']) * self._annual_factor
        ts = self.pnl_ratio_window_simple['M']
        result = DataFrameExtended([], index=ts.index.rename('time'))
        for key, value in self._column_names['M'].items():
            result[value[0]] = ts.rolling(key).sum().apply(calculator, axis=1)
        result.total = calculator(ts.sum())
        return result

    @property
    @cache_calculator
    def ar_window_compound(self):
        calculator = lambda x: (x['rate'] / x['trade_days']) * self._annual_factor
        ts = self.pnl_ratio_window_compound['M']
        result = DataFrameExtended([], index=ts.index.rename('time'))
        for key, value in self._column_names['M'].items():
            result[value[0]] = pd.rolling_sum(ts, key).apply(calculator, axis=1)
        result.total = calculator(ts.sum())
        return result

    @property
    @cache_calculator
    def volatility_window_simple(self):
        # TODO pandas好像并不支持分组上的移动窗口函数
        result = self._roll_std(self.pnl_ratio_window_simple['D'])
        result *= self._annual_factor ** 0.5
        result.total *= self._annual_factor ** 0.5
        return result

    @property
    @cache_calculator
    def volatility_window_compound(self):
        result = self._roll_std(self.pnl_ratio_window_compound['D'])
        result *= self._annual_factor ** 0.5
        result.total *= self._annual_factor ** 0.5
        return result

    @property
    @cache_calculator
    def sharpe_ratio_window_simple(self):
        expected = self.ar_window_simple
        std = _deal_float_error(self.volatility_window_simple, fill=np.nan)  # 年化标准差
        std.total = self.volatility_window_simple.total
        result = expected / std
        result.total = expected.total / std.total
        return result

    @property
    @cache_calculator
    def sharpe_ratio_window_compound(self):
        expected = self.ar_window_compound
        std = _deal_float_error(self.volatility_window_compound, fill=np.nan)
        std.total = self.volatility_window_compound.total
        result = expected / std
        result.total = expected.total / std.total
        return result

    def sortino_ratio(self):
        pass

    def information_ratio(self):
        pass


class ReportSheet(Performance):
    def __init__(self):
        super(ReportSheet, self).__init__()
        self._report_sheet = None
        self._units = {}

    @property
    @cache_calculator
    def trade_details(self):
        df = self._fills[["position_id", "local_id", "time", "ticker", "action", "price", "quantity", "profit"]]
        dct = {k: v for k, v in df.groupby(["ticker"])}
        for trade in dct.values():
            temp = trade.groupby("position_id")["quantity"].first().apply(
                lambda x: DIRECTION.LONG.value if x > 0 else DIRECTION.SHORT.value)
            trade["direction"] = trade["position_id"].apply(lambda x: temp[x])
            trade["volume"] = trade["quantity"].abs()
            trade["entry"] = trade["action"].apply(
                lambda x: ACTION.IN.value if x else ACTION.OUT.value)
            trade["profit"] = trade["profit"].fillna(0)
            trade.rename_axis({"local_id": "trade_id"}, axis=1)
            del trade["quantity"], trade["action"]
        return dct

    @property
    @cache_calculator
    def trade_summary(self):
        self._units.update({
            "(%s)" % self._currency: {
                u"总净利", u"总盈利", u"总亏损", u"平均每笔盈利", u"平均每笔亏损",
                u"单笔最大盈利", u"单笔最大亏损", u"最大连续盈利金额", u"最大连续亏损金额",
            },
            '': [
                u"总盈利/总亏损", u"平均每笔盈利/平均每笔亏损", u"平均连续盈利次数",
                u"平均连续亏损次数",
            ],
            "%": [
                u"胜率"
            ]
        })
        result = {}
        for ticker, trade in self.trade_details.items():
            total = pd.DataFrame()
            total["profit"] = trade.groupby("position_id")["profit"].sum()
            total["direction"] = trade.groupby("position_id")["direction"].last()
            total["volume"] = abs(trade[trade["entry"] == ACTION.IN.value]["volume"]).sum()
            long_ = total[total["direction"] == DIRECTION.LONG.value]
            short = total[total["direction"] == DIRECTION.SHORT.value]
            temp = [total, long_, short]
            win = [t["profit"] > 0 for t in temp]
            loss = [t["profit"] < 0 for t in temp]
            dct = dict()
            dct[u"总净利"] = np.array([t["profit"].sum() for t in temp])
            # fi means fancy indexing
            dct[u"总盈利"] = np.array([t[fi]["profit"].sum() for fi, t in zip(win, temp)])
            dct[u"总亏损"] = abs(np.array([t[fi]["profit"].sum() for fi, t in zip(loss, temp)]))
            volume = np.array([t["volume"].sum() for t in temp])
            dct[u"平均每笔盈利"] = dct[u"总盈利"] / volume
            dct[u"平均每笔亏损"] = dct[u"总亏损"] / volume
            dct[u"单笔最大盈利"] = np.array([(t["profit"] / t["volume"]).max() for t in temp])
            dct[u"单笔最大亏损"] = abs(np.minimum(np.array([(t["profit"] / t["volume"]).min() for t in temp]), 0))
            section = {
                True: np.array([0] * 3),
                False: np.array([0] * 3),
            }
            for i_, t_ in zip(range(3), temp):
                t_ = t_["profit"]
                if not t_.empty:
                    win_flag = np.NaN
                    for v_ in t_:
                        if ((v_ >= 0) * win_flag) == 0:
                            section[win_flag][i_] += 1
                        win_flag = v_ >= 0
                    section[win_flag][i_] += 1
            dct[u"平均连续盈利次数"] = np.array([len(t[fi]) / section[True][i] for i, fi, t in zip(range(3), win, temp)])
            dct[u"平均连续亏损次数"] = np.array([len(t[fi]) / section[False][i] for i, fi, t in zip(range(3), loss, temp)])
            result[ticker] = pd.DataFrame(data=dct, index=[u"全部", u"多头", u"空头"]).T
        return result

    def calculate(self):
        pass

    @cache_calculator
    def csv(self):
        pass

    @cache_calculator
    def html(self):
        pass