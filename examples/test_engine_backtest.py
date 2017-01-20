# encoding: utf-8
try:
    from Queue import PriorityQueue
except ImportError:
    from queue import PriorityQueue

from datetime import datetime
from pymongo import MongoClient
import pandas as pd

import strategy
from bigfishtrader.portfolio.handlers import PortfolioHandler
from bigfishtrader.quotation.handlers import MongoHandler
from bigfishtrader.router.exchange import DummyExchange
from bigfishtrader.engine.core import Engine
from bigfishtrader.backtest.engine_backtest import EngineBackTest
from bigfishtrader.middleware.timer import CountTimer
from bigfishtrader.performance import WindowFactorPerformance, ReportSheet
from bigfishtrader.data.mongo_data_support import MongoDataSupport
from bigfishtrader.order.handlers import OrderBookHandler
from bigfishtrader.portfolio.context import Context


def run_backtest(collection, ticker, start, end, period='D'):
    event_queue = PriorityQueue()
    portfolio_handler = PortfolioHandler(event_queue)
    data_support = MongoDataSupport(**{'.'.join([ticker, period]): collection})
    price_handler = MongoHandler(collection, ticker, event_queue, fetchall=True, data_support=data_support)
    router = DummyExchange(event_queue, price_handler)
    order_handler = OrderBookHandler()
    context = Context()
    context.ticker = ticker
    engine = Engine(event_queue=event_queue)
    timer = CountTimer()
    timer.register(engine)
    backtest = EngineBackTest(
        event_queue, engine, strategy,
        price_handler, portfolio_handler,
        router, data_support, context
    )
    order_handler.register(engine)
    portfolio = backtest.run(start, end)

    # performance
    history = pd.DataFrame(portfolio.history)
    performance = ReportSheet()
    performance.set_equity(pd.Series(history["equity"].values, index=history["datetime"]))
    # print(pd.DataFrame([order.to_dict() for order in order_handler.orders.values()]))
    fills = pd.DataFrame([fill.to_dict() for fill in order_handler.fills.values()])
    performance.set_fills(fills)
    print(performance.equity)
    print(performance.trade_details)
    print(performance.trade_summary)
    print(performance.trade_summary_all)
    print(performance.pnl_indicator)
    print(performance.risk_indicator)
    print(performance.strategy_summary)
    # print(performance.ar_window_simple)
    # print(performance.volatility_window_simple)
    # print(performance.sharpe_ratio_window_simple)
    positions = pd.DataFrame(
        [position.show() for position in portfolio.closed_positions]
    )

    print(positions)
    print('Total_profit ', positions['profit'].sum() - positions["commission"].sum())
    print("Count of BAR %s" % timer.bar_counts)
    print("AVHT of BAR: %f nanoseconds" % timer.avht_bar)
    print("Count of ORDER %s" % timer.order_counts)
    print("AVHT of ORDER: %f nanoseconds" % timer.avht_order)


if __name__ == '__main__':
    import time

    st = time.time()
    run_backtest(
        MongoClient("192.168.1.103", port=27018).Oanda['EUR_USD.D'],
        'EUR_USD', datetime(2014, 1, 1), datetime(2015, 12, 31)
    )
    print("Total spending time: %s seconds" % (time.time() - st))
