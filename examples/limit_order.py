from fxdayu.api import *
from datetime import datetime


def initialize(context, data):
    context.empty = 1
    context.symbol = symbol("000001")


def handle_data(context, data):
    # print data.history('000001', length=2)
    if context.empty:
        context.order = order('000001', 100, style=LimitOrder(data.current('000001').close * 0.99))
        # context.empty = 0
        print("Order:%s" % context.order)
        opens = get_open_orders(context.symbol)
        print(opens)
        for o in opens.values():
            o.cancel()

if __name__ == '__main__':
    from fxdayu.trader import Trader

    trader = Trader()
    trader["data"].kwargs = {
        "host": "192.168.0.103",
        "port": 27018,
    }
    trader.back_test(__file__, {'HS': ['000001']}, "D", datetime(2016, 1, 1), datetime(2016, 5, 1))
    print trader.modules['portfolio'].info
    print trader.performance.order_details
