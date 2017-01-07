# encoding: utf-8
try:
    from Queue import PriorityQueue
except ImportError:
    from queue import PriorityQueue

from datetime import datetime
from pymongo import MongoClient
import pandas as pd

from examples import strategy
from bigfishtrader.portfolio.handlers import PortfolioHandler
from bigfishtrader.quotation.handlers import MongoHandler
from bigfishtrader.router.exchange import DummyExchange
from bigfishtrader.engine.core import Engine
from bigfishtrader.backtest.engine_backtest import EngineBackTest
from bigfishtrader.middleware.timer import CountTimer


def run_backtest(collection, ticker, start, end):
    event_queue = PriorityQueue()
    portfolio_handler = PortfolioHandler(event_queue)
    price_handler = MongoHandler(collection, ticker, event_queue)
    router = DummyExchange(event_queue, price_handler)
    engine = Engine(event_queue=event_queue)
    timer = CountTimer()
    timer.register(engine)
    backtest = EngineBackTest(
        event_queue, engine, strategy,
        price_handler, portfolio_handler, router
    )

    portfolio = backtest.run(start, end)
    print(
        pd.DataFrame(portfolio.history)
    )

    positions = pd.DataFrame(
        [position.show() for position in portfolio.closed_positions]
    )

    print(positions)
    print('Total_profit ', positions['profit'].sum())
    print("Count of BAR %s" % timer.bar_counts)
    print("AVHT of BAR: %f seconds" % timer.avht_bar)
    print("Count of ORDER %s" % timer.order_counts)
    print("AVHT of ORDER: %f seconds" % timer.avht_order)

if __name__ == '__main__':
    import time

    st = time.time()
    run_backtest(
        MongoClient("192.168.1.103", port=27018).Oanda['EUR_USD.D'],
        'EUR_USD', datetime(2014, 1, 1), datetime(2015, 12, 31)
    )
    print("Total spending time: %s seconds" % (time.time() - st))
