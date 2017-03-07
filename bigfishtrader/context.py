# encoding:utf-8
from functools import wraps
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
        self._handlers['on_schedule'] = Handler(
            self.on_time, EVENTS.SCHEDULE, '', 100
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

    def time_schedule(self, func, condition, priority=0, ahead=False, topic=''):
        def schedule(event, kwargs=None):
            func(self, self.data)
        self.data.time_schedule(topic, ahead, condition)

        self.engine.register(schedule, EVENTS.SCHEDULE, topic, priority)

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

    def send_order(self, *args, **kwargs):
        return self.portfolio.send_order(*args, **kwargs)

    def set_commission(self, *args, **kwargs):
        self.router.set_commission(*args, **kwargs)

    def set_slippage(self, *args, **kwargs):
        self.router.set_slippage(*args, **kwargs)
