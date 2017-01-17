from bigfishtrader.engine.handler import HandlerCompose, Handler
from bigfishtrader.event import EVENTS


class Context(HandlerCompose):
    def __init__(self):
        super(Context, self).__init__()
        self._current_time = None
        self._handlers['on_time'] = Handler(
            self.on_time, EVENTS.TIME, '', 100
        )

    @property
    def current_time(self):
        return self._current_time

    def on_time(self, event, kwargs=None):
        self._current_time = event.time