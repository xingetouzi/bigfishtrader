import logging
from threading import Thread

try:
    from Queue import Empty
except ImportError:
    from queue import Empty
from bigfishtrader.engine.stream import StreamManager, StreamEnd
from bigfishtrader.event import EVENTS


class Engine(object):
    def __init__(self, event_queue):
        self.event_queue = event_queue
        self._stream_manager = StreamManager()
        self._running = False
        self._thread = None
        self.register(self._stop, EVENTS.EXIT, topic=".", priority=0)

    def run(self):
        self._running = True
        while self._running:
            try:
                event = self.event_queue.get(timeout=0)
                kwargs = {}
                for handle in self._stream_manager.get_iter(event.type, event.topic):
                    handle(event, kwargs)
            except StreamEnd:
                pass
            except Empty:
                pass
            except Exception as e:
                logging.exception(e)

    def start(self):
        self._thread = Thread(target=self.run)
        self._thread.start()

    def join(self):
        self._thread.join()

    def _stop(self, event, kwargs):
        self._running = False

    def stop(self):
        if not self._running:
            return
        self._running = False
        if self._thread:
            self._thread.join()
            self._thread = None

    def register(self, handler, stream, topic=".", priority=0):
        self._stream_manager.register_handler(handler, stream, topic, priority)

    def unregister(self, handler, stream, topic="."):
        self._stream_manager.unregister_handler(handler, stream, topic)