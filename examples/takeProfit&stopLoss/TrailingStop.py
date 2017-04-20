from functools import partial
from collections import defaultdict

import talib as ta
import numpy as np
from fxdayu.api import *
from datetime import datetime

MA_FAST_LEN = 10
MA_SLOW_LEN = 20
STOP_LEN = 5


def nan_array(*args):
    a = np.empty(args)
    a.fill(np.nan)
    return a


def initialize(context, data):
    context.s = "000001"
    context.security = symbol(context.s)
    context.ma_fast = defaultdict(partial(nan_array, 2))
    context.ma_slow = defaultdict(partial(nan_array, 2))
    context.stop_order = {}


def highest(data, s, length):
    return data.history(s, fields="close", length=length).max()


def lowest(data, s, length):
    return data.history(s, fields="close", length=length).min()


def entry(context, data, s, lot=1):
    def order_to(n):
        order_target(s, n)
        # cancel former stop_order
        sod = context.stop_order.pop(s, None)
        if sod:
            get_order(sod).cancel()
            # cancel_order(sod.id)

    dc = data.history(s, fields="close", length=MA_SLOW_LEN).values
    ma_fast = context.ma_fast[s]
    ma_slow = context.ma_slow[s]
    ma_fast[0] = ma_fast[1]
    ma_slow[0] = ma_slow[1]
    ma_fast[1] = ta.MA(dc, MA_FAST_LEN)[-1]
    ma_slow[1] = ta.MA(dc, MA_SLOW_LEN)[-1]
    if ma_fast[0] <= ma_slow[0] and ma_fast[1] > ma_slow[1]:
        order_to(lot)
        context.stop_order[s] = order(s, -lot, style=StopOrder(lowest(data, s, STOP_LEN)))
    elif ma_fast[0] >= ma_slow[0] and ma_fast[1] < ma_slow[1]:
        order_to(-lot)
        context.stop_order[s] = order(s, lot, style=StopOrder(highest(data, s, STOP_LEN)))


def place_stop_order(context, data, s, price):
    if s in context.stop_order:
        od = get_order(context.stop_order[s])
        if od:
            od.price = price
            od.send()
        # send_order(OrderReq())
    else:
        context.stop_order[s] = order_target(s, 0, style=StopOrder(price))


def trailing_stop(context, data, s):
    position = context.portfolio.positions.get(s, 0)
    if position > 0:
        place_stop_order(context, data, s, lowest(data, s, STOP_LEN))
    elif position < 0:
        place_stop_order(context, data, s, highest(data, s, STOP_LEN))


def handle_data(context, data):
    entry(context, data, context.s)
    trailing_stop(context, data, context.s)


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
