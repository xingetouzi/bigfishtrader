from bigfishtrader.engine.handler import HandlerCompose, Handler
from bigfishtrader.event import EVENTS
import logging


class LogRecorder(HandlerCompose):
    def __init__(self, logger=""):
        super(LogRecorder, self).__init__()
        if isinstance(logger, logging.Logger):
            self._logger = logger
        else:
            self._logger = logging.getLogger(logger)
        self._handlers["on_tick_begin"] = Handler(self.on_tick_begin, EVENTS.TICK, topic="", priority=200)
        self._handlers["on_tick_end"] = Handler(self.on_tick_end, EVENTS.TICK, topic=".", priority=-200)
        self._handlers["on_order"] = Handler(self.on_order, EVENTS.ORDER, topic=".", priority=-200)
        self._handlers["on_fill"] = Handler(self.on_fill, EVENTS.FILL, topic="", priority=100)

    def on_tick_begin(self, event, kwarg=None):
        """

        Args:
            event(bigfishtrader.event.TickEvent): TickEvent
            kwarg(dct): dict for sharing data

        Returns:

        """
        self._logger.info("Get ticker, timestamp=%s" % event.time.isoformat())

    def on_tick_end(self, event, kwarg=None):
        self._logger.info("Finish handle ticker")

    def on_order(self, event, kwarg=None):
        """

        Args:
            event(bigfishtrader.event.OrderEvent):
            kwarg(dct):

        Returns:

        """

        self._logger.info("Order <Ref: %s> has been send at %s" % (event.local_id, event.time.isoformat()))

    def on_fill(self, event, kwarg=None):
        """

        Args:
            event(bigfishtrader.event.FillEvent):
            kwarg(dct):

        Returns:

        """
        self._logger.info("Order <ID: %s> has been filled at %s" % (event.exchange_id, event.time.isoformat()))
