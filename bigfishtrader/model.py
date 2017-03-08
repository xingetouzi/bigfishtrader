# encoding: utf-8

from collections import OrderedDict
from datetime import datetime

import numpy as np

from bigfishtrader.const import EMPTY_INT, EMPTY_STRING, EMPTY_UNICODE, EMPTY_FLOAT


class BaseData(object):
    __slots__ = []

    def to_dict(self, ordered=False):
        """

        Args:
            ordered: whether to use OrderedDict

        Returns:
            dict | OrderedDict : represent the data with dict
        """
        if ordered:
            return OrderedDict([(attr, getattr(self, attr)) for attr in self.__slots__])
        else:
            return {attr: getattr(self, attr) for attr in self.__slots__}


class TickData(BaseData):
    """
    tick quotation data, namely market depth data
    """
    __slots__ = ["symbol", "exchange", "lastPrice", "lastVolume", "volume", "openInterest",
                 "time", "date", "openPrice", "highPrice", "lowPrice", "preClose", "vwapPrice",
                 "upperLimit", "lowerLimit", "depth", "askPrice", "bidPrice", "askVolume", "bidVolume"]
    MAX_DEPTH = 10

    def __init__(self, depth=MAX_DEPTH):
        # ticker
        self.symbol = EMPTY_STRING
        self.exchange = EMPTY_STRING

        # trade
        self.lastPrice = EMPTY_FLOAT
        self.lastVolume = EMPTY_INT
        self.volume = EMPTY_INT
        self.openInterest = EMPTY_INT
        self.time = EMPTY_STRING
        self.date = EMPTY_STRING

        # quotation
        self.openPrice = EMPTY_FLOAT
        self.highPrice = EMPTY_FLOAT
        self.lowPrice = EMPTY_FLOAT
        self.preClose = EMPTY_FLOAT
        self.vwapPrice = EMPTY_FLOAT

        # limit
        self.upperLimit = EMPTY_FLOAT
        self.lowerLimit = EMPTY_FLOAT

        # depth
        self.depth = depth
        self.askPrice = np.empty(self.depth)
        self.askPrice.fill(np.nan)
        self.bidPrice = np.empty(self.depth)
        self.bidPrice.fill(np.nan)
        self.askVolume = np.empty(self.depth)
        self.askVolume.fill(np.nan)
        self.bidVolume = np.empty(self.depth)
        self.bidVolume.fill(np.nan)

    @property
    def gSymbol(self):
        return self.symbol + "." + self.exchange


class OrderData(BaseData):
    __slots__ = ["orderReq", "orderStatus"]

    def __init__(self):
        self.orderReq = None
        self.orderStatus = None

    def to_dict(self, ordered=False):
        dct = self.orderReq.to_dict(ordered)
        dct.update(**self.orderStatus.to_dict(ordered))
        return dct


class OrderStatusData(BaseData):
    __slots__ = ["symbol", "exchange", "clOrdID", "secondaryClOrdID",
                 "side", "action", "price", "orderQty",
                 "cumQty", "leavesQty", "ordStatus", "orderTime",
                 "cancelTime", "gateway"]

    def __init__(self):
        self.symbol = EMPTY_STRING
        self.exchange = EMPTY_STRING

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
            return ".".join([self.gateway, self.secondaryClOrdID, self.clOrdID])
        else:
            return self.gateway + "." + self.clOrdID


class OrderReq(BaseData):
    """
    OrderReq is created by a strategy when it wants to open an order and
    will be handled by Simulation or Trade section
    """
    __slots__ = ["clOrdID", "exchange", "symbol", "secType", "side", "action", "orderQty", "ordType", "price",
                 "tradedQty", "timeInForce", "transactTime", "expireTime", "account", "slippage", "gateway", "time"]

    def __init__(self):
        super(OrderReq, self).__init__()
        self.clOrdID = EMPTY_STRING
        self.exchange = EMPTY_STRING
        self.symbol = EMPTY_STRING
        self.secType = EMPTY_STRING
        self.side = EMPTY_UNICODE
        self.action = EMPTY_UNICODE
        self.orderQty = EMPTY_INT
        self.ordType = EMPTY_STRING
        self.price = EMPTY_FLOAT
        self.tradedQty = EMPTY_FLOAT
        self.timeInForce = EMPTY_STRING
        self.transactTime = EMPTY_STRING
        self.expireTime = EMPTY_STRING
        self.account = EMPTY_STRING
        self.gateway = EMPTY_STRING
        self.slippage = EMPTY_FLOAT
        self.time = datetime.now()

    @property
    def gClOrdID(self):
        return self.gateway + "." + self.clOrdID

    @property
    def gSymbol(self):
        return self.gateway + "." + self.symbol

    @property
    def gAccount(self):
        return self.gateway + "." + self.account


