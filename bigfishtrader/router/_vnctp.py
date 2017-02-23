import json
import logging
import time
from datetime import datetime
from weakref import proxy

from bigfishtrader.engine.handler import HandlerCompose, Handler
from bigfishtrader.event import EVENTS, OPEN_ORDER, CLOSE_ORDER, FillEvent, TickEvent
from bigfishtrader.vt.ctpGateway import EVENT_TICK
from bigfishtrader.vt.ctpGateway import MyMainEngine
from bigfishtrader.vt.ctpGateway import PRICETYPE_MARKETPRICE_, DIRECTION_LONG, DIRECTION_SHORT, OFFSET_OPEN, OFFSET_CLOSE, \
    STATUS_ALLTRADED, STATUS_UNKNOWN
from bigfishtrader.vt.ctpGateway import VtOrderReq


class VnCtpMainEngine(MyMainEngine):
    def __init__(self, router, user_id, account):
        super(VnCtpMainEngine, self).__init__(user_id, account)
        self.eventEngine.register(EVENT_TICK, self.on_tick)
        self.router = proxy(router)

    def onOrder(self, event):
        data = event.dict_["data"]
        if (data.frontID == long(self.gateway.tdApi.frontID)) and (
                    data.sessionID == long(self.gateway.tdApi.sessionID)):
            if data.vtOrderID in self.orders:
                if data.status != STATUS_UNKNOWN:
                    self.logger.info(u"Order:%s" % json.dumps(data.to_dict()))
                    if data.status == STATUS_ALLTRADED:
                        self.orders.remove(data.vtOrderID)
                        self.on_all_trade(data)
                else:
                    t_str = datetime.now().strftime("%Y-%m-%dT") + data.orderTime
                    logging.getLogger("trade").info("Order <Ref: %s, ID: %s> has been placed at %s" %
                                                    (data.orderID, data.orderID, t_str))

    def on_all_trade(self, order):
        self.router.on_fill(order)

    def on_tick(self, event):
        self.router.on_tick(event.dict_["data"])


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
                                                 or (
                                                     event.quantity > 0 and event.action == CLOSE_ORDER) else DIRECTION_LONG
        order_req.offset = OFFSET_OPEN if event.action == OPEN_ORDER else OFFSET_CLOSE
        event.exchange_id = self._main_engine.sendOrder(order_req)

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
        t_str = datetime.now().strftime("%Y%m%d") + vt_order.orderTime
        dt = datetime.strptime(t_str, "%Y%m%d%H:%M:%S")
        fill_event = FillEvent(
            dt,
            vt_order.symbol,
            OPEN_ORDER if vt_order.offset == OFFSET_OPEN else CLOSE_ORDER,
            vt_order.tradedVolume,
            vt_order.price,
        )
        fill_event.exchange_id = vt_order.orderID
        self._event_queue.put(fill_event)

    def on_tick(self, vt_ticker):
        """

        Args:
            vt_ticker(ctpgateway.vtGateway.VtTickData):

        Returns:
            pass

        """
        # TODO other attributes
        timestamp = datetime.strptime(vt_ticker.date + vt_ticker.time, "%Y%m%d%H:%M:%S.%f")
        tick = TickEvent(vt_ticker.symbol, timestamp, 0, 0)
        self._event_queue.put(tick)
