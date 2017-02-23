# encoding: utf-8

from collections import OrderedDict
from datetime import datetime

from bigfishtrader.const import EMPTY_INT, EMPTY_STRING, EMPTY_UNICODE, EMPTY_FLOAT


class BaseData(object):
    __slots__ = []

    def to_dict(self, ordered=False):
        if ordered:
            return OrderedDict([(attr, getattr(self, attr)) for attr in self.__slots__])
        else:
            return {attr: getattr(self, attr) for attr in self.__slots__}


class Order(BaseData):
    """
    Order is created by a strategy when it wants to open an order and
    will be handled by Simulation or Trade section
    """
    __slots__ = ["cliOrdID", "exchange", "symbol", "side", "action", "orderQty", "ordType", "price", "tradedQty",
                 "timeInForce", "transactTime", "expireTime", "account", "slippage",
                 "gateway"]

    def __init__(self):
        super(Order, self).__init__()
        self.cliOrdID = EMPTY_INT
        self.exchange = EMPTY_STRING
        self.symbol = EMPTY_STRING
        self.side = EMPTY_UNICODE
        self.action = EMPTY_UNICODE
        self.orderQty = EMPTY_INT
        self.ordType = EMPTY_STRING
        self.price = EMPTY_FLOAT
        self.tradedQty = EMPTY_INT
        self.timeInForce = EMPTY_STRING
        self.transactTime = EMPTY_STRING
        self.expireTime = EMPTY_STRING
        self.account = EMPTY_STRING
        self.gateway = EMPTY_STRING

    @property
    def gCliOrdID(self):
        return self.gateway + "." + str(self.cliOrdID)

    @property
    def gSymbol(self):
        return self.gateway + "." + str(self.symbol)

    @property
    def gAccount(self):
        return self.gateway + "." + str(self.account)


class Account(BaseData):
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
        super(Account, self).__init__()
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


class Fill(BaseData):
    __slots__ = ["time", "ticker", "action", "quantity", "price", "profit", "commission", "lever", "deposit_rate",
                 "order_id", "client_id", "order_ext_id", "position_id", "fill_type",
                 "exec_id", "account", "exchange", "cum_qty", "avg_price"]

    def __init__(self):
        self.time = datetime.now()
        self.ticker = EMPTY_STRING
        self.action = None
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
        self.exchange = None
        self.cum_qty = 0
        self.avg_price = 0
        self.lever = 1
        self.deposit_rate = 1