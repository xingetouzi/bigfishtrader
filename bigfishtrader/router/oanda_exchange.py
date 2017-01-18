import oandapy
import json
from bigfishtrader.event import EVENTS, FillEvent, OPEN_ORDER, CLOSE_ORDER, OrderEvent
from bigfishtrader.router.base import AbstractRouter
from bigfishtrader.engine.handler import Handler


class OandaExchange(AbstractRouter):
    def __init__(self, oanda_api, event_queue, data_support, trade_type='paper', **ticker_info):
        super(OandaExchange, self).__init__()
        self.event_queue = event_queue
        self.api = oanda_api
        self.data = data_support
        self.ticker_info = ticker_info
        self.order_handlers = {
            EVENTS.ORDER: self._handle_order,
            EVENTS.LIMIT: self._handle_limit,
            EVENTS.STOP: self._handle_stop
        }
        self.orders = {}

        if trade_type == 'paper':
            self.on_order = self.on_order_paper

        self._handlers["on_order"] = Handler(self.on_order, EVENTS.ORDER, topic="oanda", priority=0)
        self._handlers["on_time"] = Handler(self.on_time_paper, EVENTS.TIME, topic=".", priority=100)


    @staticmethod
    def calculate_commission(order, price):
        return 1

    @staticmethod
    def calculate_slippage(order, price):
        return 0

    def on_order_paper(self, event, kwargs=None):
        self.orders[event.local_id] = event

    def on_time_paper(self, event, kwargs=None):
        for order in self.orders.values():
            self.order_handlers[order.order_type](order)

    def _put_fill(self, _id, timestamp, ticker, action, quantity, price, commission, **kwargs):
        self.event_queue.put(
            FillEvent(
                timestamp, ticker, action,
                quantity, price, commission,
                topic='oanda', **kwargs
            )
        )
        self.orders.pop(_id, None)

    def _create_sl_tp(self, order):
        if order.stop_lost:
            self.orders[order.local_id] = OrderEvent(
                self.data.context.current_time, order.ticker, CLOSE_ORDER,
                order.quantity, order.stop_lost,EVENTS.STOP, topic='oanda'
            )

        if order.take_profit:
            self.orders[order.local_id] = OrderEvent(
                self.data.context.current_time, order.ticker, CLOSE_ORDER,
                order.quantity, order.take_profit, EVENTS.LIMIT, topic='oanda'
            )

    def _handle_order(self, order):
        current = self.data.current(order.ticker)
        self._put_fill(
            order.local_id, current['datetime'], order.ticker,
            order.action, order.quantity, current['open'],
            self.calculate_commission(order, current['open']),
            local_id=order.local_id, fill_type='order',
            position_id=order.local_id,
            **self.ticker_info.get(order.ticker, {})
        )
        self._create_sl_tp(order)

    def _handle_limit(self, order):
        current = self.data.current(order.ticker)
        if (order.quantity > 0) and (order.action == OPEN_ORDER) or \
                ((order.quantity < 0) and (order.action == CLOSE_ORDER)):
            if current['low'] <= order.price:
                price = current['open'] if current['open'] <= order.price else current['low']
                self._put_fill(
                    order.local_id, current['datetime'], order.ticker,
                    order.action, order.quantity, price,
                    self.calculate_commission(order, price),
                    local_id=order.local_id, fill_type='order',
                    position_id=order.local_id,
                    **self.ticker_info.get(order.ticker, {})
                )
                self._create_sl_tp(order)
        else:
            if current['high'] >= order.price:
                price = current['open'] if current['open'] >= order.price else current['high']
                self._put_fill(
                    order.local_id, current['datetime'], order.ticker,
                    order.action, order.quantity, price,
                    self.calculate_commission(order, price),
                    local_id=order.local_id, fill_type='order',
                    position_id=order.local_id,
                    **self.ticker_info.get(order.ticker, {})
                )
                self._create_sl_tp(order)

    def _handle_stop(self, order):
        current = self.data.current(order.ticker)
        if (order.quantity > 0) and (order.action == OPEN_ORDER) or \
                ((order.quantity < 0) and (order.action == CLOSE_ORDER)):
            if current['high'] >= order.price:
                price = current['open'] if current['open'] >= order.price else current['high']
                self._put_fill(
                    order.local_id, current['datetime'], order.ticker,
                    order.action, order.quantity, price,
                    self.calculate_commission(order, price),
                    local_id=order.local_id, fill_type='order',
                    position_id=order.local_id,
                    **self.ticker_info.get(order.ticker, {})
                )
                self._create_sl_tp(order)
        else:
            if current['low'] <= order.price:
                price = current['open'] if current['open'] <= order.price else current['low']
                self._put_fill(
                    order.local_id, current['datetime'], order.ticker,
                    order.action, order.quantity, price,
                    self.calculate_commission(order, price),
                    local_id=order.local_id, fill_type='order',
                    position_id=order.local_id,
                    **self.ticker_info.get(order.ticker, {})
                )
                self._create_sl_tp(order)

    def on_cancel(self, event, kwargs=None):
        pass

    def on_bar(self, bar_event, kwargs=None):
        pass

    def on_order(self, event, kwargs=None):
        pass

    def get_orders(self):
        return self.orders.copy()



if __name__ == '__main__':
    pass
