# encoding:utf-8
from functools import wraps
from weakref import proxy
from fxdayu.engine.handler import HandlerCompose, Handler
from fxdayu.event import *


class Context(HandlerCompose):
    """
    全局变量, 可以通过context调用所有模块
    """

    def __init__(self, engine):
        super(Context, self).__init__(engine)
        self._current_time = None
        self._handlers['on_time'] = Handler(
            self.on_time, EVENTS.TIME, 'bar.open', 200
        )
        self.dct = {}

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


class ContextMixin(object):
    def __init__(self, use_proxy=False):
        self.context = None
        self.environment = None
        self.data = None
        self.__use_proxy = use_proxy

    def init(self):
        # TODO 和initializedMixin做统一
        self.link_context()

    def set_context(self, context):
        if self.__use_proxy:
            self.context = proxy(context)
        else:
            self.context = context

    def set_environment(self, environment):
        if self.__use_proxy:
            self.environment = proxy(environment)
        else:
            self.environment = environment

    def set_data(self, data):
        if self.__use_proxy:
            self.data = proxy(data)
        else:
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
