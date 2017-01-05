from bigfishtrader.event import FillEvent,ORDER,LIMIT,STOP


class Simulation(object):

    def __init__(self,event_queue,price_handler,exchange=None,**ticker_information):
        self.event_queue=event_queue
        self.ticker_info=ticker_information
        self.exchange=exchange
        self.limits=[]
        self.stops=[]


    @staticmethod
    def calculate_commission(order):
        return 1

    def on_bar(self,event):
        self._fill_limit(event.ticker,event.high,event.low)
        self._fill_stop(event.ticker,event.high,event.low)



    def _fill_limit(self,ticker,high,low):
        for limit in self.limits:
            if limit.ticker==ticker:
                if limit.quantity>0 and limit.price>low:
                    self.limits.remove(limit)
                    self.on_order(limit)
                if limit.quantity<0 and limit.price<high:
                    self.limits.remove(limit)
                    self.on_order(limit)

    def _fill_stop(self,ticker,high,low):
        for stop in self.stops:
            if stop.ticker==ticker:
                if stop.quantity>0 and stop.price<high:
                    self.stops.remove(stop)
                    self.on_order(stop)
                if stop.quantity<0 and stop.price>low:
                    self.stops.remove(stop)
                    self.on_order(stop)

    def on_order(self,event):

        fill=FillEvent(
            event.time,event.ticker,event.action,
            event.quantity,event.price,
            self.calculate_commission(event),
            **self.ticker_info.get(event.ticker,{})
        )

        self.event_queue.put(fill)

    def on_cancel(self,event):
        for limit in self.limits:
            cancel=1
            for key,value in event.conditions.items():
                if getattr(limit,key,None)!=value:
                    cancel=0
                    break
            if cancel:
                self.limits.remove(limit)

        for stop in self.stops:
            cancel=1
            for key,value in event.conditions.items():
                if getattr(stop,key,None)!=value:
                    cancel=0
                    break
            if cancel:
                self.stops.remove(stop)



    def on_limit(self,event):
        self.limits.append(event)

    def on_stop(self,event):
        self.stops.append(event)