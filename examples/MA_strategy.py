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
    from bigfishtrader.trader import Trader
    from bigfishtrader.practice import settings

    trader = Trader(settings)

    trader["data"].kwargs.update({'port': 27018, 'host': '192.168.0.103'})
    p = trader.initialize().back_test(
        __import__('MA_strategy'),
        ['000001'], 'D', datetime(2016, 1, 1),
        ticker_type='HS'
    )

    print pd.DataFrame(
        p.history_eqt
    )
    
    print pd.DataFrame(
        p.transactions
    )
