from queue import Empty
from bigfishtrader.event import BAR,ORDER,FILL,EXIT,LIMIT,STOP,CANCEL

class BackTest(object):

    def __init__(self,event_queue,strategy,price_handler,portfolio_handler,trader):
        self.event_queue=event_queue
        self.strategy=strategy
        self.price_handler=price_handler
        self.portfolio_handler=portfolio_handler
        self.portfolio=portfolio_handler.portfolio
        self.trader=trader

        self.handle={
            BAR:self._handle_bar,
            ORDER:self._handle_order,
            FILL:self._handle_fill,
            LIMIT:self._handle_order,
            STOP:self._handle_order,
            CANCEL:self.trader.on_cancel,
            EXIT:self._exit
        }




    def run(self,start=None,end=None):
        self.price_handler.initialize(start,end)
        self.strategy.initialize_operation(
            self.event_queue,self.price_handler,self.portfolio
        )

        while self.price_handler.running or self.event_queue.qsize():
            try:
                event=self.event_queue.get(timeout=0)
            except Empty:
                self.price_handler.next_stream()
            else:
                self.handle[event.type](event)

        return self.portfolio

    def _exit(self,event):

        for position in self.portfolio.positions.copy().values():
            self.portfolio.close_position(
                position.ticker,position.price,
                position.quantity,self.portfolio.current_time()
            )


    def _handle_bar(self,event):
        self.portfolio_handler.on_bar(event)
        self.strategy.handle_data(self.portfolio,self.price_handler.get_instance())

    def _handle_order(self,event):
        self.trader.on_order(event)

    def _handle_fill(self,event):
        self.portfolio_handler.on_fill(event)
