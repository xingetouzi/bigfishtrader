# encoding=utf-8

from fxdayu.engine.handler import HandlerCompose


class AbstractRouter(HandlerCompose):
    """
    Router 的基类 定义了Router需要对外暴露的接口
    """

    def on_cancel(self, event, kwargs=None):
        """
        处理CancelEvent

        Args:
            event (bigfishtrade.event.CancelEvent): 撤单事件
            kwargs (dict): 共享数据字典,存储工作流中需要传递的数据，如需传递数据，
                请将其key和value含义写入文档中。

        Returns:
            None

        Raises:
            NotImplementedError: Should implement on_cancel
        """
        raise NotImplementedError("Should implement on_cancel")

    def on_order(self, event, kwargs=None):
        """
        处理OrderEvent

        Args:
            event (bigfishtrader.event.OrderEvent): 订单事件
            kwargs (dict): 共享数据字典,存储工作流中需要传递的数据，如需传递数据，
                请将其key和value含义写入文档中。

        Returns:
            None

        Raises:
            NotImplementedError: Should implement on_order
        """
        raise NotImplementedError("Should implement on_order")