try:
    from Queue import Queue
except ImportError:
    from queue import Queue
from bigfishtrader.quotation.base import AbstractPriceHandler


class TimeEventHandler(AbstractPriceHandler):
    def __init__(self, event_queue):
        super(TimeEventHandler, self).__init__()
        self._event_queue = event_queue
        self._q = Queue()

    def get_ticker(self):
        pass

    def get_last_time(self):
        pass

    def get_instance(self, ticker):
        pass

    def next_stream(self):
        events = self._q.get()
        for event in events:
            self._event_queue.put(event)
