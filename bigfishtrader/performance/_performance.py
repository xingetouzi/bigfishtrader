# encoding: utf-8
from __future__ import division
import math
from collections import OrderedDict

from functools import wraps, partial
from weakref import WeakKeyDictionary

from dateutil import rrule
import numpy as np
import pandas as pd
import pytz

from bigfishtrader.const import DIRECTION, ACTION, SIDE

__all__ = ["Performance", "WindowFactorPerformance", "OrderAnalysis"]

FLOAT_ERR = 1e-7


def _get_percent_from_log(n, factor=1):
    return (math.exp(n * factor) - 1) * 100


def _deal_float_error(dataframe, fill=0):
    dataframe[abs(dataframe) <= FLOAT_ERR] = fill
    return dataframe


def _workdays(start, end, day_off=None):
    if day_off is None:
        day_off = 5, 6
    workdays = [x for x in range(7) if x not in day_off]
    days = rrule.rrule(rrule.DAILY, dtstart=start, until=end, byweekday=workdays)
    return days.count()


def lru_cache(max_size=10):
    def decorator(func):
        # XXX 由于python的垃圾回收机制只有引用计数，不像java一样也使用缩圈的拓扑算法，需要用弱引用防止内存泄漏,
        # 弱引用字典还会在垃圾回收发生时自动删除字典中所对应的键值对
        cache = WeakKeyDictionary()

        @wraps(func)
        def wrapper(self, *args):
            if self in cache:
                dct = cache[self]
                if args in dct:
                    last, count = dct[args]
                    if count == self._count:
                        return last
                else:
                    if len(dct) >= max_size:
                        dct.popitem(last=False)
            else:
                cache[self] = OrderedDict()
                dct = cache[self]
            result = func(self, *args)
            dct[args] = (result, self._count)  # recalculate due to data update
            return result

        return wrapper

    return decorator


