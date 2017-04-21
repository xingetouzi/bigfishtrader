# encoding:utf-8


class TimeRule(object):
    def __init__(self, tag=None, **rules):
        self.rules = rules
        self.tag = tag

    def __hash__(self):
        return hash(self.tag)

    def __eq__(self, other):
        if isinstance(other, TimeRule):
            return self.tag == other.tag
        else:
            return False

    def match(self, time):
        for key, value in self.rules.items():
            v = getattr(time, key)
            if not callable(v):
                if v != value:
                    return False
            else:
                if v() != value:
                    return False
        return True


class Selector(object):

    __name__ = 'selector'

    def __init__(self, rule=None, priority=0):
        """

        :param rule(TimeRule): 时间规则
        :param priority(int): 优先级, 小的先执行
        :return:
        """
        self.name = None
        self.priority = priority
        self.rule = rule if rule else TimeRule()

    def __lt__(self, other):
        return self.priority < other.priority

    def __gt__(self, other):
        return self.priority > other.priority

    def __str__(self):
        return self.__name__

    def execute(self, pool, context, data):
        """
        执行选股逻辑

        :param pool: 可选股票池
        :param data: 获取市场数据的对象
        :return:
        """
        raise NotImplementedError("Should implement function execute()")

    def start(self, pool, context, data):
        """
        在一个选股周期开始时被调用

        :param context:
        :param data:
        :return:
        """
        pass

    def end(self, pool, context, data):
        """
        在一个选股周期结束时被调用

        :param context:
        :param data:
        :return:
        """
        pass


from collections import OrderedDict


def sort_selector(selectors):
    dct = OrderedDict()

    for s in sorted(selectors):
        dct.setdefault(s.rule, []).append(s)

    return dct


class SelectorAdmin(object):
    def __init__(self, *selectors):
        self.selectors = sort_selector(selectors)

    def on_time(self, time, context, data):
        pass


class IntersectionAdmin(SelectorAdmin):
    def on_time(self, time, context, data):
        for rule, selectors in self.selectors.items():
            if rule.match(time):
                pool = data.can_trade()
                selectors[0].start(pool, context, data)
                for selector in selectors:
                    pool = selector.execute(pool, context, data)
                selectors[0].end(pool, context, data)
                context.selector_pool = pool


class UnionAdmin(SelectorAdmin):
    def on_time(self, time, context, data):
        for rule, selectors in self.selectors.items():
            if rule.match(time):
                pool = data.can_trade()
                result = []
                selectors[0].start(pool, context, data)
                for selector in selectors:
                    result.extend(filter(lambda x: x not in result, selector.execute(pool, context, data)))
                selectors[0].end(pool, context, data)
                context.selector_pool = result


def selector_wrapper(**k):
    def wrapper(cls):
        from fxdayu.engine.handler import HandlerCompose, Handler
        from fxdayu.event import EVENTS
        from fxdayu.context import ContextMixin

        class SelectorHandler(HandlerCompose, ContextMixin, cls):
            def __init__(self, engine, context, environment, data, *args, **kwargs):
                super(SelectorHandler, self).__init__(engine)
                ContextMixin.__init__(self)
                self.set_context(context)
                self.set_environment(environment)
                self.set_data(data)
                cls.__init__(self, *args, **kwargs)
                self._handlers['on_time'] = Handler(self.on_time, EVENTS.TIME, **k)
                context.selector_pool = []

            def on_time(self, event, kwargs=None):
                cls.on_time(self, event.time, self.context, self.data)

            def link_context(self):
                pass

        return SelectorHandler

    return wrapper