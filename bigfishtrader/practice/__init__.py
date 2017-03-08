from bigfishtrader.trader import Component
from collections import OrderedDict
from bigfishtrader.practice._portfolio import Portfolio
from bigfishtrader.context import Context
from bigfishtrader.data.support import MultiDataSupport
from bigfishtrader.practice._dummy_exchange import PracticeExchange, BACKTESTDEALMODE
from bigfishtrader.engine.core import Engine
try:
    from Queue import PriorityQueue
except ImportError:
    from queue import PriorityQueue


basic = OrderedDict([
    ('event_queue', Component('event_queue', PriorityQueue, (), {})),
    ('engine', Component('engine', Engine, (), {'event_queue': Component.Lazy('event_queue')})),
    ('context', Component('context', Context, (), {})),
    ('data', Component('data', MultiDataSupport, (), {
        'context': Component.Lazy('context'),
        'event_queue': Component.Lazy('event_queue'),
        'port': 27017
    })),
    ('portfolio', Component('portfolio', Portfolio, (
        Component.Lazy("event_queue"), Component.Lazy("data")
    ), {})),
    ('router', Component('router', PracticeExchange, (), {
        'event_queue': Component.Lazy('event_queue'),
        'data': Component.Lazy('data'),
        'portfolio': Component.Lazy('portfolio')
    })),
])