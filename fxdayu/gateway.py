# encoding:utf-8

from fxdayu.adapter import VtAdapter
from fxdayu.context import ContextMixin, InitializeMixin
from fxdayu.engine.handler import HandlerCompose
from fxdayu.event import *


class Gateway(HandlerCompose, ContextMixin, InitializeMixin):
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
        ContextMixin.__init__(self)
        self.eventEngine = eventEngine
        self._handlers = {}
        self.gatewayName = gatewayName
        self._order_map_fx2vn = {}
        self._order_map_vn2fx = {}

    def onTick(self, tick):
        """
        市场深度行情推送

        Args:
            tick(fxdayu.vt.vtData.VtTickData)

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
            trade(fxdayu.vt.vtData.VtTradeData):
        """
        execution = VtAdapter.transform(trade)
        execution.account = self.context.account.id
        event = ExecutionEvent(execution)
        self.eventEngine.event_queue.put(event)

    def onOrder(self, order):
        """
        订单回报

        Args:
            order(fxdayu.vt.vtData.VtOrderData):
        """
        order_status = VtAdapter.transform(order)
        order_status.clOrdID = self._order_map_vn2fx.get(order_status.clOrdID, "")
        # TODO 过滤掉不在本次发出的订单
        order_status.account = self.context.account.id
        event = OrderStatusEvent(order_status, topic=order_status.gClOrdID)
        self.eventEngine.event_queue.put(event)

    def onPosition(self, position):
        """
        仓位信息回报

        Args:
            position(fxdayu.vt.vtData.VtPositionData):
        """
        position_ = VtAdapter.transform(position)
        event = PositionEvent(position_, topic=position_.symbol)
        self.eventEngine.event_queue.put(event)

    def onAccount(self, account):
        """
        账户信息回报

        Args:
            account(fxdayu.vt.vtData.VtAccountData):

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
            error(fxdayu.vt.vtData.VtErrorData):

        Returns:
            None
        """
        error = VtAdapter.transform(error)
        self.eventEngine.event_queue.put(ErrorEvent(error))

    def onLog(self, log):
        """
        记录日志

        Args:
            log(fxdayu.vt.vtData.VtLogData):

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

    def cancelOrder(self, orderReq):
        raise NotImplementedError

    def subscribe(self, subscribeReq):
        """

        Args:
            subscribeReq:

        Returns:

        """
        raise NotImplementedError

    def qryAccount(self):
        pass

    def qryPosition(self):
        pass

    def close(self):
        pass

    def subscribe_contract(self, contract):
        """

        Args:
            contract(fxdayu.event.ContractData):

        Returns:
            None
        """
        req = VtAdapter.transform(contract)
        return self.subscribe(req)

    def send_order(self, order):
        """

        Args:
            order(fxdayu.models.order.OrderReq):
        Returns:

        """
        vt_order = VtAdapter.transform(order)
        vt_order_id = self.sendOrder(vt_order)
        self._order_map_fx2vn[order.clOrdID] = vt_order_id
        self._order_map_vn2fx[vt_order_id] = order.clOrdID
        order.gateway, _ = vt_order_id.split(".")

    def cancel_order(self, cancel):
        """

        Args:
            cancel(fxdayu.models.order.CancelReq):

        Returns:

        """
        cancel.orderID = self._order_map_fx2vn.get(cancel.orderID, "")
        if cancel.orderID:
            gateway, cancel.orderID = cancel.orderID.split(".")
            cancel_req = VtAdapter.transform(cancel)
            self.cancelOrder(cancel_req)
        else:
            pass  # warning

    def link_context(self):
        self.environment.set_private("real_send_order", self.send_order)
        self.environment.set_private("real_cancel_order", self.cancel_order)
        self.environment["subscribe"] = self.subscribe_contract
