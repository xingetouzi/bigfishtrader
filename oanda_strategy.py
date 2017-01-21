from bigfishtrader.operation import *
from datetime import datetime
import pandas as pd


def initialize(context, data):
    context.ticker = 'EUR_USD'
    context.period = 'H1'
    context.tickers = ['EUR_USD', 'USD_JPY']
    data.init(context.tickers, context.period, datetime(2016, 10, 1))
    data.subscribe(context.ticker, 'D', datetime(2016, 10, 1))
    set_ticker_info(EUR_USD={'lever': 10000, 'deposit_rate': 0.02})


def handle_data(context, data):

    if context.current_time.isoweekday() == 1 and context.current_time.hour == 1:
        # print(context.current_time)
        # print(data.current(context.ticker))
        # print(data.history(context.ticker, frequency=context.period, fields=['close', 'open'], length=3))
        # print(data.history(context.ticker, frequency='D', fields=['close', 'open', 'high', 'low'], length=3))
        # print(data.history(context.tickers, frequency=context.period, fields='close', length=3))

        current = data.current(context.ticker)
        open_limit(
            context.ticker, 10, current['low'], topic='oanda',
            take_profit=current['low']*1.01, stop_lost=current['low']*0.99)


@time_limit
def handle_day(context, data):
    print('handler_day', context.current_time)