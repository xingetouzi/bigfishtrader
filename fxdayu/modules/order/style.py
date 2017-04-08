# encoding: utf-8

from fxdayu.models.data import Security
from fxdayu.models.order import OrderReq
from fxdayu.const import Direction, OrderType, OrderAction
from fxdayu.context import ContextMixin

__all__ = ["OrderReqAdapter", "OrderStyle", "MarketOrder", "LimitOrder", "StopOrder",
           "StopLimitOrder"]


class OrderStyle(object):
    __slots__ = []


class MarketOrder(OrderStyle):
    __slots__ = ["exchange"]

    def __init__(self, exchange=None):
        self.exchange = exchange


class LimitOrder(OrderStyle):
    __slots__ = ["exchange", "limit_price"]

    def __init__(self, price, exchange=None):
        self.limit_price = price
        self.exchange = exchange


class StopOrder(OrderStyle):
    __slots__ = ["exchange", "stop_price"]

    def __init__(self, price, exchange=None):
        self.stop_price = price
        self.exchange = exchange


class StopLimitOrder(OrderStyle):
    __slots__ = ["exchange", "limit_price", "stop_price"]

    def __init__(self, limit_price, stop_price, exchange=None):
        self.limit_price = limit_price
        self.stop_price = stop_price
        self.exchange = exchange


class OrderReqAdapter(ContextMixin):
    STYLE_ORDER_MAP = {
        MarketOrder: OrderType.MARKET.value,
        LimitOrder: OrderType.LIMIT.value,
        StopOrder: OrderType.STOP.value,
        StopLimitOrder: OrderType.LIMIT.value,
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
            if isinstance(style, OrderStyle):
                order_req.security = s
                order_req.symbol = s.localSymbol  # order
                order_req.orderQty = int(abs(amount))
                if amount > 0:
                    order_req.side = Direction.LONG.value  # IB
                else:
                    order_req.side = Direction.SHORT.value
                order_req.account = self.context.account.id
                order_req.ordType = self.STYLE_ORDER_MAP[type(style)]
                order_req.action = OrderAction.NONE.value
                # TODO 暂时不支持stop_limit单,因为价格都放在price中考虑了。
                if isinstance(style, LimitOrder) or isinstance(style, StopLimitOrder):
                    order_req.price = style.limit_price
                if isinstance(style, StopOrder) or isinstance(style, StopLimitOrder):
                    order_req.price = style.stop_price
                if style.exchange:
                    order_req.exchange = style.exchange
                else:
                    order_req.exchange = s.exchange
                # GATEWAY AND ACCOUNT
                order_req.account = "BACKTEST"
                order_req.gateway = "BACKTEST"
                return order_req
            else:
                pass
        else:
            pass  # TODO raise warning

    def link_context(self):
        pass
