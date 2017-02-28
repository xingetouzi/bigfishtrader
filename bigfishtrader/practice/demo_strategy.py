from bigfishtrader.trader import Trader
from bigfishtrader.practice import settings, BACKTESTDEALMODE
from datetime import datetime
import pandas as pd


def initialize(context, data):
    pass


def handle_data(context, data):
    portfolio = context.portfolio
    positions = portfolio.positions

    if '000001' not in positions:
        portfolio.send_order('000001', 100, price=data.current('000001').low, sec_type='STK', order_type='LIMIT')
    else:
        if context.current_time.isoweekday() == 5:
            position = positions['000001']
            portfolio.send_order('000001', -position['quantity'])


if __name__ == '__main__':
    trader = Trader(settings)
    trader['data'].kwargs.update({'port': 10001})
    trader['router'].kwargs.update({'deal_model': BACKTESTDEALMODE.THIS_BAR_CLOSE})

    p = trader.initialize().back_test(
        __import__('p_strategy'),
        ['000001'], 'D', datetime(2016, 6, 1),
        ticker_type='HS'
    )

    print(pd.DataFrame(p.history_eqt))
    print(pd.DataFrame(
        [transaction.to_dict() for transaction in p.transactions]
    ))

