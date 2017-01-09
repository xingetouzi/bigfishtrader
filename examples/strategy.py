from bigfishtrader.operation import *

gap = 0.02


def initialize():
    set_commission(0.0001, 0.0001, 'value')
    set_slippage(0.0001, 'pct')


def handle_data(account, data):
    index = data.index[-1]
    if index % 10 == 0:
        if len(account.positions):
            for position in account.positions.copy().values():
                close_limit(data.get_value(index, 'highMid') * (1 - gap), position=position)

        open_limit(ticker(), -1000, data.get_value(index, 'highMid') * (1 + gap))
