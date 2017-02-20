# encoding:utf-8
from bigfishtrader.operation import *
from datetime import datetime
from talib import abstract

# 参数
fast = 10
slow = 20


def initialize(context, data):
    register_time_limit(after_week_end, topic='we', priority=50, isoweekday=5, hour=15, minute=0, second=0)
    context.target = []


def handle_data(context, data):
    for key, value in context.portfolio.security.items():
        if key not in context.target:
            close_position(key, value)

    for ticker in context.target:
        if ticker not in context.portfolio.security.keys():
            open_position(ticker, 1000, topic='this_bar')


@time_limit
def after_week_end(context, data):
    target = {}
    for ticker in context.tickers:
        if not data.can_trade(ticker):
            continue

        close = data.history(ticker, 'D', length=5)['close']
        up = close[-1]/close.min()
        if len(target) < 2:
            target[ticker] = up
            continue

        for key, value in target.copy().items():
            if value > up:
                target.pop(key)
                target[ticker] = up
                break

    context.target = list(target.keys())


if __name__ == '__main__':
    from bigfishtrader.trader import Trader
    import pandas

    # 使用trader启动策略，initialize改变默认的模块和方法，back_test进行回测并返回portfolio作为回测结果
    portfolio = Trader().initialize(
        data={'port': 10001}, portfolio={'init_cash': 200000}
    ).back_test(
        __import__('factors_strategy'),
        ['000001', '600016', '600036', '600000', '601166'], 'D',
        start=datetime(2016, 1, 1),
        ticker_type='HS'
    )
    print pandas.DataFrame(
        portfolio.history
    )

    # 输出订单信息
    print pandas.DataFrame(
        [position.show() for position in portfolio.closed_positions]
    )