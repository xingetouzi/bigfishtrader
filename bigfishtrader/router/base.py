# encoding=utf-8
from bigfishtrader.core import HandlerCompose


class AbstractRouter(HandlerCompose):
    """
    Router 的基类 定义了Router需要对外暴露的接口
    """
    def on_cancel(self, event):
        """
        处理CancelEvent
        :param event:
        :return:
        """
        raise NotImplementedError("Should implement on_cancel")

    def on_order(self, event, kwargs=None):
        """
        处理OrderEvent
        :param event:
        :param kwargs:
        :return:
        """
        raise NotImplementedError("Should implement on_order")

    def on_bar(self, bar_event, kwargs=None):
        """
        处理BarEvent
        :param bar_event:
        :param kwargs:
        :return:
        """
        raise NotImplementedError("Should implement on_bar")

    def get_orders(self):
        """
        被用户调用，返回未成交订单
        :return:
        """
        raise NotImplementedError("Should implement get_orders()")