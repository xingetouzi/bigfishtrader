from collections import OrderedDict


class BaseData(object):
    __slots__ = []

    def to_dict(self, ordered=False):
        """

        Args:
            ordered: whether to use OrderedDict

        Returns:
            dict | OrderedDict : represent the data with dict
        """
        if ordered:
            return OrderedDict([(attr, getattr(self, attr)) for attr in self.__slots__])
        else:
            return {attr: getattr(self, attr) for attr in self.__slots__}