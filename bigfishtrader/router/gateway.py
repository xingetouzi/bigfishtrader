# encoding:utf-8
from bigfishtrader.engine.handler import HandlerCompose, Handler
from bigfishtrader.event import EVENTS


class Gateway(HandlerCompose):
    """
    信息交换网关
    """

    def __init__(self, event_engine, name):
        """

        Args:
            event_engine(bigfishtrader.engine.core.EventEngine):
            name:

        Returns:

        """
        super(Gateway, self).__init__()
        self.event_engine = event_engine
        self._handlers = {
            "on_order": Handler(self.send_order, EVENTS.ORDER, topic="", priority=0)
        }
        self.name = name

    def on_tick(self, event):
        """市场深度行情推送"""
        self.event_engine.event_queue.put(event)

    def on_execution(self, event):
        """订单执行回报"""
        pass

    def on_order(self, event):
        """订单回报"""
        pass

    def on_position(self, event):
        """
        仓位信息回报

        Args:
            event:
        """
        pass

    def on_account(self, event):
        """
        账户信息回报

        Args:
            event:
        """
        pass

    def on_error(self, event):
        """
        错误回报

        Args:
            event:
        """
        pass

    def on_log(self, event):
        pass

    def on_contract(self, event):
        pass

    def send_order(self, event):
        pass

    def cancel_order(self, event):
        pass

    def qry_account(self):
        pass

    def qry_position(self):
        pass

    def close(self):
        pass