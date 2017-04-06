from fxdayu.models.data import Security
from fxdayu.models.order import OrderReq
from fxdayu.const import DIRECTION, ORDERTYPE, ACTION
from fxdayu.context import ContextMixin

__all__ = ["OrderReqAdapter", "OrderType", "MarketOrder", "LimitOrder", "StopOrder",
           "StopLimitOrder"]


class OrderType(object):
    __slots__ = []


class MarketOrder(OrderType):
    __slots__ = ["exchange"]

    def __init__(self, exchange=None):
        self.exchange = exchange


class LimitOrder(OrderType):
    __slots__ = ["exchange", "limit_price"]

    def __init__(self, price, exchange=None):
        self.limit_price = price
        self.exchange = exchange


class StopOrder(OrderType):
    __slots__ = ["exchange", "stop_price"]

    def __init__(self, price, exchange=None):
        self.stop_price = price
        self.exchange = exchange


class StopLimitOrder(OrderType):
    __slots__ = ["exchange", "limit_price", "stop_price"]

    def __init__(self, limit_price, stop_price, exchange=None):
        self.limit_price = limit_price
        self.stop_price = stop_price
        self.exchange = exchange


class OrderReqAdapter(ContextMixin):
    STYLE_ORDER_MAP = {
        MarketOrder: ORDERTYPE.MARKET.value,
        LimitOrder: ORDERTYPE.LIMIT.value,
        StopOrder: ORDERTYPE.STOP.value,
        StopLimitOrder: ORDERTYPE.LIMIT.value,
    }

    def __init__(self, context, environment):
        ContextMixin.__init__(self, context, environment)

    def parse(self, security, amount, style=None):
        """

        Args:
            security():
            amount:
            style:

        Returns:

        """
        if isinstance(security, Security):
            s = security
        else:
            s = self.environment.symbol(security)
        if s:
            order_req = OrderReq()
            if style is None:
                style = MarketOrder(exchange=None)
            if isinstance(style, OrderType):
                order_req.security = s
                order_req.symbol = s.localSymbol  # order
                order_req.orderQty = int(abs(amount))
                if amount > 0:
                    order_req.side = DIRECTION.LONG.value  # IB
                else:
                    order_req.side = DIRECTION.SHORT.value
                order_req.account = self.context.account.id
                order_req.ordType = self.STYLE_ORDER_MAP[type(style)]
                order_req.action = ACTION.NONE.value
                if isinstance(style, LimitOrder) or isinstance(style, StopLimitOrder):
                    order_req.price = style.limit_price
                if isinstance(style, StopOrder) or isinstance(style, StopLimitOrder):
                    order_req.stopPx = style.stop_price
                if style.exchange:
                    order_req.exchange = style.exchange
                else:
                    order_req.exchange = s.exchange
                return order_req
            else:
                pass
        else:
            pass  # TODO raise warning

    def link_context(self):
        pass
