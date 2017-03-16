import bisect
from itertools import chain
from collections import deque

__all__ = ["PriorityList", "StreamManager", "StreamEnd"]


class StreamEnd(Exception):
    """
    In a handler, you can stop a event stream just by raise StreamEnd.
    """
    pass


class PriorityList(object):
    """
    List of which items sorted by its priority
    and inserting timestamp if have same priority,
    maintained by bisect (binary search)
    """

    def __init__(self):
        self._p = []
        self._v = []
        self._i = {}

    def put(self, priority, value):
        """
        Insert a item of given value and priority to the PriorityList

        Args:
            priority(int): item's priority
            value: item's value

        Returns:
            None
        """
        if value not in self._i:
            pos = bisect.bisect(self._p, -priority)
            self._p.insert(pos, -priority)
            self._v.insert(pos, value)
            self._i[value] = pos

    def remove(self, value):
        """
        Remove item of given value from the PriorityList

        Args:
            value: item's value

        Returns:
            None
        """
        if value in self._i:
            pos = self._i[value]
            self._v.pop(pos)
            self._p.pop(pos)
            del self._i[value]

    def __contains__(self, value):
        """
        Check whether value is in this PriorityList

        Args:
            value: item's value

        Returns:
            bool: whether item of given value is in the PriorityList
        """
        return value in self._i

    def __iter__(self):
        """
        Get iterator of this PriorityList

        Returns:
            iter(iterator): the PriorityList's iterator
        """
        return self._v.__iter__()

    def __len__(self):
        """
        Get the length of this PriorityList

        Returns:
            len(int): the PriorityList's length
        """
        return self._v.__len__()


class StreamManager(object):
    """
    Manager all event stream
    """

    def __init__(self):
        self._streams = {}

    def get_iter(self, stream, topic):
        """
        Search for handlers chain in given event stream under given topic

        Args:
            stream(fxdayu.event.EVENTS): type of event stream
            topic(str): topic of event
        Returns:
            chain: chain of the handlers
        """
        if stream in self._streams:
            handlers = self._streams[stream]
            head = deque([handlers[""]]) if "" in handlers else deque()
            tail = deque([handlers["."]]) if "." in handlers else deque()
            if topic:
                paths = topic.split(".")
                path = ""
                for s in paths:
                    path += s
                    path_ = path + "."
                    if path in handlers:
                        head.append(handlers[path])
                    if path_ in handlers:
                        tail.appendleft(handlers[path_])
                    path += "."
            return chain(*chain(head, tail))
        else:
            return chain()

    def register_stream(self, stream):
        """
        Register given new event stream

        Args:
            stream(fxdayu.event.EVENTS):

        Returns:
            None
        """
        if stream not in self._streams:
            self._streams[stream] = {}

    def unregister_stream(self, stream):
        """
        Remove given event stream

        Args:
            stream(fxdayu.event.EVENTS): event stream

        Returns:
            None
        """
        if stream in self._streams:
            del self._streams[stream]

    def register_handler(self, handler, stream, topic=".", priority=0):
        """
        Register a handler in given event stream under given topic with
        given priority.

        Args:
            handler(fxdayu.engine.handler.Handler): event handler
            stream(fxdayu.event.EVENTS): type of event stream
            topic(str): topic of event
            priority(int): priority of handler

        Returns:
            None
        """
        self.register_stream(stream)
        handlers = self._streams[stream]
        if topic not in handlers:
            handlers[topic] = PriorityList()
        handlers[topic].put(priority, handler)

    def unregister_handler(self, handler, stream, topic="."):
        """
        Unregister a handler in given event stream under given topic.

        Args:
            handler(fxdayu.engine.handler.Handler): event handler
            stream(fxdayu.event.EVENTS): type of event stream
            topic(str): topic of event

        Returns:
            None
        """
        if stream not in self._streams:
            return
        handlers = self._streams[stream]
        handlers[topic].remove(handler)
        if len(handlers[topic]) == 0:
            del handlers[topic]
        if len(handlers) == 0:
            self.unregister_stream(stream)

    def _show_flows(self, stream):
        pass

    def show_flows(self, stream):
        if stream is None:
            for stream in self._streams.keys():
                self._show_flows(stream)
        else:
            self._show_flows(stream)
