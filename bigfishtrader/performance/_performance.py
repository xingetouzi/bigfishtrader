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
                 copy=False, total=None, title=""):
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
        """

        Returns:
            pandas.Series: profit and loss
        """
        return self.equity - self.base

    @property
    @cache_calculator
    def equity_ratio(self):
        """

        Returns:
            pandas.Series: equity_ratio
        """
        return self.equity / self.base

    @property
    @cache_calculator
    def pnl_ratio(self):
        """

        Returns:
            pandas.Series: profit and loss ratio
        """
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
        self._column_names = {"M": (lambda x: OrderedDict(sorted(x.items(), key=lambda t: t[0])))(
            {1: ("month1", "1个月"), 3: ("month3", "3个月"), 6: ("month6", "6个月"), 12: ("month12", "1年")})}

    def _roll_exp(self, sample):
        calculator = lambda x: x["rate"] / x["trade_days"]
        ts = sample
        result = DataFrameExtended([], index=ts.index.rename("time"))
        for key, value in self._column_names["M"].items():
            result[value[0]] = pd.rolling_sum(ts, key).apply(calculator, axis=1)
        result.total = calculator(ts.sum())
        return result

    def _roll_std(self, sample):
        calculator = lambda x: (x["rate_square"] - x["rate"] * x["rate"] / x["trade_days"]) \
                               / (x["trade_days"] - (x["trade_days"] > 1))
        ts = (lambda x: pd.DataFrame(
            dict(rate=x["rate"],
                 rate_square=(x["rate"] * x["rate"]),
                 trade_days=x["trade_days"]))
              .resample("MS").sum())(sample)
        result = DataFrameExtended([], index=ts.index.rename("time"))
        # TODO numpy.sqrt np自带有开根号运算
        for key, value in self._column_names["M"].items():
            # XXX 开根号运算会将精度缩小一半，必须在此之前就处理先前浮点运算带来的浮点误差
            result[value[0]] = _deal_float_error(ts.rolling(key).sum().apply(calculator, axis=1)) ** 0.5
        result.total = (lambda x: int(abs(x) > FLOAT_ERR) * x)(calculator(ts.sum())) ** 0.5
        return _deal_float_error(result)

    @property
    @cache_calculator
    def pnl_compound_log_window(self):
        result = {}
        result["R"] = self.equity_ratio  # "R" means raw
        # TODO 对爆仓情况的考虑
        if result["R"].min() <= 0:
            result["D"], self.__index_daily = \
                (lambda x, y: (pd.DataFrame({x.name: x, "trade_days": y}).dropna(), x.index))(
                    *(lambda x, y: (x - x.shift(1).fillna(method="ffill").fillna(y), x.notnull().astype("int")))(
                        *(lambda x: (x, x[0]))(
                            result["R"].resample("D", label="left").last() * 0
                        )
                    )
                )

        else:
            # 由于是取了对数，日收率是以复利的方式计算
            result["D"], self.__index_daily = \
                (lambda x, y: (pd.DataFrame({x.name: x, "trade_days": y}).dropna(), x.index))(
                    *(lambda x, y: (x - x.shift(1).fillna(method="ffill").fillna(y), x.notnull().astype("int")))(
                        *(lambda x: (x, x[0]))(
                            result["R"].resample("D", label="left").last().apply(math.log)
                        )
                    )
                )
        result["W"] = result["D"].resample("W-MON").sum().dropna()
        result["M"] = result["D"].resample("MS").sum().dropna()
        result["Y"] = result["M"].resample("AS").sum().dropna()
        return result

    @property
    @cache_calculator
    def pnl_compound_ratio_window(self):
        """
        :return:
        """
        result = {}
        result["D"] = \
            (lambda x: pd.DataFrame(
                {"rate": x["rate"].apply(partial(_get_percent_from_log)),
                 "trade_days": x["trade_days"]}))(
                self.pnl_compound_log_window["D"]
            )
        result["W"] = result["D"].resample("W-MON").sum().dropna()
        result["M"] = result["D"].resample("MS").sum().dropna()
        result["Y"] = result["M"].resample("AS").sum().dropna()
        return result

    @property
    @cache_calculator
    def pnl_simple_ratio_window(self):
        result = {}
        result["R"] = self.equity_ratio
        # TODO 对爆仓情况的考虑
        if result["R"].min() <= 0:
            result["D"], self.__index_daily = \
                (lambda x, y: (pd.DataFrame({x.name: x, "trade_days": y}).dropna(), x.index))(
                    *(lambda x, y: (x - x.shift(1).fillna(method="ffill").fillna(y), x.notnull().astype("int")))(
                        *(lambda x: (x, x[0]))(
                            result["R"].resample("D", label="left").last() * 0
                        )
                    )
                )
        else:
            # 由于是取了对数，日收率是以复利的方式计算
            result["D"], self.__index_daily = \
                (lambda x, y: (pd.DataFrame({x.name: x, "trade_days": y}).dropna(), x.index))(
                    *(lambda x, y: (x - x.shift(1).fillna(method="ffill").fillna(y), x.notnull().astype("int")))(
                        *(lambda x: (x, x[0]))(
                            result["R"].resample("D", label="left").last() * 100 - 100
                        )
                    )
                )
        result["W"] = result["D"].resample("W-MON").sum().dropna()
        result["M"] = result["D"].resample("MS").sum().dropna()
        result["Y"] = result["M"].resample("AS  ").sum().dropna()
        return result

    @property
    @cache_calculator
    def ar_window_simple(self):
        calculator = lambda x: (x["rate"] / x["trade_days"]) * self._annual_factor
        ts = self.pnl_simple_ratio_window["M"]
        result = DataFrameExtended([], index=ts.index.rename("time"))
        for key, value in self._column_names["M"].items():
            result[value[0]] = ts.rolling(key).sum().apply(calculator, axis=1)
        result.total = calculator(ts.sum())
        return result

    @property
    @cache_calculator
    def ar_window_compound(self):
        calculator = lambda x: (x["rate"] / x["trade_days"]) * self._annual_factor
        ts = self.pnl_compound_ratio_window["M"]
        result = DataFrameExtended([], index=ts.index.rename("time"))
        for key, value in self._column_names["M"].items():
            result[value[0]] = pd.rolling_sum(ts, key).apply(calculator, axis=1)
        result.total = calculator(ts.sum())
        return result

    @property
    @cache_calculator
    def volatility_window_simple(self):
        # TODO pandas好像并不支持分组上的移动窗口函数
        result = self._roll_std(self.pnl_simple_ratio_window["D"])
        result *= self._annual_factor ** 0.5
        result.total *= self._annual_factor ** 0.5
        return result

    @property
    @cache_calculator
    def volatility_window_compound(self):
        result = self._roll_std(self.pnl_compound_ratio_window["D"])
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


