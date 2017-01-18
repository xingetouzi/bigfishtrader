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


def run(strategy, db_setting, account_info, trade_type='paper'):
    event_queue = PriorityQueue()

    engine = Engine(event_queue)

    # streamer = OandaStream(event_queue, account_info)
    # quotation.register(engine)

    context = Context()
    context.register(engine)

    data_support = MultiDataSupport(context, **db_setting)
    data_support.register(engine)

    portfolio_handler = PortfolioHandler(event_queue, data_support)
    portfolio_handler.register(engine)

    oanda_api = oandapy.API(account_info['environment'], account_info['access_token'])
    router = OandaExchange(oanda_api, event_queue, data_support, trade_type)
    router.register(engine)

    strategy.initialize_operation(event_queue, data_support, portfolio_handler.portfolio, engine, router, context)
    strategy.initialize(context, data_support)
    data_support.put_time_events(event_queue)

    def on_time(event, kwargs=None):
        strategy.handle_data(context, data_support)

    engine.register(on_time, EVENTS.TIME, '.', priority=90)

    engine.start()
    print('join')
    engine.join()
    print('stop')
    engine.stop()

    return portfolio_handler.portfolio



if __name__ == '__main__':
    import pandas
    setting = {
        "host": "192.168.1.103",
        "port": 27018,
        "db": "Oanda",
    }

    account_info = json.load(open('D:/bigfishtrader/bigfish_oanda.json'))
    portfolio = run(oanda_strategy, setting, account_info, 'paper')

    print pandas.DataFrame(portfolio.history)
    print pandas.DataFrame([
        position.show() for position in portfolio.closed_positions
    ])





