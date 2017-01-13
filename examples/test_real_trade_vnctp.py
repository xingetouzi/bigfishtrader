try:
    from Queue import PriorityQueue
except ImportError:
    from queue import PriorityQueue

from ctpgateway.myMainEngine import TradeAccount

from bigfishtrader.engine.core import Engine
from bigfishtrader.engine.handler import BigFishTrader
from bigfishtrader.middleware.timer import StatsdTimer
from bigfishtrader.operation import *
from bigfishtrader.order.handlers import OrderHandler
from bigfishtrader.portfolio.handlers import PortfolioHandler
from bigfishtrader.quotation.handlers import ArtificialTickHandler
from bigfishtrader.router import VnCtpRouter


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
        # print (self.bar_num)
        if self.bar_num % 3 == 0:
            if self.bar_num % 6 == 0:
                print("haha")
                open_position(event.ask, event.ticker, 1)
            else:
                print("hehe")
                for position in self.portfolio.positions.copy().values():
                    close_position(
                        price=event.bid,
                        position=position,
                    )
        self.bar_num += 1


def run():
    event_queue = PriorityQueue()
    symbol = "IF1701"
    account = TradeAccount("068709", "520lmj", "SIMNOW")
    trade_handler = VnCtpRouter(event_queue, account)
    portfolio_handler = PortfolioHandler(event_queue)
    price_handler = ArtificialTickHandler(event_queue, symbol, interval=1000)
    order_handler = OrderHandler()
    engine = Engine(event_queue=event_queue)
    timer = StatsdTimer(host="192.168.1.201")
    timer.register(engine)
    trader = MyTrader(event_queue, engine, price_handler, portfolio_handler,
                      order_handler, trade_handler)
    trader.run()


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.FATAL)
    run()
