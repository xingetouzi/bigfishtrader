from fxdayu.engine.handler import HandlerCompose, Handler
from fxdayu.event import EVENTS
import logging


class LogRecorder(HandlerCompose):
    def __init__(self, logger=""):
        super(LogRecorder, self).__init__()
        if isinstance(logger, logging.Logger):
            self._logger = logger
        else:
            self._logger = logging.getLogger(logger)
        self._count = 0
        self._handlers["on_tick_begin"] = Handler(self.on_tick_begin, EVENTS.TICK, topic="", priority=200)
        self._handlers["on_tick_end"] = Handler(self.on_tick_end, EVENTS.TICK, topic=".", priority=-200)
        self._handlers["on_order_begin"] = Handler(self.on_order_begin, EVENTS.ORDER, topic="", priority=200)
        self._handlers["on_order_end"] = Handler(self.on_order_end, EVENTS.ORDER, topic=".", priority=-200)
        self._handlers["on_fill"] = Handler(self.on_fill, EVENTS.EXECUTION, topic="", priority=100)

    def on_tick_begin(self, event, kwarg=None):
        """

        Args:
            event(fxdayu.event.TickEvent): TickEvent
            kwarg(dct): dict for sharing data

        Returns:

        """
        self._logger.info("Get ticker, timestamp=%s" % event.time.isoformat())

    def on_tick_end(self, event, kwarg=None):
        self._logger.info("Finish handle ticker")

    def on_order_begin(self, event, kwargs=None):
        self._count += 1
        event.order_id = self._count
        self._logger.info("Order <Ref: %s> has been generated" % event.order_id)

    def on_order_end(self, event, kwarg=None):
        """

        Args:
            event(fxdayu.event.OrderEvent):
            kwarg(dct):

        Returns:

        """

        self._logger.info("Order <Ref: %s> has been sent" % event.order_id)

    def on_fill(self, event, kwarg=None):
        """

        Args:
            event(fxdayu.event.ExecutionEvent):
            kwarg(dct):

        Returns:

        """
        fill = event.data
        self._logger.info("Order <ID: %s> has been filled at %s" % (fill.order_ext_id, fill.time.isoformat()))
