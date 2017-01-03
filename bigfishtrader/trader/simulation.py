from bigfishtrader.event import FillEvent


class Simulation(object):

    def __init__(self,event_queue,price_handler,exchange=None,**ticker_information):
        self.event_queue=event_queue
        self.price_handler=price_handler
        self.ticker_info=ticker_information
        self.exchange=exchange

    @staticmethod
    def calculate_commission(order):
        return 1

    def on_order(self,event):

        fill=FillEvent(
            event.time,event.ticker,event.action,
            event.quantity,event.price,
            self.calculate_commission(event),
            **self.ticker_info.get(event.ticker,{})
        )

        self.event_queue.put(fill)

