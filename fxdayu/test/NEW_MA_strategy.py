from datetime import datetime
from talib import abstract
import pandas as pd

fast = 10
slow = 15


def initialize(context, data):
    # context.time_schedule(
    #     after_week_end,
    #     context.time_rules(isoweekday=5),
    #     topic='.',
    #     priority=0
    # )
    context.set_commission(0.0007, 0.0007, min_cost=5)


def handle_data(context, data):
    portfolio = context.portfolio
    for sid in portfolio.positions.keys():
        ticker = symbol(sid).symbol
        if not data.can_trade(ticker):
            continue

        ma_fast = abstract.MA(data.history(ticker, 'D', length=fast + 1), timeperiod=fast, price='close').dropna()
        ma_slow = abstract.MA(data.history(ticker, 'D', length=slow + 1), timeperiod=slow, price='close').dropna()

        if ma_slow[0] < ma_fast[0] and ma_slow[1] > ma_fast[1]:
            order(sid, -1000)

    for ticker in context.tickers:
        sid = symbol(ticker).sid
        if not data.can_trade(ticker):
            continue

        ma_fast = abstract.MA(data.history(ticker, 'D', length=fast + 1), timeperiod=fast, price='close').dropna()
        ma_slow = abstract.MA(data.history(ticker, 'D', length=slow + 1), timeperiod=slow, price='close').dropna()

        if ma_slow[0] > ma_fast[0] and ma_slow[1] < ma_fast[1]:
            order(sid, 1000)
