from fxdayu.const import EMPTY_STRING, EMPTY_UNICODE, EMPTY_FLOAT, EMPTY_INT
from fxdayu.models.meta import BaseData


class OrderStatusData(BaseData):
    __slots__ = ["symbol", "exchange", "clOrdID", "secondaryClOrdID",
                 "side", "account", "action", "price", "orderQty",
                 "cumQty", "leavesQty", "ordStatus", "orderTime",
                 "cancelTime", "gateway"]

    def __init__(self):
        self.symbol = EMPTY_STRING
        self.exchange = EMPTY_STRING
        self.account = EMPTY_STRING
        self.clOrdID = EMPTY_STRING
        self.secondaryClOrdID = EMPTY_STRING
        self.side = EMPTY_UNICODE
        self.action = EMPTY_UNICODE
        self.price = EMPTY_FLOAT
        self.orderQty = EMPTY_INT
        self.cumQty = EMPTY_INT
        self.leavesQty = EMPTY_INT
        self.ordStatus = EMPTY_STRING
        self.orderTime = EMPTY_STRING
        self.cancelTime = EMPTY_STRING
        self.gateway = EMPTY_STRING

    @property
    def gClOrdID(self):
        if self.secondaryClOrdID:
            return ".".join([self.gateway, self.account, self.clOrdID, self.secondaryClOrdID])
        else:
            return ".".join([self.gateway, self.account, self.clOrdID])

    @property
    def gSymbol(self):
        return ".".join([self.gateway, self.symbol])


class OrderReq(BaseData):
    """
    OrderReq is created by a strategy when it wants to open an order and
    will be handled by Simulation or Trade section
    """
    __slots__ = ["clOrdID", "exchange", "security", "symbol", "side", "action", "orderQty", "ordType", "price",
                 "stopPx", "timeInForce", "transactTime", "expireTime", "account", "gateway"]

    def __init__(self):
        super(OrderReq, self).__init__()
        self.clOrdID = EMPTY_STRING
        self.exchange = EMPTY_STRING
        self.security = None
        self.symbol = EMPTY_STRING
        self.side = EMPTY_UNICODE
        self.action = EMPTY_UNICODE
        self.orderQty = EMPTY_INT
        self.ordType = EMPTY_STRING
        self.price = EMPTY_FLOAT
        self.stopPx = EMPTY_FLOAT
        self.timeInForce = EMPTY_STRING
        self.transactTime = EMPTY_STRING  # create time
        self.expireTime = EMPTY_STRING
        self.account = EMPTY_STRING
        self.gateway = EMPTY_STRING

    @property
    def gClOrdID(self):
        return ".".join([self.gateway, self.account, self.clOrdID])

    @property
    def gSymbol(self):
        return ".".join([self.gateway, self.exchange, self.symbol])

    @property
    def gAccount(self):
        return ".".join([self.gateway, self.account])


class CancelReq(BaseData):
    __slots__ = ["orderID", "secondaryClOrdID"]

    def __init__(self, order_id):
        self.orderID = order_id
        self.secondaryClOrdID = EMPTY_STRING


class OrderGroupData(BaseData):
    __slots__ = ["orderID", "groupID"]

    def __init__(self):
        self.orderID = EMPTY_STRING
        self.groupID = EMPTY_INT
