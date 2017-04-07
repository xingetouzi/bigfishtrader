# encoding:utf-8

from fxdayu.engine.handler import HandlerCompose, Handler
from fxdayu.event import *
from fxdayu.adapter import VtAdapter
from fxdayu.context import InitializeMixin
from fxdayu.const import GatewayType


class Gateway(HandlerCompose, InitializeMixin):
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
        InitializeMixin.__init__(self)
        self.eventEngine = eventEngine
        self._handlers = {
            "on_order": Handler(self.send_order, EVENTS.ORDER, topic="", priority=0),
            "on_init": Handler(self.on_init, EVENTS.INIT, topic="", priority=0)
        }
        self.gatewayName = gatewayName
        self.context = None
        self.environment = None

    def onTick(self, tick):
        """
        市场深度行情推送

        Args:
            tick(fxdayu.vt.vtGateway.VtTickData)

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
            trade(fxdayu.vt.vtGateway.VtTradeData):
        """
        execution = VtAdapter.transform(trade)
        execution.account = self.context.account.id
        event = ExecutionEvent(execution)
        self.eventEngine.event_queue.put(event)

    def onOrder(self, order):
        """
        订单回报

        Args:
            order(fxdayu.vt.vtGateway.VtOrderData):
        """
        order_status = VtAdapter.transform(order)
        order_status.account = self.context.account.id
        event = OrderStatusEvent(order_status, topic=order_status.gClOrdID)
        self.eventEngine.event_queue.put(event)

    def onPosition(self, position):
        """
        仓位信息回报

        Args:
            position(fxdayu.vt.vtGateway.VtPositionData):
        """
        position_ = VtAdapter.transform(position)
        event = PositionEvent(position_, topic=position_.symbol)
        self.eventEngine.event_queue.put(event)

    def onAccount(self, account):
        """
        账户信息回报

        Args:
            account(fxdayu.vt.vtGateway.VtAccountData):

        Returns:
            None
        """
        account_ = VtAdapter.transform(account)
        event = AccountEvent(account_, topic=account_.gateway)
        self.eventEngine.event_queue.put(event)

    def onError(self, error):
        """
        错误回报

        Args:
            error(fxdayu.vt.vtGateway.VtErrorData):

        Returns:
            None
        """
        error = VtAdapter.transform(error)
        self.eventEngine.event_queue.put(ErrorEvent(error))

    def onLog(self, log):
        """
        记录日志

        Args:
            log(fxdayu.vt.vtGateway.VtLogData):

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
            contract(fxdayu.event.ContractData):

        Returns:
            None
        """
        req = VtAdapter.transform(contract)
        return self.subscribe(req)

    def send_order(self, event, kwargs=None):
        """

        Args:
            event(fxdayu.event.OrderEvent):
            kwargs:
        Returns:

        """
        order = event.data
        vt_order = VtAdapter.transform(order)
        vt_order_id = self.sendOrder(vt_order)
        order.gateway, order.clOrdID = vt_order_id.split(".")

    def on_init(self, event, kwargs=None):
        self.context = kwargs["context"]
        self.environment = kwargs["environment"]
        self.environment["subscribe"] = self.subscribe_contract

    def cancel_order(self, event):
        pass

    def qryAccount(self):
        pass

    def qryPosition(self):
        pass

    def close(self):
        pass
