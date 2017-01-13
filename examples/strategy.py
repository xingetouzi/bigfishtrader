from bigfishtrader.operation import *

gap = 0.02


def initialize(context, data):
    set_commission(0.001, 0.001, 'value')
    set_slippage(0.001, 'pct')


def commission(order, price):
    print('commission = 3')
    return 3


def handle_data(context, data):
    now_time = data.current_time
    if now_time.day == 5:
        positions = get_positions()

        if len(positions):
            for position in positions.values():
                close_limit(data.current(context.ticker).high * (1 - gap), position=position)

        open_limit(context.ticker, -1000, data.current(context.ticker).high * (1 + gap))
