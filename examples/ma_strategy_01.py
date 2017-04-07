from fxdayu.api import *
from datetime import datetime
import talib

fast = 10
slow = 20


def initialize(context, data):
    context.ma = {}


def handle_data(context, data):
    calculate_ma(context, data)
    sell(context.ma, context.portfolio, data)
    buy(context.ma, data)


def calculate_ma(context, data):
    for ticker in context.tickers:
        if data.can_trade(ticker):
            context.ma[ticker] = {
                'fast': talib.MA(data.history(ticker, fields='close', length=fast + 1).values, fast),
                'slow': talib.MA(data.history(ticker, fields='close', length=slow + 1).values, slow)
            }


def buy(ma, data):
    for ticker, value in ma.items():
        if data.can_trade(ticker):
            f, s = value['fast'], value['slow']
            if f[-1] > s[-1] and (f[-2] < s[-1]):
                order_target_percent(ticker, 1.0)


def sell(ma, portfolio, data):
    for ticker in portfolio.positions:
        ticker = sid(ticker).symbol
        if data.can_trade(ticker):
            f, s = ma[ticker]['fast'], ma[ticker]['slow']
            if f[-1] < s[-1] and (f[-2] > s[-1]):
                order_target_percent(ticker, 0)


if __name__ == '__main__':
    from fxdayu.trader import Trader, Optimizer

    trader = Trader()
    trader["data"].kwargs = {
        "host": "192.168.0.103",
        "port": 27018,
    }
    trader.back_test(__file__, ['000001', '600000', '600016'], 'D', start=datetime(2016, 1, 1), ticker_type='HS',
                     params={'fast': 15, 'slow': 25}, save=True)
    print trader.output("risk_indicator")
    print trader.performance.order_details
