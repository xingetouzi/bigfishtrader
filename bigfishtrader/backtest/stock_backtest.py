from bigfishtrader.portfolio.portfolio import NewPortfolio
from bigfishtrader.portfolio.context import Context
from bigfishtrader.engine.core import Engine
from bigfishtrader.router.exchange import DummyExchange
from bigfishtrader.data.support import TushareDataSupport
from bigfishtrader.event import EVENTS
try:
    from Queue import PriorityQueue
except ImportError:
    from queue import PriorityQueue


def back_test(strategy, **params):
    event_queue = PriorityQueue()
    engine = Engine(event_queue)

    context = Context()
    context.register(engine)

    data = TushareDataSupport(context)
    data.register(engine)

    portfolio = NewPortfolio(data)
    portfolio.register(engine)

    router = DummyExchange(event_queue, data)
    router.register(engine)

    def on_time(event, kwargs=None):
        strategy.handle_data(context, data)

    engine.register(on_time, EVENTS.TIME, priority=100)

    for key, value in params.items():
        setattr(strategy, key, value)

    strategy.initialize_operation(event_queue, data, portfolio, engine, router, context)

    strategy.initialize(context, data)

    data.put_time_event(event_queue)

    engine.start()

    engine.join()
    engine.stop()

    for position in portfolio.positions.copy().values():
        portfolio.close_position(position.ticker, data.current(position.ticker)['close'], position.quantity, context.current_time)

    return portfolio


def optimalize(strategy, *single, **params):
    try:
        key, param = params.popitem()

    except KeyError:
        params = dict(single)
        return [(params, back_test(strategy, **params))]

    result = []

    if isinstance(param, list):
        for p in param:
            s = [(key, p)]
            s.extend(single)
            result.extend(
                optimalize(strategy, *s, **params)
            )
    else:
        s = [(key, param)]
        s.extend(single)
        result.extend(
            optimalize(strategy, *s, **params)
        )
    return result

