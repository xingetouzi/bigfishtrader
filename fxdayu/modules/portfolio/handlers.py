# encoding: utf-8

import copy

import numpy as np
from dictproxyhack import dictproxy

from fxdayu.const import *
from fxdayu.context import ContextMixin, InitializeMixin
from fxdayu.engine.handler import HandlerCompose, Handler
from fxdayu.event import EVENTS
from fxdayu.models.data import PositionData
from fxdayu.models.order import OrderStatusData
from fxdayu.utils.api_support import callback_method

STAGE = {
    OrderStatus.UNKNOWN.value: 0,
    OrderStatus.GENERATE.value: 1,
    OrderStatus.NOTTRADED.value: 2,
    OrderStatus.PARTTRADED.value: 3,
    OrderStatus.ALLTRADED.value: 4,
    OrderStatus.CANCELLED.value: 5,
}

MAP_DIRECTION_SIGN = {
    Direction.LONG: 1,
    Direction.SHORT: -1
}


class PortfolioHandlerMeta(object):
    def __init__(self, mode=None, sync_policy=None, exec_mode=None, has_frozen=False):
        self.mode = mode
        self.sync_policy = sync_policy
        self.exec_mode = exec_mode
        self.has_frozen = has_frozen


class PortfolioHandler(HandlerCompose, ContextMixin, InitializeMixin):
    class MODE(Enum):
        BROKER = 0  # 以按一定频率从交易所获取的仓位数据为准
        SYNC = 1  # 以本地仓位为准，异步更新(收到报单回报才更新)
        STRATEGY = 2  # 以本地仓位为准，同步更新(发单即更新)

    class SYNCPOLICY(Enum):
        BROKER = 0
        STRATEGY = 1
        NONE = 2

    class EXECUTION_MODE(Enum):
        AVG = "AVG"  # 持仓均价成交模式,适合股票
        FIFO = "FIFO"  # 先进先出成交模式，适合期货

    SYNC_FREQUENCY = 1000  # in millisecond
    DEFAULT_CAPITAL_BASE = 100000

    def __init__(self, engine, meta=PortfolioHandlerMeta()):
        super(PortfolioHandler, self).__init__(engine)
        ContextMixin.__init__(self, use_proxy=True)
        InitializeMixin.__init__(self)
        self._mode = self.MODE.SYNC if meta.mode is None else self.MODE(meta.mode)
        # sync policy when there is difference between broker position and strategy position
        # TODO realize the sync logic
        self._sync_policy = self.SYNCPOLICY.BROKER if meta.sync_policy is None else self.SYNCPOLICY(meta.sync_policy)
        self._exec_mode = self.EXECUTION_MODE.AVG if meta.exec_mode is None else self.EXECUTION_MODE(meta.exec_mode)
        self._has_frozen = meta.has_frozen  # Is there frozen volume field in position message from broker
        self._handlers = {
            "on_position": Handler(self.on_position, EVENTS.POSITION, topic=".", priority=0),
            "on_init_finish": Handler(self.on_init_finish, EVENTS.INIT, priority=-100)
        }
        if self._mode == self.MODE.STRATEGY:
            self._handlers["on_order"] = Handler(self.on_order, EVENTS.ORDER, priority=-100)
            self._handlers["on_cancel"] = Handler(self.on_cancel, EVENTS.CANCEL, priority=-100)
        else:
            self._handlers["on_order_status"] = Handler(self.on_order_status, EVENTS.ORD_STATUS, topic="", priority=100)
        self._handlers["on_execution"] = Handler(self.on_execution, EVENTS.EXECUTION)
        self._handlers['on_time'] = Handler(self.on_time, EVENTS.TIME, topic="bar.close", priority=150)

        # back_test
        self._history_positions = []
        self._info = []

        self._capital_used = EMPTY_FLOAT
        self._positions_value = EMPTY_FLOAT
        self._starting_cash = self.DEFAULT_CAPITAL_BASE
        self._cash = self.DEFAULT_CAPITAL_BASE
        self._margin = EMPTY_FLOAT  # TODO realize it
        self._persistence = None
        self._position_dao = None
        self._order_status_dao = None

    def init(self):
        self._persistence = self.environment["persistence"]
        self._position_dao = self._persistence.get_dao(PositionData)
        self._order_status_dao = self._persistence.get_dao(OrderStatusData)

    @staticmethod
    def get_sign(n):
        if n > 0:
            return 1
        elif n < 0:
            return -1
        else:
            return 0  # position = 0

    @staticmethod
    def _trans_position(position):
        """

        Args:
            position(fxdayu.models.data.PositionData):

        Returns:
            None
        """
        if Direction(position.side) == Direction.SHORT:
            position.volume = - position.volume
            position.frozenVolume = - position.frozenVolume
        position.side = Direction.NET.value

    @staticmethod
    def _empty_position(sid, data):
        """

        Args:
            sid:
            data(fxdayu.models.order.OrderStatusData | fxdayu.models.data.ExecutionData):

        Returns:

        """
        position = PositionData()
        position.account = data.account
        position.symbol = data.symbol
        position.sid = data.symbol
        position.side = Direction.NET.value  # 保存下来的position都使用net模式
        position.exchange = data.exchange
        position.gateway = data.gateway
        position.volume = 0
        position.frozenVolume = 0
        position.avgPrice = 0  # avgPrice 暂时不可用
        return position

    def _close_position(self, position):
        """

        Args:
            position(fxdayu.models.data.PositionData):

        Returns:

        """
        security = self.environment.symbol(position.symbol)
        close = self.data.current(security.symbol).close
        traded_qty = position.volume - position.frozenVolume
        return close * traded_qty

    def on_init_start(self, event, kwargs=None):
        self.environment.gateway.qryPosition()
        # TODO query all open data

    def on_init_finish(self, event, kwargs=None):
        pass

    def on_order(self, event, kwargs=None):
        """

        Args:
            event(fxdayu.event.OrderEvent):
            kwargs:

        Returns:
            None
        """
        order = event.data
        status = self.environment.get_order_status(order.gClOrdID)
        sign = MAP_DIRECTION_SIGN[Direction(status.side)]
        position = self._position_dao.find(status.gateway, status.account, status.symbol)
        if position is None:
            position = self._empty_position(status.symbol, status)
        position.volume += status.orderQty * sign
        position.frozenVolume += status.leavesQty * sign
        self._position_dao.insert(position)

    def on_cancel(self, event, kwargs=None):
        order = event.data
        status = self.environment.get_order_status(order.orderID)
        sign = MAP_DIRECTION_SIGN[Direction(status.side)]
        position = self._position_dao.find(status.gateway, status.account, status.symbol)
        if position is None:
            position = self._empty_position(status.symbol, status)
        position.volume -= (status.orderQty - status.cumQty) * sign
        position.frozenVolume -= (status.orderQty - status.cumQty) * sign
        self._position_dao.insert(position)

    # deprecated
    def on_position(self, event, kwargs=None):
        """

        Args:
            event(fxdayu.event.PositionEvent):
            kwargs:

        Returns:
            None
        """
        position = event.data
        security = self.environment.symbol(position.symbol)
        if security is None:
            return
        position.sid = security.sid
        self._trans_position(position)
        self._position_dao.insert(position)

    def on_order_status(self, event, kwargs=None):
        """

        Args:
            event(fxdayu.event.OrderStatusEvent):
            kwargs:

        Returns:

        """
        new = event.data
        old = self.environment.get_order_status(new.gClOrdID)
        # print("old: %s" % new.to_dict(ordered=True))
        # print("new: %s" % new.to_dict(ordered=True))
        security = self.environment.symbol(new.symbol)
        if security is None:
            return
        sid = security.sid
        if STAGE[old.ordStatus] > STAGE[new.ordStatus]:  # error stage of order
            return  # TODO test order status == unknown
        sign = MAP_DIRECTION_SIGN[Direction(new.side)]
        if OrderStatus(old.ordStatus) == OrderStatus.GENERATE:  # new order execution in first time
            position = self._position_dao.find(old.gateway, old.account, old.symbol)
            if position is None:
                position = self._empty_position(sid, new)
            position.volume += new.orderQty * sign
            position.frozenVolume += new.leavesQty * sign
            self._position_dao.insert(position)
        # TODO 撤单回报走execution而不走status
        if OrderStatus(new.ordStatus) == OrderStatus.CANCELLED:
            position = self._position_dao.find(old.gateway, old.account, old.symbol)
            if position is None:
                position = self._empty_position(sid, new)
            position.volume -= (new.orderQty - new.cumQty) * sign
            position.frozenVolume -= (new.orderQty - new.cumQty) * sign
            self._position_dao.insert(position)

    def on_execution(self, event, kwargs=None):
        """

        Args:
            event(fxdayu.event.ExecutionEvent):
            kwargs:

        Returns:
            None
        """
        execution = event.data
        self.transaction(execution, self.context, self.data)
        order = self.environment.get_order_status(execution.gClOrdID)
        symbol = execution.symbol
        position = self._position_dao.find(execution.gateway, execution.account, execution.symbol)
        if position is None:
            position = self._empty_position(symbol, execution)
        sign_o = MAP_DIRECTION_SIGN[Direction(order.side)]
        if (OrderStatus(order.ordStatus) == OrderStatus.GENERATE) and (self._mode == self.MODE.SYNC):
            # # new order execution in first time, and execution arrive before order status
            position.volume += order.orderQty * sign_o
            position.frozenVolume += order.leavesQty * sign_o
            order.ordStatus = OrderStatus.NOTTRADED.value
            self._order_status_dao.insert(order)
        if self._exec_mode == self.EXECUTION_MODE.AVG:
            traded_qty = position.volume - position.frozenVolume
            last_qty = execution.lastQty * MAP_DIRECTION_SIGN[Direction(execution.side)]
            if traded_qty * last_qty >= 0:  # 加仓
                position.avgPrice = (position.avgPrice * traded_qty + execution.lastPx * last_qty) / \
                                    (traded_qty + last_qty)
            else:
                if abs(traded_qty) < abs(last_qty):  # 反向
                    position.avgPrice = execution.lastPx
            self._cash -= execution.lastPx * last_qty
            position.frozenVolume -= last_qty
            if position.volume == 0 and position.frozenVolume == 0:
                self._position_dao.delete(execution.gateway, execution.account,
                                          execution.symbol)
            else:
                self._position_dao.insert(position)
        elif self._exec_mode == self.EXECUTION_MODE.FIFO:
            # TODO 先开先平的结算
            pass

    def on_time(self, event, kwargs=None):
        for sid, position in self.positions.items():
            show = position.to_dict()
            show["datetime"] = event.time
            self._history_positions.append(show)
        self._info.append(
            {'datetime': event.time, 'cash': self.cash, 'equity': self.portfolio_value},
        )

    def on_exit(self, event, kwargs=None):
        # TODO 对待挂单的处理
        # for sid, position in self._strategy_positions.copy().items():
        #     execution = ExecutionData()
        #     security = self.environment.symbol(sid)
        #     amount = position.volume
        pass

    @property
    def capital_used(self):
        return self._capital_used

    @property
    def starting_cash(self):
        return self._starting_cash

    @property
    def cash(self):
        return self._cash

    @property
    def pnl(self):
        return self.portfolio_value - self._starting_cash

    @property
    def portfolio_value(self):
        return self._cash + sum([self._close_position(p) for p in self.positions.values()]) + self._margin

    @property
    def positions_value(self):
        return sum([abs(p.volume - p.frozenVolume) * p.avgPrice for p in self.positions.values()])

    @property
    def returns(self):
        return self.portfolio_value / self._starting_cash

    @property
    def positions(self):
        return {item.symbol: item for item in self._position_dao.find_all()}

    @property
    def info(self):
        return self._info

    @property
    def history(self):
        return self._history_positions

    def link_context(self):
        self.context.portfolio = self

    @staticmethod
    @callback_method('transaction')
    def transaction(self, execution, context, data):
        pass
