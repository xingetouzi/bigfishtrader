from bigfishtrader.operation import *
from datetime import datetime
import pandas as pd


def initialize(context, data):
    context.ticker = 'EUR_USD'
    context.period = 'H1'
    data.init(context.ticker, context.period, datetime(2016, 12, 1))
    set_ticker_info(EUR_USD={'lever': 10000, 'deposit_rate': 0.02})


def handle_data(context, data):
    if context.current_time.isoweekday() == 1 and context.current_time.hour == 1:
        open_position(context.ticker, 10)
    elif context.current_time.isoweekday() == 5:
        for order in get_orders().values():
            close_order(order.order_id, order.quantity)


@time_limit
def handle_day(context, data):
    print 'handler_day', context.current_time