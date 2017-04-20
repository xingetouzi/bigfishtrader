import talib as ta
import numpy as np
from fxdayu.api import *
from datetime import datetime


def initialize(context, data):
    context.empty = 1
    context.s = "000001"
    context.security = symbol(context.s)
    context.ma10 = np.empty(2)
    context.ma10.fill(np.nan)
    context.ma20 = np.empty(2)
    context.ma20.fill(np.nan)


def handle_data(context, data):
    # print data.history('000001', length=2)
    dc = data.history(context.s, fields="close", length=20).values
    context.ma10[0] = context.ma10[1]
    context.ma20[0] = context.ma20[1]
    context.ma10[1] = ta.MA(dc, 10)[-1]
    context.ma20[1] = ta.MA(dc, 20)[-1]
    if context.ma10[0] <= context.ma20[0] and context.ma10[1] > context.ma20[1]:
        print(context.ma10, context.ma20)
        order_target(context.security, 1)
    elif context.ma10[0] >= context.ma20[0] and context.ma10[1] < context.ma20[1]:
        print(context.ma10, context.ma20)
        order_target(context.security, -1)
    position = context.portfolio.positions.get(context.s, 0)

if __name__ == '__main__':
    from fxdayu.trader import Trader
    import pandas as pd

    trader = Trader()
    trader["data"].kwargs = {
        "host": "192.168.0.103",
        "port": 27018,
    }
    pd.set_option("display.colheader_justify", "left")
    pd.set_option("display.width", 160)
    trader.back_test(__file__, {'HS': ['000001']}, "D", datetime(2016, 1, 1), datetime(2016, 5, 1))
    print trader.modules['portfolio'].info
    print trader.performance.order_details
