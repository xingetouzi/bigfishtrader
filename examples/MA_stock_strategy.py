# encoding:utf-8
from bigfishtrader.operation import *
from datetime import datetime
from talib import abstract

# 参数
fast = 10
slow = 20


def initialize(context, data):
    pass


def handle_data(context, data):
    for ticker in context.tickers:
        # 计算MA，先从data中取出数据然后用talib.abstract.Ma()计算
        # 计算出的数据为Series或DataFrame，以时间为索引，一般含有nan用dropna()去除
        fast_ma = abstract.MA(data.history(ticker, 'D', length=fast+1), timeperiod=fast).dropna()
        slow_ma = abstract.MA(data.history(ticker, 'D', length=slow+1), timeperiod=slow).dropna()

        # 判断金叉
        if (fast_ma[-1] > slow_ma[-1]) and (fast_ma[-2] < slow_ma[-2]):
            # 买入1000股(1000手)
            print context.current_time, 'gold', ticker
            # topic='this_bar' 表示在当前bar的收盘价结算, 一般默认是在下一根bar开盘结算
            open_position(ticker, 1000, topic='this_bar')

        # 死叉
        elif (fast_ma[-1] < slow_ma[-1]) and (fast_ma[-2] > slow_ma[-2]):
            # 如果当前持有的ticker的可交易数量不为0, 全部卖出
            print context.current_time, 'death', ticker
            available = context.portfolio.security.get(ticker, 0)
            if available:
                close_position(ticker, available, topic='this_bar')


@time_limit
def after_market_close(context, data):
    print context.current_time


if __name__ == '__main__':
    from bigfishtrader.trader import Trader
    import pandas

    # 使用trader启动策略，initialize改变默认的模块和方法，back_test进行回测并返回portfolio作为回测结果
    portfolio = Trader().initialize(
        data={'port': 10001}, portfolio={'init_cash': 20000}
    ).back_test(
        __import__('MA_stock_strategy'),
        ['000001', '600016'], 'D',
        start=datetime(2016, 1, 1),
        ticker_type='HS'
    )

    # 输出订单信息
    print pandas.DataFrame(
        [position.show() for position in portfolio.closed_positions]
    )