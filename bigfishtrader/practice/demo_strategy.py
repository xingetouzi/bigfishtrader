from bigfishtrader.trader import Trader, output
from bigfishtrader.practice import basic, BACKTESTDEALMODE
from datetime import datetime
import pandas as pd


def initialize(context, data):
    context.time_schedule(
        week_start,
        context.time_rules(isoweekday=1)
    )


def handle_data(context, data):
    portfolio = context.portfolio

    for symbol in ['000001', '600016', '600036']:
        portfolio.order_pct_to(symbol, 0.3)


def week_start(context, data):
    print context.portfolio.equity
    for symbol, position in context.portfolio.positions.items():
        print symbol
        print position
    print '----------------------------------------'


if __name__ == '__main__':
    trader = Trader()
    trader['data'].kwargs.update({'port': 10001})
    trader['router'].kwargs.update({'deal_model': BACKTESTDEALMODE.THIS_BAR_CLOSE})

    trader.back_test(
        __import__('demo_strategy'),
        ['000001', '600016', '600036'], 'D', datetime(2016, 1, 1),
        ticker_type='HS'
    )


