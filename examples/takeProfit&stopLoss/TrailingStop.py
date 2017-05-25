from functools import partial
from collections import defaultdict

import talib as ta
import numpy as np
from fxdayu.api import *
from datetime import datetime

MA_FAST_LEN = 10
MA_SLOW_LEN = 20
STOP_LEN = 5
LOT = 100


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


def entry(context, data, s, lot=LOT):
    def order_to(n):
        sod = context.stop_order.pop(s, None)
        # cancel_order(sod.id)
        if sod:
            o = get_order(sod)
            if o.is_open:
                o.cancel()
                n *= 2
        order(s, n)
        # cancel former stop_order

    dc = data.history(s, fields="close", length=MA_SLOW_LEN).values
    ma_fast = context.ma_fast[s]
    ma_slow = context.ma_slow[s]
    ma_fast[0] = ma_fast[1]
    ma_slow[0] = ma_slow[1]
    try:
        ma_fast[1] = ta.MA(dc, MA_FAST_LEN)[-1]
        ma_slow[1] = ta.MA(dc, MA_SLOW_LEN)[-1]
    except:
        return
    if ma_fast[0] <= ma_slow[0] and ma_fast[1] > ma_slow[1]:
        order_to(lot)
    elif ma_fast[0] >= ma_slow[0] and ma_fast[1] < ma_slow[1]:
        order_to(-lot)


def place_stop_order(context, data, s, price, n):
    if s in context.stop_order:
        od = get_order(context.stop_order[s])
        if od:
            od.price = price
            od.send()
            # send_order(OrderReq())
    else:
        context.stop_order[s] = order(s, n, style=StopOrder(price))


def trailing_stop(context, data, s, lot=LOT):
    position = context.portfolio.positions.get(s, None)
    if position:
        # print(context.current_time, position.volume - position.frozenVolume)
        if position > 0:
            place_stop_order(context, data, s, lowest(data, s, STOP_LEN), -lot)
        elif position < 0:
            place_stop_order(context, data, s, highest(data, s, STOP_LEN), lot)
    else:
        pass
        # print(context.current_time, 0)


def handle_data(context, data):
    trailing_stop(context, data, context.s)
    entry(context, data, context.s)


if __name__ == '__main__':
    from fxdayu.trader import Trader
    import pandas as pd
    import logging

    logging.basicConfig(format='%(asctime)s - %(filename)s:%(lineno)s - %(name)s - %(message)s', level=logging.DEBUG)
    trader = Trader()
    trader["data"].kwargs = {
        "host": "192.168.0.12",
        "port": 27017,
    }
    pd.set_option("display.colheader_justify", "left")
    pd.set_option("display.width", 160)
    trader.back_test(__file__, {'HS': ['000001']}, "D", datetime(2014, 4, 1), datetime(2015, 1, 1))
    print trader.performance.equity
    print trader.performance.order_details
