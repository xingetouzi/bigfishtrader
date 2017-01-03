import strategy
from bigfishtrader.portfolio.portfolio_handler import PortfolioHandler
from bigfishtrader.price_handler.mongo_handler import MongoHandler
from bigfishtrader.trader.simulation import Simulation
from bigfishtrader.backtest.simple_backtest import BackTest
from queue import PriorityQueue
from pymongo import MongoClient
from datetime import datetime

def run_backtest(collection,ticker,start,end):
    event_queue=PriorityQueue()
    portfolioHandler=PortfolioHandler(event_queue)
    priceHandler=MongoHandler(collection,ticker,event_queue)
    trader=Simulation(event_queue,priceHandler)
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

    print (positions)
    print(positions['profit'].sum())



if __name__ == '__main__':
    run_backtest(
        MongoClient(port=10001).Oanda['EUR_USD.D'],
        'EUR_USD',datetime(2015,1,1),datetime(2015,12,31)
    )
