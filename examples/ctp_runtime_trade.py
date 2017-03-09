# encoding: utf-8

import json
import logging
import logging.handlers
import time
from datetime import datetime, timedelta

import oanda_strategy as strategy
from ctpgateway.myMainEngine import TradeAccount
from fxdayu.data.support import MultiDataSupport
from fxdayu.engine.core import Engine
from fxdayu.event import EVENTS, OrderEvent, OPEN_ORDER, CLOSE_ORDER
from fxdayu.middleware.logger import LogRecorder
from fxdayu.portfolio.context import Context
from fxdayu.portfolio.handlers import PortfolioHandler
from fxdayu.router import VnCtpRouter

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
file_handler = logging.FileHandler(filename="ctp_windows.log", encoding="utf-8", mode="w")
file_handler.setLevel(logging.INFO)
formatter = MyFormatter("%(asctime)-15s %(levelname)-8s %(message)s", datefmt=None)
handler.setFormatter(formatter)
file_handler.setFormatter(formatter)
logger.addHandler(handler)
logger.addHandler(file_handler)

last_trade = None
po = 0


def run(db_setting, account_info):
    symbol = "IF1702"
    event_queue = PriorityQueue()
    engine = Engine(event_queue)

    # quotation.register(engine)

    portfolio_handler = PortfolioHandler(event_queue)
    portfolio_handler.register(engine)

    log_recorder = LogRecorder("trade")
    log_recorder.register(engine)

    account = TradeAccount("068709", "520lmj", "SIMNOW")
    ctp_router = VnCtpRouter(event_queue, account)

    context = Context()
    context.register(engine)

    data_support = MultiDataSupport(context, **db_setting)
    data_support.register(engine)
    strategy.initialize_operation(event_queue, data_support, portfolio_handler.portfolio, engine, ctp_router)
    strategy.initialize(context, data_support)

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

    def on_tick(event, kwargs=None):
        global last_trade, po

        if last_trade is None or event.time - last_trade >= timedelta(milliseconds=1000):
            positions = strategy.get_positions()
            if len(positions) == 0 and po == 0:
                last_trade = event.time
                po = 1
                open_event = OrderEvent(
                    datetime.now(),
                    symbol,
                    OPEN_ORDER,
                    1,
                )
                event_queue.put(
                    open_event
                )
            elif len(positions) == 1 and po == 1:
                last_trade = event.time
                po = 0
                close_event = OrderEvent(
                    datetime.now(),
                    symbol,
                    CLOSE_ORDER,
                    1,
                )
                close_event.exchange_id = positions[symbol].ticket
                event_queue.put(
                    close_event
                )

    def on_fill(event, kwargs=None):
        print(event.to_dict())

    # register handlers
    engine.register(on_time, EVENTS.TIME, '.', priority=90)
    engine.register(on_test, EVENTS.TIME, '.', priority=90)
    engine.register(on_tick, EVENTS.TICK, '.', priority=0)
    # engine.register(partial(on_tick_close, id_="10610756920"), EVENTS.TICK, ".", priority=0)
    engine.register(on_fill, EVENTS.EXECUTION, '.', priority=100)
    # start engine
    for item in engine._stream_manager.get_iter(EVENTS.ORDER, topic=""):
        print(item)
    engine.start()
    ctp_router.register(engine)

    class SubReq(object):
        def __init__(self, s=None):
            self.symbol = s

    ctp_router._main_engine.subscribe(SubReq(symbol))
    engine.join()
    engine.stop()


if __name__ == '__main__':
    setting = {
        "host": "127.0.0.1",
        "port": 27017,
        "db": "Oanda",
    }

    account_info = json.load(open('../fxdayu/bigfish_oanda.json'))
    run(setting, account_info)
