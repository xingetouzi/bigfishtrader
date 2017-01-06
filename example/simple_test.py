# coding=utf-8

try:
    from Queue import PriorityQueue
except ImportError:
    from queue import PriorityQueue
from datetime import datetime

from pymongo import MongoClient

from example import strategy
from bigfishtrader.portfolio.portfolio_handler import PortfolioHandler
from bigfishtrader.price_handler.mongo_handler import MongoHandler
from bigfishtrader.trader.dummy_exchange import DummyExchange
from bigfishtrader.backtest.simple_backtest import BackTest


def run_backtest(collection, ticker, start, end):
    event_queue = PriorityQueue()
    portfolio_handler = PortfolioHandler(event_queue)
    trader = DummyExchange(event_queue)
    price_handler = MongoHandler(collection, ticker, event_queue, trader)
    back_test = BackTest(
        event_queue, strategy,
        price_handler, portfolio_handler, trader
    )

    portfolio = back_test.run(start, end, period=100)
    import pandas as pd

    print(
        pd.DataFrame(portfolio.history)
    )

    positions = pd.DataFrame(
        [position.show() for position in portfolio.closed_positions]
    )

    print(positions)
    print('Total_profit ', positions['profit'].sum())


if __name__ == '__main__':
    run_backtest(
        MongoClient("192.168.1.103", port=27018).Oanda['EUR_USD.D'],
        'EUR_USD', datetime(2014, 1, 1), datetime(2015, 12, 31)
    )
