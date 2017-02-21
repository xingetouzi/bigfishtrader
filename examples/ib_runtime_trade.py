# encoding: utf-8

import json
import logging
import logging.handlers
import time
from datetime import datetime, timedelta

import oanda_strategy as strategy
from bigfishtrader.data.support import MultiDataSupport
from bigfishtrader.engine.core import Engine
from bigfishtrader.event import EVENTS, OrderEvent, OPEN_ORDER, CLOSE_ORDER
from bigfishtrader.middleware.logger import LogRecorder
from bigfishtrader.portfolio.context import Context
from bigfishtrader.portfolio.handlers import PortfolioHandler
from bigfishtrader.router.ib import IbGateway

try:
    from Queue import PriorityQueue
except ImportError:
    from queue import PriorityQueue


class MyFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        ct = self.converter(record.created)
        if datefmt:
            s = time.strftime(datefmt, ct)
        else:
            # t = time.strftime("%Y-%m-%d %H:%M:%S", ct)
            s = datetime.now().isoformat()
        return s


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("trade")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
file_handler = logging.FileHandler(filename="ib_windows.log", encoding="utf-8", mode="w")
file_handler.setLevel(logging.INFO)
formatter = MyFormatter("%(asctime)-15s %(levelname)-8s %(message)s", datefmt=None)
handler.setFormatter(formatter)
file_handler.setFormatter(formatter)
logger.addHandler(handler)
logger.addHandler(file_handler)

last_trade = None
positions = {}
po = 0


def run(db_setting):
    symbol = "EURUSD"
    event_queue = PriorityQueue()
    engine = Engine(event_queue)

    # quotation.register(engine)
    log_recorder = LogRecorder("trade")
    log_recorder.register(engine)

    ib_router = IbGateway(engine, "ib")

    context = Context()
    context.register(engine)

    data_support = MultiDataSupport(context, **db_setting)
    data_support.register(engine)
    portfolio_handler = PortfolioHandler(event_queue, data_support)
    portfolio_handler.register(engine)
    strategy.initialize_operation(event_queue, data_support, portfolio_handler.portfolio, engine, ib_router)

    # strategy.initialize(context, data_support)

    # data_support.put_time_events(event_queue)

    def on_time(event, kwargs=None):
        strategy.handle_data(context, data_support)

    def on_test(event, kwargs=None):
        pass

    def on_tick_close(event, kwargs, id_=None):
        close_event = OrderEvent(
            datetime.now(),
            symbol,
            CLOSE_ORDER,
            1000,
        )
        close_event.exchange_id = id_
        event_queue.put(
            close_event
        )

    def sync_time():
        logger = logging.getLogger("trade")
        logger.info("Ask Timer")

    def on_tick(event, kwargs=None):
        global last_trade, po, positions
        if last_trade is None or event.time - last_trade >= timedelta(milliseconds=3000):
            if len(positions) == 0 and po == 0:
                last_trade = event.time
                po = 1
                open_event = OrderEvent(
                    datetime.now(),
                    symbol,
                    OPEN_ORDER,
                    20000,
                )
                event_queue.put(
                    open_event
                )
                positions = {1}
            elif len(positions) == 1 and po == 1:
                last_trade = event.time
                po = 0
                close_event = OrderEvent(
                    datetime.now(),
                    symbol,
                    CLOSE_ORDER,
                    20000,
                )
                event_queue.put(
                    close_event
                )
                positions = {}

    def on_fill(event, kwargs=None):
        print(event.to_dict())

    # register handlers
    engine.register(on_time, EVENTS.TIME, '.', priority=90)
    engine.register(on_test, EVENTS.TIME, '.', priority=90)
    engine.register(on_tick, EVENTS.TICK, '.', priority=0)
    # engine.register(partial(on_tick_close, id_="10610756920"), EVENTS.TICK, ".", priority=0)
    engine.register(on_fill, EVENTS.FILL, '.', priority=100)
    # start engine
    for item in engine._stream_manager.get_iter(EVENTS.ORDER, topic=""):
        print(item)
    engine.start()
    ib_router.register(engine)

    class SubReq(object):
        def __init__(self, s=None):
            self.symbol = s

    ib_router.ib_wrapper.connect()
    ib_router.subscribe(symbol)
    engine.join()
    engine.stop()


if __name__ == '__main__':
    setting = {
        "host": "127.0.0.1",
        "port": 27017,
        "db": "test",
    }
    run(setting)
