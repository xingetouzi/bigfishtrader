from bigfishtrader.operation import *

gap = 0.02


def initialize():
    set_commission(0.001, 0.001, 'value')
    set_slippage(0.001, 'pct')


def commission(order, price):
    print('commission = 3')
    return 3


def handle_data(account, data):
    now_time = current_time()
    if now_time.day == 5:
        positions = account.get_positions()
        if len(positions):
            for position in positions.values():
                close_limit(data['highMid'].values[-1] * (1 - gap), position=position)

        open_limit(get_ticker(), -1000, data['highMid'].values[-1] * (1 + gap))
