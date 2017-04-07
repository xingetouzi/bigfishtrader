from fxdayu.api import *


def initialize(context, data):
    context.ticker = symbol("000001")


def handle_data(context, data):
    position = context.portfolio.positions.get(context.ticker.sid, None)
    if position:
        print("p:%s" % position.volume)
    else:
        print("p:%s" % 0)
    order_target_percent(context.ticker, 1.0)


if __name__ == '__main__':
    from fxdayu.trader import Trader
    from datetime import datetime

    trader = Trader()
    trader["data"].kwargs = {
        "host": "192.168.0.103",
        "port": 27018,
    }
    trader.back_test(__file__, ['000001'], 'D', start=datetime(2016, 1, 1), ticker_type='HS',
                     params={'fast': 15, 'slow': 25})
    print trader.output("risk_indicator")
    print trader.performance.order_details