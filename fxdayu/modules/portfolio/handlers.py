# encoding: utf-8

import copy
import time

from dictproxyhack import dictproxy
import numpy as np
from enum import Enum

from fxdayu.const import *
from fxdayu.engine.handler import HandlerCompose, Handler
from fxdayu.event import EVENTS, ExecutionEvent
from fxdayu.models.data import PositionData, ExecutionData
from fxdayu.context import ContextMixin, InitializeMixin
from fxdayu.utils.api_support import api_method, callback_method

STAGE = {
    OrderStatus.UNKNOWN.value: 0,
    OrderStatus.GENERATE.value: 1,
    OrderStatus.NOTTRADED.value: 2,
    OrderStatus.ALLTRADED.value: 3,
    OrderStatus.CANCELLED.value: 4,
}


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

    def __init__(self, engine, context, environment, data, mode=None, sync_policy=None, execution_mode=None,
                 has_frozen=False):
        super(PortfolioHandler, self).__init__(engine)
        ContextMixin.__init__(self, context, environment, data, use_proxy=True)
        InitializeMixin.__init__(self)
        # setting
        if mode is None:
            mode = self.MODE.SYNC.value  # 默认同步的方式
        if sync_policy is None:
            sync_policy = self.SYNCPOLICY.BROKER.value
        if execution_mode is None:
            execution_mode = self.EXECUTION_MODE.AVG.value
        self._mode = mode
        # sync policy when there is difference between broker position and strategy position
        self._sync_policy = sync_policy  # TODO realize the sync logic
        self._execution_mode = execution_mode
        self._has_frozen = has_frozen  # Is there frozen volume field in position message from broker
        self._handlers = {
            "on_position": Handler(self.on_position, EVENTS.POSITION, topic=".", priority=0),
            # "on_init_start": Handler(self.on_init_start, EVENTS.INIT, priority=100),
            "on_init_finish": Handler(self.on_init_finish, EVENTS.INIT, priority=-100)
        }
        if self._mode == self.MODE.STRATEGY.value:
            self._handlers["on_order"] = Handler(self.on_order, EVENTS.ORDER)
        else:
            self._handlers["on_order_status"] = Handler(self.on_order_status, EVENTS.ORD_STATUS, topic="", priority=100)
            self._handlers["on_execution"] = Handler(self.on_execution, EVENTS.EXECUTION)
        self._handlers['on_time'] = Handler(self.on_time, EVENTS.TIME, topic="bar.close", priority=150)

        # position data
        self._strategy_positions = {}
        self._broker_positions = {}

        # back_test
        self._history_positions = []
        self._info = []

        self._capital_used = EMPTY_FLOAT
        self._positions_value = EMPTY_FLOAT
        self._starting_cash = self.DEFAULT_CAPITAL_BASE
        self._cash = self.DEFAULT_CAPITAL_BASE
        self._margin = EMPTY_FLOAT  # TODO realize it

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
        if position.side == Direction.SHORT.value:
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
        if close != np.nan:
            return traded_qty * (close - position.avgPrice) + abs(traded_qty) * position.avgPrice
        else:
            return abs(traded_qty) * position.avgPrice

    def on_init_start(self, event, kwargs=None):
        self.environment.gateway.qryPosition()
        # TODO query all open data

    def on_init_finish(self, event, kwargs=None):
        if self._sync_policy == self.SYNCPOLICY.BROKER.value:
            self._strategy_positions = copy.deepcopy(self._broker_positions)
            print(self._strategy_positions)

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
        print("Position: %s" % position.to_dict(ordered=True))

        old = self._broker_positions.pop(position.sid, None)
        # IB接口中并不给出frozenVolume,只能从openOrder得出
        self._trans_position(position)
        if not self._has_frozen and old is not None:
            position.frozenVolume = old.frozenVolume
            position.volume += old.frozenVolume
        if position.volume != 0 or position.frozenVolume != 0:
            self._broker_positions[position.sid] = position

    def on_order(self, event, kwargs=None):
        """

        Args:
            event(fxdayu.event.OrderEvent):
            kwargs:

        Returns:
            None
        """
        order = event.data
        # TODO 发单即仓位更新模式

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
        sign = 1 if new.side == Direction.LONG.value else -1
        if old.ordStatus == OrderStatus.GENERATE.value:  # new order execution in first time
            if sid not in self._strategy_positions:  # create new position
                self._strategy_positions[sid] = self._empty_position(sid, new)
            position = self._strategy_positions[sid]
            position.volume += new.orderQty * sign
            position.frozenVolume += new.leavesQty * sign

        # TODO position为None时候的处理
        position = self._strategy_positions.get(sid, None)
        if position:
            if not self._has_frozen and self._mode == self.MODE.BROKER.value:
                if sid not in self._broker_positions:
                    if position.frozenVolume:
                        temp = copy.copy(position)
                        # there is no realized volume in broker side
                        temp.volume = temp.frozenVolume
                        temp.avgPrice = 0
                        self._broker_positions[sid] = temp
                else:
                    temp = self._broker_positions[sid]
                    temp.volume -= temp.frozenVolume
                    temp.frozenVolume = position.frozenVolume
                    temp.volume += temp.frozenVolume

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
        # sid = self.environment.symbol(execution.symbol).sid
        symbol = execution.symbol
        if symbol not in self._strategy_positions:
            self._strategy_positions[symbol] = self._empty_position(symbol, execution)
        position = self._strategy_positions[symbol]
        sign_o = 1 if order.side == Direction.LONG.value else -1
        if order.ordStatus == OrderStatus.GENERATE.value:
            # # new order execution in first time, and execution arrive before order status
            position.volume += order.orderQty * sign_o
            position.frozenVolume += order.leavesQty * sign_o
            order.ordStatus = OrderStatus.NOTTRADED.value
        if self._execution_mode == self.EXECUTION_MODE.AVG.value:
            traded_qty = position.volume - position.frozenVolume
            last_qty = execution.lastQty * (1 if execution.side == Direction.LONG.value else -1)

            if traded_qty * last_qty >= 0:  # 加仓
                position.avgPrice = (position.avgPrice * traded_qty + execution.lastPx * last_qty) / \
                                    (traded_qty + last_qty)
                self._cash -= execution.lastPx * abs(last_qty)
            else:
                if abs(traded_qty) < abs(last_qty):  # 反向
                    position.avgPrice = execution.lastPx if last_qty != traded_qty else 0
                    self._cash -= execution.lastPx * abs(last_qty - traded_qty)  # 减掉新开仓现金
                    # 其他情况 avxPrice 不变
                self._cash += execution.lastPx * min(abs(last_qty), abs(traded_qty))
            position.frozenVolume -= last_qty
            if position.volume == 0 and position.frozenVolume == 0:
                self._strategy_positions.pop(symbol)
        elif self._execution_mode == self.EXECUTION_MODE.FIFO.value:
            # TODO 先开先平的结算
            pass

    def on_time(self, event, kwargs=None):
        for sid, position in self._strategy_positions.items():
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
        if self._mode == self.MODE.BROKER.value:
            return dictproxy(self._broker_positions)
        else:
            return dictproxy(self._strategy_positions)

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
