from bigfishtrader.operation import *


def handle_data(account,data):
    index=data.index[-1]
    if index % 10 == 0:
        if len(account.positions):
            for position in account.positions.copy().values():
                close_position(
                    data.get_value(index,'closeMid'),
                    position=position
                )
        open_position(data.get_value(index,'highMid')*0.98,ticker(),-1000,STOP)

