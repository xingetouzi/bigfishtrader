from fxdayu.context import ContextMixin
from fxdayu.engine.handler import HandlerCompose, Handler
from fxdayu.event import EVENTS
from fxdayu.utils.api_support import api_method

from .factory import OrderGroupFactory


class OrderGroupHandler(HandlerCompose, ContextMixin):
    def __init__(self, engine):
        super(OrderGroupHandler, self).__init__(engine)
        ContextMixin.__init__(self)
        self._valid_group_id = 0
        self._groups = {}
        self._order_group_map = {}
        self._handlers["on_execution"] = Handler(self.on_execution, EVENTS.EXECUTION, topic=".", priority=0)
        self._handlers["on_cancel"] = Handler(self.on_cancel, EVENTS.CANCEL, topic=".", priority=0)
        self._handlers["on_modify"] = Handler(self.on_execution, EVENTS.MODIFY, topic=".", priority=0)

    @property
    def next_group_id(self):
        self._valid_group_id += 1
        return self._valid_group_id

    @next_group_id.setter
    def next_group_id(self, value):
        self._valid_group_id = max(value, self._valid_group_id)

    def on_execution(self, execution, kwargs=None):
        pass

    def on_cancel(self, execution, kwargs=None):
        pass

    @api_method
    def create_order_group(self, meta=None, group_id=None):
        if group_id is None or group_id in self._groups:
            group_id = self.next_group_id
        else:
            self.next_group_id = group_id
        self._groups[group_id] = OrderGroupFactory.create_group(meta)
        return group_id

    @api_method
    def bind_order_group(self, orders, group_id):
        if group_id in self._groups:
            for order in orders:
                self._groups[group_id].orders.add(order)
                if order not in self._order_group_map:
                    self._order_group_map[order] = set()
                self._order_group_map[order].add(group_id)
                # TODO warning or exception

    @api_method
    def unbind_order_group(self, orders, group_id):
        if group_id in self._groups:
            for order in orders:
                self._groups[group_id].orders.remove(order)
                if order in self._order_group_map:
                    self._order_group_map[order].remove(group_id)
                if not self._order_group_map[order]:
                    del self._order_group_map

    @api_method
    def remove_order_group(self, group_id):
        self._groups.pop(group_id, None)

    def link_context(self):
        self.environment["create_order_group"] = self.create_order_group
        self.environment["bind_order_group"] = self.bind_order_group
        self.environment["unbind_order_group"] = self.unbind_order_group
        self.environment["remove_order_group"] = self.remove_order_group
