import strategy
from bigfishtrader.portfolio.portfolio_handler import PortfolioHandler
from bigfishtrader.price_handler.mongo_handler import MongoHandler
from bigfishtrader.trader.dummy_exchange import DummyExchange
from bigfishtrader.backtest.simple_backtest import BackTest
from queue import PriorityQueue
from pymongo import MongoClient
from datetime import datetime

def run_backtest(collection,ticker,start,end):
    event_queue=PriorityQueue()
    portfolioHandler=PortfolioHandler(event_queue)
    trader=DummyExchange(event_queue)
    priceHandler=MongoHandler(collection,ticker,event_queue,trader)

    backTest=BackTest(
        event_queue,strategy,
        priceHandler,portfolioHandler,trader
    )


    portfolio=backTest.run(start,end)
    import pandas as pd

    print(
        pd.DataFrame(portfolio.history)
    )

    positions=pd.DataFrame(
            [position.show() for position in portfolio.closed_positions]
        )

    print(positions)
    print('Total_profit ',positions['profit'].sum())



if __name__ == '__main__':
    run_backtest(
        MongoClient(port=10001).Oanda['EUR_USD.D'],
        'EUR_USD',datetime(2014,1,1),datetime(2015,12,31)
    )
