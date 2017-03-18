# encoding:utf-8
from fxdayu.engine.handler import HandlerCompose


class Admin(HandlerCompose):

    def __init__(self, context, environment, data, engine):
        super(Admin, self).__init__(engine)
        self.context = context
        self.environment = environment
        self.data = data