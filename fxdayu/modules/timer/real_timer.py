# encoding:utf-8
from fxdayu.context import ContextMixin
from fxdayu.event import TimeEvent
from fxdayu.utils.api_support import api_method
from fxdayu.engine.handler import HandlerCompose
from datetime import datetime


class RealTimer(HandlerCompose, ContextMixin):
    def __init__(self, engine):
        super(RealTimer, self).__init__(engine)
        ContextMixin.__init__(self)

        print(self.data)
        self.data.subscribe('tick')
        self.data.listen(self.put_time)

    def put_time(self, time):
        try:
            time = datetime.strptime(time, "%Y-%m-%d %H:%M:%S.%f")
            self.engine.put(TimeEvent(time))
        except Exception as e:
            print(e)

    def link_context(self):
        pass