class Performance(object):
    def __init__(self):
        self.equity = pd.Series()
        self._orders = pd.Series()
        self.base = 100000
        self._currency = "$"
        self._count = 0

    def _update(self, equity):
        self.equity = equity
        self.equity.index.name = "datetime"
        self.equity.name = "rate"
        self._count += 1

    @property
    @lru_cache()
    def pnl(self):
        """

        Returns:
            pandas.Series: 成交均价 and loss
        """
        return self.equity - self.base

    @property
    @lru_cache()
    def equity_ratio(self):
        """

        Returns:
            pandas.Series: equity_ratio
        """
        return self.equity / self.base

    @property
    @lru_cache()
    def pnl_ratio(self):
        """

        Returns:
            pandas.Series: 成交均价 and loss ratio
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

    def set_orders(self, orders):
        self._orders = orders

    def set_currency(self, currency):
        self._currency = currency


class WindowFactorPerformance(Performance):
    def __init__(self):
        super(WindowFactorPerformance, self).__init__()
        self._precision = 4
        self._annual_factor = 250
        self._column_names = {"M": (lambda x: OrderedDict(sorted(x.items(), key=lambda t: t[0])))(
            {1: ("month1", "1个月"), 3: ("month3", "3个月"), 6: ("month6", "6个月"), 12: ("month12", "1年")})}

    def calculator_arithmetic_mean(self, x):
        return (x["rate"] / x["trade_days"]) * self._annual_factor

    @staticmethod
    def calculator_variance(x):
        return (x["rate_square"] - x["rate"] * x["rate"] / x["trade_days"]) \
               / (x["trade_days"] - (x["trade_days"] > 1))

    @staticmethod
    def calculator_square(df):
        """

        Args:
            df(pandas.DataFrame):

        Returns:
            pandas.DataFrame
        """
        result = df.copy(deep=False)
        result["rate_square"] = result["rate"] * result["rate"]
        return result

    def _roll_exp(self, sample):
        ts = sample
        result = pd.DataFrame([], index=ts.index.rename("time"))
        for key, value in self._column_names["M"].items():
            result[value[0]] = pd.rolling_sum(ts, key).apply(self.calculator_arithmetic_mean, axis=1)
        return result

    def _roll_std(self, sample):
        ts = self.calculator_square(sample).resample("MS").sum()
        result = pd.DataFrame([], index=ts.index.rename("time"))
        # TODO numpy.sqrt np自带有开根号运算
        for key, value in self._column_names["M"].items():
            # XXX 开根号运算会将精度缩小一半，必须在此之前就处理先前浮点运算带来的浮点误差
            result[value[0]] = _deal_float_error(ts.rolling(key).sum().apply(self.calculator_variance, axis=1)) ** 0.5
        return _deal_float_error(result)

    @lru_cache()
    def pnl_compound_log(self, frequency="D"):
        """

        Args:
            frequency:  sampling frequency

        Returns:
            pandas.DataFrame
        """
        # TODO 默认只有有行情数据的时候才会有净值信息，并据此计算交易日信息
        if frequency == "D":
            ts = self.equity_ratio
            # TODO 对爆仓情况的考虑
            if ts.min() <= 0:
                result, self.__index_daily = \
                    (lambda x, y: (pd.DataFrame({x.name: x, "trade_days": y}).dropna(), x.index))(
                        *(lambda x, y: (x - x.shift(1).fillna(method="ffill").fillna(y), x.notnull().astype("int")))(
                            *(lambda x: (x, x[0]))(
                                ts.resample("D", label="left").last() * 0
                            )
                        )
                    )

            else:
                # 由于是取了对数，日收率是以复利的方式计算
                result, self.__index_daily = \
                    (lambda x, y: (pd.DataFrame({x.name: x, "trade_days": y}).dropna(), x.index))(
                        *(lambda x, y: (x - x.shift(1).fillna(method="ffill").fillna(y), x.notnull().astype("int")))(
                            *(lambda x: (x, x[0]))(
                                ts.resample("D", label="left").last().apply(math.log)
                            )
                        )
                    )
        else:
            result = self.pnl_compound_log().resample(frequency).sum().dropna()
        # result["W"] = result["D"].resample("W-MON").sum().dropna()
        # result["M"] = result["D"].resample("MS").sum().dropna()
        # result["Y"] = result["M"].resample("AS").sum().dropna()
        return result

    @lru_cache()
    def pnl_compound_ratio(self, frequency="D"):
        """


        Args:
            frequency: sampling frequency

        Returns:
            pandas.DataFrame
        """
        if frequency == "D":
            result = \
                (lambda x: pd.DataFrame(
                    {"rate": x["rate"].apply(partial(_get_percent_from_log)),
                     "trade_days": x["trade_days"]}))(
                    self.pnl_compound_log()
                )
        else:
            result = self.pnl_compound_ratio().resample(frequency).sum().dropna()
        return result

    @lru_cache()
    def pnl_simple_ratio(self, frequency="D"):
        """

        Args:
            frequency:

        Returns:
            pandas.DataFrame
        """
        if frequency == "D":
            ts = self.equity_ratio
            # TODO 对爆仓情况的考虑
            if ts.min() <= 0:
                result, self.__index_daily = \
                    (lambda x, y: (pd.DataFrame({x.name: x, "trade_days": y}).dropna(), x.index))(
                        *(lambda x, y: (x - x.shift(1).fillna(method="ffill").fillna(y), x.notnull().astype("int")))(
                            *(lambda x: (x, x[0]))(
                                ts.resample("D", label="left").last() * 0
                            )
                        )
                    )
            else:
                # 由于是取了对数，日收率是以复利的方式计算
                result, self.__index_daily = \
                    (lambda x, y: (pd.DataFrame({x.name: x, "trade_days": y}).dropna(), x.index))(
                        *(lambda x, y: (x - x.shift(1).fillna(method="ffill").fillna(y), x.notnull().astype("int")))(
                            *(lambda x: (x, x[0]))(
                                ts.resample("D", label="left").last() * 100 - 100
                            )
                        )
                    )
        else:
            result = self.pnl_simple_ratio().resample(frequency).sum().dropna()
        return result

    @property
    @lru_cache()
    def ar_window_simple(self):
        ts = self.pnl_simple_ratio("MS")
        result = pd.DataFrame([], index=ts.index.rename("time"))
        for key, value in self._column_names["M"].items():
            result[value[0]] = ts.rolling(key).sum().apply(self.calculator_arithmetic_mean, axis=1)
        return result

    @property
    @lru_cache()
    def ar_window_compound(self):
        ts = self.pnl_compound_ratio("MS")
        result = pd.DataFrame([], index=ts.index.rename("time"))
        for key, value in self._column_names["M"].items():
            result[value[0]] = pd.rolling_sum(ts, key).apply(self.calculator_arithmetic_mean, axis=1)
        return result

    @property
    @lru_cache()
    def annual_return(self):
        return _get_percent_from_log(self.calculator_arithmetic_mean(self.pnl_compound_log().sum()))

    @property
    @lru_cache()
    def annual_return_arithmetic(self):
        return self.calculator_arithmetic_mean(self.pnl_compound_ratio().sum())

    @property
    @lru_cache()
    def volatility_window_simple(self):
        # TODO pandas好像并不支持分组上的移动窗口函数
        result = self._roll_std(self.pnl_simple_ratio("D"))
        result *= self._annual_factor ** 0.5
        return result

    @property
    @lru_cache()
    def volatility_window_compound(self):
        result = self._roll_std(self.pnl_compound_ratio("D"))
        result *= self._annual_factor ** 0.5
        return result

    @property
    @lru_cache()
    def volatility(self):
        ts = self.calculator_square(self.pnl_compound_ratio())
        result = (lambda x: int(abs(x) > FLOAT_ERR) * x)(self.calculator_variance(ts.sum())) ** 0.5
        result *= self._annual_factor ** 0.5  # annualize
        return result

    @property
    @lru_cache()
    def downside_risk(self):
        # TODO 计算并不正确
        ts = self.pnl_compound_ratio()
        mean = ts["rate"].mean()
        delta = ts["rate"] - mean
        delta = delta[delta < 0]
        print(delta, "\n", delta.count())
        result = (lambda x: int(abs(x) > FLOAT_ERR) * x)(
            self._annual_factor / delta.count() * (delta * delta).sum()) ** 0.5
        return result

    @property
    @lru_cache()
    def sharpe_ratio_window_simple(self):
        expected = self.ar_window_simple
        std = _deal_float_error(self.volatility_window_simple, fill=np.nan)  # 年化标准差
        std.total = self.volatility_window_simple.total
        result = expected / std
        return result

    @property
    @lru_cache()
    def sharpe_ratio_window_compound(self):
        expected = self.ar_window_compound
        std = _deal_float_error(self.volatility_window_compound, fill=np.nan)
        std.total = self.volatility_window_compound.total
        result = expected / std
        return result

    @property
    @lru_cache()
    def sharpe_ratio(self):
        return self.annual_return / self.volatility

    def sortino_ratio(self):
        return None

    def information_ratio(self):
        pass


class OrderAnalysis(WindowFactorPerformance):
    def __init__(self):
        super(OrderAnalysis, self).__init__()
        self._units = {}

    def _update_units(self, d):
        for key, value in d.items():
            self._units.update(dict.fromkeys(value, key))

    def apply_units(self, item):
        if isinstance(item, pd.DataFrame):
            return item.rename_axis(lambda x: x + self._units.get(x, ""), axis=0) \
                .rename_axis(lambda x: x + self._units.get(x, ""), axis=1)
        elif isinstance(item, pd.Series):
            return item.rename_axis(lambda x: x + self._units.get(x, ""), axis=0)
        else:
            return item

    @property
    @lru_cache()
    def order_details(self):
        self._orders["报单编号"] = self._orders["报单编号"].astype(int)
        df = self._orders[["报单编号", "合约", "买卖", "开平", "报单状态", "报单价格", "报单数", "未成交数",
                           "成交数",  "报单时间", "最后成交时间", "成交均价", "手续费"]]
        return df

    @property
    @lru_cache()
    def position_details(self, mode="avg"):
        """

        Args:
            mode(str):
            "avg" means maintain average price of position,
            "fifo" means the first the order was filled the first it was closed

        Returns:
            pandas.DataFrame
        """

        def side2sign(x):
            return (x == SIDE.BUY.value) * 2 - 1

        def side2direction(x):
            if x == SIDE.BUY.value:
                return DIRECTION.LONG.value
            elif x == SIDE.SELL.value:
                return DIRECTION.SHORT.value
            else:
                return DIRECTION.NONE.value

        def sign2direction(x):
            return DIRECTION.LONG.value if x >= 0 else DIRECTION.SHORT.value

        df = self.order_details.copy()
        addition = []
        for ticker, orders in df.groupby("合约"):
            temp = pd.DataFrame(index=orders.index)
            temp["持仓数量"] = (orders["成交数"] * orders["买卖"].apply(side2sign)).cumsum()
            temp["持仓方向"] = (temp["持仓数量"] >= 0).apply(sign2direction)
            market_values = []
            position_avx_prices = []
            profits = []
            market_value = 0
            position_avx_price = 0
            last_volume = 0
            for _, direction, volume in zip(orders.iterrows(), temp["持仓方向"].values, temp["持仓数量"].values):
                # TODO 未考虑反向开仓
                _, order = _
                if mode == "avg":
                    if last_volume * side2sign(order["买卖"]) >= 0:
                        market_value += order["成交数"] * order["成交均价"]
                        profits.append(np.nan)
                    else:
                        market_value -= order["成交数"] * position_avx_price  # 按持仓均价平仓
                        profits.append((position_avx_price - order["成交均价"]) * order["成交数"] * side2sign(order["买卖"]))
                    last_volume = volume
                    position_avx_price = market_value / volume if volume else 0
                    market_values.append(market_value)
                    position_avx_prices.append(position_avx_price)
                elif mode == "fifo":
                    return  # TODO fifo

            temp["持仓编号"] = (temp["持仓数量"] == 0).cumsum().shift(1).fillna(0) + 1  # TODO 未考虑反向开仓
            temp["持仓编号"] = temp["持仓编号"].astype(int)
            temp["市值"] = market_values
            temp["持仓均价"] = position_avx_prices
            temp["盈利"] = profits
            # cover commission to every pair of trade
            commission_sum = orders.groupby["持仓编号"].sum()
            commission_num = orders.groupby["持仓编号"].count()
            print(commission_sum)
            print(commission_num)
            commission_cover = commission_sum / commission_num
            temp["盈利"] -= temp["持仓编号"].map(lambda x: commission_cover[x])
            # cumsum profit
            temp["累积盈利"] = temp["盈利"].sum()
            addition.append(temp)
        position = pd.concat([df, pd.concat(addition, axis=0)],
                             axis=1)  # concat addition position info of all tickers with order info
        position.index = position["最后成交时间"]
        return position

    @lru_cache()
    def position_analysis(self, frequency="D", label="left"):
        return self.position_details.groupby("合约").resample(frequency, label=label).last().dropna()

    @lru_cache()
    def mv_analysis(self, frequency="D", label="left"):
        return self.position_analysis(frequency, label).groupby(level=1)["市值"].sum()

    @lru_cache()
    def pnl_analysis(self, frequency="MS", label="left"):
        now = self.equity.resample(frequency, closed="left", label=label).last().dropna()
        pre = now.shift(1).fillna(self.base)
        return (now - pre) / pre

    @property
    @lru_cache()
    def drawdown(self):
        return self.equity - self.equity.cummax()

    @property
    @lru_cache()
    def drawdown_ratio(self):
        return self.drawdown / self.equity.cummax()

    @property
    @lru_cache()
    def trade_summary(self):
        self._update_units({
            "(%s)" % self._currency: [
                u"总净利", u"总盈利", u"总亏损", u"平均每笔盈利", u"平均每笔亏损",
                u"单笔最大盈利", u"单笔最大亏损", u"最大连续盈利金额", u"最大连续亏损金额",
            ],
            "": [
                u"总盈利/总亏损", u"平均每笔盈利/平均每笔亏损", u"平均连续盈利次数",
                u"平均连续亏损次数"
            ],
            "%": [
                u"胜率"
            ]
        })
        # TODO 对股票的概述
        result = {}
        for ticker, trade in self.position_details.groupby("合约"):
            total = pd.DataFrame()
            group_by_id = trade.groupby("持仓编号")
            total["profit"] = group_by_id["盈利"].sum()
            total["direction"] = group_by_id["持仓方向"].first()  # 持仓方向
            total["volume"] = group_by_id["持仓数量"].agg(lambda s: abs(s).max())
            total["delta_time"] = group_by_id["最后成交时间"].last() - group_by_id["最后成交时间"].first()
            long_ = total[total["direction"] == DIRECTION.LONG.value]
            short = total[total["direction"] == DIRECTION.SHORT.value]
            temp = [total, long_, short]
            win = [t["profit"] >= 0 for t in temp]
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
            dct[u"总持仓时间"] = np.array([t["delta_time"].sum() for t in temp])
            dct[u"平均持仓时间"] = np.array([t["delta_time"].mean() for t in temp])
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
            dct[u"胜率"] = dct[u"总盈利次数"] / dct[u"总交易次数"]
            result[ticker] = pd.DataFrame(data=dct, index=[u"全部", u"多头", u"空头"]).T
        return result

    @property
    @lru_cache()
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
        dct[u"平均持仓时间"] = dct[u"总持仓时间"] / dct[u"总交易次数"]
        dct[u"胜率"] = dct[u"总盈利次数"] / dct[u"总交易次数"]
        orders = self.order_details
        start = orders["最后成交时间"].iloc[0]
        end = orders["最后成交时间"].iloc[-1]
        dct[u"交易天数"] = [_workdays(start, end), np.nan, np.nan]
        result = pd.DataFrame(data=dct).T
        return result

    @property
    @lru_cache()
    def strategy_summary(self):
        dct = OrderedDict()
        t_y = self.pnl_compound_log("AS")[-5:]
        pnl_y = t_y["rate"] / t_y["trade_days"] * self._annual_factor
        pnl_m = self.pnl_compound_log("MS")["rate"]
        dct[u"五年平均年收益"] = pnl_y.apply(_get_percent_from_log).mean()
        dct[u"年化收益标准差"] = self.volatility
        dct[u"平均月收益"] = pnl_m.apply(_get_percent_from_log).mean()
        dct[u"最大回撤率"] = - self.drawdown_ratio.min() * 100
        dct[u"夏普比率"] = self.sharpe_ratio
        if self.trade_summary_all[u"全部"][u"总亏损"] > FLOAT_ERR:
            dct[u"盈利因子"] = self.trade_summary_all[u"全部"][u"总盈利"] / self.trade_summary_all[u"全部"][u"总亏损"]
        else:
            dct[u"盈利因子"] = np.inf
        return pd.Series(dct)

    @property
    @lru_cache()
    def risk_indicator(self):
        self._update_units({
            "(%s)" % self._currency: [
                u"最大回撤金额"
            ],
            "(%)": [
                u"最大回撤比率"
            ]
        })
        dct = OrderedDict()
        dct[u"最大回撤金额"] = self.drawdown.min()
        dct[u"最大回撤比率"] = self.drawdown_ratio.min() * 100
        dct[u"最大回撤发生时间"] = self.drawdown_ratio.argmin()
        dct[u"净利回撤比"] = self.trade_summary_all[u"全部"][u"总净利"] / - dct[u"最大回撤金额"]
        dct[u"持仓时间比率"] = None
        return pd.Series(dct)

    @property
    @lru_cache()
    def pnl_indicator(self):
        self._update_units({
            "%s" % self._currency: [u"金额"],
            "%": [u"收益率[单利]", u"收益率[复利]"]
        })

        dct = dict()
        dct[u"初始资金"] = [self.base, 0, 0]
        if not self.equity.empty:
            dct[u"最新资金"] = [self.equity[-1], self.pnl_ratio[-1] * 100, self.pnl_ratio[-1] * 100]
            simple1 = self.pnl_simple_ratio("AS")["rate"][-1]
            compound1 = _get_percent_from_log(self.pnl_compound_log("AS")["rate"][-1])
            dct[u"年初至今"] = [self.base * (simple1 / 100), simple1, compound1]
            simple2 = self.pnl_simple_ratio("MS")["rate"][-1]
            compound2 = _get_percent_from_log(self.pnl_compound_log("MS")["rate"][-1])
            dct[u"当月收益"] = [self.base * (simple2 / 100), simple2, compound2]
            if len(self.pnl_simple_ratio("AS")) >= 2:
                simple3 = self.pnl_simple_ratio("AS")["rate"][-2]  # to percentage
                compound3 = _get_percent_from_log(self.pnl_compound_log("AS")["rate"][-2])
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

    @lru_cache()
    def csv(self):
        pass

    @lru_cache()
    def html(self):
        pass
