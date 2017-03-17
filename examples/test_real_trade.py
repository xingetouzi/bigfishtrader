try:
    from Queue import PriorityQueue
except ImportError:
    from queue import PriorityQueue

from fxdayu.engine.core import Engine
from fxdayu.engine.handler import BigFishTrader
from fxdayu.middleware.timer import StatsdTimer
from fxdayu.operation import *
from fxdayu.order.handlers import OrderHandler
from fxdayu.portfolio.handlers import PortfolioHandler
from fxdayu.quotation.handlers import ArtificialTickHandler
from fxdayu.router.exchange import DummyExchange


class MyTrader(BigFishTrader):
    def __init__(self, event_queue, engine, price_handler, portfolio_handler, order_handler, trade_handler):
        super(MyTrader, self).__init__(event_queue, engine, price_handler, portfolio_handler, order_handler,
                                       trade_handler)
        self.bar_num = 0

    def on_tick(self, event, kwargs):
        """
        :param event: tick event
        :type event: bigfishtrader.event.TickEvent
        :param kwargs: other parameters
        :type kwargs: dict
        :return:
        """
        print (self.bar_num)
        if self.bar_num % 3 == 0:
            if self.bar_num % 6 == 0:
                open_position(event.ask, event.ticker, -1000)
            else:
                for position in self.portfolio.positions.copy().values():
                    close_position(
                        price=event.bid,
                        position=position,
                    )
        self.bar_num += 1


def run():
    event_queue = PriorityQueue()
    symbol = "rb1701"
    portfolio_handler = PortfolioHandler(event_queue)
    price_handler = ArtificialTickHandler(event_queue, symbol)
    trade_handler = DummyExchange(event_queue, price_handler)
    order_handler = OrderHandler()
    engine = Engine(event_queue=event_queue)
    timer = StatsdTimer(host="192.168.1.201")
    timer.register(engine)
    trader = MyTrader(event_queue, engine, price_handler, portfolio_handler,
                      order_handler, trade_handler)
    trader.run()


if __name__ == "__main__":
    run()
