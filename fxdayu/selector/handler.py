from fxdayu.context import ContextMixin
from fxdayu.engine.handler import HandlerCompose, Handler
from fxdayu.selector.admin import SelectorAdmin, ExecutorAdmin
from fxdayu.event import EVENTS


class SelectorHandler(HandlerCompose, ContextMixin):
    def __init__(self, engine, context, environment, data):
        super(SelectorHandler, self).__init__(engine)
        ContextMixin.__init__(self, context, environment, data)
        self._handlers['on_time'] = Handler(self.initialize, EVENTS.TIME, 'bar.open')
        self.selectors = []
        self.executors = []
        self.sa = None
        self.ea = None
        self.initialized = False

    def link_context(self):
        pass

    def initialize(self, event, kwargs=None):
        if not self.initialized:
            if self.sa is None:
                self.sa = SelectorAdmin(*self.selectors)
            if self.ea is None:
                self.ea = ExecutorAdmin(*self.executors)
            self.initialized = True

        self._handlers['on_time'].unregister(self.engine)
        self.engine.register(self.on_time, EVENTS.TIME, 'bar.close')

    def on_time(self, event, kwargs=None):
        self.sa.on_time(event.time, self.context, self.data)
        self.ea.on_time(event.time, self.context, self.data, self.environment)
