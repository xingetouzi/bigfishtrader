from abc import abstractmethod


class AbstractPriceHandler(object):

    @abstractmethod
    def next_stream(self):
        raise NotImplementedError("Should implement next_stream()")

    @abstractmethod
    def get_instance(self):
        raise NotImplementedError("Should implement get_instance()")

    @abstractmethod
    def get_last_time(self):
        raise NotImplementedError("Should implement get_last_time()")