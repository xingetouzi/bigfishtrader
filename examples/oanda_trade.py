import json

from pymongo import MongoClient
import oandapy

from bigfishtrader.engine.core import Engine
from bigfishtrader.router.oanda_exchange import OandaExchange
from bigfishtrader.data.support import MultiDataSupport
from bigfishtrader.context import Context
from bigfishtrader.portfolio.oanda_portfolio import OandaPortfolio
from bigfishtrader.oanda_api.Oanda_quotation import OandaQuotation
from bigfishtrader.event import EVENTS
import oanda_strategy

try:
    from Queue import PriorityQueue
except ImportError:
    from queue import PriorityQueue


def run(strategy, db_setting, account_info, trade_type='paper'):
    event_queue = PriorityQueue()

    engine = Engine(event_queue)

    context = Context()
    context.register(engine)

    data_support = MultiDataSupport(context, **db_setting)
    data_support.register(engine)

    portfolio = OandaPortfolio(init_cash=100000, data_support=data_support, client=MongoClient(port=10001))
    portfolio.register(engine)

    if trade_type == 'paper':
        oanda_api = oandapy.API(account_info['environment'], account_info['access_token'])
        router = OandaExchange(oanda_api, event_queue, data_support, trade_type)
        router.register(engine)
    else:
        router = OandaQuotation(event_queue, **db_setting)
        router.register(engine)


    strategy.initialize_operation(event_queue, data_support, portfolio, engine, router, context)
    strategy.initialize(context, data_support)
    if trade_type == 'paper':
        data_support.put_time_events(event_queue)
    else:
        router.init(tickers=data_support.tickers, **account_info)

    def on_time(event, kwargs=None):
        strategy.handle_data(context, data_support)

    engine.register(on_time, EVENTS.TIME, '.', priority=90)

    engine.start()
    if trade_type == 'paper':
        print('join')
        engine.join()
        print('stop')
        engine.stop()

        return portfolio

if __name__ == '__main__':
    setting = {
        "host": "localhost",
        "port": 10001,
        "db": "Oanda",
    }

    account_info = json.load(open('D:/bigfishtrader/bigfishtrader/oanda_api/bigfish_oanda.json'))
    portfolio = run(oanda_strategy, setting, account_info, 'trade')

    # print (pandas.DataFrame(portfolio.history))
    # positions = pandas.DataFrame([
    #     position.show() for position in portfolio.closed_positions
    # ])
    # print(positions)
    # print(positions['profit'].sum())





