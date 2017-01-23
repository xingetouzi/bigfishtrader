from bigfishtrader.portfolio.portfolio import Portfolio
from bigfishtrader.portfolio.context import Context
from bigfishtrader.engine.core import Engine
from bigfishtrader.router.exchange import DummyExchange
from bigfishtrader.data.support import TushareDataSupport
from bigfishtrader.data.support import MultiPanelData
from bigfishtrader.event import EVENTS
from Queue import PriorityQueue


def back_test(strategy, **params):
    event_queue = PriorityQueue()
    engine = Engine(event_queue)

    context = Context()
    context.register(engine)

    data = TushareDataSupport(MultiPanelData(context))
    data.register(engine)

    portfolio = Portfolio(data)
    portfolio.register(engine)

    router = DummyExchange(event_queue, data)
    router.register(engine)

    def on_time(event, kwargs=None):
        strategy.handle_data(context, data)

    engine.register(on_time, EVENTS.TIME, priority=100)

    strategy.initialize_operation(event_queue, data, portfolio, engine, router, context)

    strategy.initialize(context, data)

    data.put_time_event(event_queue)

    engine.start()

    engine.join()
    engine.stop()

    for ticker, position in portfolio.positions.items():
        portfolio.close_position(ticker, data.current(ticker)['close'], position.quantity, context.current_time)

    return portfolio
