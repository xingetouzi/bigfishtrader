# encoding:utf-8

import logging
from threading import Thread

try:
    from Queue import Empty
except ImportError:
    from queue import Empty
from bigfishtrader.engine.stream import StreamManager, StreamEnd
from bigfishtrader.event import EVENTS

__all__ = ["Engine"]


class Engine(object):
    """
    事件驱动引擎对象，负责管理事件处理的工作流、事件处理函数的注册，启动后开始按照
    工作流开始处理外部输入的事件

    Attributes:
        event_queue(Queue): 事件队列，推荐使用优先级队列PriorityQueue。
        is_running(bool): 引擎是否在运行的标记。
        _stream_manager(StreamManager): 工作流管理器对象。
        _thread(Thread): 工作线程
    """

    def __init__(self, event_queue):
        self.event_queue = event_queue
        self._stream_manager = StreamManager()
        self._is_running = False
        self._thread = None
        self.register(self._stop, EVENTS.EXIT, topic=".", priority=0)

    @property
    def is_running(self):
        return self._is_running

    def run(self):
        """
        事件驱动引擎的工作逻辑，一般运行在单独的线程中。

        Returns:
            None
        """
        self._is_running = True
        while self._is_running:
            try:
                event = self.event_queue.get(timeout=0)
                kwargs = {}
                for handle in self._stream_manager.get_iter(event.type, event.topic):
                    handle(event, kwargs)
            except StreamEnd:
                pass
            except Empty:
                pass
            except Exception as e:
                logging.exception(e)

    def start(self):
        """
        在单独的工作线程中启动事件驱动引擎。若事件引擎已启动，直接返回。

        Returns:
            None
        """
        if self._is_running:
            return
        self._thread = Thread(target=self.run)
        self._thread.start()

    def join(self):
        """
        等待工作线程结束。

        Returns:
            None
        """
        self._thread.join()

    def _stop(self, event, kwargs):
        """
        负责监听EVENTS.EXIT事件，接受该事件时停止事件引擎。

        Args:
            event(bigfishtrader.event.ExitEvent): EVENTS.EXIT 事件
            kwargs(dict):共享数据字典

        Returns:
            None
        """
        self._is_running = False

    def stop(self):
        """
        停止工作线程，结束事件驱动引擎的运行。若事件引擎已停止，直接返回。

        Returns:
            None
        """
        if not self._is_running:
            return
        self._is_running = False
        if self._thread:
            self._thread.join()
            self._thread = None

    def register(self, handler, stream, topic=".", priority=0):
        """
        在引擎上注册事件处理函数

        Args:
            handler(function): 事件处理函数函数体。
            stream(EVENTS): 事件(工作流)类型。
            topic(str): 需要注册到哪一个topic列表上,默认为'.'，即整个工作流最后。
            priority(int): 在topic列表中的优先级，越大表示越靠前，
                优先级相同的加入时间早的靠前。默认优先级为0

        Returns:
            None
        """
        self._stream_manager.register_handler(handler, stream, topic, priority)

    def unregister(self, handler, stream, topic="."):
        """
        取消引擎上事件处理函数的注册

        Args:
            handler(function): 事件处理函数函数体。
            stream(EVENTS): 事件(工作流)类型。
            topic(str): 需要取消在哪一个topic列表上的注册,默认为'.'。

        Returns:
            None
        """
        self._stream_manager.unregister_handler(handler, stream, topic)
