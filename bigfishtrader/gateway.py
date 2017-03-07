# encoding:utf-8

from bigfishtrader.engine.handler import HandlerCompose, Handler
from bigfishtrader.event import *
from bigfishtrader.adapter import VtAdapter
from bigfishtrader.const import GATEWAY


class Gateway(HandlerCompose):
    """
    信息交换网关
    """

    def __init__(self, eventEngine, gatewayName):
        """

        Args:
            eventEngine(bigfishtrader.engine.core.EventEngine):
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
        event = PositionEvent(position_, topic=position_.symbol)
        self.eventEngine.event_queue.put(event)

    def onAccount(self, account):
        """
        账户信息回报

        Args:
            account(bigfishtrader.vt.vtGateway.VtAccountData):

        Returns:
            None
        """
        account_ = VtAdapter.transform(account)
        event = AccountEvent(account_, topic=account_.accountID)
        self.eventEngine.event_queue.put(event)

    def onError(self, error):
        """
        错误回报

        Args:
            error(bigfishtrader.vt.vtGateway.VtErrorData):

        Returns:
            None
        """
        error = VtAdapter.transform(error)
        self.eventEngine.event_queue.put(ErrorEvent(error))

    def onLog(self, log):
        """
        记录日志

        Args:
            log(bigfishtrader.vt.vtGateway.VtLogData):

        Returns:
            None
        """
        log_ = VtAdapter.transform(log)
        self.eventEngine.event_queue.put(LogEvent(log_))

    def onContract(self, event):
        pass

    def sendOrder(self, orderReq):
        """

        Args:
            orderReq:

        Returns:
            str: clOrderID
        """
        raise NotImplementedError

    def subscribe(self, subscribeReq):
        """

        Args:
            subscribeReq:

        Returns:

        """
        raise NotImplementedError

    def subscribe_contract(self, contract):
        """

        Args:
            contract(bigfishtrader.event.ContractData):

        Returns:
            None
        """
        req = VtAdapter.transform(contract)
        return self.subscribe(req)

    def send_order(self, event, kwargs=None):
        """

        Args:
            event(bigfishtrader.event.OrderEvent):
            kwargs:
        Returns:

        """
        order = event.data
        vt_order = VtAdapter.transform(order)
        vt_order_id = self.sendOrder(vt_order)
        order.gateway, order.clOrdID = vt_order_id.split(".")

    def cancel_order(self, event):
        pass

    def qryAccount(self):
        pass

    def qryPosition(self):
        pass

    def close(self):
        pass
