from enum import Enum
from collections import Iterable


class GroupStyleType(Enum):
    NONE = 0
    OCO = 1
    OTO = 2


class OrderGroup(object):
    STYLE = GroupStyleType.NONE

    def __init__(self, meta, trigger_order, cancel_order, unregister):
        self._id = meta.identity
        self.orders = set()
        self.trigger_order = trigger_order  # Inversion of Control
        self.cancel_order = cancel_order
        self.unregister = unregister
        self.style = self.STYLE

    def on_execution(self, execution):
        raise NotImplementedError

    def on_cancel(self, cancel):
        self.remove(cancel.clOrdID)

    def add(self, order):
        if isinstance(order, str) or not isinstance(order, Iterable):
            self.orders.add(order)
        else:
            self.orders.update(order)

    def remove(self, order):
        if isinstance(order, str) or not isinstance(order, Iterable):
            self.orders.remove(order)
        else:
            self.orders.difference_update(order)

    def finish(self):
        self.unregister(self._id)  # release order group


class OCOOrderGroup(OrderGroup):
    STYLE = GroupStyleType.OCO

    def __init__(self, meta, trigger_order, cancel_order, unregister):
        """
        Args:
            meta(meta.OCOGroupMeta)
        """
        super(OCOOrderGroup, self).__init__(meta, trigger_order, cancel_order, unregister)
        self.add(meta.orders)

    def on_execution(self, order):
        for ordID in self.orders:
            if ordID != order.clOrdID:
                self.cancel_order(ordID)
            self.unregister(self)


class OTOOrderGroup(OrderGroup):
    STYLE = GroupStyleType.OTO

    def __init__(self, meta, trigger_order, cancel_order, unregister):
        super(OTOOrderGroup, self).__init__(meta, trigger_order, cancel_order, unregister)
        self._master = None
        self.master = meta.master
        self.add(meta.slaves)

    @property
    def master(self):
        return self.master

    @master.setter
    def master(self, master):
        if self._master:
            self.remove(self._master)
        self._master = master
        self.orders.add(master)

    def on_execution(self, order):
        if order.clOrdID == self.master:
            for ordID in self.orders.difference({self.master}):
                self.trigger_order(ordID)
            self.finish()
        else:
            self.remove(order)

    def on_cancel(self, order):
        if order == self.master:
            for ordID in self.orders.difference({self.master}):
                self.cancel_order(ordID)
            self.finish()
        else:
            self.remove(order)
