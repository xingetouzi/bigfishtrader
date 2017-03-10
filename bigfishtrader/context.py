# encoding:utf-8
from functools import wraps
from weakref import proxy
from bigfishtrader.engine.handler import HandlerCompose, Handler
from bigfishtrader.event import *


class Context(HandlerCompose):
    """
    全局变量, 可以通过context调用所有模块
    """

    def __init__(self):
        super(Context, self).__init__()
        self._current_time = None
        self._handlers['on_time'] = Handler(
            self.on_time, EVENTS.TIME, '', 100
        )

    @property
    def current_time(self):
        """
        返回当前时间, 该时间表示当前引擎所在的时间
        :return: datetime
        """
        return self._current_time

    def on_time(self, event, kwargs=None):
        self._current_time = event.time

    def link(self, **kwargs):
        kwargs.pop('context', None)
        for name, model in kwargs.items():
            self.__setattr__(name, model)

        return self

    def time_schedule(self, func, condition, **kwargs):
        def schedule(event, kwargs=None):
            if condition(event.time):
                func(self, self.data)

        self.engine.register(schedule, EVENTS.TIME, **kwargs)

    @staticmethod
    def time_rules(**kwargs):
        def function(time):
            for key, value in kwargs.items():
                v = getattr(time, key)
                if not callable(v):
                    if v != value:
                        return False
                else:
                    if v() != value:
                        return False

            return True

        return function

    @property
    def send_open(self):
        return self.portfolio.send_open

    @property
    def send_close(self):
        return self.portfolio.send_close

    def set_commission(self, buy_cost=None, sell_cost=None, unit='value', min_cost=0, calculate_function=None):
        """
        佣金设置
        :param buy_cost: 买入(开仓)佣金
        :param sell_cost: 卖出(平仓)佣金
        :param unit:
            'value' : commission = price * quantity * (buy_cost or sell_cost)
            'share' : commission = quantity * (buy_cost or sell_cost)
        :param calculate_function:
            可自定义佣金计算方法，以order和price作为输入参数，返回佣金值
            sample:
            def calculation(order, price):
                return price * 0.0001
        :return:
        """
        exchange = self.router
        if not exchange:
            return
        if buy_cost and sell_cost and unit:
            if unit == 'value':

                @wraps(exchange.calculate_commission)
                def calculate_commission(order, price):
                    return max(
                        abs(order.orderQty) * price * (buy_cost if order.action == ACTION.OPEN.value else sell_cost),
                        min_cost
                    )

                exchange.calculate_commission = calculate_commission
            elif unit == 'share':

                @wraps(exchange.calculate_commission)
                def calculate_commission(order, price):
                    return max(
                        abs(order.quantity) * (buy_cost if order.action == ACTION.OPEN.value else sell_cost),
                        min_cost
                    )

                exchange.calculate_commission = calculate_commission

        if calculate_function:
            exchange.calculate_commission = wraps(exchange.calculate_commission)(calculate_function)

    def set_slippage(self, value=0, unit='pct', function=None):
        """
        滑点设置
        :param value: 滑点值
        :param unit:
            'pct': slippage = price * value
            'value': slippage = value
        :param function:
            可自定义滑点计算方法，以order和price作为输入参数，返回滑点值
            sample:
            def calculation(order, price):
                if order.quantity > 0:
                    return price * 0.0001
                else:
                    return -price * 0.0001
        :return:
        """
        exchange = self.router
        if exchange:
            if value and unit:
                if unit == 'pct':
                    setattr(
                        exchange, 'calculate_slippage',
                        lambda order, price: value * price if (order.quantity > 0 and order.action) or
                                                              (order.quantity < 0 and order.action == 0)
                        else -value * price
                    )
                elif unit == 'value':
                    setattr(
                        exchange, 'calculate_slippage',
                        lambda order, price: value if (order.quantity > 0 and order.action) or
                                                      (order.quantity < 0 and order.action == 0)
                        else -value
                    )
            elif function:
                setattr(exchange, 'calculate_slippage', function)


class ContextMixin(object):
    def __init__(self, context, environment, data=None, use_proxy=False):
        if use_proxy:
            self.context = proxy(context)
            self.environment = proxy(environment)
            if self.data:
                self.data = proxy(data)
        else:
            self.context = context
            self.environment = environment
            self.data = data

    def link_context(self):
        raise NotImplementedError


class InitializeMixin(object):
    def __init__(self):
        self._initialized = False

    @property
    def initialized(self):
        return self._initialized

    def _finish_initialize(self):
        self._initialized = True

    def _reset_initialize(self):
        self._initialized = False

if __name__ == '__main__':
    pass
