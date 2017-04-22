from fxdayu.models.data import *
from fxdayu.models.order import *
from fxdayu.vnpy.vtData import VtOrderReq, VtCancelOrderReq
from fxdayu.vnpy.vtConstant import *
from fxdayu.const import *

MAP_VT_DIRECTION = {
    DIRECTION_NONE: Direction.NONE.value,
    DIRECTION_LONG: Direction.LONG.value,
    DIRECTION_SHORT: Direction.SHORT.value,
    DIRECTION_UNKNOWN: Direction.UNKNOWN.value,
}

MAP_VT_DIRECTION_REVERSE = {
    Direction.NONE.value: DIRECTION_NONE,
    Direction.LONG.value: DIRECTION_LONG,
    Direction.SHORT.value: DIRECTION_SHORT,
    Direction.UNKNOWN.value: DIRECTION_UNKNOWN,
}

MAP_VT_OFFSET = {
    OFFSET_NONE: OrderAction.NONE.value,
    OFFSET_OPEN: OrderAction.OPEN.value,
    OFFSET_CLOSE: OrderAction.CLOSE.value,
    OFFSET_UNKNOWN: OrderAction.UNKNOWN.value,
}

MAP_VT_OFFSET_REVERSE = {
    OrderAction.NONE.value: OFFSET_NONE,
    OrderAction.OPEN.value: OFFSET_OPEN,
    OrderAction.CLOSE.value: OFFSET_CLOSE,
    OrderAction.UNKNOWN.value: OFFSET_UNKNOWN,
}

MAP_VT_STATUS = {
    STATUS_NOTTRADED: OrderStatus.NOTTRADED.value,
    STATUS_PARTTRADED: OrderStatus.PARTTRADED.value,
    STATUS_ALLTRADED: OrderStatus.ALLTRADED.value,
    STATUS_CANCELLED: OrderStatus.CANCELLED.value,
    STATUS_UNKNOWN: OrderStatus.UNKNOWN.value,
}

MAP_VT_STATUS_REVERSE = {
    OrderStatus.NOTTRADED.value: STATUS_NOTTRADED,
    OrderStatus.PARTTRADED.value: STATUS_PARTTRADED,
    OrderStatus.ALLTRADED.value: STATUS_ALLTRADED,
    OrderStatus.CANCELLED.value: STATUS_CANCELLED,
    OrderStatus.UNKNOWN.value: STATUS_UNKNOWN,
}

MAP_VT_PRICETYPE = {
    PRICETYPE_LIMITPRICE: OrderType.LIMIT.value,
    PRICETYPE_MARKETPRICE: OrderType.MARKET.value,
    PRICETYPE_FAK: OrderType.FAK.value,
    PRICETYPE_FOK: OrderType.FOK.value,
}

MAP_VT_PRICETYPE_REVERSE = {
    OrderType.MARKET.value: OrderType.MARKET,
    OrderType.LIMIT.value: OrderType.LIMIT,
    OrderType.FAK.value: OrderType.FAK,
    OrderType.FOK.value: OrderType.FOK,
}


class VtAdapter(object):
    @classmethod
    def transform(cls, data):
        try:
            func = getattr(cls, "transform_" + data.__class__)
        except AttributeError:
            raise TypeError("VtAdapter don't support transformation of type: %s" % data.__class__)
        return func(data)

    @classmethod
    def transform_VtTickData(cls, data):
        """
        Args:
            data(fxdayu.vt.vtGateway.VtTickData)
        Returns:
            fxdayu.models.data.TickData
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
            fxdayu.model.PositionData
        """
        position = PositionData()
        position.symbol = data.symbol
        position.exchange = data.exchange
        position.side = MAP_VT_DIRECTION[data.direction]
        position.volume = data.position
        position.frozenVolume = data.frozen
        position.avgPrice = data.price
        return position

    @classmethod
    def transform_VtOrderData(cls, data):
        """
        Args:
            data(fxdayu.vnpy.vtData.VtOrderData):
        Returns:
            fxdayu.model.OrderStatusData
        """
        order_status = OrderStatusData()
        order_status.symbol = data.symbol
        order_status.exchange = data.exchange

        order_status.clOrdID = data.vtOrderID
        order_status.secondaryClOrdID = data.frontID + "_" + data.sessionID
        order_status.side = MAP_VT_DIRECTION[data.direction]
        order_status.action = MAP_VT_OFFSET[data.offset]
        order_status.price = data.offset
        order_status.orderQty = data.totalVolume
        order_status.cumQty = data.tradedVolume
        order_status.leavesQty = data.totalVolume - data.tradedVolume
        order_status.ordStatus = MAP_VT_STATUS[data.status]
        order_status.orderTime = data.orderTime
        order_status.cancelTime = data.cancelTime
        order_status.gateway = data.gatewayName
        return order_status

    @classmethod
    def transform_OrderReq(cls, data):
        """
        Args:
            data(fxdayu.model.OrderReq):
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
        vt_order.offset = MAP_VT_DIRECTION_REVERSE[data.action]
        return vt_order

    @classmethod
    def transform_CancelReq(cls, data):
        vt_cancel = VtCancelOrderReq()
        vt_cancel.orderID = data.orderID
        if data.secondaryClOrdID:
            vt_cancel.frontID, vt_cancel.sessionID = data.secondaryClOrdID.split("_")
        return vt_cancel
