from datetime import datetime
from talib import abstract
import pandas as pd


fast = 10
slow = 15


def after_week_end(context, data):
    print context.current_time


def initialize(context, data):
    context.time_schedule(
        after_week_end,
        context.time_rules(isoweekday=5),
        priority=0
    )
    context.set_commission(0.0007, 0.0007, min_cost=5)


def handle_data(context, data):
    portfolio = context.portfolio

    for ticker in portfolio.security:
        if not data.can_trade(ticker):
            continue

        ma_fast = abstract.MA(data.history(ticker, 'D', length=fast+1), timeperiod=fast, price='close').dropna()
        ma_slow = abstract.MA(data.history(ticker, 'D', length=slow+1), timeperiod=slow, price='close').dropna()

        if ma_slow[0] < ma_fast[0] and ma_slow[1] > ma_fast[1]:
            portfolio.send_close(ticker)

    for ticker in context.tickers:
        if not data.can_trade(ticker):
            continue

        ma_fast = abstract.MA(data.history(ticker, 'D', length=fast+1), timeperiod=fast, price='close').dropna()
        ma_slow = abstract.MA(data.history(ticker, 'D', length=slow+1), timeperiod=slow, price='close').dropna()

        if ma_slow[0] > ma_fast[0] and ma_slow[1] < ma_fast[1]:
            portfolio.send_open(ticker, 1000)



if __name__ == '__main__':
    from bigfishtrader.trader import PracticeTrader

    trader = PracticeTrader()

    p = trader.initialize(data={'port': 10001}).back_test(
        __import__('MA_strategy'),
        ['000001'], 'D', datetime(2016, 1, 1),
        ticker_type='HS'
    )

    print pd.DataFrame(
        p.info
    )

    print pd.DataFrame(
        p.trades
    )




