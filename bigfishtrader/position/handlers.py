# encoding: utf-8

import copy
import time

from dictproxyhack import dictproxy
from enum import Enum

from bigfishtrader.const import ACTION, DIRECTION
from bigfishtrader.engine.handler import HandlerCompose, Handler
from bigfishtrader.event import EVENTS
from bigfishtrader.models.data import PositionData
from bigfishtrader.context import ContextMixin, InitializeMixin


class PortfolioHandler(HandlerCompose, ContextMixin, InitializeMixin):
    class MODE(Enum):
        BROKER = 0  # 以按一定频率从交易所获取的仓位数据为准
        SYNC = 1  # 以本地仓位为准，异步更新(收到报单回报才更新)
        STRATEGY = 2  # 以本地仓位为准，同步更新(发单即更新)

    class SYNCPOLICY(Enum):
        BROKER = 0
        STRATEGY = 1
        NONE = 2

    SYNC_FREQUENCY = 1000  # in millisecond

    def __init__(self, context, environment, mode=None, sync_policy=None, has_frozen=False, snapshot=True):
        super(PortfolioHandler, self).__init__()
        ContextMixin.__init__(self, context, environment)
        InitializeMixin.__init__(self)
        if mode is None:
            mode = PortfolioHandler.MODE.BROKER.value
        if sync_policy is None:
            sync_policy = PortfolioHandler.SYNCPOLICY.BROKER.value
        self._strategy_positions = {}
        self._broker_positions = {}
        self._strategy_positions_snapshot = {}
        self._broker_positions_snapshot = {}
        self._mode = mode
        # sync policy when there is difference between broker position and strategy position
        self._sync_policy = sync_policy  # TODO realize the sync logic
        self._has_frozen = has_frozen  # Is there frozen volume field in position message from broker
        self._snapshot = snapshot
        self._handlers = {
            "on_position": Handler(self.on_position, EVENTS.POSITION, topic=".", priority=0),
        }
        if self._mode == self.MODE.STRATEGY.value:
            self._handlers["on_order"] = Handler(self.on_order, EVENTS.ORDER)
        else:
            self._handlers["on_execution"] = Handler(self.on_execution, EVENTS.EXECUTION)
        # 是否在bar运算开始之时获取仓位快照，以保证单次运算中仓位不变
        if self._snapshot:
            self._handlers["on_bar"] = Handler(self.on_bar, EVENTS.TIME, topic="bar", priority=100)

    def on_init_start(self, event, kwargs=None):
        self.environment.gateway.qryPosition()
        # TODO query all open data
        time.sleep(1)

    def on_init_finish(self, event, kwargs=None):
        if self._sync_policy == self.SYNCPOLICY.BROKER.value:
            self._strategy_positions = copy.deepcopy(self._broker_positions)

    def on_bar(self):
        if self._mode == PortfolioHandler.MODE.BROKER:
            self._broker_positions_snapshot = copy.deepcopy(self._broker_positions)
        else:
            self._strategy_positions_snapshot = copy.deepcopy(self._strategy_positions)

    def on_position(self, event, kwargs=None):
        """

        Args:
            event(bigfishtrader.event.PositionEvent):
            kwargs:

        Returns:

        """
        position = event.data
        old = self._broker_positions.pop(position.gSymbol, None)
        # IB接口中并不给出frozenVolume,只能从openOrder得出
        if not self._has_frozen and old is not None:
            position.frozenVolume = old.frozenVolume
        if position.volume != 0 or position.frozenVolume != 0:
            self._broker_positions[position.gSymbol] = position

    def on_order(self, event, kwargs=None):
        """

        Args:
            event(bigfishtrader.event.OrderEvent):
            kwargs:

        Returns:
            None
        """
        order = event.data
        # TODO 发单即仓位更新模式

    def on_execution(self, event, kwargs=None):
        """

        Args:
            event(bigfishtrader.event.ExecutionEvent):
            kwargs:

        Returns:
            None
        """

        def get_sign(n):
            if n > 0:
                return 1
            elif n < 0:
                return -1
            else:
                return 0  # position = 0

        execution = event.data
        if execution.gSymbol not in self._strategy_positions:  # create new position
            if execution.action == ACTION.IN:
                position = PositionData()
                position.account = execution.account
                position.symbol = execution.symbol
                position.side = DIRECTION.LONG.value
                position.exchange = execution.exchange
                position.volume = 0
                position.frozenVolume = 0
                position.avgPrice = 0
            else:
                # TODO warning
                return
        else:
            position = self._strategy_positions[execution.gSymbol]

        # change position according to execution
        tradedVolume = position.volume - position.frozenVolume
        sign_p = 1 if position.side == DIRECTION.LONG.value else -1
        sign_t = get_sign(tradedVolume) * sign_p
        sign_e = 1 if execution.side == DIRECTION.LONG.value else -1
        if sign_t * sign_e >= 0:  # 加仓
            position.avgPrice = (position.avgPrice * tradedVolume + execution.lastQty * execution.lastPx) / \
                                (tradedVolume + execution.lastQty)
        else:
            if tradedVolume < execution.lastQty:  # 反向
                position.avgPrice = execution.lastPx
                # 其他情况 avxPrice 不变
        sign = 1 if (sign_p * sign_e) >= 0 else -1
        if execution.cumQty == execution.lastQty:  # new order execution in first time
            position.volume += (execution.cumQty + execution.leavesQty) * sign
            position.frozenVolume += execution.leavesQty * sign
        else:
            position.volume += execution.lastQty * sign
            position.frozenVolume -= execution.lastQty * sign
        if position.volume < 0:
            position.side = DIRECTION.SHORT.value if position.side == DIRECTION.LONG.value else DIRECTION.LONG.value
            position.volume = - position.volume
            position.frozenVolume = - position.frozenVolume
        if execution.leavesQty == 0:  # when cancel order or reject order or order expire
            order = self.environment.get_order(execution.gClOrdID)
            position.frozenVolume -= (order.orderQty - execution.cumQty) * sign

        # copy frozenVolume to broker positions
        if not self._has_frozen and self._mode == self.MODE.BROKER:
            if execution.gSymbol not in self._broker_positions:
                if position.frozenVolume:
                    temp = copy.copy(position)
                    # there is no realized volume in broker side
                    temp.volume = 0
                    temp.avgPrice = 0
                    self._broker_positions[execution.gSymbol] = temp
            else:
                temp = self._broker_positions[execution.gSymbol]
                temp.frozenVolume = position.frozenVolume

    @property
    def positions(self):
        if self._mode == PortfolioHandler.MODE.BROKER:
            if self._snapshot:
                return dictproxy(self._broker_positions_snapshot)
            else:
                return dictproxy(self._broker_positions)
        else:
            if self._snapshot:
                return dictproxy(self._strategy_positions_snapshot)
            else:
                return dictproxy(self._strategy_positions)

    def link_context(self):
        pass

