# encoding:utf-8

from dictproxyhack import dictproxy
from bigfishtrader.event import EVENTS


class Handler(object):
    """
    事件处理函数对象基类，在调用事件处理函数注册方法时会先生成该对象传入底事件
    引擎的注册方法。

    Attributes:
        func(function): 事件处理函数，在某一个topic列表中相同的函数只能注册一次。
        stream(EVENTS): 事件(工作流)类型。
        topic(str): 需要注册到哪一个topic列表上,默认为'.'，即整个工作流最后。
        priority(int): 在topic列表中的优先级，越大表示越靠前，
            优先级相同的加入时间早的靠前。默认优先级为0
    """
    __slots__ = ["func", "stream", "topic", "priority"]

    def __init__(self, func, stream, topic=".", priority=0):
        """
        初始化事件处理函数对象

        Args:
            func(function): 事件处理函数。
            stream(EVENTS): 工作流类型。
            topic(str): topic,默认为".",即放在整个工作流的最后。
            priority(int): 优先级，默认为0。

        Returns:
            None
        """
        self.func = func
        self.stream = stream
        self.topic = topic
        self.priority = priority

    def register(self, engine):
        """
        将事件处理函数对象注册到事件驱动引擎engine上

        Args:
            engine(bigfishtrader.engine.core.Engine): 所注册的事件驱动引擎。

        Returns:
            None
        """
        engine.register(self.func, stream=self.stream, topic=self.topic, priority=self.priority)

    def unregister(self, engine):
        """
        取消事件处理函数对象在事件驱动引擎engine上的注册

        Args:
            engine(bigfishtrader.engine.core.Engine): 所取消注册的事件驱动引擎。

        Returns:
            None
        """
        engine.unregister(self.func, stream=self.stream, topic=self.topic)


class HandlerCompose(object):
    """
    事件处理组件对象，由一系列相关的事件处理函数组成，共同完成一项特定功能，
    其register和unregister函数控制了内部所有的事件处理函数的注册和反注册，
    从而控制了组件自身的活动周期。

    Attributes:
        handlers(dict): 字典，按便于识别的名字储存了组件内部所包含的所有
            :class:`Handler` 对象
    """
    def __init__(self):
        self._handlers = {}

    @property
    def handlers(self):
        return dictproxy(self._handlers)

    def register(self, engine):
        """
        将组件内部的所有事件处理函数对象注册到事件驱动引擎engine上

        Args:
            engine(bigfishtrader.engine.core.Engine): 所注册的事件驱动引擎。

        Returns:
            None
        """
        for handler in self._handlers.values():
            handler.register(engine)

    def unregister(self, engine):
        """
        取消组件内部的所有事件处理函数对象在事件驱动引擎engine上的注册

        Args:
            engine(bigfishtrader.engine.core.Engine): 所取消注册的事件驱动引擎。

        Returns:
            None
        """
        for handler in self._handlers.values():
            handler.unregister(engine)


class BigFishTrader(object):
    def __init__(self, event_queue, engine, price_handler, portfolio_handler, order_handler, trade_handler):
        self.event_queue = event_queue
        self.engine = engine
        self.price_handler = price_handler
        self.portfolio_handler = portfolio_handler
        self.order_handler = order_handler
        self.portfolio = portfolio_handler.portfolio
        self.trade_handler = trade_handler
        if self.order_handler:
            self.order_handler.register(self.engine)
        if self.price_handler:
            self.price_handler.register(self.engine)
        if self.portfolio_handler:
            self.portfolio_handler.register(self.engine)
        if self.trade_handler:
            self.trade_handler.register(self.engine)
        self.engine.register(self.on_tick, stream=EVENTS.TICK, topic=".", priority=0)

    def run(self):
        self.engine.start()
        self.price_handler.run()
        self.engine.join()
        self.engine.stop()

    def stop(self):
        self.engine.stop()

    def on_tick(self, event, kwargs):
        pass
