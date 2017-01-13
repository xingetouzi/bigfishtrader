import time
from weakref import proxy

from ctpgateway.myMainEngine import MyMainEngine
from ctpgateway.vtConstant import PRICETYPE_MARKETPRICE_, DIRECTION_LONG, DIRECTION_SHORT, OFFSET_OPEN, OFFSET_CLOSE
from ctpgateway.vtGateway import VtOrderReq

from bigfishtrader.engine.handler import HandlerCompose, Handler
from bigfishtrader.event import EVENTS, OPEN_ORDER, CLOSE_ORDER, FillEvent


class VnCtpMainEngine(MyMainEngine):
    def __init__(self, router, user_id, account):
        super(VnCtpMainEngine, self).__init__(user_id, account)
        self.router = proxy(router)

    def on_all_trade(self, order):
        self.router.on_fill(order)


class VnCtpRouter(HandlerCompose):
    def __init__(self, event_queue, account):
        super(VnCtpRouter, self).__init__()
        self._event_queue = event_queue
        self._main_engine = VnCtpMainEngine(self, "123", account)
        self._handlers = {
            "on_order": Handler(self.on_order, EVENTS.ORDER, topic=".", priority=0)
        }

    def on_order(self, event, kwargs=None):
        """
        :param event: order event
        :type event: bigfishtrader.event.OrderEvent
        :param kwargs:
        :return:
        """
        order_req = VtOrderReq()
        order_req.symbol = event.ticker
        order_req.exchange = "CFFEX"
        order_req.priceType = PRICETYPE_MARKETPRICE_  # TODO support limit order
        order_req.volume = abs(event.quantity)
        order_req.direction = DIRECTION_SHORT if (event.quantity < 0 and event.action == OPEN_ORDER) \
            or (event.quantity > 0 and event.action == CLOSE_ORDER) else DIRECTION_LONG
        order_req.offset = OFFSET_OPEN if event.action == OPEN_ORDER else OFFSET_CLOSE
        event.local_id = self._main_engine.sendOrder(order_req)

    def register(self, engine):
        self._main_engine.start()
        super(VnCtpRouter, self).register(engine)
        time.sleep(3)

    def unregister(self, engine):
        super(VnCtpRouter, self).unregister(engine)
        self._main_engine.stop()

    def on_fill(self, vt_order):
        """
        :param vt_order:
        :type vt_order: ctpgateway.vtGateway.VtOrderData
        :return:
        """
        print(vt_order.to_dict())
        fill_event = FillEvent(
            vt_order.orderTime,
            vt_order.symbol,
            OPEN_ORDER if vt_order.offset == OFFSET_OPEN else CLOSE_ORDER,
            vt_order.tradedVolume,
            vt_order.price,
        )
        self._event_queue.put(fill_event)
