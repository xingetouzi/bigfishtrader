from fxdayu.const import EMPTY_STRING, EMPTY_UNICODE, EMPTY_FLOAT, EMPTY_INT
from fxdayu.models.meta import BaseData


class OrderStatusData(BaseData):
    def __init__(self):
        self.gateway = EMPTY_STRING
        self.account = EMPTY_STRING
        self.clOrdID = EMPTY_STRING
        self.secondaryClOrdID = EMPTY_STRING
        self.exchange = EMPTY_STRING

        self.side = EMPTY_UNICODE
        self.action = EMPTY_UNICODE
        self.symbol = EMPTY_STRING
        self.price = EMPTY_FLOAT
        self.orderQty = EMPTY_INT
        self.cumQty = EMPTY_INT
        self.leavesQty = EMPTY_INT
        self.ordStatus = EMPTY_STRING
        self.orderTime = None
        self.cancelTime = None

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
    def __init__(self):
        super(OrderReq, self).__init__()
        self.account = EMPTY_STRING
        self.gateway = EMPTY_STRING
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
        self.transactTime = None  # create time
        self.expireTime = None

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
    def __init__(self, order_id):
        self.orderID = order_id
        self.secondaryClOrdID = EMPTY_STRING


class OrderGroupData(BaseData):
    def __init__(self):
        self.orderID = EMPTY_STRING
        self.groupID = EMPTY_INT
