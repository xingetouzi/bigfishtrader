# encoding:utf-8


class Executor(object):

    __name__ = 'executor'

    def __init__(self, weight=1):
        """

        :return:
        """
        self.weight = weight

    def __str__(self):
        return self.__name__

    def execute(self, pool, context, data):
        """

        :param pool:
        :param data:
        :return:
        """
        raise NotImplementedError("Should implement function execute()")

    def start(self, pool, context, data):
        """

        :param context:
        :param data:
        :param environment:
        :return:
        """
        pass

    def end(self, pool, context, data):
        """

        :param context:
        :param data:
        :param environment:
        :return:
        """
        pass


class ExecutorAdmin(object):

    def __init__(self, *executors):
        self.executors = executors

    def on_time(self, context, data, environment, pool):
        pass

    def send_order(self, context, data, environment, target):
        for code, pct in target.items():
            environment['order_target_percent'](code, pct)


class EqualWeightAdmin(ExecutorAdmin):

    def __init__(self, *executors):
        super(EqualWeightAdmin, self).__init__(*executors)
        self.weight = 1/len(executors)

    def on_time(self, context, data, environment, pool):
        target = {}
        self.executors[0].start(pool, context, data)
        for executor in self.executors:
            for code, pct in executor.execute(pool, context, data).items():
                target[code] = target.get(code, 0) + pct*self.weight
        self.executors[-1].end(pool, context, data)
        self.send_order(context, data, environment, target)


def executor_wrapper(**k):
    def wrapper(cls):
        from fxdayu.engine.handler import HandlerCompose, Handler
        from fxdayu.context import ContextMixin
        from fxdayu.event import EVENTS

        class ExecutorHandler(HandlerCompose, ContextMixin, cls):
            def __init__(self, engine, context, environment, data, *args, **kwargs):
                super(ExecutorHandler, self).__init__(engine)
                ContextMixin.__init__(self, context, environment, data)
                cls.__init__(self, *args, **kwargs)
                self._handlers['on_time'] = Handler(self.on_time, EVENTS.TIME, **k)

            def on_time(self, event, kwargs=None):
                cls.on_time(self, self.context, self.data, self.environment, self.context.selector_pool)

            def link_context(self):
                pass

        return ExecutorHandler
    return wrapper