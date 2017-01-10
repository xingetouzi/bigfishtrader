from bigfishtrader.core import HandlerCompose


class AbstractPriceHandler(HandlerCompose):
    def __init__(self):
        super(AbstractPriceHandler, self).__init__()
        self._is_running = False

    @property
    def is_running(self):
        return self._is_running

    def run(self):
        if self._is_running:
            return
        self._is_running = True
        while self._is_running:
            self.next_stream()

    def stop(self):
        if not self._is_running:
            return
        self._is_running = False

    def next_stream(self):
        raise NotImplementedError("Should implement next_stream()")

    def get_instance(self):
        raise NotImplementedError("Should implement get_instance()")

    def get_last_time(self):
        raise NotImplementedError("Should implement get_last_time()")
