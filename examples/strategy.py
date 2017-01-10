from bigfishtrader.operation import *

gap = 0.02


def initialize():
    set_commission(0.0001, 0.0001, 'value')
    set_slippage(0.0001, 'pct')


def handle_data(account, data):
    index = data.index[-1]
    if index % 10 == 0:
        positions = account.get_positions()
        if len(positions):
            for position in positions.values():
                close_limit(data.get_value(index, 'highMid') * (1 - gap), position=position)

        open_limit(get_ticker(), -1000, data.get_value(index, 'highMid') * (1 + gap))
