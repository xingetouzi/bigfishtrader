import copy
from weakref import proxy

from bigfishtrader.context import ORDERSTATUS
from bigfishtrader.engine.handler import HandlerCompose, Handler
from bigfishtrader.event import EVENTS
from bigfishtrader.models.data import OrderStatusData, ContractData


class AbstractOrderHandler(HandlerCompose):
    def __init__(self, context, environment):
        """

        Args:
            context:
            environment(bigfishtrader.environment.Environment):

        Returns:

        """
        super(AbstractOrderHandler, self).__init__()
        self.context = proxy(context)
        self.environment = proxy(environment)
        #  Order.clOrderID should be confirmed before this handler be called in working stream
        self._handlers["on_order"] = Handler(self.on_order, EVENTS.ORDER, topic=".", priority=-100)
        self._handlers["on_execution"] = Handler(self.on_execution, EVENTS.EXECUTION, topic=".", priority=-100)
        self._handlers["on_order_status"] = Handler(self.on_order_status, EVENTS.ORD_STATUS, topic=".", priority=-100)

    def on_order(self, order, kwargs=None):
        raise NotImplementedError

    def on_order_status(self, status, kwargs=None):
        raise NotImplementedError

    def on_execution(self, execution, kwargs=None):
        raise NotImplementedError


class OrderBookHandler(AbstractOrderHandler):
    def __init__(self, context, environment):
        super(OrderBookHandler, self).__init__(context, environment)
        self._orders = {}
        self._open_orders = {}
        self._executions = {}
        self._order_status = {}

    def on_order(self, event, kwargs=None):
        """
        Args:
            event(bigfishtrader.event.OrderEvent): order event
            kwargs(dict): other optional parameters

        Returns:

        """
        order = event.data
        if order.clOrdID:
            self._orders[order.gClOrdID] = order
            if order.gSymbol not in self._open_orders:
                self._open_orders[order.gSymbol] = []
            self._open_orders[order.gSymbol].append(order)
            status = OrderStatusData()
            status.exchange = order.exchange
            status.symbol = order.symbol
            status.clOrdID = order.clOrdID
            status.action = order.action
            status.side = order.side
            status.price = order.price
            status.orderQty = order.orderQty
            status.leavesQty = order.orderQty
            status.ordStatus = ORDERSTATUS.UNKNOWN.value
            status.gateway = order.gateway
            self._order_status[status.gClOrdID] = status
        else:
            pass  # TODO warning Order send failed

    def on_execution(self, event, kwargs=None):
        """

        Args:
            event(bigfishtrader.event.ExecutionEvent):
            kwargs:

        Returns:

        """
        execution = event.data
        self._executions[execution.execID] = event

    def on_order_status(self, event, kwargs=None):
        """

        Args:
            event(bigfishtrader.event.OrderStatusEvent):
            kwargs:

        Returns:
            None
        """
        status_new = event.data
        status_old = self._order_status[status_new.gClOrdID]
        status_old.status = status_new.status
        status_old.cumQty = status_new.cumQty
        status_old.leavesQty = status_new.leavesQty
        status_old.orderTime = status_new.orderTime
        status_old.cancelTime = status_new.cancelTime
        if status_new.status == ORDERSTATUS.ALLTRADED.value or status_new.status == ORDERSTATUS.CANCELLED.value:
            order = self._orders[status_new.gClOrdID]
            self._open_orders[order.gSymbol].remove(order)

    def get_order(self, order):
        return copy.copy(self._orders[order])

    def get_open_orders(self, contract):
        if isinstance(contract, ContractData):
            contract = contract.conId
        if contract is None:
            return copy.deepcopy(self._open_orders)
        elif contract in self._open_orders:
            return copy.deepcopy(self._open_orders[contract])
        else:
            return {}

    def link(self):
        self.environment.get_order = self.get_order
        self.environment.get_open_orders = self.get_open_orders
