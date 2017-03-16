# encoding: utf-8

from fxdayu.const import *
from fxdayu.models.data import *
from fxdayu.vt.vtConstant import *
from fxdayu.vt.vtGateway import VtOrderReq, VtSubscribeReq

MAP_VT_DIRECTION = {
    DIRECTION_NONE: DIRECTION.NONE.value,
    DIRECTION_LONG: DIRECTION.LONG.value,
    DIRECTION_SHORT: DIRECTION.SHORT.value,
    DIRECTION_UNKNOWN: DIRECTION.UNKNOWN.value,
    DIRECTION_NET: DIRECTION.NET.value,
}

MAP_VT_DIRECTION_REVERSE = {
    DIRECTION.NONE.value: DIRECTION_NONE,
    DIRECTION.LONG.value: DIRECTION_LONG,
    DIRECTION.SHORT.value: DIRECTION_SHORT,
    DIRECTION.UNKNOWN.value: DIRECTION_UNKNOWN,
    DIRECTION.NET.value: DIRECTION_NET,
}

MAP_VT_OFFSET = {
    OFFSET_NONE: ACTION.NONE.value,
    OFFSET_OPEN: ACTION.OPEN.value,
    OFFSET_CLOSE: ACTION.CLOSE.value,
    OFFSET_UNKNOWN: ACTION.UNKNOWN.value,
}

MAP_VT_OFFSET_REVERSE = {
    ACTION.NONE.value: OFFSET_NONE,
    ACTION.OPEN.value: OFFSET_OPEN,
    ACTION.CLOSE.value: OFFSET_CLOSE,
    ACTION.UNKNOWN.value: OFFSET_UNKNOWN,
}

MAP_VT_STATUS = {
    STATUS_NOTTRADED: ORDERSTATUS.NOTTRADED.value,
    STATUS_PARTTRADED: ORDERSTATUS.PARTTRADED.value,
    STATUS_ALLTRADED: ORDERSTATUS.ALLTRADED.value,
    STATUS_CANCELLED: ORDERSTATUS.CANCELLED.value,
    STATUS_UNKNOWN: ORDERSTATUS.UNKNOWN.value,
}

MAP_VT_STATUS_REVERSE = {
    ORDERSTATUS.NOTTRADED.value: STATUS_NOTTRADED,
    ORDERSTATUS.PARTTRADED.value: STATUS_PARTTRADED,
    ORDERSTATUS.ALLTRADED.value: STATUS_ALLTRADED,
    ORDERSTATUS.CANCELLED.value: STATUS_CANCELLED,
    ORDERSTATUS.UNKNOWN.value: STATUS_UNKNOWN,
}

MAP_VT_PRICETYPE = {
    PRICETYPE_LIMITPRICE: ORDERTYPE.LIMIT.value,
    PRICETYPE_MARKETPRICE: ORDERTYPE.MARKET.value,
    PRICETYPE_FAK: ORDERTYPE.FAK.value,
    PRICETYPE_FOK: ORDERTYPE.FOK.value,
}

MAP_VT_PRICETYPE_REVERSE = {
    ORDERTYPE.MARKET.value: PRICETYPE_MARKETPRICE,
    ORDERTYPE.LIMIT.value: PRICETYPE_LIMITPRICE,
    ORDERTYPE.STOP.value: PRICETYPE_LIMITPRICE,  # 还未支持停损单
    ORDERTYPE.FAK.value: ORDERTYPE.FAK,
    ORDERTYPE.FOK.value: ORDERTYPE.FOK,
}

# 合约类型映射
productClassMap = {}
productClassMap[PRODUCT_EQUITY] = 'STK'
productClassMap[PRODUCT_FUTURES] = 'FUT'
productClassMap[PRODUCT_OPTION] = 'OPT'
productClassMap[PRODUCT_FOREX] = 'CASH'
productClassMap[PRODUCT_INDEX] = 'IND'
productClassMapReverse = {v: k for k, v in productClassMap.items()}

# 期权类型映射
optionTypeMap = {}
optionTypeMap[OPTION_CALL] = 'CALL'
optionTypeMap[OPTION_PUT] = 'PUT'
optionTypeMapReverse = {v: k for k, v in optionTypeMap.items()}

