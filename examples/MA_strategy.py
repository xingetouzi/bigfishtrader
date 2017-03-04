from datetime import datetime
from talib import abstract


fast = 10
slow = 15


def after_week_end(context, data):
    print context.current_time


def initialize(context, data):
    # context.time_schedule(
    #     after_week_end,
    #     context.time_rules(isoweekday=5),
    #     priority=0
    # )
    pass

def handle_data(context, data):
    portfolio = context.portfolio

    for ticker, position in portfolio.positions.items():
        if not data.can_trade(ticker):
            continue

        ma_fast = abstract.MA(data.history(ticker, 'D', length=fast + 1), timeperiod=fast, price='close').dropna()
        ma_slow = abstract.MA(data.history(ticker, 'D', length=slow + 1), timeperiod=slow, price='close').dropna()

        if ma_slow[0] < ma_fast[0] and ma_slow[1] > ma_fast[1]:
            portfolio.send_order(ticker, -position['quantity'])

    for ticker in context.tickers:
        if not data.can_trade(ticker):
            continue

        ma_fast = abstract.MA(data.history(ticker, 'D', length=fast + 1), timeperiod=fast, price='close').dropna()
        ma_slow = abstract.MA(data.history(ticker, 'D', length=slow + 1), timeperiod=slow, price='close').dropna()

        if ma_slow[0] > ma_fast[0] and ma_slow[1] < ma_fast[1]:
            portfolio.send_order(ticker, 1000)


if __name__ == '__main__':
    from bigfishtrader.trader import Trader, Optimizer
    from bigfishtrader.practice import BACKTESTDEALMODE

    trader = Trader()

    trader["data"].kwargs.update({'port': 10001})
    trader["router"].kwargs.update({'deal_model': BACKTESTDEALMODE.THIS_BAR_CLOSE})
    p = trader.initialize().back_test(
        __import__('MA_strategy'),
        ['000001', '600016'], 'D', datetime(2016, 1, 1),
        ticker_type='HS', params={'fast': 15, 'slow': 20}, save=True
    )

    for values in trader.output('strategy_summary', 'risk_indicator').values():
        print values

    # optimizer = Optimizer()
    # optimizer["data"].kwargs.update({'port': 10001})
    # optimizer["router"].kwargs.update({'deal_model': BACKTESTDEALMODE.THIS_BAR_CLOSE})
    # optimizer.optimization(
    #     __import__('MA_strategy'),
    #     ['000001', '600016'], 'D', datetime(2016, 1, 1),
    #     ticker_type='HS', save=True,
    #     fast=range(10, 15), slow=range(20, 30, 2)
    # )