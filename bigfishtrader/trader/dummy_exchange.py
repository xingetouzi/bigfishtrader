from ..event import FillEvent,ORDER,LIMIT,STOP

class DummyExchange(object):
    """
    DummyExchange if a simulation of a real exchange.
    It handles OrderEvent(ORDER,LIMIT,STOP) and
    generate FillEvent which then be put into the event_queue
    """

    def __init__(self,event_queue,exchange_name=None,**ticker_information):
        '''

        :param event_queue:
        :param exchange_name:
        :param ticker_information: ticker={'lever':10000,'deposit_rate':0.02}
        :return:
        '''
        self.event_queue=event_queue
        self.ticker_info=ticker_information
        self.exchange_name=exchange_name
        self.orders=[]
        self.handle_order={
            ORDER:self._fill_order,
            LIMIT:self._fill_limit,
            STOP:self._fill_stop
        }

    @staticmethod
    def calculate_commission(order):
        return 1

    def _put_fill(self,order,price,timestamp):
        fill=FillEvent(
            timestamp,order.ticker,order.action,
            order.quantity,price,
            self.calculate_commission(order),
            **self.ticker_info.get(order.ticker,{})
        )
        self.orders.remove(order)
        self.event_queue.put(fill)

    def on_cancel(self,event):
        '''
        When a CancelEvent arrives, remove the orders that satisfy the event's condition
        :param event:
        :return:
        '''
        for order in self.orders:
            if order.match(event.conditions):
                self.orders.remove(order)

    def _fill_order(self,order,bar):
        self._put_fill(order,bar.open,bar.time)

    def _fill_limit(self,order,bar):
        if order.action:
            if order.quantity>0 and bar.low<order.price:
                price=order.price if bar.open>=order.price else bar.open
                self._put_fill(order,price,bar.time)
            elif order.quantity<0 and bar.high>order.price:
                price=order.price if bar.open<=order.price else bar.open
                self._put_fill(order,price,bar.time)
        else:
            self._fill_stop(order,bar)

    def _fill_stop(self,order,bar):
        if order.action:
            if order.quantity>0 and bar.high>order.price:
                price=order.price if bar.open<=order.price else bar.open
                self._put_fill(order,price,bar.time)
            elif order.quantity<0 and bar.low<order.price:
                price=order.price if bar.open>=order.price else bar.open
                self._put_fill(order,price,bar.time)
        else:
            self._fill_limit(order,bar)

    def on_order(self,event):
        '''
        When an order arrives put it into self.orders
        :param event:
        :return:
        '''
        self.orders.append(event)

    def on_bar(self,bar_event):
        '''
        When a bar arrive, execute orders that satisfy the fulfilled condition
        :param bar_event:
        :return:
        '''

        for order in self.orders:
            self.handle_order[order.type](order,bar_event)
