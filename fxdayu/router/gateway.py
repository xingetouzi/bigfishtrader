# encoding:utf-8
import logging

from fxdayu.engine.handler import HandlerCompose, Handler
from fxdayu.event import *
from fxdayu.adapter import VtAdapter


class Gateway(HandlerCompose):
    """
    信息交换网关
    """

    def __init__(self, eventEngine, gatewayName):
        """

        Args:
            eventEngine(fxdayu.engine.core.EventEngine):
            gatewayName:

        Returns:

        """
        super(Gateway, self).__init__()
        self.eventEngine = eventEngine
        self._handlers = {
            "on_order": Handler(self.send_order, EVENTS.ORDER, topic="", priority=0)
        }
        self.gatewayName = gatewayName

    def onTick(self, tick):
        """
        市场深度行情推送

        Args:
            tick(bigfishtrader.vt.vtGateway.VtTickData)

        Returns:
            None
        """
        tick_ = VtAdapter.transform(tick)
        event = TickEvent(tick_, topic=tick_.symbol)
        self.eventEngine.event_queue.put(event)

    def onTrade(self, trade):
        """
        订单执行回报

        Args:
            trade(bigfishtrader.vt.vtGateway.VtTradeData):
        """
        execution = VtAdapter.transform(trade)
        event = ExecutionEvent(execution)
        self.eventEngine.event_queue.put(event)

    def onOrder(self, order):
        """
        订单回报

        Args:
            order(bigfishtrader.vt.vtGateway.VtOrderData):
        """
        order_status = VtAdapter.transform(order)
        event = OrderStatusEvent(order_status, topic=order_status.gClOrderID)
        self.eventEngine.event_queue.put(event)

    def onPosition(self, position):
        """
        仓位信息回报

        Args:
            position(bigfishtrader.vt.vtGateway.VtPositionData):
        """
        position_ = VtAdapter.transform(position)
        event = PositionEvent(position, topic=position_.symbol)
        self.eventEngine.event_queue.put(event)

    def onAccount(self, action):
        """
        账户信息回报

        Args:
            action(bigfishtrader.vt.vtGateway.VtAccountData):

        Returns:
            None
        """
        pass

    def onError(self, error):
        """
        错误回报

        Args:
            error(bigfishtrader.vt.vtGateway.VtErrorData):

        Returns:
            None
        """
        logging.error(" ".join([
            error.gatewayName, error.errorTime, error.errorID,
            error.errorMsg, error.additionalInfo
        ]))

    def onLog(self, log):
        """
        记录日志

        Args:
            log(bigfishtrader.vt.vtGateway.VtLogData):

        Returns:
            None
        """
        logging.info(" ".join([
            log.gatewayName, log.logTime, log.logContent
        ]))

    def onContract(self, event):
        pass

    def send_order(self, event):
        pass

    def cancel_order(self, event):
        pass

    def qry_account(self):
        pass

    def qry_position(self):
        pass

    def close(self):
        pass
