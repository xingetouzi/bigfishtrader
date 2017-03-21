from fxdayu.context import ContextMixin
from fxdayu.engine.handler import HandlerCompose


class SelectorHandler(HandlerCompose, ContextMixin):
    def __init__(self, engine, context, environment, data, selector_admin, execute_admin):
        super(SelectorHandler, self).__init__(engine)
        ContextMixin.__init__(self, context, environment, data)
        self.selector_admin = selector_admin
        self.execute_admin = execute_admin
        self.configure = {}


