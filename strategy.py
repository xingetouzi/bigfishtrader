from bigfishtrader.operation import *

ticker = 'EUR_USD'


def handle_data(account, data):
    index = data.index[-1]
    if index % 10 == 0:
        if len(account.positions):
            for position in account.positions.copy().values():
                # print(position.show())
                close_position(
                    data.get_value(index, 'closeMid'),
                    position=position
                )
        open_position(data.get_value(index, 'closeMid'), ticker, -1000)
