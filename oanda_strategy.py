from bigfishtrader.operation import *
from datetime import datetime
import pandas as pd


def initialize(context, data):
    context.ticker = 'EUR_USD'
    context.period = 'H1'
    context.modified = []
    data.init(context.ticker, context.period, datetime(2016, 10, 1))
    set_ticker_info(EUR_USD={'lever': 10000, 'deposit_rate': 0.02})


def handle_data(context, data):

    if context.current_time.isoweekday() == 1 and context.current_time.hour == 1:
        current = data.current(context.ticker)
        open_limit(
            context.ticker, 10, current['low'], topic='oanda',
            take_profit=current['low']*1.01, stop_lost=current['low']*0.99)

    # if context.current_time.isoweekday() == 2 and context.current_time.hour == 1:
    #     for _id, order in get_orders().items():
    #         order_modify(_id, stop_lost=order.stop_lost*1.001, take_profit=order.take_profit*0.999)


    # elif context.current_time.isoweekday() == 5:
    #     for order in get_positions().values():
    #         order_close(position=order)


@time_limit
def handle_day(context, data):
    print 'handler_day', context.current_time