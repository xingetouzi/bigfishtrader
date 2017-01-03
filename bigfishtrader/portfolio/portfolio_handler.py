from bigfishtrader.portfolio.portfolio import Portfolio
from bigfishtrader.event import OPEN_ORDER,CLOSE_ORDER

class PortfolioHandler(object):
    '''
    This class is to handle Portfolio,
    including updating portfolio when a BAR, a TICK
    or a FILL event arrives
    '''

    def __init__(self,event_queue,init_cash=100000,portfolio=None):
        self.event_queue=event_queue
        self.portfolio=portfolio if portfolio is not None \
        else Portfolio(init_cash)

    def on_bar(self,event):
        self.portfolio.update_position(event.time,event.ticker,event.close)
        self.portfolio.log()

    def on_tick(self,event):
        pass

    def on_fill(self,event):
        if event.action==OPEN_ORDER:
            self.portfolio.open_position(
                event.ticker,event.price,
                event.quantity,event.time,
                event.commission
            )
        elif event.action==CLOSE_ORDER:
            self.portfolio.close_position(
                event.ticker,event.price,
                event.quantity,event.time,
            )


    def on_confirm(self,event):
        pass