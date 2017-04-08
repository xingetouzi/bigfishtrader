# encoding: utf-8
from functools import total_ordering
from datetime import datetime

import numpy as np

from fxdayu.const import EMPTY_INT, EMPTY_STRING, EMPTY_UNICODE, EMPTY_FLOAT
from fxdayu.models.meta import BaseData


class TickData(BaseData):
    """
    tick quotation data, namely market depth data
    """
    __slots__ = ["gateway", "symbol", "exchange", "lastPrice", "lastVolume", "volume", "openInterest",
                 "time", "date", "openPrice", "highPrice", "lowPrice", "preClose", "vwapPrice",
                 "upperLimit", "lowerLimit", "depth", "askPrice", "bidPrice", "askVolume", "bidVolume"]
    MAX_DEPTH = 10

    def __init__(self, depth=MAX_DEPTH):
        # ticker
        self.gateway = EMPTY_STRING
        self.exchange = EMPTY_STRING
        self.symbol = EMPTY_STRING

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
        return ".".join([self.gateway, self.exchange, self.symbol])


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
                 "closePnL", "positionPnL", "exchangeRate", "gateway"]

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
        self.exchangeRate = 1.0  # 默认汇率(用于对子账户和分账户的基础货币不同的情况,主要是IB)

    @property
    def gAccountID(self):
        return ".".join([self.gateway, self.accountID])


@total_ordering
class PositionData(BaseData):
    """

    Attributes:
        symbol(str): symbol of position
    """
    __slots__ = ["gateway", "account", "symbol", "sid", "exchange", "side", "volume", "frozenVolume", "avgPrice",
                 "marketValue"]

    def __init__(self):
        self.gateway = EMPTY_STRING
        self.account = EMPTY_STRING
        self.symbol = EMPTY_STRING
        self.sid = EMPTY_INT
        self.exchange = EMPTY_STRING
        self.side = EMPTY_UNICODE
        self.volume = EMPTY_INT
        self.frozenVolume = EMPTY_UNICODE
        self.avgPrice = EMPTY_FLOAT
        self.marketValue = EMPTY_FLOAT

    def __eq__(self, other):
        if isinstance(other, int):
            return self.volume - self.frozenVolume == other
        else:
            return super(PositionData, self).__eq__(other)

    def __lt__(self, other):
        if isinstance(other, int):
            return self.volume - self.frozenVolume < other
        else:
            return super(PositionData, self).__eq__(other)


class ExecutionData(BaseData):
    __slots__ = ["time", "symbol", "action", "side", "leavesQty", "lastQty", "lastPx", "profit", "commission", "lever",
                 "deposit_rate", "clOrdID", "clientID", "orderID", "position_id", "fill_type",
                 "execID", "account", "exchange", "cumQty", "avgPx", "gateway"]

    def __init__(self):
        self.time = datetime.now()
        self.symbol = EMPTY_STRING
        self.gateway = EMPTY_STRING
        self.clOrdID = EMPTY_STRING
        self.clientID = EMPTY_STRING
        self.orderID = EMPTY_STRING
        self.execID = EMPTY_STRING
        self.account = EMPTY_STRING
        self.exchange = EMPTY_STRING

        self.action = EMPTY_STRING
        self.side = EMPTY_STRING
        self.profit = None

        self.cumQty = EMPTY_INT
        self.leavesQty = EMPTY_INT
        self.lastQty = EMPTY_INT
        self.avgPx = EMPTY_FLOAT
        self.lastPx = EMPTY_FLOAT

        self.position_id = None
        self.fill_type = "position"
        self.lever = 1
        self.commission = EMPTY_FLOAT
        self.deposit_rate = 1

    @property
    def gSymbol(self):
        return ".".join([self.gateway, self.symbol])

    @property
    def gExecID(self):
        return ".".join([self.gateway, self.account, self.execID])

    @property
    def gClOrdID(self):
        return ".".join([self.gateway, self.account, self.clOrdID])


class LogData(BaseData):
    __slots__ = ["logTime", "logContent", "gateway"]

    def __init__(self):
        self.logTime = EMPTY_STRING  # 日志生成时间
        self.logContent = EMPTY_UNICODE
        self.gateway = EMPTY_STRING


class ErrorData(BaseData):
    __slots__ = ["errorID", "errorMsg", "additionalInfo", "errorTime", "requestID", "gateway"]

    def __init__(self):
        self.errorID = EMPTY_STRING  # 错误代码
        self.errorMsg = EMPTY_UNICODE  # 错误信息
        self.additionalInfo = EMPTY_UNICODE  # 补充信息
        self.errorTime = EMPTY_STRING  # 错误生成时间
        self.requestID = EMPTY_STRING  # 错误对应请求编号
        self.gateway = EMPTY_STRING


class Security(BaseData):
    __slots__ = ["name", "localSymbol", "sid", "gateway", "symbol", "exchange", "secType", "currency",
                 "expiry", "right", "strike", "multiplier", ]

    def __init__(self):
        self.sid = EMPTY_STRING
        self.name = EMPTY_UNICODE
        self.localSymbol = EMPTY_STRING
        self.gateway = EMPTY_STRING
        self.symbol = EMPTY_STRING
        self.exchange = EMPTY_STRING
        self.secType = EMPTY_STRING
        self.currency = EMPTY_STRING
        self.expiry = EMPTY_STRING
        self.right = EMPTY_STRING
        self.strike = EMPTY_FLOAT
        self.multiplier = EMPTY_INT

    def __eq__(self, other):
        return self.sid and self.sid == other.sid
