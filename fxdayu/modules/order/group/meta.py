__all__ = ["OrderGroupStyle", "OCOGroup", "OTOGroup"]


class OrderGroupMeta(object):
    __slots__ = []


class OCOGroupMeta(object):
    __slots__ = ["orders"]

    def __init__(self, order):
        return


class OTOGroupMeta(object):
    __slots__ = ["master", "slaves"]

