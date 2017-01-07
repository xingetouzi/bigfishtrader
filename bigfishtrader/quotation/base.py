from bigfishtrader.core import HandlerCompose


class AbstractPriceHandler(HandlerCompose):
    def next_stream(self):
        raise NotImplementedError("Should implement next_stream()")

    def get_instance(self):
        raise NotImplementedError("Should implement get_instance()")

    def get_last_time(self):
        raise NotImplementedError("Should implement get_last_time()")
