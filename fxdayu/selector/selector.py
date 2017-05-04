# encoding:utf-8


class TimeRule(object):
    def __init__(self, tag):
        self.tag = tag

    def __hash__(self):
        return hash(self.tag)

    def __eq__(self, other):
        if isinstance(other, SimpleRule):
            return self.tag == other.tag
        else:
            return False

    def match(self, time):
        return True


class SimpleRule(TimeRule):
    def __init__(self, tag=None, **rules):
        super(SimpleRule, self).__init__(tag)
        self.rules = rules

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


class CustomRule(TimeRule):
    def __init__(self, tag=None, func=lambda t: True):
        super(CustomRule, self).__init__(tag)
        self.match = func


class Selector(object):

    __name__ = 'selector'

    frequency = None

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

