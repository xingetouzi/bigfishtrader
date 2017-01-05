from bigfishtrader.operation import *

gap=0.02

def handle_data(account,data):
    index=data.index[-1]
    if index % 10 == 0:
        if len(account.positions):
            for position in account.positions.copy().values():
                close_position(
                    data.get_value(index,'closeMid'),
                    position=position
                )

        open_position(data.get_value(index,'highMid')*(1-0.02),ticker(),-1000,STOP)
