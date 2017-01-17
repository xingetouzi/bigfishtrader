# from bigfishtrader.quotation.oanda_quotation import OandaStream, OandaQuotation
from bigfishtrader.portfolio.handlers import PortfolioHandler
from bigfishtrader.engine.core import Engine
from bigfishtrader.router.oanda_exchange import OandaExchange
from bigfishtrader.data.support import MultiDataSupport
from bigfishtrader.portfolio.context import Context
from bigfishtrader.event import EVENTS
import oanda_strategy
import json
import oandapy
try:
    from Queue import PriorityQueue
except ImportError:
    from queue import PriorityQueue


def run(strategy, db_setting, account_info, trade_type='practice'):
    event_queue = PriorityQueue()

    engine = Engine(event_queue)

    # streamer = OandaStream(event_queue, account_info)
    # quotation.register(engine)

    portfolio_handler = PortfolioHandler(event_queue)
    portfolio_handler.register(engine)

    oanda_api = oandapy.API(account_info['environment'], account_info['access_token'])
    router = OandaExchange(oanda_api, event_queue, trade_type)
    router.register(engine)

    context = Context()
    context.register(engine)

    data_support = MultiDataSupport(context, **db_setting)
    data_support.register(engine)

    strategy.initialize_operation(event_queue, data_support, portfolio_handler.portfolio, engine, router)
    strategy.initialize(context, data_support)
    data_support.put_time_events(event_queue)

    def on_time(event, kwargs=None):
        strategy.handle_data(context, data_support)

    def on_test(event, kwargs=None):
        pass

    engine.register(on_time, EVENTS.TIME, '.', priority=90)
    engine.register(on_test, EVENTS.TIME, '.', priority=90)

    engine.start()
    engine.join()
    engine.stop()


if __name__ == '__main__':
    from datetime import datetime
    setting = {
        "host": "192.168.1.103",
        "port": 27018,
        "db": "Oanda",
    }

    account_info = json.load(open('D:/bigfishtrader/bigfish_oanda.json'))
    run(oanda_strategy, setting, account_info, 'paper')