class AccountData(BaseData):
    """
    Data structure of account information

    Attributes:
        accountID(str): identity of account
        gAccountID(str): global identity of account
        preBalance(float): account balance of yesterday
        balance(float): account balance now
        available(float): available capital in account
        commission(float): trading commission
        margin(float): margin held
        closePnL(float): profit and loss of closed position
        positionPnL(float): profit and loss of holding position
    """
    __slots__ = ["accountID", "preBalance", "balance", "available", "commission", "margin",
                 "closePnL", "positionPnL", "gateway"]

    def __init__(self):
        super(AccountData, self).__init__()
        # 账号代码相关
        self.accountID = EMPTY_STRING  # 账户代码
        self.gateway = EMPTY_STRING  # 交易网关

        # 数值相关
        self.preBalance = EMPTY_FLOAT  # 昨日账户结算净值
        self.balance = EMPTY_FLOAT  # 账户净值
        self.available = EMPTY_FLOAT  # 可用资金
        self.commission = EMPTY_FLOAT  # 今日手续费
        self.margin = EMPTY_FLOAT  # 保证金占用
        self.closePnL = EMPTY_FLOAT  # 平仓盈亏
        self.positionPnL = EMPTY_FLOAT  # 持仓盈亏

    @property
    def gAccountID(self):
        return self.gateway + "." + self.accountID


class PositionData(BaseData):
    """

    Attributes:
        symbol(str): symbol of position
    """
    __slots__ = ["symbol", "exchange", "side", "volume", "frozenVolume", "avxPrice"]

    def __init__(self):
        self.symbol = EMPTY_STRING
        self.exchange = EMPTY_STRING
        self.side = EMPTY_UNICODE
        self.volume = EMPTY_INT
        self.frozenVolume = EMPTY_UNICODE
        self.avxPrice = EMPTY_FLOAT

    @property
    def gSymbol(self):
        return self.exchange + "." + self.symbol


class ExecutionData(BaseData):
    __slots__ = ["time", "ticker", "secType", "action", "quantity", "price", "profit", "commission", "lever",
                 "deposit_rate", "order_id", "client_id", "order_ext_id", "position_id", "fill_type",
                 "exec_id", "account", "exchange", "cum_qty", "avg_price", "reqTime", "status", "side"]

    def __init__(self):
        self.time = datetime.now()
        self.reqTime = self.time
        self.ticker = EMPTY_STRING
        self.secType = EMPTY_UNICODE
        self.action = EMPTY_UNICODE
        self.quantity = 0
        self.price = 0
        self.profit = None
        self.commission = 0
        self.fill_type = "position"
        self.position_id = None
        self.order_id = None
        self.client_id = None
        self.order_ext_id = None
        self.exec_id = None
        self.account = None
        self.exchange = EMPTY_UNICODE
        self.cum_qty = 0
        self.avg_price = 0
        self.lever = 1
        self.deposit_rate = 1
        self.status = EMPTY_UNICODE
        self.side = EMPTY_UNICODE


class Transaction(BaseData):
    """
    成交信息
    """
    __slots__ = ['time', 'security', 'action', 'quantity', 'price', 'value', 'order_id', 'commission', 'reqQuantity',
                 'ufQuantity', 'reqPrice', 'status', 'side', 'reqTime', 'exchange', 'point', 'deposit_rate']

    def __init__(
            self, time=datetime.now(), security=EMPTY_UNICODE, action=EMPTY_UNICODE,
            quantity=0, price=0, value=0, commission=0, order_id=0
    ):
        self.time = time
        self.security = security
        self.action = action
        self.quantity = quantity
        self.price = price
        self.value = value if value else quantity * price
        self.order_id = order_id
        self.commission = commission
        self.reqQuantity = quantity
        self.ufQuantity = 0
        self.reqPrice = price
        self.status = EMPTY_STRING
        self.side = EMPTY_STRING
        self.reqTime = time
        self.exchange = EMPTY_STRING
        self.point = 1
        self.deposit_rate = 1
