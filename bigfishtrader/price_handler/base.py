from abc import abstractmethod


class AbstractPriceHandler(object):

    def next_stream(self):
        raise NotImplementedError("Should implement next_stream()")

    def get_instance(self):
        raise NotImplementedError("Should implement get_instance()")

    def get_last_time(self):
        raise NotImplementedError("Should implement get_last_time()")