# 货币类型映射
currencyMap = {}
currencyMap[CURRENCY_USD] = 'USD'
currencyMap[CURRENCY_CNY] = 'CNY'
currencyMap[CURRENCY_HKD] = 'HKD'
currencyMapReverse = {v: k for k, v in currencyMap.items()}

# 交易所类型映射
exchangeMap = {}
exchangeMap[EXCHANGE_SMART] = 'SMART'
exchangeMap[EXCHANGE_NYMEX] = 'NYMEX'
exchangeMap[EXCHANGE_GLOBEX] = 'GLOBEX'
exchangeMap[EXCHANGE_IDEALPRO] = 'IDEALPRO'
exchangeMap[EXCHANGE_HKEX] = 'HKEX'
exchangeMap[EXCHANGE_HKFE] = 'HKFE'
exchangeMapReverse = {v: k for k, v in exchangeMap.items()}


class VtAdapter(object):
    @classmethod
    def transform(cls, data, *args, **kwargs):
        try:
            func = getattr(cls, "transform_" + data.__class__.__name__)
        except AttributeError:
            raise TypeError("VtAdapter don't support transformation of type: %s" % data.__class__)
        return func(data, *args, **kwargs)

    @classmethod
    def transform_VtAccountData(cls, data):
        """

        Args:
            data(fxdayu.vt.vtGateway.VtAccountData):

        Returns:
            fxdayu.models.AccountData
        """
        account = AccountData()
        account.accountID = data.accountID
        account.gateway = data.gatewayName

        account.preBalance = data.preBalance
        account.balance = data.balance
        account.available = data.available
        account.commission = data.commission
        account.margin = data.margin
        account.closePnL = data.closeProfit
        account.positionPnL = data.positionProfit
        account.exchangeRate = getattr(data, "exchangeRate", 1.0)
        return account

    @classmethod
    def transform_VtTickData(cls, data):
        """

        Args:
            data(fxdayu.vt.vtGateway.VtTickData)

        Returns:
            fxdayu.models.TickData
        """
        tick = TickData()
        tick.symbol = data.symbol
        tick.exchange = data.exchange

        tick.lastPrice = data.lastPrice
        tick.lastVolume = data.lastVolume
        tick.volume = data.volume
        tick.openInterest = data.openInterest
        tick.time = data.time
        tick.date = data.date

        tick.openPrice = data.openPrice
        tick.highPrice = data.highPrice
        tick.lowPrice = data.lowPrice
        tick.preClose = data.preClosePrice

        tick.upperLimit = data.upperLimit
        tick.lowerLimit = data.lowerLimit

        tick.depth = 5
        tick.askPrice[0] = data.askPrice1
        tick.askPrice[1] = data.askPrice2
        tick.askPrice[2] = data.askPrice3
        tick.askPrice[3] = data.askPrice4
        tick.askPrice[4] = data.askPrice5
        tick.askVolume[0] = data.askVolume1
        tick.askVolume[1] = data.askVolume2
        tick.askVolume[2] = data.askVolume3
        tick.askVolume[3] = data.askVolume4
        tick.askVolume[4] = data.askVolume5
        tick.bidPrice[0] = data.bidPrice1
        tick.bidPrice[1] = data.bidPrice2
        tick.bidPrice[2] = data.bidPrice3
        tick.bidPrice[3] = data.bidPrice4
        tick.bidPrice[4] = data.bidPrice5
        tick.bidVolume[0] = data.bidVolume1
        tick.bidVolume[1] = data.bidVolume2
        tick.bidVolume[2] = data.bidVolume3
        tick.bidVolume[3] = data.bidVolume4
        tick.bidVolume[4] = data.bidVolume5
        return tick

    @classmethod
    def transform_VtPositionData(cls, data):
        """


        Args:
            data(fxdayu.vt.vtGateway.VtPositionData):

        Returns:
            fxdayu.models.PositionData
        """
        position = PositionData()
        position.symbol = data.symbol
        position.exchange = data.exchange
        position.side = MAP_VT_DIRECTION[data.direction]
        position.volume = data.position
        position.frozenVolume = data.frozen
        position.avgPrice = data.price
        position.account = getattr(data, "account", EMPTY_STRING)
        position.gateway = data.gatewayName
        if position.side == DIRECTION.NET.value:
            if position.volume >= 0:
                position.side = DIRECTION.LONG.value
            else:
                position.side = DIRECTION.SHORT.value
                position.volume = abs(position.volume)
        return position

    @classmethod
    def transform_VtOrderData(cls, data):
        """

        Args:
            data(fxdayu.vt.vtGateway.VtOrderData):

        Returns:
            fxdayu.models.OrderStatusData
        """
        order_status = OrderStatusData()
        order_status.symbol = data.symbol
        order_status.exchange = data.exchange

        order_status.clOrdID = data.orderID
        if data.frontID and data.sessionID:
            order_status.secondaryClOrdID = str(data.frontID) + "_" + str(data.sessionID)
        order_status.side = MAP_VT_DIRECTION[data.direction]
        if data.offset:
            order_status.action = MAP_VT_OFFSET[data.offset]
        order_status.price = data.offset
        order_status.orderQty = data.totalVolume
        order_status.cumQty = data.tradedVolume
        order_status.leavesQty = data.totalVolume - data.tradedVolume
        order_status.ordStatus = MAP_VT_STATUS.get(data.status, ORDERSTATUS.UNKNOWN.value)
        order_status.orderTime = data.orderTime
        order_status.cancelTime = data.cancelTime
        order_status.gateway = data.gatewayName
        return order_status

    @classmethod
    def transform_VtErrorData(cls, data):
        """

        Args:
            data(fxdayu.vt.vtGateway.VtErrorData):

        Returns:
            fxdayu.models.ErrorData
        """
        error = ErrorData()
        error.errorID = data.errorID
        error.errorMsg = data.errorMsg
        error.errorTime = data.errorTime
        error.gateway = data.gatewayName
        return error

    @classmethod
    def transform_VtLogData(cls, data):
        """

        Args:
            data(fxdayu.vt.vtGateway.VtLogData):

        Returns:
            fxdayu.models.data.LogData
        """
        log = LogData()
        log.logTime = data.logTime
        log.logContent = data.logContent
        log.gateway = data.gatewayName
        return log

    @classmethod
    def transform_VtTradeData(cls, data):
        """

        Args:
            data(fxdayu.vt.vtGateway.VtTradeData):

        Returns:
            fxdayu.models.data.ExecutionData
        """
        execution = ExecutionData()
        execution.time = data.tradeTime
        execution.symbol = data.symbol
        execution.gateway = data.gatewayName
        execution.clOrderID = data.orderID
        execution.execID = data.tradeID
        execution.account = EMPTY_STRING  # TODO 确定账户
        execution.exchange = data.exchange
        if data.offset:
            execution.action = MAP_VT_OFFSET[data.offset]
        execution.side = MAP_VT_DIRECTION[data.direction]
        execution.lastPx = data.price
        execution.lastQty = data.volume
        return execution

    @classmethod
    def transform_OrderReq(cls, data, security=None):
        """

        Args:
            data(fxdayu.models.data.OrderReq):
            security(fxdayu.models.data.Security):
        Returns:
            fxdayu.vt.vtGateway.VtOrderReq
        """
        vt_order = VtOrderReq()
        vt_order.symbol = data.symbol
        vt_order.exchange = data.exchange
        vt_order.price = data.price
        vt_order.volume = data.orderQty
        vt_order.priceType = MAP_VT_PRICETYPE_REVERSE[data.ordType]
        vt_order.direction = MAP_VT_DIRECTION_REVERSE[data.side]
        vt_order.offset = MAP_VT_OFFSET_REVERSE[data.action]
        if data.security:
            vt_order.productClass = productClassMapReverse[data.security.secType]
        return vt_order

    @classmethod
    def transform_Security(cls, data):
        """

        Args:
            data(fxdayu.models.data.Security):

        Returns:
            fxdayu.vt.vtGateway.VtSubscribeReq
        """
        sub_req = VtSubscribeReq()
        sub_req.symbol = data.localSymbol
        sub_req.exchange = exchangeMapReverse[data.exchange]
        sub_req.productClass = productClassMapReverse[data.secType]
        sub_req.currency = data.currency
        sub_req.expiry = data.expiry
        sub_req.strikePrice = data.strike
        sub_req.optionType = data.right
        return sub_req
