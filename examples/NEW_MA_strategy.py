from datetime import datetime
from talib import abstract
import pandas as pd

fast = 10
slow = 15


def initialize(context, data):
    # context.time_schedule(
    #     after_week_end,
    #     context.time_rules(isoweekday=5),
    #     topic='.',
    #     priority=0
    # )
    context.set_commission(0.0007, 0.0007, min_cost=5)


def handle_data(context, data):
    portfolio = context.portfolio
    for sid in portfolio.positions.keys():
        ticker = symbol(sid).symbol
        if not data.can_trade(ticker):
            continue

        ma_fast = abstract.MA(data.history(ticker, 'D', length=fast + 1), timeperiod=fast, price='close').dropna()
        ma_slow = abstract.MA(data.history(ticker, 'D', length=slow + 1), timeperiod=slow, price='close').dropna()

        if ma_slow[0] < ma_fast[0] and ma_slow[1] > ma_fast[1]:
            order(sid, -1000)

    for ticker in context.tickers:
        sid = symbol(ticker).sid
        if not data.can_trade(ticker):
            continue

        ma_fast = abstract.MA(data.history(ticker, 'D', length=fast + 1), timeperiod=fast, price='close').dropna()
        ma_slow = abstract.MA(data.history(ticker, 'D', length=slow + 1), timeperiod=slow, price='close').dropna()

        if ma_slow[0] > ma_fast[0] and ma_slow[1] < ma_fast[1]:
            order(sid, 1000)


if __name__ == "__main__":
    import os
    import time
    from datetime import datetime

    import pandas as pd
    from fxdayu.trader.trader import Trader
    from fxdayu.event import EVENTS

    s = time.time()
    pwd = os.path.dirname(os.path.abspath(__file__))
    name = "NEW_MA_strategy"
    path = os.path.join(pwd, name + ".py")
    trader = Trader()
    trader["data"].kwargs.update({"port": 27018, "host": "192.168.0.103"})
    p = trader.initialize().back_test(
        path,
        ['000001'], 'D', datetime(2016, 1, 1),
        ticker_type='HS', fast=10, slow=15
    )
    # print(trader.engine.get_flows(EVENTS.TIME, "bar.open"))
    # print(trader.engine.get_flows(EVENTS.TIME, "bar.close"))
    # print(trader.engine.get_flows(EVENTS.TIME, ""))
    # print(trader.engine.get_flows(EVENTS.ORDER, ""))
    equity = (pd.DataFrame(
        p.info
    ))
    equity.to_csv(os.path.join(pwd, "result", "equity.csv"), index=False, encoding="utf-8")
    position = (pd.DataFrame(
        p.history)
    )
    position.to_csv(os.path.join(pwd, "result", "position.csv"), index=False, encoding="utf-8")
    execution = pd.DataFrame(trader.models["order_book_handler"].get_executions(method="df"))
    execution.to_csv(os.path.join(pwd, "result", "execution.csv"), encoding="utf-8")
    print(time.time() - s)