class ReportSheet(WindowFactorPerformance):
    def __init__(self):
        super(ReportSheet, self).__init__()
        self._report_sheet = None
        self._units = {}

    def _update_units(self, d):
        for key, value in d.items():
            self._units.update(dict.fromkeys(value, key))

    @property
    @cache_calculator
    def trade_details(self):
        df = self._fills[["position_id", "local_id", "time", "ticker", "action", "price", "quantity", "profit",
                          "commission"]]
        dct = {k: v for k, v in df.groupby(["ticker"])}
        for trade in dct.values():
            temp = trade.groupby("position_id")["quantity"].first().apply(
                lambda x: DIRECTION.LONG.value if x > 0 else DIRECTION.SHORT.value)
            trade["direction"] = trade["position_id"].apply(lambda x: temp[x])
            trade["volume"] = trade["quantity"].abs()
            trade["entry"] = trade["action"].apply(
                lambda x: ACTION.IN.value if x else ACTION.OUT.value)
            # commission is separated from profit
            trade["profit"] = trade["profit"].fillna(0) - trade["commission"].fillna(0)
            trade.rename_axis({"local_id": "trade_id"}, axis=1)
            del trade["quantity"], trade["action"]
        return dct

    @property
    @cache_calculator
    def trade_summary(self):
        self._update_units({
            "(%s)" % self._currency: [
                u"总净利", u"总盈利", u"总亏损", u"平均每笔盈利", u"平均每笔亏损",
                u"单笔最大盈利", u"单笔最大亏损", u"最大连续盈利金额", u"最大连续亏损金额",
            ],
            "": [
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
            dct = OrderedDict()
            dct[u"总净利"] = np.array([t["profit"].sum() for t in temp])
            # fi means fancy indexing
            dct[u"总盈利"] = np.array([t[fi]["profit"].sum() for fi, t in zip(win, temp)])
            dct[u"总亏损"] = abs(np.array([t[fi]["profit"].sum() for fi, t in zip(loss, temp)]))
            dct[u"总交易次数"] = np.array([len(t) for t in temp])
            dct[u"总盈利次数"] = np.array([len(t[fi]) for fi, t in zip(win, temp)])
            dct[u"总亏损次数"] = np.array([len(t[fi]) for fi, t in zip(loss, temp)])
            dct[u"总交易笔数"] = np.array([t["volume"].sum() for t in temp])
            dct[u"总盈利笔数"] = np.array([t[fi]["volume"].sum() for fi, t in zip(win, temp)])
            dct[u"总亏损笔数"] = np.array([t[fi]["volume"].sum() for fi, t in zip(loss, temp)])
            section = {
                True: np.array([0] * 3),
                False: np.array([0] * 3),
            }
            for i_, t_ in zip(range(3), temp):
                t_ = t_["profit"]
                if not t_.empty:
                    win_flag = [None, t_.iloc[0] >= 0]
                    for v_ in t_:
                        win_flag[0] = win_flag[1]
                        win_flag[1] = v_ >= 0
                        if win_flag[0] ^ win_flag[1]:
                            section[win_flag[0]][i_] += 1
                    section[win_flag[1]][i_] += 1
            dct[u"总盈利段数"] = section[True]
            dct[u"总亏损段数"] = section[False]
            dct[u"单笔最大盈利"] = np.array([(t[fi]["profit"] / t[fi]["volume"]).max() for fi, t in zip(win, temp)])
            dct[u"单笔最大亏损"] = abs(np.array([(t[fi]["profit"] / t[fi]["volume"]).min() for fi, t in zip(loss, temp)]))
            dct[u"平均每笔盈利"] = dct[u"总盈利"] / dct[u"总盈利笔数"]
            dct[u"平均每笔亏损"] = dct[u"总亏损"] / dct[u"总亏损笔数"]
            dct[u"平均连续盈利次数"] = dct[u"总盈利次数"] / dct[u"总盈利段数"]
            dct[u"平均连续亏损次数"] = dct[u"总亏损次数"] / dct[u"总亏损段数"]
            result[ticker] = pd.DataFrame(data=dct, index=[u"全部", u"多头", u"空头"]).T
        return result

    @property
    @cache_calculator
    def trade_summary_all(self):
        dct = OrderedDict()
        panel = pd.Panel(self.trade_summary).swapaxes(0, 1)
        for field in panel.keys():
            if field.startswith(u"总"):
                dct[field] = panel[field].apply(np.sum, axis=0)
        for field in [u"单笔最大盈利", u"单笔最大亏损"]:
            dct[field] = panel[field].apply(np.max, axis=0)
        dct[u"平均每笔盈利"] = dct[u"总盈利"] / dct[u"总盈利笔数"]
        dct[u"平均每笔亏损"] = dct[u"总亏损"] / dct[u"总亏损笔数"]
        dct[u"平均连续盈利次数"] = dct[u"总盈利次数"] / dct[u"总盈利段数"]
        dct[u"平均连续亏损次数"] = dct[u"总亏损次数"] / dct[u"总亏损段数"]
        return pd.DataFrame(data=dct).T

    @property
    @cache_calculator
    def strategy_summary(self):
        dct = OrderedDict()
        t_y = self.pnl_compound_log_window["Y"][-5:]
        pnl_y = t_y["rate"] / t_y["trade_days"] * self._annual_factor
        pnl_m = self.pnl_compound_log_window["M"]["rate"]
        dct[u"五年平均年收益"] = pnl_y.apply(_get_percent_from_log).mean()
        dct[u"年化收益标准差"] = self.volatility_window_compound.total
        dct[u"平均月收益"] = pnl_m.apply(_get_percent_from_log).mean()
        dct[u"最大回撤率"] = self.draw_down_ratio.max() * 100
        dct[u"夏普比率"] = self.sharpe_ratio_window_simple.total
        dct[u"盈利因子"] = self.trade_summary_all[u"全部"][u"总盈利"] / self.trade_summary_all[u"全部"][u"总亏损"]
        return pd.Series(dct)

    @property
    @cache_calculator
    def risk_indicator(self):
        dct = OrderedDict()
        dct[u"最大回撤金额"] = self.draw_down.max()
        dct[u"最大回撤比率"] = self.draw_down_ratio.max() * 100
        dct[u"最大回撤发生时间"] = self.draw_down_ratio.argmax()
        dct[u"净利回撤比"] = self.trade_summary_all[u"全部"][u"总净利"] / dct[u"最大回撤金额"]
        dct[u"持仓时间比率"] = None
        return pd.Series(dct)

    @property
    @cache_calculator
    def draw_down(self):
        return self.equity - self.equity.cummax()

    @property
    @cache_calculator
    def draw_down_ratio(self):
        return self.draw_down / self.equity.cummax()

    @property
    @cache_calculator
    def pnl_indicator(self):
        self._update_units({
            "%s" % self._currency: [u"金额"],
            "%": [u"收益率[单利]", u"收益率[复利]"]
        })

        dct = dict()
        dct[u"初始资金"] = [self.base, 0, 0]
        if not self.equity.empty:
            dct[u"最新资金"] = [self.equity[-1], self.pnl_ratio[-1], self.pnl_ratio[-1]]
            simple1 = self.pnl_simple_ratio_window["Y"]["rate"][-1]
            compound1 = _get_percent_from_log(self.pnl_compound_log_window["Y"]["rate"][-1])
            dct[u"年初至今"] = [self.base * (simple1 / 100), simple1, compound1]
            simple2 = self.pnl_simple_ratio_window["M"]["rate"][-1]
            compound2 = _get_percent_from_log(self.pnl_compound_log_window["M"]["rate"][-1])
            dct[u"当月收益"] = [self.base * (simple2 / 100), simple2, compound2]
            if len(self.pnl_simple_ratio_window["Y"]) >= 2:
                simple3 = self.pnl_simple_ratio_window["Y"]["rate"][-2]
                compound3 = _get_percent_from_log(self.pnl_compound_log_window["Y"]["rate"][-2])
                dct[u"去年收益"] = [self.base * (simple3 / 100), simple3, compound3]
            else:
                dct[u"去年收益"] = [0] * 3
        else:
            dct[u"最新资金"] = [0] * 3
            dct[u"年初至今"] = [0] * 3
            dct[u"当月收益"] = [0] * 3
            dct[u"去年收益"] = [0] * 3
        result = pd.DataFrame(
            dct, index=[u"金额", u"收益率[单利]", u"收益率[复利]"],
            columns=[u"初始资金", u"最新资金", u"年初至今", u"去年收益", u"当月收益"]
        ).T
        return result

    def calculate(self):
        pass

    @cache_calculator
    def csv(self):
        pass

    @cache_calculator
    def html(self):
        pass
